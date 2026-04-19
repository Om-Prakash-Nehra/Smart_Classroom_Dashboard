from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import RoomStatus
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check for offline devices'
    
    def handle(self, *args, **options):
        # Mark devices as offline if no data for 3 minutes
        offline_threshold = timezone.now() - timedelta(minutes=3)
        
        offline_devices = RoomStatus.objects.filter(
            last_data_received__lt=offline_threshold,
            is_online=True
        )
        
        count = offline_devices.update(is_online=False)
        
        if count > 0:
            self.stdout.write(f"Marked {count} device(s) as offline")