import time
import re
import ipaddress
import hashlib
import socket
import zlib

from functools import wraps

from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.utils.module_loading import import_string


_PERIODS = {
    's': 1,
    'm': 60,
    'h': 60 * 60,
    'd': 24 * 60 * 60,
}

rate_re = re.compile(r'(\d+)/(\d*)([smhd])?')

# Extend the expiration time by a few seconds to avoid misses.
EXPIRATION_FUDGE = 5


def _get_ip(request):
    ip_meta = getattr(settings, 'RATELIMIT_IP_META_KEY', None)
    if not ip_meta:
        ip = request.META['REMOTE_ADDR']
        if not ip:
            raise ImproperlyConfigured(
                'IP address in REMOTE_ADDR is empty. This can happen when '
                'using a reverse proxy and connecting to the app server with '
                'Unix sockets. See the documentation for '
                'RATELIMIT_IP_META_KEY: https://bit.ly/3iIpy2x')
    elif callable(ip_meta):
        ip = ip_meta(request)
    elif isinstance(ip_meta, str) and '.' in ip_meta:
        ip_meta_fn = import_string(ip_meta)
        ip = ip_meta_fn(request)
    elif ip_meta in request.META:
        ip = request.META[ip_meta]
    else:
        raise ImproperlyConfigured(
            'Could not get IP address from "%s"' % ip_meta)

    if ':' in ip:
        # IPv6
        mask = getattr(settings, 'RATELIMIT_IPV6_MASK', 64)
    else:
        # IPv4
        mask = getattr(settings, 'RATELIMIT_IPV4_MASK', 32)

    network = ipaddress.ip_network(f'{ip}/{mask}', strict=False)

    return str(network.network_address)


def user_or_ip(request):
    if request.user.is_authenticated:
        return str(request.user.pk)
    return _get_ip(request)


def _get_window(value, period):
    """
    Given a value, and time period return when the end of the current time
    period for rate evaluation is.
    """
    ts = int(time.time())
    if period == 1:
        return ts
    if not isinstance(value, bytes):
        value = value.encode('utf-8')
    # This logic determines either the last or current end of a time period.
    # Subtracting (ts % period) gives us the a consistent edge from the epoch.
    # We use (zlib.crc32(value) % period) to add a consistent jitter so that
    # all time periods don't end at the same time.
    w = ts - (ts % period) + (zlib.crc32(value) % period)
    if w < ts:
        return w + period
    return w


def _make_cache_key(window, limit, period, value):
    safe_rate = '%d/%ds' % (limit, period)
    parts = [safe_rate, value, str(window)]

    return hashlib.md5(''.join(parts).encode('utf-8')).hexdigest()


def _split_rate(rate):
    if isinstance(rate, tuple):
        return rate
    count, multi, period = rate_re.match(rate).groups()
    count = int(count)
    if not period:
        period = 's'
    seconds = _PERIODS[period.lower()]
    if multi:
        seconds = seconds * int(multi)
    return count, seconds


def check_bad_requests(request, rate, methods):
    if isinstance(methods, str):
        methods = [methods]

    limit, period = _split_rate(rate)
    value = user_or_ip(request)
    window = _get_window(value, period)

    cache_name = getattr(settings, 'RATELIMIT_CACHE', 'default')
    cache = caches[cache_name]
    cache_prefix = getattr(settings, 'RATELIMIT_BAD_REQUEST_CACHE_PREFIX', 'bad_request_rl:')
    cache_key = cache_prefix + _make_cache_key(window, limit, period, value)

    try:
        cache.add(cache_key, 0, period + EXPIRATION_FUDGE)
        # Since we will use the cache_key later in the request, it's better to add the key first
    except socket.gaierror:  # for redis
        pass

    if request.method in methods:
        count = cache.get(cache_key, 0)
    else:
        count = False
        try:
            # python3-memcached will throw a ValueError if the server is
            # unavailable or (somehow) the key doesn't exist. redis, on the
            # other hand, simply returns None.
            cache.incr(cache_key)
        except ValueError:
            pass

    # Getting or setting the count from the cache failed
    if count is False or count is None:
        return {
            'count': 0,
            'limit': 0,
            'should_limit': True,
            'time_left': -1,
        }

    time_left = window - int(time.time())
    return {
        'count': count,
        'limit': limit,
        'should_limit': count > limit,
        'time_left': time_left,
    }


def check_usage(request, rate):

    limit, period = _split_rate(rate)
    value = user_or_ip(request)

    window = _get_window(value, period)

    cache_name = getattr(settings, 'RATELIMIT_CACHE', 'default')
    cache = caches[cache_name]
    cache_prefix = getattr(settings, 'RATELIMIT_REQUEST_CACHE_PREFIX', 'request_rl:')
    cache_key = cache_prefix + _make_cache_key(window, limit, period, value)

    count = None
    try:
        added = cache.add(cache_key, 1, period + EXPIRATION_FUDGE)
    except socket.gaierror:  # for redis
        added = False
    if added:
        count = 1
    else:
        try:
            # python3-memcached will throw a ValueError if the server is
            # unavailable or (somehow) the key doesn't exist. redis, on the
            # other hand, simply returns None.
            count = cache.incr(cache_key)
        except ValueError:
            pass

    # Getting or setting the count from the cache failed
    if count is False or count is None:
        return {
            'count': 0,
            'limit': 0,
            'should_limit': True,
            'time_left': -1,
        }

    time_left = window - int(time.time())
    return {
        'count': count,
        'limit': limit,
        'should_limit': count > limit,
        'time_left': time_left,
    }


def request_ratelimit(rate):
    def decorator(fn):
        @wraps(fn)
        def _wrapped(request, *args, **kw):
            old_limited = getattr(request, 'limited', False)
            if old_limited:
                raise PermissionDenied('Sorry you are blocked!')

            limit_status = check_usage(request, rate)
            if limit_status['should_limit']:
                raise PermissionDenied(f'Sorry you are blocked for {limit_status["time_left"]} seconds!')

            return fn(request, *args, **kw)
        return _wrapped
    return decorator


def bad_request_ratelimit(rate='15/h', methods='GET'):
    def decorator(fn):
        @wraps(fn)
        def _wrapped(request, *args, **kw):
            old_limited = getattr(request, 'limited', False)
            if old_limited:
                raise PermissionDenied('Sorry you are blocked!')

            limit_status = check_bad_requests(request, rate, methods)
            if limit_status['should_limit']:
                raise PermissionDenied(f'Sorry you are blocked for {limit_status["time_left"]} seconds!')

            return fn(request, *args, **kw)
        return _wrapped
    return decorator
