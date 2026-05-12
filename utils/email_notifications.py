# utils/email_notifications.py
"""
Email Notification Service
"""
import logging
from typing import Dict, Any, Optional
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class EmailNotificationService:
    """Send email notifications for all actions"""
    
    @staticmethod
    def send(action_type: str, recipient_email: str, context: Dict[str, Any]) -> bool:
        """Send email notification"""
        
        subjects = {
            'request_created': f"✅ Service Request Created: {context.get('request_code', '')}",
            'request_updated': f"📝 Request Updated: {context.get('request_code', '')}",
            'request_cancelled': f"❌ Request Cancelled: {context.get('request_code', '')}",
            'status_changed': f"🔄 Status Updated: {context.get('request_code', '')}",
            'offer_received': f"💰 New Offer Received: {context.get('request_code', '')}",
            'offer_accepted': f"✅ Offer Accepted: {context.get('request_code', '')}",
            'appointment_confirmed': f"✅ Appointment Confirmed: {context.get('appointment_code', '')}",
            'appointment_reminder': f"🔔 Appointment Reminder: {context.get('appointment_code', '')}",
            'appointment_cancelled': f"❌ Appointment Cancelled: {context.get('appointment_code', '')}",
            'appointment_status_update': f"📋 Appointment Update: {context.get('appointment_code', '')}",
            'workshop_new_request': f"🔧 New Service Request: {context.get('request_code', '')}",
            'workshop_offer_accepted': f"🎉 Your Offer Was Accepted: {context.get('request_code', '')}",
        }
        
        subject = subjects.get(action_type, f"QuickFix Update: {context.get('request_code', '')}")
        
        # Simple HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{subject}</h2>
                </div>
                <div class="content">
                    <p>Hello {context.get('customer_name', 'Customer')},</p>
                    <p>{context.get('message', 'Your request has been updated.')}</p>
                    
                    {context.get('details', '')}
                    
                    <p>Login to your dashboard for more details.</p>
                </div>
                <div class="footer">
                    <p>QuickFix Auto - Your Trusted Auto Service Partner</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_content)
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Email sent: {action_type} to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

# Global instance
email_notifier = EmailNotificationService()