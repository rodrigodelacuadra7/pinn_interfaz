from django.urls import path
from predictor import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/predict', views.api_predict, name='api_predict'),
    path('api/view/3d', views.api_view_3d, name='api_view_3d'),
    path('api/view/planta', views.api_view_planta, name='api_view_planta'),
]
