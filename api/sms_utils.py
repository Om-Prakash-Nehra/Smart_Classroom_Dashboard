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