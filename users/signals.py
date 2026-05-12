# booking/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from .models import Booking
from .sms import sms_manager
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Booking)
def handle_booking_sms(sender, instance, created, **kwargs):
    """Handle SMS notifications after booking save"""
    
    # Only proceed if SMS is enabled
    if not settings.SMS_CONFIG['ENABLED']:
        return
    
    if created:
        # New booking - send confirmation
        try:
            booking_data = {
                'full_name': instance.full_name,
                'booking_number': instance.booking_number,
                'mobile_number': instance.mobile_number,
                'service_name': instance.service.name if instance.service else instance.custom_service_name,
                'garage_name': instance.garage.name,
                'garage_city': instance.garage.city,
                'garage_phone': instance.garage.phone,
                'scheduled_date_formatted': instance.scheduled_date.strftime('%Y-%m-%d %H:%M'),
                'total_price': str(instance.total_price),
            }
            
            sms_result = sms_manager.send_booking_confirmation(booking_data)
            
            if sms_result.get('success'):
                instance.mark_sms_sent('confirmation', 'sent')
                logger.info(f"Auto-sent confirmation SMS for booking #{instance.booking_number}")
            else:
                instance.log_sms_error(sms_result.get('error', 'Unknown error'))
                logger.error(f"Failed to auto-send SMS for booking #{instance.booking_number}")
                
        except Exception as e:
            logger.error(f"Error in booking SMS signal: {str(e)}")
            instance.log_sms_error(str(e))


@receiver(pre_save, sender=Booking)
def track_status_change(sender, instance, **kwargs):
    """Track status changes before save"""
    if instance.pk:
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Booking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Booking)
def handle_status_change_sms(sender, instance, created, **kwargs):
    """Send SMS when status changes"""
    
    if created or not hasattr(instance, '_old_status'):
        return
    
    # Check if status changed
    if instance._old_status != instance.status:
        # Prepare SMS data
        booking_data = {
            'booking_number': instance.booking_number,
            'mobile_number': instance.mobile_number,
            'status_display': instance.get_status_display(),
            'service_name': instance.service.name if instance.service else instance.custom_service_name,
            'scheduled_date_formatted': instance.scheduled_date.strftime('%Y-%m-%d %H:%M'),
        }
        
        # Send status update
        sms_result = sms_manager.send_status_update(booking_data)
        
        if sms_result.get('success'):
            logger.info(f"Sent status update SMS for booking #{instance.booking_number}")
        else:
            logger.error(f"Failed to send status update SMS: {sms_result.get('error')}")