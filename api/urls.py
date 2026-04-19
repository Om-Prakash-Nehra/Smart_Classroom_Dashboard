from django.urls import path
from . import views

urlpatterns = [
    path('update/', views.update_sensor_data, name='update_sensor'),
    path('alert/', views.alert_endpoint, name='alert'),
    path('status/<str:room_id>/', views.get_room_status, name='room_status'),
    path('alerts/', views.get_alerts, name='alerts'),
    path('set-threshold/', views.set_alert_threshold, name='set_threshold'),
    path('latest/', views.get_latest_readings, name='latest_readings'), 
    path('online-status/', views.get_online_status, name='online_status'),
    path('test-sms/', views.test_sms, name='test_sms'),  # ADD THIS LINE
]