from django.http import JsonResponse
from django.views import View
from .models import Set


class Sum(View):
    def get(self, request):

        try:
            num_a = int(request.GET.get('a'))
            num_b = int(request.GET.get('b'))
        except ValueError:
            raise ValueError("a and b should be provided as Integer values.")
        except TypeError:
            raise ValueError("a and b numbers should be provided.")

        Set.objects.create(num_a=num_a, num_b=num_b)

        return JsonResponse({'result': num_a + num_b})
