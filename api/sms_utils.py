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
    """
    message = f"""🏫 SMART CLASSROOM ALERT

Room: {room_id}
Status: EMPTY for {empty_duration_minutes} minutes
Temperature: {temperature}°C
AC: {'ON' if ac_status else 'OFF'}
Lights: {'ON' if lights_status else 'OFF'}

⚠️ Energy waste detected! Please check the classroom.

- Smart Classroom System"""
    
    # Get phone number from settings
    phone_number = getattr(settings, 'ALERT_PHONE_NUMBER', None)
    
    if not phone_number:
        logger.error("ALERT_PHONE_NUMBER not configured in settings")
        return False, "No phone number configured"
    
    return send_sms(phone_number, message)