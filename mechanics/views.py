# views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
import logging

from users.models import Garage
from .models import (
    ServiceRequest, ServiceRequestUpdate, 
    ServiceRequestAttachment, ServiceType
)
from .serializers import (
    ServiceRequestSerializer, ServiceRequestListSerializer,
    CreateServiceRequestSerializer, ServiceRequestUpdateSerializer,
    ServiceRequestAttachmentSerializer, ServiceTypeSerializer,
    GarageSerializer, UpdateServiceRequestStatusSerializer
)

logger = logging.getLogger(__name__)


class GarageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing garages (read-only)
    Anyone can view garage listings
    """
    queryset = Garage.objects.filter(is_active=True, is_open=True).order_by('name')
    serializer_class = GarageSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name', 'address', 'city', 'services__name']
    filterset_fields = ['city', 'delivery_available', 'is_verified']
    ordering_fields = ['rating', 'name', 'created_at']
    
    @action(detail=True, methods=['get'])
    def service_requests(self, request, pk=None):
        """Get all service requests for a specific garage"""
        garage = self.get_object()
        requests = garage.garage_service_requests.filter(is_archived=False).order_by('-created_at')
        
        # Allow filtering by status
        status_filter = request.query_params.get('status')
        if status_filter:
            status_list = status_filter.split(',')
            requests = requests.filter(status__in=status_list)
        
        page = self.paginate_queryset(requests)
        if page is not None:
            serializer = ServiceRequestListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ServiceRequestListSerializer(requests, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Get list of all cities with garages"""
        cities = Garage.objects.filter(
            is_active=True, 
            is_open=True,
            city__isnull=False
        ).exclude(city='').values_list('city', flat=True).distinct().order_by('city')
        return Response({'cities': list(cities)})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get garage statistics"""
        total_garages = Garage.objects.filter(is_active=True, is_open=True).count()
        verified_garages = Garage.objects.filter(is_active=True, is_open=True, is_verified=True).count()
        
        cities_with_garages = Garage.objects.filter(
            is_active=True, 
            is_open=True
        ).exclude(city='').values('city').distinct().count()
        
        return Response({
            'total_garages': total_garages,
            'verified_garages': verified_garages,
            'cities_with_garages': cities_with_garages,
            'garages_with_delivery': Garage.objects.filter(
                is_active=True, is_open=True, delivery_available=True
            ).count(),
            'average_rating': Garage.objects.filter(
                is_active=True, is_open=True, rating__isnull=False
            ).aggregate(Avg('rating'))['rating__avg'] or 0
        })


class ServiceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing service types
    Anyone can view service types
    """
    queryset = ServiceType.objects.filter(is_active=True).order_by('name')
    serializer_class = ServiceTypeSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'base_price']


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Service Request CRUD operations
    Email System:
    - Garage receives email when NEW request is created
    - Request sender receives email when request is UPDATED
    """
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'location', 'request_id', 'email', 'phone']
    filterset_fields = ['status', 'priority', 'garage', 'is_emergency', 'user']
    ordering_fields = ['created_at', 'submitted_at', 'estimated_cost', 'priority', 'status']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CreateServiceRequestSerializer
        elif self.action == 'list':
            return ServiceRequestListSerializer
        elif self.action == 'update_status':
            return UpdateServiceRequestStatusSerializer
        return ServiceRequestSerializer
    
    def get_queryset(self):
        """Return all service requests"""
        queryset = ServiceRequest.objects.all()
        queryset = self.apply_filters(queryset)
        return queryset.order_by('-created_at')
    
    def apply_filters(self, queryset):
        """Apply additional filters from query parameters"""
        # Filter by garage
        garage_id = self.request.query_params.get('garage_id')
        if garage_id:
            queryset = queryset.filter(garage_id=garage_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__date__range=[start_date, end_date])
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            status_list = status_param.split(',')
            queryset = queryset.filter(status__in=status_list)
        
        # Filter by priority
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            priority_list = priority_param.split(',')
            queryset = queryset.filter(priority__in=priority_list)
        
        # Filter by archive status
        archived = self.request.query_params.get('archived')
        if archived is not None:
            queryset = queryset.filter(is_archived=archived.lower() == 'true')
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create a new service request
        Send email to GARAGE (not to request sender)
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        try:
            serializer.is_valid(raise_exception=True)
            service_request = serializer.save()
            
            # Send notification email to GARAGE (NOT to request sender)
            self.send_new_request_email_to_garage(service_request)
            
            # Prepare response
            response_serializer = ServiceRequestSerializer(
                service_request, 
                context={'request': request}
            )
            
            return Response(
                {
                    'success': True,
                    'message': 'Service request submitted successfully!',
                    'request_id': str(service_request.request_id),
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': 'Failed to create service request',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def send_new_request_email_to_garage(self, service_request):
        """
        Send notification email to GARAGE when new service request is created
        ONLY garage receives this email
        """
        if not service_request.garage or not hasattr(service_request.garage, 'email'):
            logger.warning(f"No garage or garage email found for request {service_request.request_id}")
            return
        
        garage_email = service_request.garage.email
        if not garage_email:
            logger.warning(f"No email address for garage {service_request.garage.name}")
            return
        
        try:
            # Prepare email context for garage
            context = {
                'request_id': str(service_request.request_id)[:8].upper(),
                'customer_name': service_request.full_name(),
                'customer_email': service_request.email,
                'customer_phone': service_request.phone,
                'service_type': service_request.service_type or 'Vehicle Service',
                'vehicle_info': f"{service_request.vehicle_year} {service_request.vehicle_make} {service_request.vehicle_model}".strip(),
                'garage_name': service_request.garage.name,
                'submitted_date': service_request.submitted_at.strftime('%B %d, %Y') if service_request.submitted_at else timezone.now().strftime('%B %d, %Y'),
                'submitted_time': service_request.submitted_at.strftime('%I:%M %p') if service_request.submitted_at else timezone.now().strftime('%I:%M %p'),
                'experience': service_request.experience[:200] + '...' if len(service_request.experience) > 200 else service_request.experience,
                'location': service_request.location,
                'priority': service_request.get_priority_display(),
                'is_emergency': 'YES - URGENT' if service_request.is_emergency else 'No',
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@example.com'),
                'admin_dashboard_url': getattr(settings, 'ADMIN_URL', 'https://admin.yourapp.com'),
                'current_year': timezone.now().year,
            }
            
            subject = f"🚗 New Service Request #{context['request_id']} - {context['customer_name']}"
            
            # Create plain text version
            plain_message = f"""
            NEW SERVICE REQUEST NOTIFICATION
            =================================
            
            Hello {context['garage_name']} Team,
            
            You have received a new service request!
            
            REQUEST DETAILS:
            ----------------
            Request ID: {context['request_id']}
            Customer: {context['customer_name']}
            Service Type: {context['service_type']}
            Vehicle: {context['vehicle_info']}
            Priority: {context['priority']}
            Emergency: {context['is_emergency']}
            
            CUSTOMER CONTACT:
            -----------------
            Email: {context['customer_email']}
            Phone: {context['customer_phone']}
            Location: {context['location']}
            
            ISSUE DESCRIPTION:
            ------------------
            {context['experience']}
            
            TIMESTAMP:
            ----------
            Submitted: {context['submitted_date']} at {context['submitted_time']}
            
            ACTION REQUIRED:
            ----------------
            1. Review the request details
            2. Contact customer for diagnosis appointment
            3. Update request status in dashboard
            
            VIEW IN DASHBOARD:
            ------------------
            {context['admin_dashboard_url']}/requests/{service_request.request_id}
            
            Thank you,
            Service Request System
            """
            
            # Create HTML version with embedded styling
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f7f9fc;
                    }}
                    
                    .email-container {{
                        max-width: 650px;
                        margin: 0 auto;
                        background: #ffffff;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                    }}
                    
                    .header {{
                        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                        color: white;
                        padding: 40px 35px;
                        text-align: center;
                    }}
                    
                    .header h1 {{
                        font-size: 30px;
                        font-weight: 700;
                        margin-bottom: 15px;
                        letter-spacing: 0.5px;
                    }}
                    
                    .header p {{
                        font-size: 17px;
                        opacity: 0.95;
                        font-weight: 400;
                    }}
                    
                    .urgent-badge {{
                        display: inline-block;
                        background: #ff3838;
                        color: white;
                        padding: 8px 20px;
                        border-radius: 20px;
                        font-weight: bold;
                        font-size: 14px;
                        margin-top: 15px;
                        animation: pulse 2s infinite;
                    }}
                    
                    @keyframes pulse {{
                        0% {{ opacity: 1; }}
                        50% {{ opacity: 0.7; }}
                        100% {{ opacity: 1; }}
                    }}
                    
                    .content {{
                        padding: 45px 35px;
                    }}
                    
                    .greeting {{
                        font-size: 20px;
                        margin-bottom: 35px;
                        color: #444;
                        font-weight: 500;
                    }}
                    
                    .request-id-section {{
                        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        border-radius: 10px;
                        padding: 25px;
                        margin-bottom: 35px;
                        border-left: 5px solid #007bff;
                        text-align: center;
                    }}
                    
                    .request-id-title {{
                        color: #495057;
                        font-size: 18px;
                        margin-bottom: 10px;
                        font-weight: 600;
                    }}
                    
                    .request-id-value {{
                        font-size: 36px;
                        font-weight: 800;
                        color: #007bff;
                        letter-spacing: 3px;
                        margin: 15px 0;
                        text-shadow: 1px 1px 3px rgba(0,0,0,0.1);
                    }}
                    
                    .customer-section {{
                        background: #fff3cd;
                        border-radius: 10px;
                        padding: 25px;
                        margin-bottom: 35px;
                        border: 2px solid #ffc107;
                    }}
                    
                    .customer-section h2 {{
                        color: #856404;
                        font-size: 22px;
                        margin-bottom: 20px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    
                    .info-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 20px;
                        margin-top: 20px;
                    }}
                    
                    .info-card {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        border: 1px solid #dee2e6;
                    }}
                    
                    .info-label {{
                        font-size: 14px;
                        color: #6c757d;
                        font-weight: 600;
                        margin-bottom: 8px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    
                    .info-value {{
                        font-size: 18px;
                        color: #212529;
                        font-weight: 500;
                    }}
                    
                    .vehicle-section {{
                        background: #d4edda;
                        border-radius: 10px;
                        padding: 25px;
                        margin-bottom: 35px;
                        border: 2px solid #28a745;
                    }}
                    
                    .vehicle-section h2 {{
                        color: #155724;
                        font-size: 22px;
                        margin-bottom: 20px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    
                    .description-section {{
                        background: #e2e3e5;
                        border-radius: 10px;
                        padding: 25px;
                        margin-bottom: 35px;
                    }}
                    
                    .description-section h2 {{
                        color: #383d41;
                        font-size: 22px;
                        margin-bottom: 20px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    
                    .description-content {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        border: 1px solid #ced4da;
                        font-size: 16px;
                        line-height: 1.8;
                        color: #495057;
                    }}
                    
                    .action-section {{
                        background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                        color: white;
                        border-radius: 10px;
                        padding: 30px;
                        margin-bottom: 35px;
                        text-align: center;
                    }}
                    
                    .action-section h2 {{
                        font-size: 24px;
                        margin-bottom: 25px;
                        font-weight: 600;
                    }}
                    
                    .action-steps {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 25px;
                        margin-bottom: 30px;
                    }}
                    
                    .step {{
                        background: rgba(255, 255, 255, 0.1);
                        padding: 20px;
                        border-radius: 8px;
                        text-align: center;
                        backdrop-filter: blur(10px);
                    }}
                    
                    .step-number {{
                        background: white;
                        color: #007bff;
                        width: 40px;
                        height: 40px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 20px;
                        margin: 0 auto 15px;
                    }}
                    
                    .step-text {{
                        font-size: 15px;
                        opacity: 0.9;
                    }}
                    
                    .dashboard-button {{
                        display: inline-block;
                        background: white;
                        color: #007bff;
                        padding: 18px 40px;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: 700;
                        font-size: 18px;
                        margin: 20px 0;
                        text-align: center;
                        transition: transform 0.3s, box-shadow 0.3s;
                        border: none;
                        cursor: pointer;
                    }}
                    
                    .dashboard-button:hover {{
                        transform: translateY(-3px);
                        box-shadow: 0 10px 25px rgba(255, 255, 255, 0.2);
                    }}
                    
                    .footer {{
                        background: #343a40;
                        color: white;
                        padding: 35px;
                        text-align: center;
                        border-top: 5px solid #007bff;
                    }}
                    
                    .footer p {{
                        margin-bottom: 12px;
                        font-size: 15px;
                        opacity: 0.9;
                    }}
                    
                    .support-email {{
                        color: #4dabf7;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 16px;
                    }}
                    
                    .timestamp {{
                        background: rgba(255, 255, 255, 0.1);
                        padding: 15px;
                        border-radius: 6px;
                        margin: 20px 0;
                        font-size: 14px;
                    }}
                    
                    .copyright {{
                        margin-top: 30px;
                        font-size: 13px;
                        opacity: 0.7;
                        border-top: 1px solid rgba(255, 255, 255, 0.1);
                        padding-top: 20px;
                    }}
                    
                    @media (max-width: 600px) {{
                        .content, .header, .footer {{
                            padding: 25px 20px;
                        }}
                        
                        .header h1 {{
                            font-size: 26px;
                        }}
                        
                        .info-grid {{
                            grid-template-columns: 1fr;
                        }}
                        
                        .action-steps {{
                            grid-template-columns: 1fr;
                        }}
                        
                        .dashboard-button {{
                            padding: 16px 30px;
                            font-size: 16px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <h1>🚗 New Service Request Received!</h1>
                        <p>A customer has submitted a new service request to your garage</p>
                        {f"<div class='urgent-badge'>⚠️ URGENT EMERGENCY REQUEST</div>" if context['is_emergency'] == 'YES - URGENT' else ''}
                    </div>
                    
                    <div class="content">
                        <p class="greeting">Hello <strong>{context['garage_name']}</strong> Team,</p>
                        
                        <div class="request-id-section">
                            <div class="request-id-title">REQUEST IDENTIFICATION NUMBER</div>
                            <div class="request-id-value">{context['request_id']}</div>
                            <div style="color: #6c757d; font-size: 14px;">Use this ID for all communications</div>
                        </div>
                        
                        <div class="customer-section">
                            <h2>👤 Customer Information</h2>
                            <div class="info-grid">
                                <div class="info-card">
                                    <div class="info-label">Customer Name</div>
                                    <div class="info-value">{context['customer_name']}</div>
                                </div>
                                <div class="info-card">
                                    <div class="info-label">Email Address</div>
                                    <div class="info-value">{context['customer_email']}</div>
                                </div>
                                <div class="info-card">
                                    <div class="info-label">Phone Number</div>
                                    <div class="info-value">{context['customer_phone']}</div>
                                </div>
                                <div class="info-card">
                                    <div class="info-label">Location</div>
                                    <div class="info-value">{context['location']}</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="vehicle-section">
                            <h2>🚙 Vehicle Details</h2>
                            <div class="info-grid">
                                <div class="info-card">
                                    <div class="info-label">Service Type</div>
                                    <div class="info-value">{context['service_type']}</div>
                                </div>
                                <div class="info-card">
                                    <div class="info-label">Vehicle</div>
                                    <div class="info-value">{context['vehicle_info'] or 'Not specified'}</div>
                                </div>
                                <div class="info-card">
                                    <div class="info-label">Priority Level</div>
                                    <div class="info-value">{context['priority']}</div>
                                </div>
                                <div class="info-card">
                                    <div class="info-label">Emergency Status</div>
                                    <div class="info-value">{context['is_emergency']}</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="description-section">
                            <h2>📝 Problem Description</h2>
                            <div class="description-content">
                                {context['experience']}
                            </div>
                        </div>
                        
                        <div class="action-section">
                            <h2>⏰ Required Actions</h2>
                            <div class="action-steps">
                                <div class="step">
                                    <div class="step-number">1</div>
                                    <div class="step-text">Review request details carefully</div>
                                </div>
                                <div class="step">
                                    <div class="step-number">2</div>
                                    <div class="step-text">Contact customer within 24 hours</div>
                                </div>
                                <div class="step">
                                    <div class="step-number">3</div>
                                    <div class="step-text">Schedule diagnosis appointment</div>
                                </div>
                                <div class="step">
                                    <div class="step-number">4</div>
                                    <div class="step-text">Update status in the dashboard</div>
                                </div>
                            </div>
                            
                            <a href="{context['admin_dashboard_url']}/requests/{service_request.request_id}" class="dashboard-button">
                                📊 Go to Dashboard
                            </a>
                            <p style="opacity: 0.9; margin-top: 15px; font-size: 14px;">
                                Click above to view complete details and manage this request
                            </p>
                        </div>
                        
                        <div class="timestamp">
                            <strong>📅 Submission Time:</strong> {context['submitted_date']} at {context['submitted_time']}
                        </div>
                    </div>
                    
                    <div class="footer">
                        <div class="timestamp">
                            <strong>⚠️ Important:</strong> Please respond to this request within 24 hours
                        </div>
                        
                        <p>Need technical support with the dashboard?</p>
                        <p>Contact: <a href="mailto:{context['support_email']}" class="support-email">{context['support_email']}</a></p>
                        
                        <div style="margin-top: 30px; padding-top: 25px; border-top: 1px solid rgba(255,255,255,0.15);">
                            <p style="font-size: 16px; margin-bottom: 5px;">Best regards,</p>
                            <p style="font-size: 18px; font-weight: 600; margin-bottom: 15px;">Service Request Management System</p>
                            <p style="font-size: 14px; opacity: 0.8;">Automated Notification System</p>
                        </div>
                        
                        <p class="copyright">
                            © {context['current_year']} Auto Service Platform. All rights reserved.<br>
                            This is an automated notification. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send email to GARAGE ONLY
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@autoservice.com'),
                to=[garage_email],
                cc=[getattr(settings, 'ADMIN_EMAIL', 'admin@autoservice.com')] if hasattr(settings, 'ADMIN_EMAIL') else None,
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Garage notification email sent to {garage_email} for request {context['request_id']}")
            
        except Exception as e:
            logger.error(f"Failed to send garage notification email: {str(e)}")
            # Don't fail the request if email fails
    
    @action(detail=True, methods=['post', 'put'])
    def update_status(self, request, pk=None):
        """
        Update status of a service request
        Send email to REQUEST SENDER (customer) about the update
        """
        service_request = self.get_object()
        
        serializer = UpdateServiceRequestStatusSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Store old status
            old_status = service_request.status
            old_status_display = service_request.get_status_display()
            
            # Update service request
            service_request = serializer.update(service_request, serializer.validated_data)
            
            # Send status update email to REQUEST SENDER (customer)
            self.send_status_update_email_to_customer(
                service_request=service_request,
                old_status=old_status,
                old_status_display=old_status_display,
                new_status=service_request.status,
                new_status_display=service_request.get_status_display(),
                notes=serializer.validated_data.get('notes', '')
            )
            
            return Response({
                'success': True,
                'message': f'Status updated from {old_status_display} to {service_request.get_status_display()}',
                'status': service_request.status,
                'status_display': service_request.get_status_display(),
                'updated_at': service_request.updated_at
            })
        
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def send_status_update_email_to_customer(self, service_request, old_status, old_status_display, 
                                          new_status, new_status_display, notes):
        """
        Send status update email to REQUEST SENDER (customer)
        Customer receives email when their request is updated
        """
        customer_email = service_request.email
        if not customer_email:
            logger.warning(f"No customer email found for request {service_request.request_id}")
            return
        
        try:
            # Get status icon based on status
            status_icons = {
                'pending': '⏳',
                'received': '📥',
                'in_progress': '🔧',
                'completed': '✅',
                'cancelled': '❌',
                'rejected': '🚫',
            }
            
            status_icon = status_icons.get(new_status, '📋')
            
            # Get garage info
            garage_name = service_request.garage.name if service_request.garage else "Service Garage"
            garage_email = service_request.garage.email if service_request.garage else None
            garage_phone = service_request.garage.phone if service_request.garage else None
            
            context = {
                'request_id': str(service_request.request_id)[:8].upper(),
                'customer_name': service_request.full_name(),
                'old_status': old_status_display,
                'new_status': new_status_display,
                'new_status_icon': status_icon,
                'notes': notes,
                'garage_name': garage_name,
                'garage_email': garage_email,
                'garage_phone': garage_phone,
                'updated_date': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
                'service_type': service_request.service_type or 'Vehicle Service',
                'vehicle_info': f"{service_request.vehicle_year} {service_request.vehicle_make} {service_request.vehicle_model}".strip(),
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@example.com'),
                'customer_portal_url': getattr(settings, 'CUSTOMER_PORTAL_URL', 'https://customer.yourapp.com'),
                'current_year': timezone.now().year,
            }
            
            subject = f"📋 Update: Your Service Request #{context['request_id']} - Now {new_status_display}"
            
            # Create plain text message
            plain_message = f"""
            SERVICE REQUEST STATUS UPDATE
            ==============================
            
            Dear {context['customer_name']},
            
            Your service request status has been updated.
            
            REQUEST DETAILS:
            ----------------
            Request ID: {context['request_id']}
            Service Type: {context['service_type']}
            Vehicle: {context['vehicle_info']}
            Previous Status: {context['old_status']}
            New Status: {context['new_status']}
            Updated: {context['updated_date']}
            
            SERVICE GARAGE:
            --------------
            Garage: {context['garage_name']}
            {f"Email: {context['garage_email']}" if context['garage_email'] else ""}
            {f"Phone: {context['garage_phone']}" if context['garage_phone'] else ""}
            
            {f"GARAGE NOTES:\n{context['notes']}" if context['notes'] else ""}
            
            VIEW YOUR REQUEST:
            ------------------
            {context['customer_portal_url']}/requests/{service_request.request_id}
            
            Need assistance?
            Contact support: {context['support_email']}
            
            Thank you for choosing our service,
            Service Request Team
            """
            
            # Create HTML version
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f7f9fc;
                    }}
                    
                    .email-container {{
                        max-width: 650px;
                        margin: 0 auto;
                        background: #ffffff;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                    }}
                    
                    .header {{
                        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
                        color: white;
                        padding: 40px 35px;
                        text-align: center;
                    }}
                    
                    .header h1 {{
                        font-size: 28px;
                        font-weight: 700;
                        margin-bottom: 10px;
                    }}
                    
                    .header p {{
                        font-size: 16px;
                        opacity: 0.95;
                        font-weight: 400;
                    }}
                    
                    .content {{
                        padding: 45px 35px;
                    }}
                    
                    .greeting {{
                        font-size: 20px;
                        margin-bottom: 30px;
                        color: #444;
                        font-weight: 500;
                    }}
                    
                    .status-card {{
                        background: #e8f5e9;
                        border-radius: 10px;
                        padding: 25px;
                        margin: 25px 0;
                        text-align: center;
                        border: 2px solid #4CAF50;
                    }}
                    
                    .status-icon {{
                        font-size: 48px;
                        margin-bottom: 15px;
                    }}
                    
                    .status-title {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #2E7D32;
                        margin-bottom: 10px;
                    }}
                    
                    .status-change {{
                        font-size: 18px;
                        color: #333;
                        margin-bottom: 15px;
                    }}
                    
                    .info-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 20px;
                        margin: 30px 0;
                    }}
                    
                    .info-card {{
                        background: #f5f5f5;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #4CAF50;
                    }}
                    
                    .info-label {{
                        font-size: 14px;
                        color: #666;
                        font-weight: 600;
                        margin-bottom: 8px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    
                    .info-value {{
                        font-size: 18px;
                        color: #333;
                        font-weight: 500;
                    }}
                    
                    .garage-info {{
                        background: #fff3cd;
                        border-radius: 10px;
                        padding: 25px;
                        margin: 30px 0;
                        border: 2px solid #ffc107;
                    }}
                    
                    .garage-info h2 {{
                        color: #856404;
                        font-size: 20px;
                        margin-bottom: 20px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    
                    .notes-section {{
                        background: #e3f2fd;
                        border-radius: 10px;
                        padding: 25px;
                        margin: 30px 0;
                        border: 2px solid #2196F3;
                    }}
                    
                    .notes-section h2 {{
                        color: #1565c0;
                        font-size: 20px;
                        margin-bottom: 15px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    
                    .notes-content {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        border: 1px solid #bbdefb;
                        font-size: 16px;
                        line-height: 1.8;
                        color: #424242;
                    }}
                    
                    .dashboard-button {{
                        display: inline-block;
                        background: #4CAF50;
                        color: white;
                        padding: 18px 40px;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: 700;
                        font-size: 18px;
                        margin: 25px 0;
                        text-align: center;
                        transition: transform 0.3s, box-shadow 0.3s;
                        border: none;
                        cursor: pointer;
                    }}
                    
                    .dashboard-button:hover {{
                        transform: translateY(-3px);
                        box-shadow: 0 10px 25px rgba(76, 175, 80, 0.3);
                    }}
                    
                    .footer {{
                        background: #37474F;
                        color: white;
                        padding: 35px;
                        text-align: center;
                        border-top: 5px solid #4CAF50;
                    }}
                    
                    .support-contact {{
                        background: rgba(255, 255, 255, 0.1);
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }}
                    
                    .support-email {{
                        color: #4dabf7;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 16px;
                    }}
                    
                    .timestamp {{
                        background: rgba(255, 255, 255, 0.1);
                        padding: 15px;
                        border-radius: 6px;
                        margin: 20px 0;
                        font-size: 14px;
                    }}
                    
                    .copyright {{
                        margin-top: 30px;
                        font-size: 13px;
                        opacity: 0.7;
                        border-top: 1px solid rgba(255, 255, 255, 0.1);
                        padding-top: 20px;
                    }}
                    
                    @media (max-width: 600px) {{
                        .content, .header, .footer {{
                            padding: 25px 20px;
                        }}
                        
                        .header h1 {{
                            font-size: 24px;
                        }}
                        
                        .info-grid {{
                            grid-template-columns: 1fr;
                        }}
                        
                        .dashboard-button {{
                            padding: 16px 30px;
                            font-size: 16px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <h1>{context['new_status_icon']} Service Request Updated</h1>
                        <p>Your service request status has been changed</p>
                    </div>
                    
                    <div class="content">
                        <p class="greeting">Dear <strong>{context['customer_name']}</strong>,</p>
                        
                        <div class="status-card">
                            <div class="status-icon">{context['new_status_icon']}</div>
                            <div class="status-title">Current Status: {context['new_status']}</div>
                            <div class="status-change">
                                Changed from: <strong>{context['old_status']}</strong>
                            </div>
                            <div style="margin-top: 10px; color: #555;">
                                Updated on: {context['updated_date']}
                            </div>
                        </div>
                        
                        <div class="info-grid">
                            <div class="info-card">
                                <div class="info-label">Request ID</div>
                                <div class="info-value">{context['request_id']}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Service Type</div>
                                <div class="info-value">{context['service_type']}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Vehicle</div>
                                <div class="info-value">{context['vehicle_info'] or 'Not specified'}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-label">Updated On</div>
                                <div class="info-value">{context['updated_date']}</div>
                            </div>
                        </div>
                        
                        <div class="garage-info">
                            <h2>🏢 Servicing Garage</h2>
                            <div class="info-grid">
                                <div class="info-card">
                                    <div class="info-label">Garage Name</div>
                                    <div class="info-value">{context['garage_name']}</div>
                                </div>
                                {f'''
                                <div class="info-card">
                                    <div class="info-label">Garage Email</div>
                                    <div class="info-value">{context['garage_email']}</div>
                                </div>
                                ''' if context['garage_email'] else ''}
                                {f'''
                                <div class="info-card">
                                    <div class="info-label">Garage Phone</div>
                                    <div class="info-value">{context['garage_phone']}</div>
                                </div>
                                ''' if context['garage_phone'] else ''}
                            </div>
                        </div>
                        
                        {f'''
                        <div class="notes-section">
                            <h2>📝 Garage Notes</h2>
                            <div class="notes-content">
                                {context['notes']}
                            </div>
                        </div>
                        ''' if context['notes'] else ''}
                        
                        <div style="text-align: center; margin: 40px 0;">
                            <a href="{context['customer_portal_url']}/requests/{service_request.request_id}" class="dashboard-button">
                                📋 View Your Request
                            </a>
                            <p style="color: #666; margin-top: 15px; font-size: 14px;">
                                Click above to view complete details and track progress
                            </p>
                        </div>
                        
                        <div class="timestamp">
                            <strong>📅 Update Time:</strong> {context['updated_date']}
                        </div>
                    </div>
                    
                    <div class="footer">
                        <div class="support-contact">
                            <p style="margin-bottom: 10px;">Need assistance or have questions?</p>
                            <p>Contact our support team: <a href="mailto:{context['support_email']}" class="support-email">{context['support_email']}</a></p>
                        </div>
                        
                        <div class="timestamp">
                            <strong>ℹ️ Note:</strong> This is an automated notification. Please do not reply to this email.
                        </div>
                        
                        <div style="margin-top: 30px; padding-top: 25px; border-top: 1px solid rgba(255,255,255,0.15);">
                            <p style="font-size: 16px; margin-bottom: 5px;">Best regards,</p>
                            <p style="font-size: 18px; font-weight: 600; margin-bottom: 15px;">Service Request Management Team</p>
                        </div>
                        
                        <p class="copyright">
                            © {context['current_year']} Auto Service Platform. All rights reserved.<br>
                            This email was sent to {customer_email}
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send email to REQUEST SENDER (customer)
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@autoservice.com'),
                to=[customer_email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=True)
            
            logger.info(f"Status update email sent to customer {customer_email} for request {context['request_id']}")
            
        except Exception as e:
            logger.error(f"Failed to send status update email to customer: {str(e)}")
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """
        Get all service requests for the authenticated user
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        queryset = ServiceRequest.objects.filter(user=request.user)
        queryset = self.apply_filters(queryset)
        
        # Get counts for dashboard
        counts = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'in_progress': queryset.filter(status='in_progress').count(),
            'completed': queryset.filter(status='completed').count(),
            'cancelled': queryset.filter(status='cancelled').count(),
        }
        
        # Paginate results
        page = self.paginate_queryset(queryset.order_by('-created_at'))
        if page is not None:
            serializer = ServiceRequestListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response({
                'counts': counts,
                'requests': serializer.data
            })
        
        serializer = ServiceRequestListSerializer(queryset, many=True, context={'request': request})
        return Response({
            'counts': counts,
            'requests': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_attachment(self, request, pk=None):
        """Add attachment to service request"""
        service_request = self.get_object()
        
        serializer = ServiceRequestAttachmentSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            attachment = serializer.save(
                service_request=service_request,
                uploaded_by=request.user if request.user.is_authenticated else None
            )
            
            # Create update record
            ServiceRequestUpdate.objects.create(
                service_request=service_request,
                updated_by=request.user if request.user.is_authenticated else None,
                update_type='note_added',
                old_value='',
                new_value='Attachment added',
                notes=f'Added {attachment.file_type} attachment'
            )
            
            return Response(
                ServiceRequestAttachmentSerializer(attachment).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def submit_feedback(self, request, pk=None):
        """
        Submit feedback and rating for completed service
        """
        service_request = self.get_object()
        
        # Check if service is completed
        if service_request.status != 'completed':
            return Response(
                {'error': 'Feedback can only be submitted for completed requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rating = request.data.get('rating')
        feedback = request.data.get('feedback', '').strip()
        
        # Validate rating
        if not rating or not 1 <= int(rating) <= 5:
            return Response(
                {'error': 'Rating must be a number between 1 and 5'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update service request
        service_request.user_rating = rating
        service_request.user_feedback = feedback
        service_request.save()
        
        # Update garage rating if applicable
        if service_request.garage:
            self.update_garage_rating(service_request.garage)
        
        # Create update record
        ServiceRequestUpdate.objects.create(
            service_request=service_request,
            updated_by=request.user if request.user.is_authenticated else None,
            update_type='note_added',
            old_value='',
            new_value='Feedback submitted',
            notes=f'Service rated {rating}/5'
        )
        
        return Response({
            'success': True,
            'message': 'Thank you for your feedback!',
            'rating': rating,
            'feedback': feedback
        })
    
    def update_garage_rating(self, garage):
        """Update garage's average rating"""
        try:
            ratings = garage.garage_service_requests.filter(
                user_rating__isnull=False
            ).values_list('user_rating', flat=True)
            
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                garage.rating = round(avg_rating, 2)
                garage.rating_count = len(ratings)
                garage.save()
        except Exception as e:
            logger.error(f"Failed to update garage rating: {str(e)}")
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get service request statistics
        """
        # Total statistics
        total_requests = ServiceRequest.objects.count()
        
        # Status counts
        status_counts = {}
        for status_code, status_name in ServiceRequest.STATUS_CHOICES:
            status_counts[status_code] = ServiceRequest.objects.filter(status=status_code).count()
        
        # Recent requests (last 30 days)
        month_ago = timezone.now() - timedelta(days=30)
        recent_requests = ServiceRequest.objects.filter(created_at__gte=month_ago).count()
        
        # Average rating
        avg_rating = ServiceRequest.objects.filter(
            user_rating__isnull=False
        ).aggregate(Avg('user_rating'))['user_rating__avg']
        
        return Response({
            'total_requests': total_requests,
            'status_counts': status_counts,
            'recent_requests_last_30_days': recent_requests,
            'average_rating': round(avg_rating, 2) if avg_rating else None,
            'timestamp': timezone.now().isoformat()
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search service requests
        """
        query = request.query_params.get('q', '').strip()
        
        if not query or len(query) < 2:
            return Response(
                {'error': 'Search query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search all fields
        queryset = ServiceRequest.objects.filter(
            Q(request_id__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(location__icontains=query)
        )
        
        # Apply additional filters
        queryset = self.apply_filters(queryset)
        
        # Paginate results
        page = self.paginate_queryset(queryset.order_by('-created_at'))
        if page is not None:
            serializer = ServiceRequestListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ServiceRequestListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class ServiceRequestUpdateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing service request updates
    Anyone can view updates
    """
    serializer_class = ServiceRequestUpdateSerializer
    permission_classes = [AllowAny]
    queryset = ServiceRequestUpdate.objects.all().order_by('-created_at')
    
    def get_queryset(self):
        """Return all updates with optional filters"""
        queryset = ServiceRequestUpdate.objects.all()
        
        # Filter by service request if specified
        service_request_id = self.request.query_params.get('service_request')
        if service_request_id:
            queryset = queryset.filter(service_request_id=service_request_id)
        
        # Filter by update type
        update_type = self.request.query_params.get('update_type')
        if update_type:
            queryset = queryset.filter(update_type=update_type)
        
        return queryset.order_by('-created_at')


class ServiceRequestAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for service request attachments
    Anyone can perform all operations
    """
    serializer_class = ServiceRequestAttachmentSerializer
    permission_classes = [AllowAny]
    queryset = ServiceRequestAttachment.objects.all().order_by('-created_at')
    
    def get_queryset(self):
        """Return all attachments with optional filters"""
        queryset = ServiceRequestAttachment.objects.all()
        
        # Filter by service request
        service_request_id = self.request.query_params.get('service_request')
        if service_request_id:
            queryset = queryset.filter(service_request_id=service_request_id)
        
        # Filter by file type
        file_type = self.request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set uploaded_by when creating attachment"""
        serializer.save(uploaded_by=self.request.user if self.request.user.is_authenticated else None)