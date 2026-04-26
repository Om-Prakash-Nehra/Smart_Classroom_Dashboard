# api/views.py
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import SensorData, RoomStatus, Alert, SystemConfig
from .sms_utils import send_empty_room_alert, send_sms
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Configuration for offline detection
OFFLINE_THRESHOLD_MINUTES = 3  # Device is considered offline after 3 minutes of no data

@csrf_exempt
def update_sensor_data(request):
    """
    Endpoint to receive sensor data from ESP32
    URL: /api/update/
    """
    if request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            
            print("\n" + "="*50)
            print("📊 RECEIVED SENSOR DATA:")
            print("="*50)
            print(f"Room ID: {data.get('room_id', 'N/A')}")
            print(f"Temperature: {data.get('temperature', 'N/A')}°C")
            print(f"Pressure: {data.get('pressure', 'N/A')} hPa")
            print(f"Occupancy: {data.get('occupancy', 'N/A')}")
            print(f"Sound Level: {data.get('sound_level', 'N/A')}")
            print(f"Distance: {data.get('distance', 'N/A')} cm")
            print(f"Motion Detected: {data.get('motion_detected', 'N/A')}")
            print(f"AC State: {data.get('ac_state', 'N/A')}")
            print(f"Vibration: {data.get('vibration', 'N/A')}")
            print(f"Light ON: {data.get('light_on', 'N/A')}")
            print(f"Lux: {data.get('lux', 'N/A')}")
            print("="*50)
            
            # Save sensor data to database
            sensor_reading = None
            try:
                sensor_reading = SensorData.objects.create(
                    accel_x=data.get('accel_x', 0),
                    accel_y=data.get('accel_y', 0),
                    accel_z=data.get('accel_z', 0),
                    vibration=data.get('vibration', 0),
                    motion_detected=data.get('motion_detected', False),
                    temperature=data.get('temperature', 0),
                    pressure=data.get('pressure', 0),
                    lux=data.get('lux', 0),
                    light_on=data.get('light_on', False),
                    sound_level=data.get('sound_level', 0),
                    distance=data.get('distance', 999),
                    room_id=data.get('room_id', 'CLASSROOM_101'),
                    occupancy=data.get('occupancy', 'unknown'),
                    wifi_rssi=data.get('wifi_rssi', 0),
                    ac_state=data.get('ac_state', False)
                )
                print(f"✓ Saved SensorData (ID: {sensor_reading.id})")
                
                # Update or create RoomStatus
                room_status, created = RoomStatus.objects.update_or_create(
                    room_id=data.get('room_id', 'CLASSROOM_101'),
                    defaults={
                        'is_occupied': data.get('occupancy') == 'occupied',
                        'current_temperature': data.get('temperature', 0),
                        'current_sound': data.get('sound_level', 0),
                        'current_distance': data.get('distance', 999),
                        'current_lux': data.get('lux', 0),
                        'ac_on': data.get('ac_state', False),
                        'lights_on': data.get('light_on', False),
                        'motion_detected': data.get('motion_detected', False),
                        'current_vibration': data.get('vibration', 0),
                        'last_data_received': timezone.now(),
                        'is_online': True,
                        'updated_at': timezone.now()
                    }
                )
                
                # Update occupancy timestamps
                if data.get('occupancy') == 'occupied':
                    if not room_status.is_occupied:
                        room_status.last_occupied_time = timezone.now()
                        room_status.empty_since = None
                        room_status.alert_sent = False  # Reset alert flag when room becomes occupied
                        print("🟢 Room became OCCUPIED - Alert flag reset")
                else:  # Room is empty
                    # Check if this is a transition from occupied to empty
                    if room_status.is_occupied:
                        room_status.last_empty_time = timezone.now()
                        room_status.empty_since = timezone.now()
                        print("🔴 Room became EMPTY - Starting timer")
                    elif not room_status.empty_since:
                        # Room was already empty but no empty_since set
                        room_status.empty_since = timezone.now()
                        print("🔴 Empty since set to now")
                
                room_status.save()
                print(f"✓ Updated RoomStatus for {room_status.room_id} (Online: True)")
                
                # ========== CHECK FOR EMPTY ROOM ALERT ==========
                # Get threshold from SystemConfig
                threshold_minutes = int(SystemConfig.get('alert_threshold_minutes', '5'))
                
                # Check if room is empty and alert not sent recently
                if not room_status.is_occupied and room_status.empty_since and not room_status.alert_sent:
                    empty_duration = timezone.now() - room_status.empty_since
                    minutes_empty = empty_duration.total_seconds() / 60
                    
                    print(f"⏱️ Room empty for {minutes_empty:.1f} minutes (threshold: {threshold_minutes})")
                    
                    if minutes_empty >= threshold_minutes:
                        print("🚨 TRIGGERING EMPTY ROOM ALERT!")
                        
                        # Determine alert type based on what's ON
                        alert_type = None
                        if room_status.ac_on and room_status.lights_on:
                            alert_type = 'both'
                        elif room_status.ac_on:
                            alert_type = 'ac'
                        elif room_status.lights_on:
                            alert_type = 'lights'
                        
                        if alert_type:
                            # Send SMS alert
                            success, result = send_empty_room_alert(
                                room_id=room_status.room_id,
                                empty_duration_minutes=int(minutes_empty),
                                temperature=room_status.current_temperature,
                                ac_status=room_status.ac_on,
                                lights_status=room_status.lights_on
                            )
                            
                            if success:
                                # Mark alert as sent in RoomStatus
                                room_status.alert_sent = True
                                room_status.alert_sent_time = timezone.now()
                                room_status.save()
                                
                                # Create Alert record in database
                                alert = Alert.objects.create(
                                    alert_type=alert_type,
                                    room_id=room_status.room_id,
                                    temperature=room_status.current_temperature,
                                    lux=room_status.current_lux,
                                    sound_level=room_status.current_sound,
                                    motion_detected=room_status.motion_detected,
                                    sent_via='sms'
                                )
                                
                                print(f"✅ Alert created (ID: {alert.id}) and SMS sent successfully!")
                            else:
                                print(f"❌ SMS failed: {result}")
                        else:
                            print("⚠️ Room empty but no devices are ON - no alert needed")
                    else:
                        print(f"⏳ Waiting {threshold_minutes - minutes_empty:.1f} more minutes before alert")
                
                # If room is occupied, make sure alert flag is reset
                elif room_status.is_occupied and room_status.alert_sent:
                    room_status.alert_sent = False
                    room_status.alert_sent_time = None
                    room_status.save()
                    print("🟢 Room occupied - Alert flag reset")
                
            except Exception as db_error:
                print(f"✗ Database error: {db_error}")
                import traceback
                traceback.print_exc()
            
            # Return success response
            return JsonResponse({
                "status": "success",
                "message": "Data received successfully",
                "data_id": sensor_reading.id if sensor_reading else None
            }, status=200)
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON decode error: {e}")
            return JsonResponse({
                "status": "error",
                "error": "Invalid JSON format"
            }, status=400)
            
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    return JsonResponse({
        "status": "error",
        "error": "Method not allowed. Use POST."
    }, status=405)


