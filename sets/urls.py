from django.urls import path
from . import views

urlpatterns = [
    path('sum/', views.Sum.as_view()),
    path('history/', views.History.as_view()),
    path('total/', views.Total.as_view()),
]
