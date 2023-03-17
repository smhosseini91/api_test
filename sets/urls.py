from django.urls import path
from . import views

urlpatterns = [
    path('sum/', views.get_sum),
    path('history/', views.get_history),
    path('total/', views.get_total),
]
