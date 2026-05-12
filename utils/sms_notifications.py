# utils/sms_notifications.py
"""
SMS Notification Service - Mirrors email notifications
"""
import logging
from typing import Dict, Any
from django.utils import timezone
from .africastalking_sms import africastalking_sms

logger = logging.getLogger(__name__)

class SMSNotificationService:
    """Send SMS notifications for all actions"""
    
    @staticmethod
    def format_message(action_type: str, context: Dict[str, Any]) -> str:
        """Format SMS message based on action type"""
        
        templates = {
            # Customer Request Actions
            'request_created': """
✅ SERVICE REQUEST CREATED
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Date: {preferred_date}
Time: {preferred_time}
Vehicle: {vehicle_details}
Location: {location}

Your request has been submitted. You'll receive offers soon.
QuickFix Auto
            """,
            
            'request_updated': """
📝 REQUEST UPDATED
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Status: {status}
Date: {preferred_date}
Time: {preferred_time}

Your request has been updated successfully.
QuickFix Auto
            """,
            
            'request_cancelled': """
❌ REQUEST CANCELLED
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Status: CANCELLED

This request has been cancelled as requested.
QuickFix Auto
            """,
            
            'status_changed': """
🔄 STATUS UPDATE
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Previous: {old_status}
New: {new_status}

Track your request in the app.
QuickFix Auto
            """,
            
            # Quote Actions
            'offer_received': """
💰 NEW OFFER RECEIVED
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Workshop: {workshop_name}
Price: TZS {price:,.2f}
Duration: {duration} hours
Notes: {notes}

Login to view and accept this offer.
QuickFix Auto
            """,
            
            'offer_accepted': """
✅ OFFER ACCEPTED
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Workshop: {workshop_name}
Price: TZS {price:,.2f}

Appointment will be created shortly.
QuickFix Auto
            """,
            
            # Appointment Actions
            'appointment_confirmed': """
✅ APPOINTMENT CONFIRMED
━━━━━━━━━━━━━━━━━━━━━━
Appointment: {appointment_code}
Request: {request_code}
Service: {service_name}
Workshop: {workshop_name}
Date: {appointment_date}
Time: {appointment_time}
Price: TZS {price:,.2f}
Contact: {workshop_phone}
Location: {location}

Thank you for choosing QuickFix!
            """,
            
            'appointment_reminder': """
🔔 APPOINTMENT REMINDER
━━━━━━━━━━━━━━━━━━━━━━
Appointment: {appointment_code}
Service: {service_name}
Workshop: {workshop_name}
Time: {appointment_time} TOMORROW
Contact: {workshop_phone}

Please arrive on time.
QuickFix Auto
            """,
            
            'appointment_cancelled': """
❌ APPOINTMENT CANCELLED
━━━━━━━━━━━━━━━━━━━━━━
Appointment: {appointment_code}
Service: {service_name}
Workshop: {workshop_name}

This appointment has been cancelled.
QuickFix Auto
            """,
            
            'appointment_status_update': """
📋 APPOINTMENT UPDATE
━━━━━━━━━━━━━━━━━━━━━━
Appointment: {appointment_code}
Service: {service_name}
New Status: {status}
Workshop: {workshop_name}
Contact: {workshop_phone}
QuickFix Auto
            """,
            
            # Workshop Notifications
            'workshop_new_request': """
🔧 NEW SERVICE REQUEST
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Customer: {customer_name}
Location: {location}
Urgency: {urgency}
Date: {preferred_date}

Login to submit your offer.
QuickFix Auto
            """,
            
            'workshop_offer_accepted': """
🎉 OFFER ACCEPTED!
━━━━━━━━━━━━━━━━━━━━━━
Request: {request_code}
Service: {service_name}
Customer: {customer_name}
Price: TZS {price:,.2f}
Date: {appointment_date}
Time: {appointment_time}

Contact customer to confirm.
QuickFix Auto
            """,
        }
        
        template = templates.get(action_type, "QuickFix Notification")
        
        try:
            message = template.format(**context)
            # Clean up whitespace
            message = '\n'.join(line.strip() for line in message.strip().split('\n'))
            # Truncate if too long
            if len(message) > 1600:
                message = message[:1597] + "..."
            return message
        except KeyError as e:
            logger.error(f"Missing template key: {e}")
            return f"QuickFix Notification for {context.get('request_code', 'your request')}"
    
    @staticmethod
    def send(phone_number: str, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS notification"""
        if not phone_number:
            logger.warning(f"No phone number for {action_type}")
            return {'success': False, 'error': 'No phone number'}
        
        message = SMSNotificationService.format_message(action_type, context)
        result = africastalking_sms.send_sms(phone_number, message)
        
        if result.get('success'):
            logger.info(f"{action_type} SMS sent")
        else:
            logger.error(f"Failed to send {action_type} SMS")
        
        return result

# Global instance
sms_notifier = SMSNotificationService()