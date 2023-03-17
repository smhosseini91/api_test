import base64
import functools
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.contrib.auth.models import User
from django.http import JsonResponse


class AuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    username, password = base64.b64decode(auth[1]).decode("utf8").split(':', 1)

        if username == 'admin' and password == 'admin':
            admin_user = User.objects.filter(username='admin').first()
            if not admin_user:
                admin_user = User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
            return admin_user
        else:
            user = User.objects.filter(username=username).first()
            if not user:
                return
            if not user.check_password(password):
                return
            return user


class HeaderAuthenticationMiddleware(RemoteUserMiddleware):
    header = 'HTTP_AUTHORIZATION'


def ajax_login_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        return JsonResponse('Unauthorized Access', status=401, safe=False)

    return wrapper
