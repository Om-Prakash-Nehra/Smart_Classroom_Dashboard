# dashboard/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.utils import timezone
from api.models import RoomStatus, Alert, SystemConfig
import logging

logger = logging.getLogger(__name__)

def index(request):
    """Main dashboard view"""
    try:
        room = RoomStatus.objects.get(room_id='CLASSROOM_101')
    except RoomStatus.DoesNotExist:
        room = None
    
    # Get recent alerts
    recent_alerts = Alert.objects.all().order_by('-timestamp')[:10]
    
    # Get current threshold
    threshold_minutes = int(SystemConfig.get('alert_threshold_minutes', '8'))
    
    context = {
        'room': room,
        'recent_alerts': recent_alerts,
        'threshold_minutes': threshold_minutes,
        'now': timezone.now(),
        'user': request.user if request.user.is_authenticated else None,
    }
    
    return render(request, 'dashboard/index.html', context)

def custom_login(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/dashboard/')
        else:
            return render(request, 'registration/login.html', {'form': form, 'error': 'Invalid credentials'})
    
    form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def custom_logout(request):
    """Custom logout view"""
    logout(request)
    return redirect('/dashboard/login/')

def admin_panel(request):
    """Admin panel for settings"""
    # Check authentication
    if not request.user.is_authenticated:
        return redirect('/dashboard/login/')
    
    if request.method == 'POST':
        threshold = request.POST.get('threshold_minutes')
        if threshold:
            SystemConfig.set('alert_threshold_minutes', threshold, 'Alert threshold in minutes')
            return render(request, 'dashboard/admin.html', {
                'threshold_minutes': int(threshold),
                'success': True,
                'user': request.user,
            })
    
    threshold_minutes = int(SystemConfig.get('alert_threshold_minutes', '8'))
    
    context = {
        'threshold_minutes': threshold_minutes,
        'user': request.user,
    }
    
    return render(request, 'dashboard/admin.html', context)

def get_threshold_api(request):
    """API endpoint to get current threshold"""
    threshold_minutes = int(SystemConfig.get('alert_threshold_minutes', '8'))
    return JsonResponse({'threshold_minutes': threshold_minutes})