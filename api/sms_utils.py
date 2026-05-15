# api/sms_utils.py
from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_sms(to_phone_number, message_body):
    """
    Send an SMS using Twilio
    Returns: (success: bool, result: str)
    """
    try:
        # Check if Twilio credentials are configured
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.error("Twilio credentials not configured in settings")
            return False, "Twilio credentials missing"
        
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            to=to_phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            body=message_body
        )
        
        logger.info(f"SMS sent successfully! SID: {message.sid}")
        return True, f"Message sent! SID: {message.sid}"
        
    except Exception as e:
        logger.error(f"Failed to send SMS: {str(e)}")
        return False, f"Error: {str(e)}"

def send_empty_room_alert(room_id, empty_duration_minutes, temperature, ac_status, lights_status):
    """
    Send formatted alert for empty room
    Simple format: Room : 101 Ac on (room empty)
    """
    # Build the "things that are on" part
    devices_on = []
    if ac_status:
        devices_on.append("Ac on")
    if lights_status:
        devices_on.append("Lights on")
    
    # Create the message
    if devices_on:
        devices_text = " " + " ".join(devices_on)
        message = f"Room : {room_id}{devices_text} (room empty)"
    else:
        message = f"Room : {room_id} (room empty)"
    
    logger.info(f"Message length: {len(message)} chars, Content: {message}")
    
    # Get phone number from settings
    phone_number = getattr(settings, 'ALERT_PHONE_NUMBER', None)
    
    if not phone_number:
        logger.error("ALERT_PHONE_NUMBER not configured in settings")
        return False, "No phone number configured"
    
    return send_sms(phone_number, message)

# api/sms_utils.py - ADD THESE FUNCTIONS to your existing file

def send_device_offline_alert(room_id, offline_duration_minutes, last_data_time=None):
    """
    Send SMS alert when a device goes offline (short version)
    Format: "Alert: Room 101 went offline"
    """
    # Short and simple message
    message = f"Alert: Room {room_id} went offline"
    
    logger.info(f"Offline alert: {message}")
    
    # Get phone number from settings
    phone_number = getattr(settings, 'ALERT_PHONE_NUMBER', None)
    
    if not phone_number:
        logger.error("ALERT_PHONE_NUMBER not configured in settings")
        return False, "No phone number configured"
    
    return send_sms(phone_number, message)


def send_device_back_online_alert(room_id, offline_duration_minutes):
    """
    Send SMS alert when an offline device comes back online (short version)
    Format: "Alert: Room 101 is back online"
    """
    # Short and simple message
    message = f"Alert: Room {room_id} is back online"
    
    logger.info(f"Back online alert: {message}")
    
    # Get phone number from settings
    phone_number = getattr(settings, 'ALERT_PHONE_NUMBER', None)
    
    if not phone_number:
        logger.error("ALERT_PHONE_NUMBER not configured in settings")
        return False, "No phone number configured"
    
    return send_sms(phone_number, message)


def check_and_send_offline_alerts():
    """
    Check all rooms for offline devices and send alerts if needed.
    """
    from .models import RoomStatus
    from django.utils import timezone
    
    # Configuration
    OFFLINE_ALERT_THRESHOLD_MINUTES = 5  # Send alert after 5 minutes offline
    
    all_rooms = RoomStatus.objects.all()
    current_time = timezone.now()
    
    results = []
    
    for room in all_rooms:
        if not room.last_data_received:
            continue
        
        # Calculate offline duration
        time_since_last_data = current_time - room.last_data_received
        offline_minutes = time_since_last_data.total_seconds() / 60
        
        is_currently_offline = offline_minutes >= OFFLINE_ALERT_THRESHOLD_MINUTES
        
        # Send offline alert if device just went offline
        if is_currently_offline and room.is_online:
            success, result = send_device_offline_alert(
                room_id=room.room_id,
                offline_duration_minutes=int(offline_minutes)
            )
            
            if success:
                room.is_online = False
                room.save()
                results.append(f"✅ Offline alert sent for {room.room_id}")
                print(f"📱 Offline alert sent for {room.room_id}")
        
        # Send back-online alert if device just came back
        elif not is_currently_offline and not room.is_online:
            # Calculate how long it was offline
            offline_duration = int(offline_minutes)
            
            success, result = send_device_back_online_alert(
                room_id=room.room_id,
                offline_duration_minutes=offline_duration
            )
            
            if success:
                room.is_online = True
                room.save()
                results.append(f"✅ Back-online alert sent for {room.room_id}")
                print(f"📱 Back-online alert sent for {room.room_id}")
    
    return results
