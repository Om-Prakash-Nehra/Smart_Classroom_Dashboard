from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('admin/', views.admin_panel, name='admin_panel'),
    path('api/threshold/', views.get_threshold_api, name='get_threshold'),
]