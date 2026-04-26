# dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('', views.index, name='dashboard_index'),
    
    # Admin panel
    path('admin/', views.admin_panel, name='admin_panel'),
    
    # API endpoints
    path('api/threshold/', views.get_threshold_api, name='get_threshold'),
    
    # Authentication - using custom views
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
]