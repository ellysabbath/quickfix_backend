# mechanics/utils.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_service_request_email(to_email, notification_type, context, recipient_type='customer'):
    """
    Send email notification for service request events
    
    notification_type: 'created', 'status_update', 'quote_ready', 'completed', 'new_request', 'garage_response'
    recipient_type: 'customer' or 'garage'
    """
    
    # Email templates mapping
    templates = {
        'customer': {
            'created': {
                'subject': f"✅ Service Request Created - {context.get('request_id', '')}",
                'template': 'emails/service_request_created.html'
            },
            'status_update': {
                'subject': f"📋 Status Update - {context.get('request_id', '')}",
                'template': 'emails/service_request_status_update.html'
            },
            'quote_ready': {
                'subject': f"💰 Quote Ready - {context.get('request_id', '')}",
                'template': 'emails/service_request_quote_ready.html'
            },
            'completed': {
                'subject': f"✅ Service Completed - {context.get('request_id', '')}",
                'template': 'emails/service_request_completed.html'
            },
            'cancelled': {
                'subject': f"❌ Service Cancelled - {context.get('request_id', '')}",
                'template': 'emails/service_request_cancelled.html'
            },
            'garage_response': {
                'subject': f"🔧 Garage Response - {context.get('request_id', '')}",
                'template': 'emails/garage_response.html'
            },
            'garage_assigned': {
                'subject': f"🏢 Garage Assigned - {context.get('request_id', '')}",
                'template': 'emails/garage_assigned.html'
            }
        },
        'garage': {
            'new_request': {
                'subject': f"🔧 New Service Request Available - {context.get('request_id', '')}",
                'template': 'emails/garage_new_request.html'
            },
            'status_update': {
                'subject': f"📋 Request Status Update - {context.get('request_id', '')}",
                'template': 'emails/garage_request_status.html'
            }
        }
    }
    
    template_info = templates.get(recipient_type, {}).get(notification_type)
    
    if not template_info:
        logger.warning(f"No template found for {recipient_type}/{notification_type}")
        return False
    
    try:
        # Add base URL for links
        context['base_url'] = settings.BASE_URL if hasattr(settings, 'BASE_URL') else 'https://autofix.pythonanywhere.com'
        context['track_url'] = f"{context['base_url']}/track-request/{context.get('request_id', '')}"
        context['dashboard_url'] = f"{context['base_url']}/dashboard"
        
        # Render HTML content
        html_content = render_to_string(template_info['template'], context)
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=template_info['subject'],
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"Email sent to {to_email} for {notification_type}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False