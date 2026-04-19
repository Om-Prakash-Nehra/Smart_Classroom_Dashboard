# api/models.py
from django.db import models
from django.utils import timezone

class SensorData(models.Model):
    """Stores incoming sensor data from ESP32"""
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Accelerometer
    accel_x = models.FloatField(default=0)
    accel_y = models.FloatField(default=0)
    accel_z = models.FloatField(default=0)
    vibration = models.FloatField(default=0)
    motion_detected = models.BooleanField(default=False)
    
    # Temperature & Pressure
    temperature = models.FloatField(default=0)
    pressure = models.FloatField(default=0)
    
    # Light
    lux = models.FloatField(default=0)
    light_on = models.BooleanField(default=False)
    
    # Sound
    sound_level = models.FloatField(default=0)
    
    # Distance
    distance = models.IntegerField(default=999)
    
    # System
    room_id = models.CharField(max_length=50, default="CLASSROOM_101")
    occupancy = models.CharField(max_length=20, default="unknown")
    wifi_rssi = models.IntegerField(default=0)
    ac_state = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['occupancy']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.occupancy}"

class RoomStatus(models.Model):
    """Tracks current room status"""
    room_id = models.CharField(max_length=50, unique=True)
    is_occupied = models.BooleanField(default=False)
    last_occupied_time = models.DateTimeField(null=True, blank=True)
    last_empty_time = models.DateTimeField(null=True, blank=True)
    empty_since = models.DateTimeField(null=True, blank=True)
    alert_sent = models.BooleanField(default=False)
    alert_sent_time = models.DateTimeField(null=True, blank=True)
    last_data_received = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    
    # Current readings
    current_temperature = models.FloatField(default=0)
    current_lux = models.FloatField(default=0)
    current_sound = models.FloatField(default=0)
    current_distance = models.IntegerField(default=999)
    ac_on = models.BooleanField(default=False)
    lights_on = models.BooleanField(default=False)
    motion_detected = models.BooleanField(default=False)
    current_vibration = models.FloatField(default=0)  # ADD THIS FIELD
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.room_id} - {'Occupied' if self.is_occupied else 'Empty'}"

class Alert(models.Model):
    """Stores alert history"""
    ALERT_TYPES = [
        ('ac', 'AC ON in empty room'),
        ('lights', 'Lights ON in empty room'),
        ('both', 'Both AC and Lights ON'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    room_id = models.CharField(max_length=50)
    temperature = models.FloatField()
    lux = models.FloatField()
    sound_level = models.FloatField()
    motion_detected = models.BooleanField()
    sent_via = models.CharField(max_length=20, default='web')
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.timestamp} - {self.get_alert_type_display()}"

class SystemConfig(models.Model):
    """System configuration (admin editable)"""
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.key} = {self.value}"
    
    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set(cls, key, value, description=""):
        obj, created = cls.objects.update_or_create(
            key=key,
            defaults={'value': str(value), 'description': description}
        )
        return obj