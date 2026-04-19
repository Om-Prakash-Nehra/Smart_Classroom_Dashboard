from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('', include('dashboard.urls')),
    
    # Add login/logout URLs
    path('admin/login/', auth_views.LoginView.as_view(), name='login'),
    path('admin/logout/', auth_views.LogoutView.as_view(), name='logout'),
]