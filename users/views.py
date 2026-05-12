from rest_framework import viewsets, status, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import logging

# Email imports
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings

# Models and serializers - UPDATED NAMES
from registration.models import (
    CustomerRequest,
    WorkshopQuote,
    ServiceAppointment,
    AutoWorkshop,
    RepairService

)
from .serializers import (
    CustomerRequestCreateSerializer,
    CustomerRequestDetailSerializer,
    WorkshopQuoteSerializer,
    WorkshopQuoteCreateSerializer,
    ServiceAppointmentSerializer,
    ServiceAppointmentCreateSerializer,
    AutoWorkshopSerializer,
    RepairServiceSerializer
)
from utils.africastalking_sms import africastalking_sms as sms_service
from  .models import CustomUser

logger = logging.getLogger(__name__)


# # ======================= CUSTOMER SERVICE REQUESTS =======================







# users/views.py
# from rest_framework import viewsets, status, permissions
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from django.db.models import Q
# from django.utils import timezone
# import logging

# # Models and serializers
# from registration.models import CustomerRequest
# from .serializers import (
#     CustomerRequestCreateSerializer,
#     CustomerRequestDetailSerializer,
# )
# from .models import CustomUser

# logger = logging.getLogger(__name__)


# class CustomerRequestViewSet(viewsets.ModelViewSet):
#     """
#     Simple ViewSet for customer service requests
#     """
#     queryset = CustomerRequest.objects.all()
#     serializer_class = CustomerRequestDetailSerializer
#     lookup_field = 'request_code'
#     lookup_url_kwarg = 'request_code'

#     # Use proper authentication
#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return CustomerRequestCreateSerializer
#         return CustomerRequestDetailSerializer

#     def get_queryset(self):
#         """
#         Users can see:
#         - All public active requests (for browsing)
#         - Their own requests
#         """
#         user = self.request.user

#         # For public listing, show active requests
#         if self.action == 'list' and 'my_requests' not in self.request.query_params:
#             return CustomerRequest.objects.filter(
#                 request_expires__gt=timezone.now(),
#                 request_status__in=['awaiting', 'viewed', 'offers_received']
#             ).order_by('-request_created')

#         # For authenticated users
#         if user.is_authenticated:
#             # For my_requests action, show only user's requests
#             if 'my_requests' in self.request.query_params:
#                 return CustomerRequest.objects.filter(customer=user).order_by('-request_created')

#             # For retrieve, allow viewing any request
#             if self.action == 'retrieve':
#                 return CustomerRequest.objects.all()

#             # Default: user's own requests
#             return CustomerRequest.objects.filter(customer=user).order_by('-request_created')

#         # For unauthenticated users (shouldn't reach here due to IsAuthenticated)
#         return CustomerRequest.objects.none()

#     def create(self, request, *args, **kwargs):
#         """
#         Create a new customer service request
#         """
#         try:
#             # Debug logging
#             logger.info(f"Creating request for user: {request.user.id}")
#             logger.info(f"User authenticated: {request.user.is_authenticated}")

#             # Check if user is authenticated
#             if not request.user.is_authenticated:
#                 return Response({
#                     'success': False,
#                     'message': 'Authentication required to create service request'
#                 }, status=status.HTTP_401_UNAUTHORIZED)

#             # Create serializer with request context
#             serializer = self.get_serializer(data=request.data, context={'request': request})
#             serializer.is_valid(raise_exception=True)

#             # Save the request (customer will be set in serializer's create method)
#             customer_request = serializer.save()

#             return Response({
#                 'success': True,
#                 'message': 'Service request created successfully!',
#                 'data': CustomerRequestDetailSerializer(customer_request, context={'request': request}).data
#             }, status=status.HTTP_201_CREATED)

#         except Exception as e:
#             logger.error(f"Failed to create service request: {str(e)}", exc_info=True)
#             return Response({
#                 'success': False,
#                 'error': str(e),
#                 'message': 'Failed to create service request'
#             }, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=False, methods=['get'])
#     def my_requests(self, request):
#         """
#         Get requests for the authenticated user
#         """
#         if not request.user.is_authenticated:
#             return Response({
#                 'success': False,
#                 'message': 'Authentication required'
#             }, status=status.HTTP_401_UNAUTHORIZED)

#         try:
#             requests = CustomerRequest.objects.filter(
#                 customer=request.user
#             ).order_by('-request_created')

#             serializer = CustomerRequestDetailSerializer(requests, many=True, context={'request': request})

#             return Response({
#                 'success': True,
#                 'count': requests.count(),
#                 'data': serializer.data
#             })
#         except Exception as e:
#             return Response({
#                 'success': False,
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=False, methods=['get'])
#     def active_requests(self, request):
#         """
#         Get active customer requests (non-expired, not accepted)
#         """
#         queryset = CustomerRequest.objects.filter(
#             request_expires__gt=timezone.now(),
#             request_status__in=['awaiting', 'viewed', 'offers_received']
#         ).order_by('-request_created')

#         serializer = CustomerRequestDetailSerializer(queryset, many=True, context={'request': request})

#         return Response({
#             'success': True,
#             'count': queryset.count(),
#             'data': serializer.data
#         })

#     @action(detail=True, methods=['post'])
#     def cancel_request(self, request, request_code=None):
#         """
#         Cancel a service request
#         """
#         if not request.user.is_authenticated:
#             return Response({
#                 'success': False,
#                 'message': 'Authentication required'
#             }, status=status.HTTP_401_UNAUTHORIZED)

#         customer_request = self.get_object()

#         # Verify customer owns the request
#         if customer_request.customer != request.user:
#             return Response({
#                 'success': False,
#                 'message': 'You can only cancel your own requests'
#             }, status=status.HTTP_403_FORBIDDEN)

#         # Check if request can be cancelled
#         if customer_request.request_status not in ['awaiting', 'viewed', 'offers_received']:
#             return Response({
#                 'success': False,
#                 'message': f'Cannot cancel request with status: {customer_request.request_status}'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         customer_request.request_status = 'cancelled'
#         customer_request.save()

#         return Response({
#             'success': True,
#             'message': 'Request cancelled successfully'
#         })


# ===================================//  WITH   EMAIL  NOTIFICATIONS //========================
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging
from datetime import datetime

# Models and serializers
from registration.models import CustomerRequest
from .serializers import (
    CustomerRequestCreateSerializer,
    CustomerRequestDetailSerializer,
    CustomerRequestUpdateSerializer,
)
from .models import CustomUser

logger = logging.getLogger(__name__)


class CustomerRequestPermissions(permissions.BasePermission):
    """
    Custom permission class for customer requests
    - Anyone can view/list requests
    - Only authenticated users can create/update/delete
    """
    def has_permission(self, request, view):
        # Allow anyone to view/list requests
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only authenticated users can create/update/delete
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow anyone to view requests
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only the owner can modify their own requests
        return obj.customer == request.user


