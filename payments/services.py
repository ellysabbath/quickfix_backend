# payments/services/email_service.py

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for handling all email notifications"""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'qfix910@gmail.com')
        self.company_name = getattr(settings, 'COMPANY_NAME', 'QuickFix Auto')
        self.dashboard_url = getattr(settings, 'DASHBOARD_URL', 'https://app.quickfixauto.com')
        self.support_email = getattr(settings, 'SUPPORT_EMAIL', 'support@quickfixauto.com')
    
    def send_email(self, subject, html_template, recipient_list, context=None):
        """
        Send email with HTML content
        """
        try:
            # Render HTML template
            if context:
                html_message = render_to_string(html_template, context)
            else:
                html_message = html_template
            
            # Plain text version
            plain_message = strip_tags(html_message)
            
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=self.from_email,
                to=recipient_list,
            )
            email.attach_alternative(html_message, "text/html")
            
            result = email.send()
            
            if result > 0:
                logger.info(f"Email sent successfully to {recipient_list}")
                return True
            else:
                logger.warning(f"Email sending failed to {recipient_list}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def send_payment_initiated_email(self, payment):
        """
        Send email when payment is initiated
        """
        context = self._get_base_context(payment)
        context.update({
            'payment_id': payment.payment_id,
            'status': payment.get_status_display(),
            'created_at': payment.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'next_steps': 'Please complete the payment using the instructions provided, then confirm your payment by providing the reference number or uploading a screenshot.',
        })
        
        subject = f"Payment Initiated - {payment.payment_id}"
        return self.send_email(
            subject=subject,
            html_template='emails/payment_initiated.html',
            recipient_list=[payment.sender_email],
            context=context
        )
    
    def send_payment_confirmation_email(self, payment):
        """
        Send email when payment is confirmed
        """
        context = self._get_base_context(payment)
        context.update({
            'payment_id': payment.payment_id,
            'confirmed_at': payment.confirmed_at.strftime('%B %d, %Y at %I:%M %p'),
            'reference': payment.transaction_reference or 'N/A',
            'has_screenshot': payment.has_screenshot(),
            'status': payment.get_status_display(),
            'next_steps': 'Our team will verify your payment and update your service request status.',
        })
        
        subject = f"Payment Confirmed - {payment.payment_id} 🎉"
        return self.send_email(
            subject=subject,
            html_template='emails/payment_confirmed.html',
            recipient_list=[payment.sender_email],
            context=context
        )
    
    def send_payment_verified_email(self, payment):
        """
        Send email when payment is verified
        """
        context = self._get_base_context(payment)
        context.update({
            'payment_id': payment.payment_id,
            'verified_at': payment.verified_at.strftime('%B %d, %Y at %I:%M %p'),
            'status': payment.get_status_display(),
        })
        
        subject = f"Payment Verified - {payment.payment_id} ✅"
        return self.send_email(
            subject=subject,
            html_template='emails/payment_verified.html',
            recipient_list=[payment.sender_email],
            context=context
        )
    
    def send_congratulations_email(self, payment):
        """
        Send congratulations email when payment is completed
        """
        context = self._get_base_context(payment)
        context.update({
            'payment_id': payment.payment_id,
            'completed_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            'status': 'Completed',
            'message': 'Your payment has been fully processed and verified.',
        })
        
        subject = f"Congratulations! Payment Completed - {payment.payment_id} 🎊"
        return self.send_email(
            subject=subject,
            html_template='emails/congratulations.html',
            recipient_list=[payment.sender_email],
            context=context
        )
    
    def send_status_update_email(self, payment, old_status, new_status):
        """
        Send email when payment status is updated
        """
        context = self._get_base_context(payment)
        context.update({
            'payment_id': payment.payment_id,
            'old_status': old_status,
            'new_status': new_status,
            'updated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        })
        
        subject = f"Payment Status Update - {payment.payment_id}"
        return self.send_email(
            subject=subject,
            html_template='emails/status_update.html',
            recipient_list=[payment.sender_email],
            context=context
        )
    
    def _get_base_context(self, payment):
        """Get base context for all email templates"""
        return {
            'company_name': self.company_name,
            'dashboard_url': self.dashboard_url,
            'support_email': self.support_email,
            'year': timezone.now().year,
            'payment': payment,
            'request_code': payment.service_request.request_code if payment.service_request else 'N/A',
            'amount': f"TZS {payment.amount:,.2f}",
            'sender_name': payment.sender_name,
            'sender_phone': payment.sender_phone,
            'sender_email': payment.sender_email,
            'receiver_name': payment.receiver_name,
            'receiver_phone': payment.receiver_phone,
            'payment_method': self._get_payment_method_name(payment.payment_method),
            'service_name': payment.service_request.requested_service if payment.service_request else 'N/A',
        }
    
    def _get_payment_method_name(self, method_id):
        """Get payment method name from ID"""
        method_names = {
            'mpesa': 'Lipa Na M-Pesa',
            'tigo_pesa': 'Tigo Pesa',
            'airtel_money': 'Airtel Money',
            'halo_pesa': 'Halo Pesa',
            'manual': 'Manual Payment',
        }
        return method_names.get(method_id, method_id)