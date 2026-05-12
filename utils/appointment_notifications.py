# utils/appointment_notifications.py
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta

from .sms_service import africastalking_sms
from registration.models import ServiceAppointment, CustomerRequest, WorkshopQuote, AutoWorkshop

logger = logging.getLogger(__name__)


class AppointmentNotificationService:
    """Service for sending appointment notifications via SMS and Email"""
    
    def __init__(self):
        self.sms_service = africastalking_sms
    
    def _format_message(self, template_name: str, context: Dict[str, Any]) -> str:
        """Format SMS message using template"""
        templates = settings.AFRICAS_TALKING_CONFIG.get('MESSAGE_TEMPLATES', {})
        template = templates.get(template_name, '')
        
        if not template:
            return ""
        
        # Format the message with context
        try:
            message = template.format(**context)
            # Clean up whitespace
            message = '\n'.join(line.strip() for line in message.strip().split('\n'))
            return message
        except KeyError as e:
            logger.error(f"Missing template key: {e}")
            return template
    
    def send_appointment_confirmation(self, appointment: ServiceAppointment) -> Dict[str, Any]:
        """
        Send appointment confirmation notification to customer
        """
        result = {'email_sent': False, 'sms_sent': False}
        
        try:
            # Prepare context for templates
            context = {
                'request_code': appointment.customer_request.request_code,
                'service_name': appointment.appointment_service,
                'workshop_name': appointment.service_workshop.workshop_name,
                'workshop_phone': appointment.service_workshop.workshop_phone,
                'appointment_date': appointment.appointment_date.strftime('%d/%m/%Y'),
                'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
                'price': appointment.agreed_price,
                'location': appointment.appointment_location,
            }
            
            # Send SMS notification
            if appointment.client.phone:
                sms_message = self._format_message('APPOINTMENT_CONFIRMATION', context)
                sms_result = self.sms_service.send_sms(
                    phone_number=appointment.client.phone,
                    message=sms_message,
                    sender_id='QuickFix'
                )
                
                result['sms_sent'] = sms_result.get('success', False)
                if result['sms_sent']:
                    appointment.sms_confirmation_sent = True
                    appointment.sms_confirmation_sent_at = timezone.now()
                    appointment.save(update_fields=['sms_confirmation_sent', 'sms_confirmation_sent_at'])
                    logger.info(f"SMS confirmation sent for appointment {appointment.appointment_code}")
            
            # Send email notification
            email_result = self._send_appointment_email(appointment, context)
            result['email_sent'] = email_result
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send appointment confirmation: {str(e)}")
            return result
    
    def send_appointment_reminder(self, appointment: ServiceAppointment) -> Dict[str, Any]:
        """
        Send appointment reminder notification
        """
        result = {'sms_sent': False}
        
        try:
            if not appointment.client.phone:
                return result
            
            context = {
                'request_code': appointment.customer_request.request_code,
                'service_name': appointment.appointment_service,
                'workshop_name': appointment.service_workshop.workshop_name,
                'workshop_phone': appointment.service_workshop.workshop_phone,
                'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            }
            
            sms_message = self._format_message('APPOINTMENT_REMINDER', context)
            sms_result = self.sms_service.send_sms(
                phone_number=appointment.client.phone,
                message=sms_message,
                sender_id='QuickFix'
            )
            
            result['sms_sent'] = sms_result.get('success', False)
            if result['sms_sent']:
                appointment.sms_reminder_sent = True
                appointment.sms_reminder_sent_at = timezone.now()
                appointment.save(update_fields=['sms_reminder_sent', 'sms_reminder_sent_at'])
                logger.info(f"SMS reminder sent for appointment {appointment.appointment_code}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send appointment reminder: {str(e)}")
            return result
    
    def send_appointment_cancelled(self, appointment: ServiceAppointment, cancelled_by: str) -> Dict[str, Any]:
        """
        Send appointment cancelled notification
        """
        result = {'sms_sent': False}
        
        try:
            if not appointment.client.phone:
                return result
            
            context = {
                'request_code': appointment.customer_request.request_code,
                'service_name': appointment.appointment_service,
                'workshop_name': appointment.service_workshop.workshop_name,
                'cancelled_by': cancelled_by,
            }
            
            sms_message = self._format_message('APPOINTMENT_CANCELLED', context)
            sms_result = self.sms_service.send_sms(
                phone_number=appointment.client.phone,
                message=sms_message,
                sender_id='QuickFix'
            )
            
            result['sms_sent'] = sms_result.get('success', False)
            
            # Also notify workshop if cancelled by customer
            if cancelled_by == 'customer' and appointment.service_workshop.workshop_phone:
                workshop_context = {
                    'request_code': appointment.customer_request.request_code,
                    'customer_name': appointment.client.get_full_name() or appointment.client.username,
                    'customer_phone': appointment.client.phone,
                    'appointment_date': appointment.appointment_date.strftime('%d/%m/%Y'),
                    'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
                }
                
                workshop_message = f"""
❌ Appointment Cancelled by Customer

Request: {workshop_context['request_code']}
Customer: {workshop_context['customer_name']}
Phone: {workshop_context['customer_phone']}
Date: {workshop_context['appointment_date']}
Time: {workshop_context['appointment_time']}

This appointment has been cancelled.
                """
                
                self.sms_service.send_sms(
                    phone_number=appointment.service_workshop.workshop_phone,
                    message=workshop_message,
                    sender_id='QuickFix'
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send appointment cancellation: {str(e)}")
            return result
    
    def send_offer_received(self, customer_request: CustomerRequest, quote: WorkshopQuote) -> Dict[str, Any]:
        """
        Send notification when customer receives an offer
        """
        result = {'sms_sent': False}
        
        try:
            if not customer_request.customer.phone:
                return result
            
            context = {
                'request_code': customer_request.request_code,
                'service_name': customer_request.requested_service,
                'workshop_name': quote.workshop.workshop_name,
                'price': quote.quoted_price,
                'estimated_duration': quote.estimated_duration,
            }
            
            sms_message = self._format_message('OFFER_RECEIVED', context)
            sms_result = self.sms_service.send_sms(
                phone_number=customer_request.customer.phone,
                message=sms_message,
                sender_id='QuickFix'
            )
            
            result['sms_sent'] = sms_result.get('success', False)
            return result
            
        except Exception as e:
            logger.error(f"Failed to send offer notification: {str(e)}")
            return result
    
    def send_request_created(self, customer_request: CustomerRequest) -> Dict[str, Any]:
        """
        Send notification when customer creates a request
        """
        result = {'sms_sent': False}
        
        try:
            if not customer_request.customer.phone:
                return result
            
            context = {
                'request_code': customer_request.request_code,
                'service_name': customer_request.requested_service,
                'preferred_date': customer_request.preferred_service_date.strftime('%d/%m/%Y'),
                'preferred_time': customer_request.preferred_service_time.strftime('%I:%M %p'),
            }
            
            sms_message = self._format_message('REQUEST_CREATED', context)
            sms_result = self.sms_service.send_sms(
                phone_number=customer_request.customer.phone,
                message=sms_message,
                sender_id='QuickFix'
            )
            
            result['sms_sent'] = sms_result.get('success', False)
            return result
            
        except Exception as e:
            logger.error(f"Failed to send request created notification: {str(e)}")
            return result
    
    def _send_appointment_email(self, appointment: ServiceAppointment, context: Dict) -> bool:
        """
        Send email notification for appointment
        """
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            
            if not appointment.client.email:
                return False
            
            subject = f"✅ Appointment Confirmed: {appointment.appointment_code}"
            
            # HTML email content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .details {{ background: #f9f9f9; padding: 15px; border-radius: 5px; }}
                    .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>✅ Appointment Confirmed!</h2>
                    </div>
                    <div class="content">
                        <p>Hello {appointment.client.get_full_name() or appointment.client.username},</p>
                        <p>Your appointment has been confirmed with the following details:</p>
                        
                        <div class="details">
                            <p><strong>Request Code:</strong> {context['request_code']}</p>
                            <p><strong>Service:</strong> {context['service_name']}</p>
                            <p><strong>Workshop:</strong> {context['workshop_name']}</p>
                            <p><strong>Date:</strong> {context['appointment_date']}</p>
                            <p><strong>Time:</strong> {context['appointment_time']}</p>
                            <p><strong>Price:</strong> TZS {context['price']:,.2f}</p>
                            <p><strong>Location:</strong> {context['location']}</p>
                            <p><strong>Workshop Contact:</strong> {context['workshop_phone']}</p>
                        </div>
                        
                        <p>Please arrive on time for your appointment. If you need to reschedule, please contact the workshop directly.</p>
                        
                        <p>Thank you for choosing QuickFix!</p>
                    </div>
                    <div class="footer">
                        <p>QuickFix Automotive - Your Trusted Auto Service Partner</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            plain_message = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[appointment.client.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Appointment confirmation email sent to {appointment.client.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send appointment email: {str(e)}")
            return False


# Global instance
appointment_notifier = AppointmentNotificationService()