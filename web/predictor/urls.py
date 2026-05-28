from django.urls import path
from predictor import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/predict', views.api_predict, name='api_predict'),
]
