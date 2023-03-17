from django.db.models import Sum as DbSum
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

        created_set = Set.objects.create(num_a=num_a, num_b=num_b, sum=num_a + num_b)

        return JsonResponse({'result': created_set.sum})


class History(View):
    def get(self, request):

        sets = Set.objects.all()

        return JsonResponse([set_item.to_dict() for set_item in sets], safe=False)


class Total(View):
    def get(self, request):

        total = Set.objects.aggregate(DbSum('sum'))

        return JsonResponse({'total': total['sum__sum']})