@csrf_exempt
def alert_endpoint(request):
    """
    Endpoint to receive alerts from ESP32
    URL: /api/alert/
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            print("\n" + "!"*50)
            print("🚨 ALERT RECEIVED:")
            print("!"*50)
            print(f"Alert Type: {data.get('alert_type', 'N/A')}")
            print(f"Room ID: {data.get('room_id', 'N/A')}")
            print(f"Temperature: {data.get('temperature', 'N/A')}°C")
            print(f"Lux: {data.get('lux', 'N/A')}")
            print(f"Sound Level: {data.get('sound_level', 'N/A')}")
            print(f"Motion Detected: {data.get('motion_detected', 'N/A')}")
            print("!"*50)
            
            # Save alert to database
            alert = None
            try:
                alert = Alert.objects.create(
                    alert_type=data.get('alert_type', 'ac'),
                    room_id=data.get('room_id', 'CLASSROOM_101'),
                    temperature=data.get('temperature', 0),
                    lux=data.get('lux', 0),
                    sound_level=data.get('sound_level', 0),
                    motion_detected=data.get('motion_detected', False),
                    sent_via='web'
                )
                print(f"✓ Alert saved (ID: {alert.id})")
                
                # Update RoomStatus to mark alert sent
                RoomStatus.objects.filter(room_id=data.get('room_id', 'CLASSROOM_101')).update(
                    alert_sent=True,
                    alert_sent_time=timezone.now()
                )
                
            except Exception as db_error:
                print(f"✗ Database error: {db_error}")
            
            return JsonResponse({
                "status": "success",
                "message": "Alert received successfully",
                "alert_id": alert.id if alert else None
            }, status=200)
            
        except Exception as e:
            print(f"✗ Alert error: {e}")
            return JsonResponse({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    return JsonResponse({
        "status": "error",
        "error": "Method not allowed. Use POST."
    }, status=405)


def get_room_status(request, room_id):
    """
    Get current status of a room with offline detection
    URL: /api/status/<room_id>/
    """
    if request.method == 'GET':
        try:
            # Get latest room status from database
            room_status = RoomStatus.objects.filter(room_id=room_id).first()
            
            # Get latest sensor data for additional fields
            latest_sensor = SensorData.objects.filter(room_id=room_id).first()
            
            # Calculate online status based on last data received
            is_online = False
            offline_duration_minutes = 0
            last_data_received = None
            
            # Calculate empty duration
            empty_duration_minutes = 0
            empty_since_str = None
            
            if room_status and room_status.last_data_received:
                last_data_received = room_status.last_data_received
                time_since_last_data = timezone.now() - room_status.last_data_received
                is_online = time_since_last_data.total_seconds() < (OFFLINE_THRESHOLD_MINUTES * 60)
                
                if not is_online:
                    offline_duration_minutes = round(time_since_last_data.total_seconds() / 60, 1)
                    
                    # Automatically update the is_online flag in database
                    if room_status.is_online:
                        room_status.is_online = False
                        room_status.save()
                        print(f"📡 Device {room_id} marked as offline (no data for {offline_duration_minutes} minutes)")
            elif room_status:
                # Has room status but no last_data_received (old record)
                room_status.is_online = False
                room_status.save()
            
            # Calculate empty duration if room is empty
            if room_status and not room_status.is_occupied and room_status.empty_since:
                empty_duration = timezone.now() - room_status.empty_since
                empty_duration_minutes = round(empty_duration.total_seconds() / 60, 1)
                empty_since_str = room_status.empty_since.isoformat()
            
            if room_status:
                # If device is offline, return None/null for sensor values
                if is_online:
                    data = {
                        'room_id': room_status.room_id,
                        'is_occupied': room_status.is_occupied,
                        'temperature': room_status.current_temperature,
                        'sound_level': room_status.current_sound,
                        'distance': room_status.current_distance,
                        'lux': room_status.current_lux if room_status.current_lux else (latest_sensor.lux if latest_sensor else 0),
                        'ac_on': room_status.ac_on,
                        'lights_on': room_status.lights_on,
                        'motion_detected': room_status.motion_detected,
                        'current_vibration': room_status.current_vibration if hasattr(room_status, 'current_vibration') else 0,
                        'last_occupied_time': room_status.last_occupied_time,
                        'empty_since': empty_since_str,
                        'empty_duration_minutes': empty_duration_minutes,
                        'alert_sent': room_status.alert_sent,
                        'updated_at': room_status.updated_at,
                        'is_online': True,
                        'last_data_received': last_data_received,
                        'offline_duration_minutes': 0,
                    }
                else:
                    # Device is offline - return null values
                    data = {
                        'room_id': room_status.room_id,
                        'is_occupied': False,
                        'temperature': None,
                        'sound_level': None,
                        'distance': None,
                        'lux': None,
                        'ac_on': False,
                        'lights_on': False,
                        'motion_detected': False,
                        'current_vibration': None,
                        'last_occupied_time': room_status.last_occupied_time,
                        'empty_since': empty_since_str,
                        'empty_duration_minutes': empty_duration_minutes if not room_status.is_occupied else 0,
                        'alert_sent': room_status.alert_sent,
                        'updated_at': room_status.updated_at,
                        'is_online': False,
                        'last_data_received': last_data_received,
                        'offline_duration_minutes': offline_duration_minutes,
                    }
            else:
                # No room status exists - device never connected
                data = {
                    'room_id': room_id,
                    'is_occupied': False,
                    'temperature': None,
                    'sound_level': None,
                    'distance': None,
                    'lux': None,
                    'ac_on': False,
                    'lights_on': False,
                    'motion_detected': False,
                    'current_vibration': None,
                    'last_occupied_time': None,
                    'empty_since': None,
                    'empty_duration_minutes': 0,
                    'alert_sent': False,
                    'updated_at': timezone.now(),
                    'is_online': False,
                    'last_data_received': None,
                    'offline_duration_minutes': 0,
                    'never_connected': True,
                }
            
            return JsonResponse(data, status=200)
            
        except Exception as e:
            print(f"Error in get_room_status: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_alerts(request):
    """
    Get recent alerts for dashboard
    URL: /api/alerts/
    """
    if request.method == 'GET':
        try:
            # Get recent alerts from database
            alerts = Alert.objects.all().order_by('-timestamp')[:50]
            
            data = []
            for alert in alerts:
                data.append({
                    'id': alert.id,
                    'alert_type': alert.alert_type,
                    'alert_display': alert.get_alert_type_display(),
                    'room_id': alert.room_id,
                    'temperature': alert.temperature,
                    'lux': alert.lux,
                    'sound_level': alert.sound_level,
                    'motion_detected': alert.motion_detected,
                    'timestamp': alert.timestamp.isoformat() if alert.timestamp else None,
                    'sent_via': alert.sent_via,
                })
            
            return JsonResponse({'alerts': data, 'count': len(data)}, status=200)
            
        except Exception as e:
            print(f"Error in get_alerts: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def set_alert_threshold(request):
    """
    Set alert thresholds (admin configurable)
    URL: /api/set-threshold/
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            print(f"📝 Threshold updated: {data}")
            
            # Save thresholds to SystemConfig
            for key, value in data.items():
                SystemConfig.set(key, value, f"Alert threshold for {key}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Thresholds updated',
                'thresholds': data
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'GET':
        # Get current thresholds
        thresholds = {
            'temperature_high': SystemConfig.get('temperature_high', '30'),
            'temperature_low': SystemConfig.get('temperature_low', '18'),
            'sound_threshold': SystemConfig.get('sound_threshold', '300'),
            'distance_threshold': SystemConfig.get('distance_threshold', '200'),
            'idle_timeout': SystemConfig.get('idle_timeout', '60000'),
            'offline_threshold_minutes': SystemConfig.get('offline_threshold_minutes', '3'),
            'alert_threshold_minutes': SystemConfig.get('alert_threshold_minutes', '5'),
        }
        return JsonResponse(thresholds, status=200)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_online_status(request):
    """
    Get online status of all devices
    URL: /api/online-status/
    """
    if request.method == 'GET':
        try:
            # Get all room statuses
            all_status = RoomStatus.objects.all()
            
            data = []
            for status in all_status:
                is_online = False
                offline_duration = 0
                
                if status.last_data_received:
                    time_since = timezone.now() - status.last_data_received
                    is_online = time_since.total_seconds() < (OFFLINE_THRESHOLD_MINUTES * 60)
                    if not is_online:
                        offline_duration = round(time_since.total_seconds() / 60, 1)
                
                data.append({
                    'room_id': status.room_id,
                    'is_online': is_online,
                    'last_data_received': status.last_data_received,
                    'offline_duration_minutes': offline_duration,
                    'last_updated': status.updated_at,
                })
            
            return JsonResponse({'devices': data, 'offline_threshold_minutes': OFFLINE_THRESHOLD_MINUTES}, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_latest_readings(request):
    """
    Get latest sensor readings for dashboard
    URL: /api/latest/
    """
    if request.method == 'GET':
        try:
            # Get the latest sensor reading
            latest = SensorData.objects.first()
            
            if latest:
                data = {
                    'timestamp': latest.timestamp,
                    'temperature': latest.temperature,
                    'pressure': latest.pressure,
                    'sound_level': latest.sound_level,
                    'distance': latest.distance,
                    'occupancy': latest.occupancy,
                    'motion_detected': latest.motion_detected,
                    'ac_state': latest.ac_state,
                    'vibration': latest.vibration,
                    'lux': latest.lux,
                    'light_on': latest.light_on,
                }
            else:
                data = {'message': 'No data yet'}
            
            return JsonResponse(data, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def test_sms(request):
    """
    Test endpoint to send test SMS
    URL: /api/test-sms/
    """
    if request.method == 'GET':
        # Return instructions for GET request
        return JsonResponse({
            'info': 'Send POST request to test SMS',
            'example': {
                'method': 'POST',
                'content_type': 'application/json',
                'body': {
                    'phone': 'optional_phone_number',
                    'message': 'Your test message here'
                }
            },
            'default_phone': getattr(settings, 'ALERT_PHONE_NUMBER', 'Not configured'),
            'note': 'Use curl or Postman to test: curl -X POST http://your-server/api/test-sms/ -H "Content-Type: application/json" -d \'{"message": "Hello"}\''
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone', settings.ALERT_PHONE_NUMBER)
            message = data.get('message', 'Test SMS from Smart Classroom System')
            
            success, result = send_sms(phone, message)
            
            return JsonResponse({
                'success': success,
                'message': result,
                'phone_sent_to': phone
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Use POST with JSON body or GET for info'}, status=405)


@csrf_exempt
def create_test_alert(request):
    """
    Endpoint to manually create a test alert
    URL: /api/create-test-alert/
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            room_id = data.get('room_id', 'CLASSROOM_101')
            alert_type = data.get('alert_type', 'ac')
            
            # Create test alert
            alert = Alert.objects.create(
                alert_type=alert_type,
                room_id=room_id,
                temperature=data.get('temperature', 25.5),
                lux=data.get('lux', 300),
                sound_level=data.get('sound_level', 45),
                motion_detected=data.get('motion_detected', False),
                sent_via='test'
            )
            
            return JsonResponse({
                'success': True,
                'alert_id': alert.id,
                'message': f'Test alert created for {room_id}'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Use POST'}, status=405)