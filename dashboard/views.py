from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from api.models import RoomStatus, Alert, SystemConfig
from django.utils import timezone
from datetime import timedelta

def index(request):
    """Main dashboard view"""
    try:
        room = RoomStatus.objects.get(room_id='CLASSROOM_101')
    except RoomStatus.DoesNotExist:
        room = None
    
    # Get recent alerts
    recent_alerts = Alert.objects.all()[:10]
    
    # Get current threshold
    threshold_minutes = int(SystemConfig.get('alert_threshold_minutes', '8'))
    
    context = {
        'room': room,
        'recent_alerts': recent_alerts,
        'threshold_minutes': threshold_minutes,
        'now': timezone.now(),
    }
    
    return render(request, 'dashboard/index.html', context)

@login_required(login_url='/admin/login/')
def admin_panel(request):
    """Admin panel for settings"""
    if request.method == 'POST':
        threshold = request.POST.get('threshold_minutes')
        if threshold:
            SystemConfig.set('alert_threshold_minutes', threshold, 'Alert threshold in minutes')
            return render(request, 'dashboard/admin.html', {
                'threshold_minutes': int(threshold),
                'success': True
            })
    
    threshold_minutes = int(SystemConfig.get('alert_threshold_minutes', '8'))
    
    context = {
        'threshold_minutes': threshold_minutes,
    }
    
    return render(request, 'dashboard/admin.html', context)

@login_required(login_url='/admin/login/')
def get_threshold_api(request):
    """API endpoint to get current threshold"""
    threshold_minutes = int(SystemConfig.get('alert_threshold_minutes', '8'))
    return JsonResponse({'threshold_minutes': threshold_minutes})