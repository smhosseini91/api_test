from django.conf import settings
from django.db.models import Sum as DbSum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from api_test.authentication import ajax_login_required
from api_test.ratelimit import request_ratelimit, bad_request_ratelimit, check_bad_requests

from .models import Set


@csrf_exempt
@request_ratelimit()
@bad_request_ratelimit()
def get_sum(request):
    try:
        num_a = int(request.GET.get('a'))
        num_b = int(request.GET.get('b'))
    except ValueError:
        check_bad_requests(request, settings.BAD_REQUEST_RATE_LIMIT, 'Wrong Parameters')
        return JsonResponse("a and b should be provided as Integer values.", status=400, safe=False)
    except TypeError:
        check_bad_requests(request, settings.BAD_REQUEST_RATE_LIMIT, 'Wrong Parameters')
        return JsonResponse("a and b numbers should be provided.", status=400, safe=False)

    created_set = Set.objects.create(num_a=num_a, num_b=num_b, sum=num_a + num_b)
    return JsonResponse({'result': created_set.sum})


@csrf_exempt
@ajax_login_required
@request_ratelimit()
@bad_request_ratelimit()
def get_history(request):

    sets = Set.objects.all()
    return JsonResponse([set_item.to_dict() for set_item in sets], safe=False)


@csrf_exempt
@ajax_login_required
@request_ratelimit()
@bad_request_ratelimit()
def get_total(request):

    total = Set.objects.aggregate(DbSum('sum'))
    return JsonResponse({'total': total['sum__sum']})