def create_email_html(template_type, context):
    """
    Create HTML email content with embedded styles

    Args:
        template_type: Type of email template ('created', 'updated', 'cancelled', 'status_changed', 'offer_received')
        context: Dictionary with email context data
    """

    # Base HTML structure with embedded CSS
    base_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Service Request Notification</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .email-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px 20px;
                text-align: center;
            }}
            .email-header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .email-header .subtitle {{
                font-size: 14px;
                opacity: 0.9;
                margin-top: 5px;
            }}
            .email-body {{
                padding: 30px;
            }}
            .request-card {{
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                border-left: 4px solid #667eea;
            }}
            .request-details {{
                margin: 15px 0;
            }}
            .detail-item {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }}
            .detail-label {{
                font-weight: 600;
                color: #555;
            }}
            .detail-value {{
                color: #333;
            }}
            .status-badge {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 10px;
            }}
            .status-pending {{ background-color: #fff3cd; color: #856404; }}
            .status-accepted {{ background-color: #d4edda; color: #155724; }}
            .status-cancelled {{ background-color: #f8d7da; color: #721c24; }}
            .status-completed {{ background-color: #d1ecf1; color: #0c5460; }}
            .action-button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white !important;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: 600;
                margin: 20px 0;
                text-align: center;
            }}
            .email-footer {{
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #666;
                border-top: 1px solid #eee;
            }}
            .footer-links a {{
                color: #667eea;
                text-decoration: none;
                margin: 0 10px;
            }}
            .important-note {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
                font-size: 14px;
            }}
            .garage-info {{
                background-color: #e8f4fd;
                border: 1px solid #b6e0fe;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
            }}
            @media (max-width: 600px) {{
                .email-body {{
                    padding: 15px;
                }}
                .detail-item {{
                    flex-direction: column;
                }}
            }}
        </style>
    </head>
    <body>
    """

    # Template-specific content
    templates = {
        'created': """
        <div class="email-container">
            <div class="email-header">
                <h1>🎉 Service Request Created!</h1>
                <div class="subtitle">Your request has been successfully submitted</div>
            </div>

            <div class="email-body">
                <p>Hello <strong>{customer_name}</strong>,</p>
                <p>Thank you for creating a new service request. We've received your request and will notify relevant service providers.</p>

                <div class="request-card">
                    <h3 style="margin-top: 0;">Request Summary</h3>
                    <div class="request-details">
                        {request_details}
                    </div>
                </div>

                <div class="important-note">
                    <strong>📋 What happens next?</strong>
                    <ul>
                        <li>Your request will be visible to qualified service providers</li>
                        <li>Providers may contact you with quotes</li>
                        <li>You can review and accept offers in your dashboard</li>
                    </ul>
                </div>

                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="action-button">View Your Request</a>
                </div>

                <p>Need to make changes? You can update your request anytime from your dashboard.</p>
            </div>
        </div>
        """,

        'updated': """
        <div class="email-container">
            <div class="email-header">
                <h1>📝 Service Request Updated</h1>
                <div class="subtitle">Your request has been modified</div>
            </div>

            <div class="email-body">
                <p>Hello <strong>{customer_name}</strong>,</p>
                <p>Your service request has been updated with new information.</p>

                <div class="request-card">
                    <h3 style="margin-top: 0;">Updated Request Details</h3>
                    <div class="request-details">
                        {request_details}
                    </div>
                </div>

                {status_change_section}

                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="action-button">View Updated Request</a>
                </div>

                <p>All service providers will be notified of these changes.</p>
            </div>
        </div>
        """,

        'cancelled': """
        <div class="email-container">
            <div class="email-header" style="background: linear-gradient(135deg, #f56565 0%, #ed64a6 100%);">
                <h1>❌ Service Request Cancelled</h1>
                <div class="subtitle">Your request has been cancelled</div>
            </div>

            <div class="email-body">
                <p>Hello <strong>{customer_name}</strong>,</p>
                <p>Your service request has been cancelled as requested.</p>

                <div class="request-card">
                    <h3 style="margin-top: 0;">Cancelled Request</h3>
                    <div class="request-details">
                        {request_details}
                    </div>
                </div>

                <div class="important-note">
                    <strong>⚠️ Important Information:</strong>
                    <ul>
                        <li>This request will no longer be visible to service providers</li>
                        <li>Any ongoing discussions about this request will be closed</li>
                        <li>You can create a new request anytime if needed</li>
                    </ul>
                </div>

                <p>If this was a mistake or you have questions, please contact our support team immediately.</p>

                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="action-button" style="background: linear-gradient(135deg, #f56565 0%, #ed64a6 100%);">Go to Dashboard</a>
                </div>
            </div>
        </div>
        """,

        'status_changed': """
        <div class="email-container">
            <div class="email-header">
                <h1>🔄 Request Status Updated</h1>
                <div class="subtitle">Status change notification</div>
            </div>

            <div class="email-body">
                <p>Hello <strong>{customer_name}</strong>,</p>
                <p>The status of your service request has been updated.</p>

                <div class="request-card">
                    <h3 style="margin-top: 0;">Status Update</h3>
                    <div style="text-align: center; margin: 20px 0;">
                        <div style="display: inline-block; text-align: center;">
                            <div style="font-size: 14px; color: #666;">Previous Status</div>
                            <div style="padding: 10px 20px; background: #f8f9fa; border-radius: 5px; margin: 5px;">
                                {old_status}
                            </div>
                        </div>
                        <div style="display: inline-block; margin: 0 20px; font-size: 20px;">→</div>
                        <div style="display: inline-block; text-align: center;">
                            <div style="font-size: 14px; color: #666;">New Status</div>
                            <div style="padding: 10px 20px; background: #d4edda; border-radius: 5px; margin: 5px;">
                                {new_status}
                            </div>
                        </div>
                    </div>

                    <div class="request-details">
                        {request_details}
                    </div>
                </div>

                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="action-button">View Request Details</a>
                </div>

                <p>You'll receive further notifications as your request progresses.</p>
            </div>
        </div>
        """,

        'offer_received': """
        <div class="email-container">
            <div class="email-header" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">
                <h1>💰 New Offer Received!</h1>
                <div class="subtitle">You have a new quote for your service request</div>
            </div>

            <div class="email-body">
                <p>Hello <strong>{customer_name}</strong>,</p>
                <p>Great news! A service provider has submitted an offer for your request.</p>

                <div class="request-card">
                    <h3 style="margin-top: 0;">Offer Details</h3>
                    <div class="request-details">
                        {request_details}
                    </div>

                    {offer_details}
                </div>

                <div class="garage-info">
                    <h4 style="margin-top: 0;">📋 From Service Provider:</h4>
                    <p><strong>{garage_name}</strong></p>
                    <p>{garage_contact}</p>
                </div>

                <div style="text-align: center;">
                    <a href="{offer_url}" class="action-button" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">Review Offer</a>
                </div>

                <p>Please review the offer and respond within 48 hours. Multiple offers may be available.</p>
            </div>
        </div>
        """,

        'garage_notification': """
        <div class="email-container">
            <div class="email-header">
                <h1>🔧 New Service Request Available</h1>
                <div class="subtitle">A customer needs your service</div>
            </div>

            <div class="email-body">
                <p>Hello <strong>{garage_name}</strong>,</p>
                <p>A new service request matching your expertise has been posted.</p>

                <div class="request-card">
                    <h3 style="margin-top: 0;">Customer Request Details</h3>
                    <div class="request-details">
                        {request_details}
                    </div>
                </div>

                <div class="important-note">
                    <strong>👤 Customer Information:</strong>
                    <ul>
                        <li><strong>Name:</strong> {customer_name}</li>
                        <li><strong>Service Needed:</strong> {service_type}</li>
                        <li><strong>Location:</strong> {location}</li>
                        {urgency_note}
                    </ul>
                </div>

                <div style="text-align: center;">
                    <a href="{request_url}" class="action-button">Submit Your Offer</a>
                </div>

                <p>This request will expire on: <strong>{expiry_date}</strong></p>
                <p>Please respond promptly to secure this opportunity.</p>
            </div>
        </div>
        """
    }

    # Close HTML
    footer_html = """
        <div class="email-footer">
            <div class="footer-links">
                <a href="{support_url}">Support</a> |
                <a href="{privacy_url}">Privacy Policy</a> |
                <a href="{terms_url}">Terms of Service</a>
            </div>
            <p>&copy; {current_year} {company_name}. All rights reserved.</p>
            <p>This is an automated notification. Please do not reply to this email.</p>
            <p style="font-size: 11px; color: #999;">Request ID: {request_code}</p>
        </div>
    </body>
    </html>
    """

    # Get template
    html_template = templates.get(template_type, templates['created'])

    # Default context values
    default_context = {
        'company_name': getattr(settings, 'COMPANY_NAME', 'AutoService Pro'),
        'support_url': getattr(settings, 'SUPPORT_URL', 'https://support.example.com'),
        'privacy_url': getattr(settings, 'PRIVACY_URL', 'https://example.com/privacy'),
        'terms_url': getattr(settings, 'TERMS_URL', 'https://example.com/terms'),
        'current_year': datetime.now().year,
        'dashboard_url': getattr(settings, 'DASHBOARD_URL', 'https://app.example.com/dashboard'),
    }

    # Merge with provided context
    email_context = {**default_context, **context}

    # Create request details HTML
    request_details = ""
    if 'request' in context:
        req = context['request']
        request_details = f"""
        <div class="detail-item">
            <span class="detail-label">Request Code:</span>
            <span class="detail-value"><strong>{req.request_code}</strong></span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Service Type:</span>
            <span class="detail-value">{req.get_service_type_display()}</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Status:</span>
            <span class="detail-value">
                {req.get_request_status_display()}
                <span class="status-badge status-{req.request_status}">{req.request_status}</span>
            </span>
        </div>
        """
        if hasattr(req, 'vehicle_make') and req.vehicle_make:
            request_details += f"""
            <div class="detail-item">
                <span class="detail-label">Vehicle:</span>
                <span class="detail-value">{req.vehicle_make} {req.vehicle_model or ''}</span>
            </div>
            """
        if hasattr(req, 'location') and req.location:
            request_details += f"""
            <div class="detail-item">
                <span class="detail-label">Location:</span>
                <span class="detail-value">{req.location}</span>
            </div>
            """
        if hasattr(req, 'request_created') and req.request_created:
            request_details += f"""
            <div class="detail-item">
                <span class="detail-label">Created:</span>
                <span class="detail-value">{req.request_created.strftime('%B %d, %Y at %I:%M %p')}</span>
            </div>
            """

    email_context['request_details'] = request_details

    # Status change section for updated template
    if template_type == 'updated' and 'old_status' in context and 'new_status' in context:
        status_change = f"""
        <div style="background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <strong>Status Change:</strong> {context['old_status']} → {context['new_status']}
        </div>
        """
        email_context['status_change_section'] = status_change
    else:
        email_context['status_change_section'] = ""

    # Generate final HTML
    html_content = base_html + html_template.format(**email_context) + footer_html.format(**email_context)

    return html_content


def send_request_email_notification(request_instance, action_type, recipient_email=None, garage_data=None):
    """
    Send email notification with embedded HTML

    Args:
        request_instance: CustomerRequest instance
        action_type: Type of action ('created', 'updated', 'cancelled', 'status_changed', 'offer_received', 'garage_notification')
        recipient_email: Optional specific recipient email
        garage_data: Dictionary with garage information for garage notifications
    """
    try:
        # Prepare context
        context = {
            'request': request_instance,
            'customer_name': request_instance.customer.get_full_name() or request_instance.customer.email,
            'request_code': request_instance.request_code,
        }

        # Add garage data if provided
        if garage_data:
            context.update(garage_data)

        # Create HTML content
        html_content = create_email_html(action_type, context)

        # Email subjects
        email_subjects = {
            'created': f'✅ Service Request Created: #{request_instance.request_code}',
            'updated': f'📝 Service Request Updated: #{request_instance.request_code}',
            'cancelled': f'❌ Service Request Cancelled: #{request_instance.request_code}',
            'status_changed': f'🔄 Status Updated: #{request_instance.request_code}',
            'offer_received': f'💰 New Offer Received for Request: #{request_instance.request_code}',
            'garage_notification': f'🔧 New Service Request Available: #{request_instance.request_code}',
        }

        subject = email_subjects.get(action_type, f'Service Request Update: #{request_instance.request_code}')

        # Determine recipients
        recipients = []

        # For garage notifications, use provided email
        if action_type == 'garage_notification' and recipient_email:
            recipients.append(recipient_email)
        # Otherwise, notify the customer
        elif request_instance.customer and request_instance.customer.email:
            recipients.append(request_instance.customer.email)

        # Fallback if no recipient found
        if not recipients:
            logger.warning(f"No recipient email found for {action_type} notification")
            return False

        # Create plain text alternative
        plain_text = f"""
        Service Request Notification
        ============================

        Request Code: {request_instance.request_code}
        Customer: {context['customer_name']}
        Status: {request_instance.get_request_status_display()}
        Service Type: {request_instance.get_service_type_display()}

        Please check your dashboard for more details: {getattr(settings, 'DASHBOARD_URL', '')}

        This is an automated notification. Please do not reply to this email.
        """

        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            to=recipients,
            reply_to=[getattr(settings, 'REPLY_TO_EMAIL', 'support@example.com')],
        )

        email.attach_alternative(html_content, "text/html")

        # Add headers for better email client compatibility
        email.extra_headers = {
            'X-Priority': '1',
            'X-MSMail-Priority': 'High',
            'Importance': 'high'
        }

        email.send(fail_silently=False)

        logger.info(f"Email sent successfully for {action_type} action on request {request_instance.request_code}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}", exc_info=True)
        return False


class CustomerRequestViewSet(viewsets.ModelViewSet):
    """
    Complete ViewSet for customer service requests with embedded email notifications
    """
    queryset = CustomerRequest.objects.all()
    lookup_field = 'request_code'
    lookup_url_kwarg = 'request_code'

    # Use custom permissions for public viewing, authenticated modifications
    permission_classes = [CustomerRequestPermissions]

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return CustomerRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CustomerRequestUpdateSerializer
        return CustomerRequestDetailSerializer

    def get_queryset(self):
        """
        Custom queryset handling with public/private access
        """
        # Public viewing endpoints
        if self.action in ['list', 'retrieve', 'active_requests']:
            if self.request.user.is_authenticated:
                return CustomerRequest.objects.all().order_by('-request_created')
            else:
                return CustomerRequest.objects.filter(
                    request_expires__gt=timezone.now(),
                    request_status__in=['awaiting', 'viewed', 'offers_received']
                ).order_by('-request_created')

        # Authenticated user endpoints
        elif self.request.user.is_authenticated:
            if 'my_requests' in self.request.query_params or self.action == 'my_requests':
                return CustomerRequest.objects.filter(customer=self.request.user).order_by('-request_created')
            return CustomerRequest.objects.filter(customer=self.request.user).order_by('-request_created')

        return CustomerRequest.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Create new request with email notification
        """
        try:
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'message': 'Authentication required to create service request'
                }, status=status.HTTP_401_UNAUTHORIZED)

            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)

            # Save with customer
            customer_request = serializer.save(customer=request.user)

            # Send email to customer
            send_request_email_notification(
                request_instance=customer_request,
                action_type='created'
            )

            # Notify relevant garages
            self._notify_relevant_garages(customer_request)

            return Response({
                'success': True,
                'message': 'Service request created successfully!',
                'data': CustomerRequestDetailSerializer(customer_request, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to create service request: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to create service request'
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Update request with email notification
        """
        try:
            instance = self.get_object()

            if instance.customer != request.user:
                return Response({
                    'success': False,
                    'message': 'You can only update your own requests'
                }, status=status.HTTP_403_FORBIDDEN)

            old_status = instance.request_status

            serializer = self.get_serializer(instance, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)

            customer_request = serializer.save()

            # Determine action type
            action_type = 'status_changed' if old_status != customer_request.request_status else 'updated'

            # Send email
            send_request_email_notification(
                request_instance=customer_request,
                action_type=action_type,
                garage_data={'old_status': old_status, 'new_status': customer_request.request_status}
            )

            return Response({
                'success': True,
                'message': 'Service request updated successfully!',
                'data': CustomerRequestDetailSerializer(customer_request, context={'request': request}).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to update service request: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to update service request'
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Delete request with email notification
        """
        try:
            instance = self.get_object()

            if instance.customer != request.user:
                return Response({
                    'success': False,
                    'message': 'You can only delete your own requests'
                }, status=status.HTTP_403_FORBIDDEN)

            # Send cancellation email
            send_request_email_notification(
                request_instance=instance,
                action_type='cancelled'
            )

            self.perform_destroy(instance)

            return Response({
                'success': True,
                'message': 'Service request deleted successfully!'
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Failed to delete service request: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to delete service request'
            }, status=status.HTTP_400_BAD_REQUEST)

    def _notify_relevant_garages(self, customer_request):
        """
        Find and notify relevant garages about new request
        """
        try:
            # Find garages based on location, service type, etc.
            # This is a simplified example - customize based on your needs

            # Example: Find garages in the same city
            if hasattr(customer_request, 'location'):
                from .models import Garage  # Import your Garage model

                # Simple matching by city (customize as needed)
                city = customer_request.location.split(',')[0].strip() if customer_request.location else None

                if city:
                    relevant_garages = Garage.objects.filter(
                        Q(location__icontains=city) |
                        Q(services_offered__icontains=customer_request.service_type)
                    ).distinct()[:200]  # Limit to 10 garages

                    for garage in relevant_garages:
                        if garage.email:
                            # Prepare garage data for email
                            garage_data = {
                                'garage_name': garage.name,
                                'location': garage.location,
                                'garage_contact': garage.phone or garage.email,
                                'urgency_note': '<li><strong>Urgency:</strong> Standard</li>' if not hasattr(customer_request, 'urgency') else f'<li><strong>Urgency:</strong> {customer_request.urgency}</li>',
                                'expiry_date': customer_request.request_expires.strftime('%B %d, %Y') if customer_request.request_expires else 'N/A'
                            }

                            send_request_email_notification(
                                request_instance=customer_request,
                                action_type='garage_notification',
                                recipient_email=garage.email,
                                garage_data=garage_data
                            )

            logger.info(f"Garage notifications sent for request {customer_request.request_code}")

        except Exception as e:
            logger.error(f"Failed to notify garages: {str(e)}", exc_info=True)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """
        Get authenticated user's requests
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            requests = CustomerRequest.objects.filter(
                customer=request.user
            ).order_by('-request_created')

            serializer = CustomerRequestDetailSerializer(requests, many=True, context={'request': request})

            return Response({
                'success': True,
                'count': requests.count(),
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def active_requests(self, request):
        """
        Public endpoint for active requests
        """
        queryset = CustomerRequest.objects.filter(
            request_expires__gt=timezone.now(),
            request_status__in=['awaiting', 'viewed', 'offers_received']
        ).order_by('-request_created')

        serializer = CustomerRequestDetailSerializer(queryset, many=True, context={'request': request})

        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel_request(self, request, request_code=None):
        """
        Cancel a request with email notification
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)

        customer_request = self.get_object()

        if customer_request.customer != request.user:
            return Response({
                'success': False,
                'message': 'You can only cancel your own requests'
            }, status=status.HTTP_403_FORBIDDEN)

        if customer_request.request_status not in ['awaiting', 'viewed', 'offers_received']:
            return Response({
                'success': False,
                'message': f'Cannot cancel request with status: {customer_request.request_status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        old_status = customer_request.request_status
        customer_request.request_status = 'cancelled'
        customer_request.save()

        send_request_email_notification(
            request_instance=customer_request,
            action_type='cancelled',
            garage_data={'old_status': old_status, 'new_status': 'cancelled'}
        )

        return Response({
            'success': True,
            'message': 'Request cancelled successfully'
        })

    @action(detail=True, methods=['post'])
    def notify_garage(self, request, request_code=None):
        """
        Manually send request to a specific garage
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)

        customer_request = self.get_object()

        if customer_request.customer != request.user:
            return Response({
                'success': False,
                'message': 'You can only share your own requests'
            }, status=status.HTTP_403_FORBIDDEN)

        garage_email = request.data.get('garage_email')
        garage_name = request.data.get('garage_name', 'Garage')

        if not garage_email:
            return Response({
                'success': False,
                'message': 'Garage email is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Send notification to garage
        garage_data = {
            'garage_name': garage_name,
            'location': customer_request.location if hasattr(customer_request, 'location') else 'Not specified',
            'garage_contact': request.data.get('garage_phone', ''),
            'urgency_note': '<li><strong>Urgency:</strong> Customer-shared request</li>',
            'expiry_date': customer_request.request_expires.strftime('%B %d, %Y') if customer_request.request_expires else 'N/A'
        }

        success = send_request_email_notification(
            request_instance=customer_request,
            action_type='garage_notification',
            recipient_email=garage_email,
            garage_data=garage_data
        )

        if success:
            return Response({
                'success': True,
                'message': f'Request shared with {garage_name} successfully'
            })
        else:
            return Response({
                'success': False,
                'message': 'Failed to send notification to garage'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def accept_offer(self, request, request_code=None):
        """
        Accept an offer for a request with email notification
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)

        customer_request = self.get_object()

        if customer_request.customer != request.user:
            return Response({
                'success': False,
                'message': 'You can only accept offers for your own requests'
            }, status=status.HTTP_403_FORBIDDEN)

        # Update request status
        old_status = customer_request.request_status
        customer_request.request_status = 'accepted'
        customer_request.save()

        # Send notification
        send_request_email_notification(
            request_instance=customer_request,
            action_type='status_changed',
            garage_data={'old_status': old_status, 'new_status': 'accepted'}
        )

        return Response({
            'success': True,
            'message': 'Offer accepted successfully'
        })


# ======================= MINIMAL VERSION FOR TESTING =======================
class SimpleCustomerRequestCreateView(viewsets.ModelViewSet):
    """
    Minimal ViewSet ONLY for creating customer requests
    """
    queryset = CustomerRequest.objects.all()
    serializer_class = CustomerRequestCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own requests
        if self.request.user.is_authenticated:
            return CustomerRequest.objects.filter(customer=self.request.user)
        return CustomerRequest.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Create a new service request - SIMPLIFIED VERSION
        """
        try:
            # Validate authentication
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'message': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Add debug logging
            logger.info(f"User ID: {request.user.id}")
            logger.info(f"User email: {request.user.email}")
            logger.info(f"Request data: {request.data}")

            # Create serializer with request context
            serializer = self.get_serializer(data=request.data, context={'request': request})

            # Validate data
            if not serializer.is_valid():
                logger.error(f"Validation errors: {serializer.errors}")
                return Response({
                    'success': False,
                    'errors': serializer.errors,
                    'message': 'Validation failed'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Save the request
            customer_request = serializer.save()

            # Return success response
            return Response({
                'success': True,
                'message': 'Service request created successfully',
                'data': {
                    'request_code': customer_request.request_code,
                    'requested_service': customer_request.requested_service,
                    'status': customer_request.request_status,
                    'created_at': customer_request.request_created,
                    'customer_id': customer_request.customer_id,
                    'customer_email': customer_request.customer.email if customer_request.customer else None
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating request: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to create service request'
            }, status=status.HTTP_400_BAD_REQUEST)







# ======================= WORKSHOP QUOTES =======================
class WorkshopQuoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for workshop quotes
    """
    queryset = WorkshopQuote.objects.all().select_related('customer_request', 'workshop')
    serializer_class = WorkshopQuoteSerializer

    # REMOVED ALL AUTHENTICATION FOR DEVELOPMENT
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by workshop
        workshop_id = self.request.query_params.get('workshop_id')
        if workshop_id:
            queryset = queryset.filter(workshop_id=workshop_id)

        # Filter by customer request
        request_code = self.request.query_params.get('request_code')
        if request_code:
            queryset = queryset.filter(customer_request__request_code=request_code)

        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(quote_status=status)

        return queryset.order_by('-quote_created')

    @action(detail=False, methods=['get'])
    def workshop_quotes(self, request):
        """
        Get quotes submitted by a specific workshop
        """
        workshop_id = request.query_params.get('workshop_id')
        if not workshop_id:
            return Response({
                'success': False,
                'message': 'Workshop ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            quotes = WorkshopQuote.objects.filter(
                workshop_id=workshop_id
            ).select_related('customer_request').order_by('-quote_created')

            # Calculate stats
            total = quotes.count()
            pending = quotes.filter(quote_status='pending').count()
            accepted = quotes.filter(quote_status='accepted').count()
            declined = quotes.filter(quote_status='declined').count()

            serializer = self.get_serializer(quotes, many=True)

            return Response({
                'success': True,
                'stats': {
                    'total': total,
                    'pending': pending,
                    'accepted': accepted,
                    'declined': declined
                },
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def withdraw_quote(self, request, pk=None):
        """
        Withdraw a quote
        """
        quote = self.get_object()

        workshop_id = request.data.get('workshop_id')
        if not workshop_id:
            return Response({
                'success': False,
                'message': 'Workshop ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if workshop owns the quote
        if str(quote.workshop_id) != workshop_id:
            return Response({
                'success': False,
                'message': 'You can only withdraw your own quotes'
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if quote can be withdrawn
        if quote.quote_status != 'pending':
            return Response({
                'success': False,
                'message': 'Only pending quotes can be withdrawn'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if request is still active
        if not quote.customer_request.can_receive_offers():
            return Response({
                'success': False,
                'message': 'Cannot withdraw quote from an inactive request'
            }, status=status.HTTP_400_BAD_REQUEST)

        quote.quote_status = 'withdrawn'
        quote.save()

        return Response({
            'success': True,
            'message': 'Quote withdrawn successfully'
        })


# ======================= SERVICE APPOINTMENTS =======================
class ServiceAppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for service appointments
    """
    queryset = ServiceAppointment.objects.all().select_related(
        'client', 'service_workshop', 'customer_request', 'accepted_quote'
    )
    serializer_class = ServiceAppointmentSerializer
    lookup_field = 'appointment_code'
    lookup_url_kwarg = 'appointment_code'

    # REMOVED ALL AUTHENTICATION FOR DEVELOPMENT
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceAppointmentCreateSerializer
        return ServiceAppointmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by customer
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(client_id=customer_id)

        # Filter by workshop
        workshop_id = self.request.query_params.get('workshop_id')
        if workshop_id:
            queryset = queryset.filter(service_workshop_id=workshop_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(appointment_status=status_filter)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                date = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(appointment_date__gte=date)
            except ValueError:
                pass

        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                date = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(appointment_date__lte=date)
            except ValueError:
                pass

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(appointment_code__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(client__phone__icontains=search) |
                Q(service_workshop__workshop_name__icontains=search) |
                Q(appointment_service__icontains=search) |
                Q(appointment_location__icontains=search)
            )

        # Ordering
        order_by = self.request.query_params.get('order_by', '-appointment_date')
        if order_by.lstrip('-') in ['appointment_date', 'appointment_created', 'agreed_price']:
            queryset = queryset.order_by(order_by)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create a service appointment from accepted quote
        """
        # Get customer request from data
        request_code = request.data.get('request_code')
        if not request_code:
            return Response({
                'success': False,
                'message': 'Request code is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer_request = CustomerRequest.objects.get(request_code=request_code)
        except CustomerRequest.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Request not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Add customer_request to context for serializer
        self.customer_request = customer_request

        serializer = self.get_serializer(data=request.data, context={
            'request': request,
            'view': self
        })
        serializer.is_valid(raise_exception=True)

        try:
            appointment = serializer.save()

            # Send SMS confirmation
            appointment.send_confirmation_notification()

            # Send email to workshop
            self._send_appointment_email(appointment)

            return Response({
                'success': True,
                'message': 'Service appointment created successfully',
                'data': ServiceAppointmentSerializer(appointment).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to create service appointment: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to create service appointment'
            }, status=status.HTTP_400_BAD_REQUEST)

    def get_customer_request(self):
        """Helper method to get customer request from context"""
        return getattr(self, 'customer_request', None)

    def _send_appointment_email(self, appointment):
        """Send appointment confirmation email to workshop"""
        try:
            if not appointment.service_workshop.workshop_email:
                return

            subject = f"📋 New Service Appointment #{appointment.appointment_code}"

            html_content = self._generate_appointment_email_content(appointment)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[appointment.service_workshop.workshop_email],
                reply_to=[settings.DEFAULT_FROM_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=True)

        except Exception as e:
            logger.error(f"Error sending appointment email: {str(e)}")

    def _generate_appointment_email_content(self, appointment):
        """Generate HTML email content for appointment notification"""
        client_name = appointment.client.get_full_name() or appointment.client.email.split('@')[0]

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background: #f9f9f9; padding: 20px; border-radius: 10px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 20px; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .info-table td {{ padding: 10px; border: 1px solid #ddd; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>New Service Appointment</h2>
                </div>
                <div class="content">
                    <h3>Appointment #{appointment.appointment_code}</h3>
                    <table class="info-table">
                        <tr><td><strong>Client:</strong></td><td>{client_name}</td></tr>
                        <tr><td><strong>Phone:</strong></td><td>{appointment.client.phone if hasattr(appointment.client, 'phone') else 'N/A'}</td></tr>
                        <tr><td><strong>Service:</strong></td><td>{appointment.appointment_service}</td></tr>
                        <tr><td><strong>Vehicle:</strong></td><td>{appointment.vehicle_details}</td></tr>
                        <tr><td><strong>Amount:</strong></td><td>TZS {appointment.agreed_price:,.2f}</td></tr>
                        <tr><td><strong>Date:</strong></td><td>{appointment.appointment_date}</td></tr>
                        <tr><td><strong>Time:</strong></td><td>{appointment.appointment_time}</td></tr>
                        <tr><td><strong>Location:</strong></td><td>{appointment.appointment_location}</td></tr>
                    </table>
                    <p>Please contact the client to confirm all details.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the service platform.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @action(detail=False, methods=['get'])
    def client_appointments(self, request):
        """
        Get appointments for a specific client
        """
        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response({
                'success': False,
                'message': 'Client ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            appointments = ServiceAppointment.objects.filter(client_id=client_id)

            # Calculate stats
            total = appointments.count()
            upcoming = appointments.filter(
                appointment_date__gte=timezone.now().date(),
                appointment_status__in=['confirmed', 'in_progress']
            ).count()
            completed = appointments.filter(appointment_status='completed').count()

            appointments = appointments.order_by('-appointment_date', '-appointment_created')
            serializer = self.get_serializer(appointments, many=True)

            return Response({
                'success': True,
                'stats': {
                    'total': total,
                    'upcoming': upcoming,
                    'completed': completed
                },
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_appointment_status(self, request, appointment_code=None):
        """
        Update appointment status
        """
        appointment = self.get_object()
        new_status = request.data.get('status')

        if not new_status:
            return Response({
                'success': False,
                'message': 'Status is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in dict(ServiceAppointment.APPOINTMENT_STATUS):
            return Response({
                'success': False,
                'message': 'Invalid status'
            }, status=status.HTTP_400_BAD_REQUEST)

        old_status = appointment.appointment_status
        appointment.appointment_status = new_status
        appointment.save()

        # Send status update notifications
        if old_status != new_status:
            self._send_status_update_notifications(appointment, old_status, new_status)

        # Send reminder SMS if appointment is tomorrow
        if new_status == 'confirmed':
            tomorrow = timezone.now().date() + timedelta(days=1)
            if appointment.appointment_date == tomorrow:
                appointment.send_reminder_notification()

        return Response({
            'success': True,
            'message': f'Status updated to {new_status}',
            'data': self.get_serializer(appointment).data
        })

    def _send_status_update_notifications(self, appointment, old_status, new_status):
        """Send status update notifications to client"""
        try:
            if not appointment.client.phone:
                return

            status_display = dict(ServiceAppointment.APPOINTMENT_STATUS).get(new_status, new_status)

            message = (
                f"📋 Appointment #{appointment.appointment_code} Status Update\n"
                f"📍 Service: {appointment.appointment_service}\n"
                f"🏢 Workshop: {appointment.service_workshop.workshop_name}\n"
                f"🔄 Status: {status_display}\n"
                f"📞 Contact: {appointment.service_workshop.workshop_phone}"
            )

            sms_service.send_sms(
                phone_number=appointment.client.phone,
                message=message,
                purpose='appointment_status_update'
            )

        except Exception as e:
            logger.error(f"Error sending status update notification: {str(e)}")

    @action(detail=True, methods=['post'])
    def cancel_appointment(self, request, appointment_code=None):
        """
        Cancel an appointment
        """
        appointment = self.get_object()

        canceller_id = request.data.get('canceller_id')
        canceller_type = request.data.get('canceller_type')  # 'client' or 'workshop'

        if not canceller_id or not canceller_type:
            return Response({
                'success': False,
                'message': 'Canceller ID and type are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify ownership
        if canceller_type == 'client':
            if str(appointment.client_id) != canceller_id:
                return Response({
                    'success': False,
                    'message': 'You cannot cancel this appointment'
                }, status=status.HTTP_403_FORBIDDEN)
        elif canceller_type == 'workshop':
            if str(appointment.service_workshop_id) != canceller_id:
                return Response({
                    'success': False,
                    'message': 'You cannot cancel this appointment'
                }, status=status.HTTP_403_FORBIDDEN)

        # Check if appointment can be cancelled
        if appointment.appointment_status not in ['scheduled', 'confirmed']:
            return Response({
                'success': False,
                'message': f'Cannot cancel appointment with status: {appointment.appointment_status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        old_status = appointment.appointment_status
        appointment.appointment_status = 'cancelled'
        appointment.save()

        # Send cancellation notification
        self._send_cancellation_notification(appointment, canceller_type)

        return Response({
            'success': True,
            'message': 'Appointment cancelled successfully',
            'data': self.get_serializer(appointment).data
        })

    def _send_cancellation_notification(self, appointment, cancelled_by):
        """Send cancellation notification"""
        try:
            # Notify the other party
            if cancelled_by == 'client':
                # Client cancelled, notify workshop
                if appointment.service_workshop.workshop_phone:
                    message = (
                        f"❌ Appointment #{appointment.appointment_code} Cancelled by Client\n"
                        f"📍 Service: {appointment.appointment_service}\n"
                        f"👤 Client: {appointment.client.get_full_name() or 'Client'}\n"
                        f"📞 Client Phone: {appointment.client.phone}\n\n"
                        f"The client has cancelled this appointment."
                    )
                    sms_service.send_sms(
                        phone_number=appointment.service_workshop.workshop_phone,
                        message=message,
                        purpose='appointment_cancelled_by_client'
                    )
            else:
                # Workshop cancelled, notify client
                if appointment.client.phone:
                    message = (
                        f"❌ Appointment #{appointment.appointment_code} Cancelled by Workshop\n"
                        f"📍 Service: {appointment.appointment_service}\n"
                        f"🏢 Workshop: {appointment.service_workshop.workshop_name}\n"
                        f"📞 Workshop Phone: {appointment.service_workshop.workshop_phone}\n\n"
                        f"The workshop has cancelled this appointment."
                    )
                    sms_service.send_sms(
                        phone_number=appointment.client.phone,
                        message=message,
                        purpose='appointment_cancelled_by_workshop'
                    )

        except Exception as e:
            logger.error(f"Error sending cancellation notification: {str(e)}")

    @action(detail=True, methods=['post'])
    def resend_confirmation(self, request, appointment_code=None):
        """
        Resend confirmation SMS
        """
        appointment = self.get_object()

        requester_id = request.data.get('requester_id')
        requester_type = request.data.get('requester_type')

        if not requester_id or not requester_type:
            return Response({
                'success': False,
                'message': 'Requester ID and type are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify ownership
        if requester_type == 'client':
            if str(appointment.client_id) != requester_id:
                return Response({
                    'success': False,
                    'message': 'You cannot resend SMS for this appointment'
                }, status=status.HTTP_403_FORBIDDEN)
        elif requester_type == 'workshop':
            if str(appointment.service_workshop_id) != requester_id:
                return Response({
                    'success': False,
                    'message': 'You cannot resend SMS for this appointment'
                }, status=status.HTTP_403_FORBIDDEN)

        success = appointment.send_confirmation_notification()

        if success:
            return Response({
                'success': True,
                'message': 'Confirmation SMS resent successfully'
            })
        else:
            return Response({
                'success': False,
                'message': 'Failed to resend confirmation SMS'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def upcoming_appointments(self, request):
        """
        Get upcoming appointments
        """
        client_id = request.query_params.get('client_id')
        workshop_id = request.query_params.get('workshop_id')

        if not client_id and not workshop_id:
            return Response({
                'success': False,
                'message': 'Either client_id or workshop_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if client_id:
            appointments = ServiceAppointment.objects.filter(
                client_id=client_id,
                appointment_date__gte=timezone.now().date(),
                appointment_status__in=['confirmed', 'in_progress']
            )
        else:
            appointments = ServiceAppointment.objects.filter(
                service_workshop_id=workshop_id,
                appointment_date__gte=timezone.now().date(),
                appointment_status__in=['confirmed', 'in_progress']
            )

        appointments = appointments.order_by('appointment_date', 'appointment_time')[:20]

        serializer = self.get_serializer(appointments, many=True)

        return Response({
            'success': True,
            'count': appointments.count(),
            'data': serializer.data
        })

    @action(detail=False, methods=['get'])
    def appointment_statistics(self, request):
        """
        Get appointment statistics
        """
        client_id = request.query_params.get('client_id')
        workshop_id = request.query_params.get('workshop_id')

        if not client_id and not workshop_id:
            return Response({
                'success': False,
                'message': 'Either client_id or workshop_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if client_id:
            queryset = ServiceAppointment.objects.filter(client_id=client_id)
        else:
            queryset = ServiceAppointment.objects.filter(service_workshop_id=workshop_id)

        # Calculate stats
        total = queryset.count()
        by_status = queryset.values('appointment_status').annotate(count=Count('id'))

        # Revenue (for workshop)
        from django.db.models import Sum
        revenue = 0
        if workshop_id:
            revenue = queryset.filter(appointment_status='completed').aggregate(
                total=Sum('agreed_price')
            )['total'] or 0

        # Today's appointments
        today = queryset.filter(
            appointment_date=timezone.now().date(),
            appointment_status__in=['confirmed', 'in_progress']
        ).count()

        # Tomorrow's appointments
        tomorrow = timezone.now().date() + timedelta(days=1)
        tomorrow_count = queryset.filter(
            appointment_date=tomorrow,
            appointment_status__in=['confirmed', 'in_progress']
        ).count()

        return Response({
            'success': True,
            'stats': {
                'total': total,
                'today': today,
                'tomorrow': tomorrow_count,
                'by_status': list(by_status),
                'revenue': float(revenue) if revenue else 0
            }
        })


# ======================= AUTO WORKSHOPS =======================
class AutoWorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for auto workshops (read-only for public)
    """
    queryset = AutoWorkshop.objects.filter(is_workshop_active=True, is_workshop_verified=True)
    serializer_class = AutoWorkshopSerializer

    # REMOVED ALL AUTHENTICATION FOR DEVELOPMENT
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by city
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(workshop_city__icontains=city)

        # Filter by service
        service_name = self.request.query_params.get('service')
        if service_name:
            # This would need a more complex query if you want to filter by services offered
            pass

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(workshop_name__icontains=search) |
                Q(workshop_address__icontains=search) |
                Q(workshop_city__icontains=search)
            )

        return queryset.order_by('workshop_name')


# ======================= REPAIR SERVICES =======================
class RepairServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for repair services
    """
    queryset = RepairService.objects.filter(is_service_active=True)
    serializer_class = RepairServiceSerializer

    # REMOVED ALL AUTHENTICATION FOR DEVELOPMENT
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(service_category__icontains=category)

        # Filter by workshop
        workshop_id = self.request.query_params.get('workshop_id')
        if workshop_id:
            queryset = queryset.filter(workshop_id=workshop_id)

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(service_title__icontains=search) |
                Q(service_description__icontains=search)
            )

        return queryset.order_by('service_title')






# ==========================================// STATUS UPDATES WITH EMAIL NOTIFICATIONS//=====================
# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from registration.models import CustomerRequest
from .serializers import CustomerReqSerializer
import logging
import json

logger = logging.getLogger(__name__)

class CustomerReqViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CustomerRequest model with email notifications
    and embedded HTML interface
    """
    queryset = CustomerRequest.objects.all()
    serializer_class = CustomerReqSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        if user.is_staff:
            return CustomerRequest.objects.all()
        return CustomerRequest.objects.filter(customer=user)

    def perform_create(self, serializer):
        """Set customer to current user when creating"""
        serializer.save(customer=self.request.user)

    # Custom action to update only the status field
    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Update only the status field of a CustomerRequest
        """
        instance = self.get_object()
        new_status = request.data.get('request_status')

        if not new_status:
            return Response(
                {'error': 'request_status field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate status
        valid_statuses = [choice[0] for choice in CustomerRequest.REQUEST_STATUS]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Valid options: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        old_status = instance.request_status
        instance.request_status = new_status
        instance.save()

        # Send email notification
        self.send_status_change_email(instance, old_status, new_status)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Override update to send email notification"""
        instance = self.get_object()
        old_status = instance.request_status

        serializer.save()

        updated_instance = self.get_object()
        new_status = updated_instance.request_status

        if old_status != new_status:
            self.send_status_change_email(updated_instance, old_status, new_status)

    def perform_destroy(self, instance):
        """Override delete to send email notification"""
        self.send_deletion_email(instance)
        instance.delete()

    # Custom API to delete by ID
    @action(detail=False, methods=['delete'], url_path='delete-by-id')
    def delete_by_id(self, request):
        """
        Delete CustomerRequest by ID
        DELETE /api/customer-requests/delete-by-id/
        """
        request_id = request.data.get('id')

        if not request_id:
            return Response(
                {'error': 'id field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if request.user.is_staff:
                instance = CustomerRequest.objects.get(id=request_id)
            else:
                instance = CustomerRequest.objects.get(id=request_id, customer=request.user)

            self.send_deletion_email(instance)
            instance.delete()

            return Response(
                {'message': f'Request {instance.request_code} deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )

        except CustomerRequest.DoesNotExist:
            return Response(
                {'error': f'Request with id {request_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting request: {str(e)}")
            return Response(
                {'error': 'An error occurred during deletion'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def send_status_change_email(self, instance, old_status, new_status):
        """Send email notification when status changes"""
        try:
            subject = f'Customer Request Status Update: {instance.request_code}'

            # Embedded HTML email template
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.8;
                        color: #333;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 40px 0;
                    }}
                    .container {{
                        max-width: 700px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 20px;
                        overflow: hidden;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #4f46e5 0%, #7e22ce 100%);
                        color: white;
                        padding: 40px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 28px;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                    }}
                    .header .code {{
                        display: inline-block;
                        background: rgba(255,255,255,0.2);
                        padding: 10px 20px;
                        border-radius: 50px;
                        margin-top: 15px;
                        font-size: 18px;
                        font-weight: bold;
                        backdrop-filter: blur(10px);
                    }}
                    .content {{
                        padding: 40px;
                    }}
                    .status-change {{
                        background: linear-gradient(135deg, #dbeafe 0%, #e0e7ff 100%);
                        padding: 25px;
                        border-radius: 15px;
                        margin-bottom: 30px;
                        border-left: 6px solid #4f46e5;
                    }}
                    .status-row {{
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 30px;
                        margin: 20px 0;
                    }}
                    .status-box {{
                        flex: 1;
                        text-align: center;
                        padding: 20px;
                        border-radius: 12px;
                        position: relative;
                    }}
                    .status-box.old {{
                        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                        color: #92400e;
                    }}
                    .status-box.new {{
                        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                        color: #065f46;
                    }}
                    .status-label {{
                        font-size: 12px;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin-bottom: 5px;
                        opacity: 0.8;
                    }}
                    .status-value {{
                        font-size: 20px;
                        font-weight: bold;
                        margin: 5px 0;
                    }}
                    .arrow {{
                        font-size: 30px;
                        color: #4f46e5;
                        font-weight: bold;
                    }}
                    .info-grid {{
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 25px;
                        margin: 30px 0;
                    }}
                    .info-card {{
                        background: #f8fafc;
                        padding: 20px;
                        border-radius: 12px;
                        border: 1px solid #e2e8f0;
                    }}
                    .info-card h3 {{
                        color: #4f46e5;
                        margin: 0 0 15px 0;
                        font-size: 16px;
                        font-weight: 600;
                    }}
                    .detail-row {{
                        display: flex;
                        justify-content: space-between;
                        padding: 8px 0;
                        border-bottom: 1px solid #e2e8f0;
                    }}
                    .detail-row:last-child {{
                        border-bottom: none;
                    }}
                    .detail-label {{
                        color: #64748b;
                        font-size: 14px;
                    }}
                    .detail-value {{
                        font-weight: 500;
                        color: #1e293b;
                    }}
                    .footer {{
                        text-align: center;
                        padding: 25px;
                        background: #f8fafc;
                        color: #64748b;
                        font-size: 13px;
                        border-top: 1px solid #e2e8f0;
                    }}
                    .badge {{
                        display: inline-block;
                        padding: 6px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 600;
                        margin: 2px;
                    }}
                    .badge-urgent {{ background: #fef3c7; color: #92400e; }}
                    .badge-priority {{ background: #fef3c7; color: #92400e; }}
                    .badge-emergency {{ background: #fee2e2; color: #991b1b; }}
                    .badge-standard {{ background: #d1fae5; color: #065f46; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📋 Customer Request Status Update</h1>
                        <div class="code">{instance.request_code}</div>
                    </div>

                    <div class="content">
                        <div class="status-change">
                            <h2 style="text-align: center; color: #4f46e5; margin: 0 0 20px 0;">Status Change Notification</h2>
                            <div class="status-row">
                                <div class="status-box old">
                                    <div class="status-label">Previous Status</div>
                                    <div class="status-value">{old_status.replace('_', ' ').title()}</div>
                                </div>
                                <div class="arrow">→</div>
                                <div class="status-box new">
                                    <div class="status-label">New Status</div>
                                    <div class="status-value">{new_status.replace('_', ' ').title()}</div>
                                </div>
                            </div>
                        </div>

                        <div class="info-grid">
                            <div class="info-card">
                                <h3>👤 Customer Information</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Name</span>
                                    <span class="detail-value">{instance.customer.get_full_name() or instance.customer.username}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Email</span>
                                    <span class="detail-value">{instance.customer.email}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Contact Preference</span>
                                    <span class="detail-value">{instance.get_preferred_contact_display()}</span>
                                </div>
                            </div>

                            <div class="info-card">
                                <h3>🔧 Service Details</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Service</span>
                                    <span class="detail-value">{instance.requested_service}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Urgency</span>
                                    <span class="detail-value">
                                        <span class="badge badge-{instance.request_urgency}">
                                            {instance.get_request_urgency_display()}
                                        </span>
                                    </span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Budget Range</span>
                                    <span class="detail-value">
                                        ${instance.budget_minimum or '0'} - ${instance.budget_maximum or 'Flexible'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div class="info-grid">
                            <div class="info-card">
                                <h3>🚗 Vehicle Information</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Details</span>
                                    <span class="detail-value">{instance.get_vehicle_details()}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Year</span>
                                    <span class="detail-value">{instance.vehicle_year or 'N/A'}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">License Plate</span>
                                    <span class="detail-value">{instance.license_plate or 'N/A'}</span>
                                </div>
                            </div>

                            <div class="info-card">
                                <h3>📅 Service Schedule</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Preferred Date</span>
                                    <span class="detail-value">{instance.preferred_service_date}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Preferred Time</span>
                                    <span class="detail-value">{instance.preferred_service_time}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Location</span>
                                    <span class="detail-value">{instance.service_location[:30]}...</span>
                                </div>
                            </div>
                        </div>

                        <div style="margin-top: 30px; padding: 20px; background: #f8fafc; border-radius: 12px;">
                            <div class="detail-row">
                                <span class="detail-label">Times Viewed by Workshops</span>
                                <span class="detail-value">{instance.times_viewed}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Request Created</span>
                                <span class="detail-value">{instance.request_created.strftime('%Y-%m-%d %H:%M')}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Last Updated</span>
                                <span class="detail-value">{instance.request_updated.strftime('%Y-%m-%d %H:%M')}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Request Expires</span>
                                <span class="detail-value">{instance.request_expires.strftime('%Y-%m-%d %H:%M')}</span>
                            </div>
                        </div>
                    </div>

                    <div class="footer">
                        <p>This is an automated notification from the Customer Request Management System</p>
                        <p>Please do not reply to this email • {timezone.now().strftime('%Y-%m-%d %H:%M')}</p>
                    </div>
                </div>
            </body>
            </html>
            """

            plain_message = f"""
            Customer Request Status Update

            Request Code: {instance.request_code}
            Customer: {instance.customer.get_full_name() or instance.customer.username}
            Service: {instance.requested_service}

            Status Changed: {old_status} → {new_status}

            Vehicle: {instance.get_vehicle_details()}
            Location: {instance.service_location}
            Scheduled: {instance.preferred_service_date} at {instance.preferred_service_time}

            Request created: {instance.request_created}
            Last updated: {instance.request_updated}
            Expires: {instance.request_expires}
            """

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['qfix910@gmail.com'],
                html_message=html_content,
                fail_silently=False,
            )

            logger.info(f"Status change email sent for request {instance.request_code}")

        except Exception as e:
            logger.error(f"Failed to send status change email: {str(e)}")

    def send_deletion_email(self, instance):
        """Send email notification when request is deleted"""
        try:
            subject = f'⚠️ Customer Request Deleted: {instance.request_code}'

            # Embedded HTML email template for deletion
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.8;
                        color: #333;
                        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                        margin: 0;
                        padding: 40px 0;
                    }}
                    .container {{
                        max-width: 700px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 20px;
                        overflow: hidden;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                        color: white;
                        padding: 40px;
                        text-align: center;
                        position: relative;
                        overflow: hidden;
                    }}
                    .header::before {{
                        content: "⚠️";
                        font-size: 80px;
                        position: absolute;
                        opacity: 0.2;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 28px;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                        position: relative;
                        z-index: 1;
                    }}
                    .header .code {{
                        display: inline-block;
                        background: rgba(255,255,255,0.2);
                        padding: 10px 20px;
                        border-radius: 50px;
                        margin-top: 15px;
                        font-size: 18px;
                        font-weight: bold;
                        backdrop-filter: blur(10px);
                        position: relative;
                        z-index: 1;
                    }}
                    .warning-banner {{
                        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                        color: #92400e;
                        padding: 20px;
                        text-align: center;
                        font-weight: bold;
                        border-bottom: 3px solid #f59e0b;
                    }}
                    .content {{
                        padding: 40px;
                    }}
                    .deleted-info {{
                        background: #fef2f2;
                        padding: 30px;
                        border-radius: 15px;
                        margin-bottom: 30px;
                        border: 2px dashed #f87171;
                    }}
                    .info-grid {{
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 25px;
                        margin: 30px 0;
                    }}
                    .info-card {{
                        background: #f8fafc;
                        padding: 20px;
                        border-radius: 12px;
                        border: 1px solid #e2e8f0;
                    }}
                    .info-card h3 {{
                        color: #dc2626;
                        margin: 0 0 15px 0;
                        font-size: 16px;
                        font-weight: 600;
                    }}
                    .detail-row {{
                        display: flex;
                        justify-content: space-between;
                        padding: 8px 0;
                        border-bottom: 1px solid #e2e8f0;
                    }}
                    .detail-row:last-child {{
                        border-bottom: none;
                    }}
                    .detail-label {{
                        color: #64748b;
                        font-size: 14px;
                    }}
                    .detail-value {{
                        font-weight: 500;
                        color: #1e293b;
                    }}
                    .footer {{
                        text-align: center;
                        padding: 25px;
                        background: #f8fafc;
                        color: #64748b;
                        font-size: 13px;
                        border-top: 1px solid #e2e8f0;
                    }}
                    .status-badge {{
                        display: inline-block;
                        padding: 6px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                    .status-awaiting {{ background: #fef3c7; color: #92400e; }}
                    .status-in_progress {{ background: #dbeafe; color: #1e40af; }}
                    .status-completed {{ background: #d1fae5; color: #065f46; }}
                    .status-cancelled {{ background: #fecaca; color: #991b1b; }}
                    .status-expired {{ background: #e5e7eb; color: #374151; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚨 Customer Request Deleted</h1>
                        <div class="code">{instance.request_code}</div>
                    </div>

                    <div class="warning-banner">
                        ⚠️ This customer request has been permanently deleted from the system
                    </div>

                    <div class="content">
                        <div class="deleted-info">
                            <h2 style="text-align: center; color: #dc2626; margin: 0 0 20px 0;">Request Information at Time of Deletion</h2>

                            <div style="text-align: center; margin: 20px 0;">
                                <span class="status-badge status-{instance.request_status}">
                                    {instance.get_request_status_display()}
                                </span>
                            </div>
                        </div>

                        <div class="info-grid">
                            <div class="info-card">
                                <h3>👤 Customer Details</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Name</span>
                                    <span class="detail-value">{instance.customer.get_full_name() or instance.customer.username}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Email</span>
                                    <span class="detail-value">{instance.customer.email}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Deleted By</span>
                                    <span class="detail-value">{self.request.user.get_full_name() or self.request.user.username}</span>
                                </div>
                            </div>

                            <div class="info-card">
                                <h3>🔧 Service Information</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Service Requested</span>
                                    <span class="detail-value">{instance.requested_service}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Description</span>
                                    <span class="detail-value">{instance.request_description[:50] or 'No description'}...</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Urgency Level</span>
                                    <span class="detail-value">{instance.get_request_urgency_display()}</span>
                                </div>
                            </div>
                        </div>

                        <div class="info-grid">
                            <div class="info-card">
                                <h3>🚗 Vehicle Details</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Vehicle</span>
                                    <span class="detail-value">{instance.get_vehicle_details()}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Brand/Model</span>
                                    <span class="detail-value">{instance.vehicle_brand or 'N/A'} {instance.vehicle_model or ''}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Year/Color</span>
                                    <span class="detail-value">{instance.vehicle_year or 'N/A'} / {instance.vehicle_color or 'N/A'}</span>
                                </div>
                            </div>

                            <div class="info-card">
                                <h3>📅 Scheduling & Location</h3>
                                <div class="detail-row">
                                    <span class="detail-label">Preferred Date</span>
                                    <span class="detail-value">{instance.preferred_service_date}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Preferred Time</span>
                                    <span class="detail-value">{instance.preferred_service_time}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">Service Location</span>
                                    <span class="detail-value">{instance.service_location[:40]}...</span>
                                </div>
                            </div>
                        </div>

                        <div style="margin-top: 30px; padding: 20px; background: #fef2f2; border-radius: 12px;">
                            <h3 style="color: #dc2626; margin: 0 0 15px 0;">Deletion Audit Trail</h3>
                            <div class="detail-row">
                                <span class="detail-label">Deletion Timestamp</span>
                                <span class="detail-value">{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Request Created</span>
                                <span class="detail-value">{instance.request_created.strftime('%Y-%m-%d %H:%M')}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Last Updated</span>
                                <span class="detail-value">{instance.request_updated.strftime('%Y-%m-%d %H:%M')}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Times Viewed</span>
                                <span class="detail-value">{instance.times_viewed}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Request Expiry</span>
                                <span class="detail-value">{instance.request_expires.strftime('%Y-%m-%d %H:%M')}</span>
                            </div>
                        </div>
                    </div>

                    <div class="footer">
                        <p><strong>⚠️ IMPORTANT:</strong> This action is irreversible. The request has been permanently removed from the database.</p>
                        <p>Automated deletion notification • {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                </div>
            </body>
            </html>
            """

            plain_message = f"""
            ⚠️ CUSTOMER REQUEST DELETED ⚠️

            Request Code: {instance.request_code}
            Customer: {instance.customer.get_full_name() or instance.customer.username}
            Service: {instance.requested_service}

            Status at deletion: {instance.request_status}

            Vehicle: {instance.get_vehicle_details()}
            Location: {instance.service_location}
            Scheduled: {instance.preferred_service_date} at {instance.preferred_service_time}

            Deleted by: {self.request.user.get_full_name() or self.request.user.username}
            Deleted at: {timezone.now()}

            Request created: {instance.request_created}
            Last updated: {instance.request_updated}
            Expires: {instance.request_expires}

            ⚠️ This action is irreversible.
            """

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['qfix910@gmail.com'],
                html_message=html_content,
                fail_silently=False,
            )

            logger.info(f"Deletion email sent for request {instance.request_code}")

        except Exception as e:
            logger.error(f"Failed to send deletion email: {str(e)}")

    @action(detail=False, methods=['get'], url_path='web-interface')
    def web_interface(self, request):
        """
        Embedded HTML web interface for managing customer requests
        GET /api/customer-requests/web-interface/
        """
        user = request.user
        requests = self.get_queryset()

        # Get status display mapping
        status_display = dict(CustomerRequest.REQUEST_STATUS)

        # Embedded HTML template with modern styling
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Customer Requests Management | QFix System</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                :root {{
                    --primary: #4f46e5;
                    --primary-dark: #3730a3;
                    --secondary: #10b981;
                    --danger: #ef4444;
                    --warning: #f59e0b;
                    --light: #f8fafc;
                    --dark: #1e293b;
                    --gray: #64748b;
                    --gray-light: #e2e8f0;
                }}

                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: var(--dark);
                    line-height: 1.6;
                    min-height: 100vh;
                    padding: 20px;
                }}

                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}

                .glass-card {{
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 24px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.15);
                    overflow: hidden;
                    margin-bottom: 30px;
                }}

                /* Header Styles */
                .header {{
                    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                    color: white;
                    padding: 40px 50px;
                    position: relative;
                    overflow: hidden;
                }}

                .header::before {{
                    content: '';
                    position: absolute;
                    top: -50%;
                    right: -50%;
                    width: 100%;
                    height: 200%;
                    background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
                    background-size: 30px 30px;
                    transform: rotate(30deg);
                }}

                .header-content {{
                    position: relative;
                    z-index: 2;
                }}

                .header h1 {{
                    font-size: 2.8rem;
                    font-weight: 800;
                    margin-bottom: 10px;
                    background: linear-gradient(135deg, #fff 0%, #e0e7ff 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }}

                .header-subtitle {{
                    font-size: 1.1rem;
                    opacity: 0.9;
                    margin-bottom: 20px;
                }}

                .user-info {{
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    margin-top: 20px;
                    padding: 15px 25px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 15px;
                    backdrop-filter: blur(5px);
                    max-width: fit-content;
                }}

                .avatar {{
                    width: 50px;
                    height: 50px;
                    background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.3rem;
                    font-weight: bold;
                    color: white;
                }}

                /* Stats Cards */
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    padding: 30px 50px;
                    background: var(--light);
                }}

                .stat-card {{
                    background: white;
                    padding: 25px;
                    border-radius: 16px;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.05);
                    text-align: center;
                    transition: transform 0.3s ease;
                }}

                .stat-card:hover {{
                    transform: translateY(-5px);
                }}

                .stat-icon {{
                    font-size: 2.5rem;
                    margin-bottom: 15px;
                    color: var(--primary);
                }}

                .stat-value {{
                    font-size: 2.2rem;
                    font-weight: 800;
                    color: var(--dark);
                    margin-bottom: 5px;
                }}

                .stat-label {{
                    color: var(--gray);
                    font-size: 0.9rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}

                /* Requests Table */
                .requests-section {{
                    padding: 40px 50px;
                }}

                .section-title {{
                    font-size: 1.8rem;
                    font-weight: 700;
                    color: var(--dark);
                    margin-bottom: 30px;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }}

                .section-title i {{
                    color: var(--primary);
                }}

                .requests-table-container {{
                    overflow-x: auto;
                    border-radius: 16px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    min-width: 1000px;
                }}

                thead {{
                    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                    color: white;
                }}

                th {{
                    padding: 20px 25px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 0.9rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}

                tbody tr {{
                    border-bottom: 1px solid var(--gray-light);
                    transition: background 0.3s ease;
                }}

                tbody tr:hover {{
                    background: var(--light);
                }}

                td {{
                    padding: 20px 25px;
                }}

                /* Status Badges */
                .status-badge {{
                    display: inline-flex;
                    align-items: center;
                    padding: 8px 16px;
                    border-radius: 50px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}

                .status-awaiting {{ background: #fef3c7; color: #92400e; }}
                .status-viewed {{ background: #dbeafe; color: #1e40af; }}
                .status-offers_received {{ background: #e0e7ff; color: #3730a3; }}
                .status-accepted {{ background: #d1fae5; color: #065f46; }}
                .status-in_progress {{ background: #f3e8ff; color: #6b21a8; }}
                .status-completed {{ background: #dcfce7; color: #166534; }}
                .status-cancelled {{ background: #fee2e2; color: #991b1b; }}
                .status-expired {{ background: #f1f5f9; color: #475569; }}

                /* Action Buttons */
                .action-buttons {{
                    display: flex;
                    gap: 10px;
                }}

                .btn {{
                    padding: 10px 20px;
                    border: none;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 0.9rem;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                }}

                .btn-primary {{
                    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                    color: white;
                }}

                .btn-primary:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 20px rgba(79, 70, 229, 0.3);
                }}

                .btn-danger {{
                    background: linear-gradient(135deg, var(--danger) 0%, #dc2626 100%);
                    color: white;
                }}

                .btn-danger:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 20px rgba(239, 68, 68, 0.3);
                }}

                .btn-warning {{
                    background: linear-gradient(135deg, var(--warning) 0%, #d97706 100%);
                    color: white;
                }}

                .btn-warning:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 20px rgba(245, 158, 11, 0.3);
                }}

                /* Modal */
                .modal {{
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.8);
                    backdrop-filter: blur(5px);
                    z-index: 1000;
                    align-items: center;
                    justify-content: center;
                }}

                .modal.active {{
                    display: flex;
                }}

                .modal-content {{
                    background: white;
                    width: 90%;
                    max-width: 500px;
                    border-radius: 24px;
                    overflow: hidden;
                    animation: modalSlide 0.3s ease;
                }}

                @keyframes modalSlide {{
                    from {{ transform: translateY(-50px); opacity: 0; }}
                    to {{ transform: translateY(0); opacity: 1; }}
                }}

                .modal-header {{
                    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                    color: white;
                    padding: 25px 30px;
                }}

                .modal-body {{
                    padding: 30px;
                }}

                .form-group {{
                    margin-bottom: 25px;
                }}

                .form-group label {{
                    display: block;
                    margin-bottom: 10px;
                    font-weight: 600;
                    color: var(--dark);
                }}

                .form-select {{
                    width: 100%;
                    padding: 15px;
                    border: 2px solid var(--gray-light);
                    border-radius: 12px;
                    font-size: 1rem;
                    background: white;
                    color: var(--dark);
                    transition: border 0.3s ease;
                }}

                .form-select:focus {{
                    outline: none;
                    border-color: var(--primary);
                }}

                .modal-footer {{
                    padding: 20px 30px;
                    background: var(--light);
                    display: flex;
                    justify-content: flex-end;
                    gap: 15px;
                }}

                /* Empty State */
                .empty-state {{
                    text-align: center;
                    padding: 60px 40px;
                }}

                .empty-state i {{
                    font-size: 4rem;
                    color: var(--gray-light);
                    margin-bottom: 20px;
                }}

                /* Responsive */
                @media (max-width: 768px) {{
                    .header {{
                        padding: 30px 25px;
                    }}

                    .header h1 {{
                        font-size: 2rem;
                    }}

                    .stats-grid,
                    .requests-section {{
                        padding: 25px;
                    }}

                    .action-buttons {{
                        flex-direction: column;
                    }}

                    .btn {{
                        width: 100%;
                        justify-content: center;
                    }}
                }}

                /* Loading */
                .loading {{
                    text-align: center;
                    padding: 40px;
                    color: var(--gray);
                }}

                .loading i {{
                    font-size: 2rem;
                    margin-bottom: 15px;
                    color: var(--primary);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="glass-card">
                    <!-- Header -->
                    <div class="header">
                        <div class="header-content">
                            <h1><i class="fas fa-tools"></i> Customer Requests Management</h1>
                            <p class="header-subtitle">Manage and monitor all customer service requests in one place</p>
                            <div class="user-info">
                                <div class="avatar">
                                    {user.username[0].upper() if user.username else 'U'}
                                </div>
                                <div>
                                    <div style="font-weight: bold;">{user.get_full_name() or user.username}</div>
                                    <div style="font-size: 0.9rem; opacity: 0.8;">{user.email}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Stats Overview -->
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-icon"><i class="fas fa-list-alt"></i></div>
                            <div class="stat-value">{requests.count()}</div>
                            <div class="stat-label">Total Requests</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon"><i class="fas fa-clock"></i></div>
                            <div class="stat-value">{requests.filter(request_status='awaiting').count()}</div>
                            <div class="stat-label">Awaiting Offers</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon"><i class="fas fa-cogs"></i></div>
                            <div class="stat-value">{requests.filter(request_status='in_progress').count()}</div>
                            <div class="stat-label">In Progress</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
                            <div class="stat-value">{requests.filter(request_status='completed').count()}</div>
                            <div class="stat-label">Completed</div>
                        </div>
                    </div>

                    <!-- Requests Table -->
                    <div class="requests-section">
                        <div class="section-title">
                            <i class="fas fa-clipboard-list"></i>
                            Service Requests
                            <span style="font-size: 0.9rem; color: var(--gray); margin-left: auto;">
                                Showing {requests.count()} requests
                            </span>
                        </div>

                        <div class="requests-table-container">
                            {self.generate_requests_table(requests, status_display) if requests.exists() else self.generate_empty_state()}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Update Status Modal -->
            <div id="updateModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 style="margin: 0; font-size: 1.5rem;"><i class="fas fa-sync-alt"></i> Update Request Status</h2>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label for="newStatus">Select New Status</label>
                            <select id="newStatus" class="form-select">
                                {self.generate_status_options()}
                            </select>
                        </div>
                        <div id="statusDescription" style="padding: 15px; background: #f8fafc; border-radius: 12px; font-size: 0.9rem; color: var(--gray);">
                            Select a status to see description
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn" onclick="closeModal()" style="background: var(--gray-light);">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="updateStatus()">
                            <i class="fas fa-save"></i> Update Status
                        </button>
                    </div>
                </div>
            </div>

            <script>
                let currentRequestId = null;
                let currentRequestCode = null;
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

                const statusDescriptions = {{
                    'awaiting': 'Request is waiting for workshop offers. Customers can still receive offers.',
                    'viewed': 'Request has been viewed by workshops but no offers received yet.',
                    'offers_received': 'One or more workshops have submitted offers for this request.',
                    'accepted': 'Customer has accepted an offer from a workshop.',
                    'in_progress': 'Workshop is currently performing the service.',
                    'completed': 'Service has been successfully completed.',
                    'cancelled': 'Request has been cancelled by customer or admin.',
                    'expired': 'Request has expired without being accepted (72 hours after creation).'
                }};

                function generateStatusOptions() {{
                    let options = '';
                    const statuses = {json.dumps([{'value': s[0], 'label': s[1]} for s in CustomerRequest.REQUEST_STATUS])};
                    statuses.forEach(status => {{
                        options += `<option value="${{status.value}}">${{status.label}}</option>`;
                    }});
                    return options;
                }}

                function openUpdateModal(requestId, requestCode, currentStatus) {{
                    currentRequestId = requestId;
                    currentRequestCode = requestCode;

                    const modal = document.getElementById('updateModal');
                    const statusSelect = document.getElementById('newStatus');
                    const descriptionEl = document.getElementById('statusDescription');

                    statusSelect.value = currentStatus;
                    descriptionEl.textContent = statusDescriptions[currentStatus] || 'No description available';

                    modal.classList.add('active');

                    // Add change event listener
                    statusSelect.onchange = function() {{
                        descriptionEl.textContent = statusDescriptions[this.value] || 'No description available';
                    }};
                }}

                function closeModal() {{
                    const modal = document.getElementById('updateModal');
                    modal.classList.remove('active');
                    currentRequestId = null;
                    currentRequestCode = null;
                }}

                async function updateStatus() {{
                    if (!currentRequestId) return;

                    const newStatus = document.getElementById('newStatus').value;

                    try {{
                        const response = await fetch(`/api/customer-requests/${{currentRequestId}}/update-status/`, {{
                            method: 'PATCH',
                            headers: {{
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCsrfToken()
                            }},
                            body: JSON.stringify({{ request_status: newStatus }})
                        }});

                        if (response.ok) {{
                            Swal.fire({{
                                icon: 'success',
                                title: 'Status Updated!',
                                text: `Request ${{currentRequestCode}} status has been updated.`,
                                confirmButtonColor: 'var(--primary)'
                            }});
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            const error = await response.json();
                            Swal.fire({{
                                icon: 'error',
                                title: 'Update Failed',
                                text: error.error || 'Failed to update status',
                                confirmButtonColor: 'var(--danger)'
                            }});
                        }}
                    }} catch (error) {{
                        Swal.fire({{
                            icon: 'error',
                            title: 'Network Error',
                            text: 'Please check your connection and try again',
                            confirmButtonColor: 'var(--danger)'
                        }});
                    }} finally {{
                        closeModal();
                    }}
                }}

                async function deleteRequest(requestId, requestCode) {{
                    const result = await Swal.fire({{
                        title: 'Delete Request?',
                        html: `<strong>${{requestCode}}</strong><br><br>
                              This action will permanently delete the request and send a notification email.<br><br>
                              <span style="color: var(--danger); font-weight: bold;">This action cannot be undone!</span>`,
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonColor: 'var(--danger)',
                        cancelButtonColor: 'var(--gray)',
                        confirmButtonText: 'Yes, delete it!',
                        cancelButtonText: 'Cancel',
                        reverseButtons: true
                    }});

                    if (result.isConfirmed) {{
                        try {{
                            const response = await fetch(`/api/customer-requests/delete-by-id/`, {{
                                method: 'DELETE',
                                headers: {{
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': getCsrfToken()
                                }},
                                body: JSON.stringify({{ id: requestId }})
                            }});

                            if (response.status === 204) {{
                                Swal.fire({{
                                    icon: 'success',
                                    title: 'Deleted!',
                                    text: `Request ${{requestCode}} has been deleted.`,
                                    confirmButtonColor: 'var(--primary)'
                                }});
                                setTimeout(() => location.reload(), 1500);
                            }} else {{
                                const error = await response.json();
                                Swal.fire({{
                                    icon: 'error',
                                    title: 'Deletion Failed',
                                    text: error.error || 'Failed to delete request',
                                    confirmButtonColor: 'var(--danger)'
                                }});
                            }}
                        }} catch (error) {{
                            Swal.fire({{
                                icon: 'error',
                                title: 'Network Error',
                                text: 'Please check your connection and try again',
                                confirmButtonColor: 'var(--danger)'
                            }});
                        }}
                    }}
                }}

                function getCsrfToken() {{
                    const cookieValue = document.cookie
                        .split('; ')
                        .find(row => row.startsWith('csrftoken='))
                        ?.split('=')[1];
                    return cookieValue || csrfToken;
                }}

                // Close modal on escape key
                document.addEventListener('keydown', (e) => {{
                    if (e.key === 'Escape') closeModal();
                }});

                // Close modal when clicking outside
                document.getElementById('updateModal').addEventListener('click', (e) => {{
                    if (e.target.id === 'updateModal') closeModal();
                }});
            </script>
        </body>
        </html>
        """

        return HttpResponse(html_template)

    def generate_requests_table(self, requests, status_display):
        """Generate HTML table rows for requests"""
        rows = []

        for req in requests:
            # Format vehicle details
            vehicle_details = req.get_vehicle_details()
            if len(vehicle_details) > 30:
                vehicle_details = vehicle_details[:27] + "..."

            # Format location
            location = req.service_location
            if len(location) > 25:
                location = location[:22] + "..."

            # Format service date
            service_date = req.preferred_service_date.strftime('%b %d, %Y')

            # Create row HTML
            row_html = f"""
            <tr>
                <td>
                    <div style="font-weight: 600; color: var(--primary);">{req.request_code}</div>
                    <div style="font-size: 0.85rem; color: var(--gray);">ID: {req.id}</div>
                </td>
                <td>
                    <div style="font-weight: 600;">{req.requested_service}</div>
                    <div style="font-size: 0.85rem; color: var(--gray);">{req.get_request_urgency_display()}</div>
                </td>
                <td>{vehicle_details}</td>
                <td>{location}</td>
                <td>
                    <div>{service_date}</div>
                    <div style="font-size: 0.85rem; color: var(--gray);">{req.preferred_service_time}</div>
                </td>
                <td>
                    <span class="status-badge status-{req.request_status}">
                        {status_display.get(req.request_status, req.request_status)}
                    </span>
                </td>
                <td>{req.times_viewed}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-primary"
                                onclick="openUpdateModal({req.id}, '{req.request_code}', '{req.request_status}')">
                            <i class="fas fa-edit"></i> Update
                        </button>
                        <button class="btn btn-danger"
                                onclick="deleteRequest({req.id}, '{req.request_code}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </td>
            </tr>
            """
            rows.append(row_html)

        table_html = f"""
        <table>
            <thead>
                <tr>
                    <th>Request Code</th>
                    <th>Service</th>
                    <th>Vehicle</th>
                    <th>Location</th>
                    <th>Preferred Date</th>
                    <th>Status</th>
                    <th>Views</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

        return table_html

    def generate_empty_state(self):
        """Generate HTML for empty requests state"""
        return """
        <div class="empty-state">
            <i class="fas fa-clipboard"></i>
            <h3 style="color: var(--gray); margin-bottom: 10px;">No Requests Found</h3>
            <p style="color: var(--gray); max-width: 400px; margin: 0 auto;">
                You don't have any customer service requests yet.
                When requests are created, they will appear here.
            </p>
        </div>
        """

    def generate_status_options(self):
        """Generate HTML options for status select"""
        options = []
        for value, label in CustomerRequest.REQUEST_STATUS:
            options.append(f'<option value="{value}">{label}</option>')
        return ''.join(options)



# =========================================//END//==========================================












# # registration/views.py
# from rest_framework import viewsets, status, permissions
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from django.db.models import Q, Count
# from django.utils import timezone
# from datetime import datetime, timedelta
# import logging

# from registration.models import (
#     CustomerRequest,
#     WorkshopQuote,
#     ServiceAppointment,
#     AutoWorkshop,
#     RepairService
# )
# from .serializers import (
#     CustomerRequestCreateSerializer,
#     CustomerRequestUpdateSerializer,
#     CustomerRequestDetailSerializer,
#     CustomerRequestListSerializer,
#     WorkshopQuoteSerializer,
#     WorkshopQuoteCreateSerializer,
#     ServiceAppointmentSerializer,
#     ServiceAppointmentCreateSerializer,
#     AutoWorkshopSerializer,
#     RepairServiceSerializer
# )

# logger = logging.getLogger(__name__)


# # ======================= PERMISSIONS =======================
# class IsOwnerOrReadOnly(permissions.BasePermission):
#     """Allow anyone to read, but only owner to modify"""

#     def has_object_permission(self, request, view, obj):
#         if request.method in permissions.SAFE_METHODS:
#             return True
#         return obj.customer == request.user


# # ======================= CUSTOMER REQUEST VIEWSET =======================
# class CustomerRequestViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for customer service requests with notifications
#     """
#     queryset = CustomerRequest.objects.all()
#     lookup_field = 'request_code'
#     lookup_url_kwarg = 'request_code'
#     permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return CustomerRequestCreateSerializer
#         elif self.action in ['update', 'partial_update']:
#             return CustomerRequestUpdateSerializer
#         elif self.action == 'list':
#             return CustomerRequestCreateSerializer
#         return CustomerRequestDetailSerializer

#     def get_queryset(self):
#         user = self.request.user

#         if self.action == 'list':
#             # Show all active requests for browsing
#             if self.request.query_params.get('active') == 'true':
#                 return CustomerRequest.objects.filter(
#                     request_expires__gt=timezone.now(),
#                     request_status__in=['awaiting', 'viewed', 'offers_received']
#                 ).order_by('-request_created')
#             # Show user's requests
#             return CustomerRequest.objects.filter(customer=user).order_by('-request_created')

#         # For detail view, anyone can see
#         return CustomerRequest.objects.all()

#     def create(self, request, *args, **kwargs):
#         """Create new request with notifications"""
#         try:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)

#             customer_request = serializer.save(customer=request.user)
#             # Notifications are sent automatically in model's save method

#             return Response({
#                 'success': True,
#                 'message': 'Service request created successfully!',
#                 'data': CustomerRequestDetailSerializer(customer_request).data
#             }, status=status.HTTP_201_CREATED)

#         except Exception as e:
#             logger.error(f"Failed to create request: {str(e)}")
#             return Response({
#                 'success': False,
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)

#     def update(self, request, *args, **kwargs):
#         """Update request with notifications"""
#         try:
#             instance = self.get_object()
#             old_status = instance.request_status

#             serializer = self.get_serializer(instance, data=request.data, partial=True)
#             serializer.is_valid(raise_exception=True)

#             customer_request = serializer.save()

#             # Send status change notification if status changed
#             if old_status != customer_request.request_status:
#                 customer_request.send_notifications('status_changed', {
#                     'old_status': old_status,
#                     'new_status': customer_request.request_status
#                 })
#             else:
#                 customer_request.send_notifications('updated')

#             return Response({
#                 'success': True,
#                 'message': 'Request updated successfully',
#                 'data': CustomerRequestDetailSerializer(customer_request).data
#             })

#         except Exception as e:
#             logger.error(f"Failed to update request: {str(e)}")
#             return Response({
#                 'success': False,
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['post'])
#     def cancel(self, request, request_code=None):
#         """Cancel a request"""
#         customer_request = self.get_object()

#         if customer_request.customer != request.user:
#             return Response({
#                 'success': False,
#                 'message': 'You can only cancel your own requests'
#             }, status=status.HTTP_403_FORBIDDEN)

#         if customer_request.request_status not in ['awaiting', 'viewed', 'offers_received']:
#             return Response({
#                 'success': False,
#                 'message': f'Cannot cancel request with status: {customer_request.request_status}'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         old_status = customer_request.request_status
#         customer_request.request_status = 'cancelled'
#         customer_request.save()

#         customer_request.send_notifications('cancelled', {
#             'old_status': old_status,
#             'new_status': 'cancelled'
#         })

#         return Response({
#             'success': True,
#             'message': 'Request cancelled successfully'
#         })

#     @action(detail=False, methods=['get'])
#     def my_requests(self, request):
#         """Get authenticated user's requests"""
#         requests = CustomerRequest.objects.filter(customer=request.user).order_by('-request_created')
#         serializer = CustomerRequestListSerializer(requests, many=True)
#         return Response({
#             'success': True,
#             'count': requests.count(),
#             'data': serializer.data
#         })

#     @action(detail=False, methods=['get'])
#     def active(self, request):
#         """Get active requests for browsing"""
#         requests = CustomerRequest.objects.filter(
#             request_expires__gt=timezone.now(),
#             request_status__in=['awaiting', 'viewed', 'offers_received']
#         ).order_by('-request_created')

#         serializer = CustomerRequestListSerializer(requests, many=True)
#         return Response({
#             'success': True,
#             'count': requests.count(),
#             'data': serializer.data
#         })


# # ======================= WORKSHOP QUOTE VIEWSET =======================
# class WorkshopQuoteViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for workshop quotes with notifications
#     """
#     queryset = WorkshopQuote.objects.all().select_related('customer_request', 'workshop')
#     permission_classes = [permissions.IsAuthenticated]

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return WorkshopQuoteCreateSerializer
#         return WorkshopQuoteSerializer

#     def get_queryset(self):
#         queryset = super().get_queryset()
#         user = self.request.user

#         # Filter by workshop
#         if user.groups.filter(name='Workshops').exists():
#             # Get workshops owned by user
#             workshops = AutoWorkshop.objects.filter(workshop_owner=user)
#             queryset = queryset.filter(workshop__in=workshops)

#         # Query params
#         workshop_id = self.request.query_params.get('workshop_id')
#         if workshop_id:
#             queryset = queryset.filter(workshop_id=workshop_id)

#         request_code = self.request.query_params.get('request_code')
#         if request_code:
#             queryset = queryset.filter(customer_request__request_code=request_code)

#         status = self.request.query_params.get('status')
#         if status:
#             queryset = queryset.filter(quote_status=status)

#         return queryset.order_by('-quote_created')

#     def create(self, request, *args, **kwargs):
#         """Create a new quote with notifications"""
#         try:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)

#             quote = serializer.save()
#             # Notifications are sent automatically in model's save method

#             return Response({
#                 'success': True,
#                 'message': 'Quote submitted successfully',
#                 'data': WorkshopQuoteSerializer(quote).data
#             }, status=status.HTTP_201_CREATED)

#         except Exception as e:
#             logger.error(f"Failed to create quote: {str(e)}")
#             return Response({
#                 'success': False,
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['post'])
#     def accept(self, request, pk=None):
#         """Accept a quote"""
#         quote = self.get_object()

#         # Verify customer owns the request
#         if quote.customer_request.customer != request.user:
#             return Response({
#                 'success': False,
#                 'message': 'You can only accept quotes for your own requests'
#             }, status=status.HTTP_403_FORBIDDEN)

#         # Accept the quote
#         appointment = quote.accept_quote()
#         # Notifications are sent in accept_quote method

#         return Response({
#             'success': True,
#             'message': 'Quote accepted successfully',
#             'data': {
#                 'quote': WorkshopQuoteSerializer(quote).data,
#                 'appointment': ServiceAppointmentSerializer(appointment).data
#             }
#         })

#     @action(detail=True, methods=['post'])
#     def withdraw(self, request, pk=None):
#         """Withdraw a quote"""
#         quote = self.get_object()

#         # Verify workshop owns the quote
#         workshops = AutoWorkshop.objects.filter(workshop_owner=request.user)
#         if quote.workshop not in workshops:
#             return Response({
#                 'success': False,
#                 'message': 'You can only withdraw your own quotes'
#             }, status=status.HTTP_403_FORBIDDEN)

#         if quote.quote_status != 'pending':
#             return Response({
#                 'success': False,
#                 'message': 'Only pending quotes can be withdrawn'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         quote.quote_status = 'withdrawn'
#         quote.save()

#         return Response({
#             'success': True,
#             'message': 'Quote withdrawn successfully'
#         })


# # ======================= SERVICE APPOINTMENT VIEWSET =======================
# class ServiceAppointmentViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for service appointments with notifications
#     """
#     queryset = ServiceAppointment.objects.all().select_related(
#         'client', 'service_workshop', 'customer_request', 'accepted_quote'
#     )
#     lookup_field = 'appointment_code'
#     lookup_url_kwarg = 'appointment_code'
#     permission_classes = [permissions.IsAuthenticated]

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return ServiceAppointmentCreateSerializer
#         return ServiceAppointmentSerializer

#     def get_queryset(self):
#         queryset = super().get_queryset()
#         user = self.request.user

#         # Filter by user role
#         if user.groups.filter(name='Workshops').exists():
#             workshops = AutoWorkshop.objects.filter(workshop_owner=user)
#             queryset = queryset.filter(service_workshop__in=workshops)
#         else:
#             queryset = queryset.filter(client=user)

#         # Query params
#         customer_id = self.request.query_params.get('customer_id')
#         if customer_id:
#             queryset = queryset.filter(client_id=customer_id)

#         workshop_id = self.request.query_params.get('workshop_id')
#         if workshop_id:
#             queryset = queryset.filter(service_workshop_id=workshop_id)

#         status = self.request.query_params.get('status')
#         if status:
#             queryset = queryset.filter(appointment_status=status)

#         # Date range
#         date_from = self.request.query_params.get('date_from')
#         if date_from:
#             try:
#                 date = datetime.strptime(date_from, '%Y-%m-%d').date()
#                 queryset = queryset.filter(appointment_date__gte=date)
#             except ValueError:
#                 pass

#         date_to = self.request.query_params.get('date_to')
#         if date_to:
#             try:
#                 date = datetime.strptime(date_to, '%Y-%m-%d').date()
#                 queryset = queryset.filter(appointment_date__lte=date)
#             except ValueError:
#                 pass

#         return queryset.order_by('-appointment_date', '-appointment_created')

#     def create(self, request, *args, **kwargs):
#         """Create appointment from accepted quote"""
#         try:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)

#             appointment = serializer.save()
#             # Notifications are sent automatically in model's save method

#             return Response({
#                 'success': True,
#                 'message': 'Appointment created successfully',
#                 'data': ServiceAppointmentSerializer(appointment).data
#             }, status=status.HTTP_201_CREATED)

#         except Exception as e:
#             logger.error(f"Failed to create appointment: {str(e)}")
#             return Response({
#                 'success': False,
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['post'])
#     def update_status(self, request, appointment_code=None):
#         """Update appointment status"""
#         appointment = self.get_object()
#         new_status = request.data.get('status')

#         if not new_status:
#             return Response({
#                 'success': False,
#                 'message': 'Status is required'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         if new_status not in dict(ServiceAppointment.APPOINTMENT_STATUS):
#             return Response({
#                 'success': False,
#                 'message': 'Invalid status'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         old_status = appointment.appointment_status
#         appointment.appointment_status = new_status
#         appointment.save()

#         # Send notifications
#         if old_status != new_status:
#             appointment.send_notifications('appointment_status_update', {
#                 'old_status': old_status,
#                 'new_status': new_status
#             })

#         # Send reminder if confirmed for tomorrow
#         if new_status == 'confirmed':
#             tomorrow = timezone.now().date() + timedelta(days=1)
#             if appointment.appointment_date == tomorrow:
#                 appointment.send_notifications('appointment_reminder')

#         return Response({
#             'success': True,
#             'message': f'Status updated to {new_status}',
#             'data': ServiceAppointmentSerializer(appointment).data
#         })

#     @action(detail=True, methods=['post'])
#     def cancel(self, request, appointment_code=None):
#         """Cancel appointment"""
#         appointment = self.get_object()

#         canceller_type = request.data.get('canceller_type', 'client')

#         # Verify permissions
#         if canceller_type == 'client' and appointment.client != request.user:
#             return Response({
#                 'success': False,
#                 'message': 'You cannot cancel this appointment'
#             }, status=status.HTTP_403_FORBIDDEN)

#         if appointment.appointment_status not in ['scheduled', 'confirmed']:
#             return Response({
#                 'success': False,
#                 'message': f'Cannot cancel appointment with status: {appointment.appointment_status}'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         appointment.appointment_status = 'cancelled'
#         appointment.save()

#         # Send cancellation notifications
#         appointment.send_notifications('appointment_cancelled')
#         if canceller_type == 'client':
#             appointment.notify_workshop('workshop_appointment_cancelled')

#         return Response({
#             'success': True,
#             'message': 'Appointment cancelled successfully',
#             'data': ServiceAppointmentSerializer(appointment).data
#         })

#     @action(detail=True, methods=['post'])
#     def resend_confirmation(self, request, appointment_code=None):
#         """Resend confirmation notifications"""
#         appointment = self.get_object()

#         # Reset tracking fields
#         appointment.sms_confirmation_sent = False
#         appointment.email_confirmation_sent = False
#         appointment.save(update_fields=['sms_confirmation_sent', 'email_confirmation_sent'])

#         # Send again
#         appointment.send_notifications('appointment_confirmed')

#         return Response({
#             'success': True,
#             'message': 'Confirmation resent successfully'
#         })

#     @action(detail=False, methods=['get'])
#     def upcoming(self, request):
#         """Get upcoming appointments"""
#         user = request.user

#         if user.groups.filter(name='Workshops').exists():
#             workshops = AutoWorkshop.objects.filter(workshop_owner=user)
#             appointments = ServiceAppointment.objects.filter(
#                 service_workshop__in=workshops,
#                 appointment_date__gte=timezone.now().date(),
#                 appointment_status__in=['confirmed', 'scheduled']
#             )
#         else:
#             appointments = ServiceAppointment.objects.filter(
#                 client=user,
#                 appointment_date__gte=timezone.now().date(),
#                 appointment_status__in=['confirmed', 'scheduled']
#             )

#         appointments = appointments.order_by('appointment_date', 'appointment_time')[:20]
#         serializer = self.get_serializer(appointments, many=True)

#         return Response({
#             'success': True,
#             'count': appointments.count(),
#             'data': serializer.data
#         })


# # ======================= AUTO WORKSHOP VIEWSET =======================
# class AutoWorkshopViewSet(viewsets.ReadOnlyModelViewSet):
#     """Read-only viewset for auto workshops"""
#     queryset = AutoWorkshop.objects.filter(is_workshop_active=True, is_workshop_verified=True)
#     serializer_class = AutoWorkshopSerializer
#     permission_classes = [permissions.AllowAny]

#     def get_queryset(self):
#         queryset = super().get_queryset()

#         city = self.request.query_params.get('city')
#         if city:
#             queryset = queryset.filter(workshop_city__icontains=city)

#         search = self.request.query_params.get('search')
#         if search:
#             queryset = queryset.filter(
#                 Q(workshop_name__icontains=search) |
#                 Q(workshop_address__icontains=search) |
#                 Q(workshop_city__icontains=search)
#             )

#         return queryset.order_by('workshop_name')


# # ======================= REPAIR SERVICE VIEWSET =======================
# class RepairServiceViewSet(viewsets.ReadOnlyModelViewSet):
#     """Read-only viewset for repair services"""
#     queryset = RepairService.objects.filter(is_service_active=True)
#     serializer_class = RepairServiceSerializer
#     permission_classes = [permissions.AllowAny]

#     def get_queryset(self):
#         queryset = super().get_queryset()

#         category = self.request.query_params.get('category')
#         if category:
#             queryset = queryset.filter(service_category__icontains=category)

#         workshop_id = self.request.query_params.get('workshop_id')
#         if workshop_id:
#             queryset = queryset.filter(workshop_id=workshop_id)

#         search = self.request.query_params.get('search')
#         if search:
#             queryset = queryset.filter(
#                 Q(service_title__icontains=search) |
#                 Q(service_description__icontains=search)
#             )

#         return queryset.order_by('service_title')