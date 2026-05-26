# mechanics/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ServiceRequest, ServiceRequestUpdate
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ServiceRequest)
def handle_service_request_notifications(sender, instance, created, **kwargs):
    """Handle all notifications for service requests"""
    
    if created:
        logger.info(f"🎉 New Service Request Created: {instance.get_request_code()}")
        
        # Create update record
        ServiceRequestUpdate.objects.create(
            service_request=instance,
            update_type='created',
            notes='Service request created'
        )
        
        # Send to customer
        instance.send_email_notification('created', recipient_type='customer')
        
        # Send to ALL GARAGES
        garage_count = len(instance.get_all_garage_emails())
        instance.send_email_to_all_garages('new_request')
        
        # Send SMS
        if instance.phone:
            instance.send_sms_notification('created')
            
        logger.info(f"📧 Notifications sent to customer and {garage_count} garages")
        
    else:
        try:
            old = ServiceRequest.objects.get(pk=instance.pk)
            
            # Status change
            if old.status != instance.status:
                logger.info(f"📊 Status Changed: {instance.get_request_code()} - {old.status} → {instance.status}")
                
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='status_change',
                    old_value=old.status,
                    new_value=instance.status,
                    notes=f'Status changed from {old.get_status_display()} to {instance.get_status_display()}'
                )
                
                # Notify customer
                instance.send_email_notification('status_update', {
                    'old_status': old.get_status_display(),
                    'new_status': instance.get_status_display()
                }, recipient_type='customer')
                
                # If garage responded
                if instance.status in ['received', 'in_progress'] and instance.garage_name:
                    instance.send_email_notification('garage_response', {
                        'garage_name': instance.garage_name,
                        'garage_phone': instance.garage_phone,
                        'garage_email': instance.garage_email,
                        'new_status': instance.get_status_display()
                    }, recipient_type='customer')
                
                # SMS
                if instance.phone:
                    instance.send_sms_notification('status_update')
                    
        except ServiceRequest.DoesNotExist:
            pass