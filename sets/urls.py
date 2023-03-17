from django.urls import path
from . import views

urlpatterns = [
    path('sum/', views.Sum.as_view())
]
