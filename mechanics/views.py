# mechanics/views.py - WITH EMBEDDED HTML EMAIL TEMPLATES

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    ServiceRequest, ServiceRequestUpdate,
    ServiceRequestNote, ServiceType
)
from .serializers import (
    ServiceRequestCreateSerializer, ServiceRequestUpdateSerializer,
    ServiceRequestDetailSerializer, ServiceRequestListSerializer,
    ServiceRequestUpdateHistorySerializer, ServiceRequestNoteSerializer,
    ServiceTypeSerializer
)
import json
import logging

logger = logging.getLogger(__name__)


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """
    Complete CRUD for Service Requests with Email Notifications
    """
    queryset = ServiceRequest.objects.all().order_by('-created_at')
    
    def get_permissions(self):
        return [AllowAny()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ServiceRequestUpdateSerializer
        elif self.action == 'list':
            return ServiceRequestListSerializer
        return ServiceRequestDetailSerializer
    
    def get_queryset(self):
        queryset = ServiceRequest.objects.all().order_by('-created_at')
        
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        email = self.request.query_params.get('email')
        if email:
            queryset = queryset.filter(email=email)
        
        phone = self.request.query_params.get('phone')
        if phone:
            queryset = queryset.filter(phone__icontains=phone)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(service_type__icontains=search) |
                Q(garage_name__icontains=search) |
                Q(request_id__icontains=search)
            )
        
        return queryset
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_confirmation_html(self, context):
        """Embedded HTML template for confirmation email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Service Request Confirmation</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f0f9ff;
                }}
                .header {{
                    background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                    border-radius: 15px 15px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .header p {{
                    margin: 10px 0 0;
                    opacity: 0.9;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border: 1px solid #e2e8f0;
                    border-radius: 0 0 15px 15px;
                }}
                .status-badge {{
                    display: inline-block;
                    background-color: #f59e0b;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                .info-box {{
                    background-color: #f8fafc;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    border-left: 4px solid #0891b2;
                }}
                .info-item {{
                    margin: 10px 0;
                    display: flex;
                    align-items: flex-start;
                }}
                .info-label {{
                    font-weight: bold;
                    width: 120px;
                    color: #475569;
                }}
                .info-value {{
                    flex: 1;
                    color: #0f172a;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                    font-size: 12px;
                    color: #64748b;
                }}
                .button {{
                    background-color: #0891b2;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 8px;
                    display: inline-block;
                    margin: 20px 0;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">🔧 QuickFix Automotive</div>
                <h1>Service Request Confirmation</h1>
                <p>Thank you for choosing us!</p>
            </div>
            <div class="content">
                <p>Dear <strong>{context['customer_name']}</strong>,</p>
                
                <p>Your service request has been successfully submitted. Our team will review it and assign a garage to assist you promptly.</p>
                
                <div class="info-box">
                    <h3 style="margin-top: 0; color: #0891b2;">📋 Request Details</h3>
                    <div class="info-item">
                        <span class="info-label">Request ID:</span>
                        <span class="info-value"><strong>{context['request_id']}</strong></span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Service Type:</span>
                        <span class="info-value">{context['service_type']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Location:</span>
                        <span class="info-value">{context['location']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Submitted:</span>
                        <span class="info-value">{context['submitted_date']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Status:</span>
                        <span class="info-value"><span class="status-badge">Pending Review</span></span>
                    </div>
                </div>
                
                <div class="info-box">
                    <h3 style="margin-top: 0; color: #0891b2;">🛠️ Issue Description</h3>
                    <p>{context['experience']}...</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{context['tracking_url']}" class="button">Track Your Request</a>
                </div>
                
                <p><strong>What happens next?</strong></p>
                <ul>
                    <li>✅ Our team will review your request</li>
                    <li>✅ A qualified garage will be assigned</li>
                    <li>✅ You'll receive status updates via email</li>
                    <li>✅ You'll get a quote before any work begins</li>
                </ul>
                
                <p>For urgent assistance, please call our support team.</p>
                
                <p>Best regards,<br>
                <strong>QuickFix Automotive Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; {context['current_year']} QuickFix Automotive. All rights reserved.</p>
                <p>Professional garage services at your doorstep</p>
            </div>
        </body>
        </html>
        """
    
    def get_status_update_html(self, context):
        """Embedded HTML template for status update email"""
        # Status colors
        status_colors = {
            'received': '#3b82f6',
            'in_progress': '#8b5cf6',
            'completed': '#10b981',
            'cancelled': '#64748b',
            'rejected': '#ef4444'
        }
        status_color = status_colors.get(context['new_status'].lower(), '#0891b2')
        
        # Status icons
        status_icons = {
            'received': '📥',
            'in_progress': '🔧',
            'completed': '✅',
            'cancelled': '❌',
            'rejected': '⚠️'
        }
        status_icon = status_icons.get(context['new_status'].lower(), '📋')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Service Request Status Update</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f0f9ff;
                }}
                .header {{
                    background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                    border-radius: 15px 15px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border: 1px solid #e2e8f0;
                    border-radius: 0 0 15px 15px;
                }}
                .status-card {{
                    background: linear-gradient(135deg, {status_color}15 0%, {status_color}05 100%);
                    border: 2px solid {status_color};
                    border-radius: 15px;
                    padding: 20px;
                    text-align: center;
                    margin: 20px 0;
                }}
                .status-icon {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                .status-text {{
                    font-size: 24px;
                    font-weight: bold;
                    color: {status_color};
                    margin: 10px 0;
                }}
                .info-box {{
                    background-color: #f8fafc;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    border-left: 4px solid {status_color};
                }}
                .info-item {{
                    margin: 10px 0;
                    display: flex;
                    align-items: center;
                }}
                .info-label {{
                    font-weight: bold;
                    width: 120px;
                    color: #475569;
                }}
                .info-value {{
                    flex: 1;
                    color: #0f172a;
                }}
                .progress-bar {{
                    background-color: #e2e8f0;
                    border-radius: 10px;
                    height: 8px;
                    margin: 20px 0;
                    overflow: hidden;
                }}
                .progress-fill {{
                    background-color: {status_color};
                    height: 100%;
                    width: {context.get('progress_percentage', 50)}%;
                    border-radius: 10px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                    font-size: 12px;
                    color: #64748b;
                }}
                .button {{
                    background-color: {status_color};
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 8px;
                    display: inline-block;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{status_icon} Service Request Status Update</h1>
                <p>Your request has been updated</p>
            </div>
            <div class="content">
                <p>Dear <strong>{context['customer_name']}</strong>,</p>
                
                <div class="status-card">
                    <div class="status-icon">{status_icon}</div>
                    <div class="status-text">{context['new_status'].upper()}</div>
                    <p>Your service request status has been updated</p>
                </div>
                
                <div class="info-box">
                    <h3 style="margin-top: 0;">📋 Request Information</h3>
                    <div class="info-item">
                        <span class="info-label">Request ID:</span>
                        <span class="info-value"><strong>{context['request_id']}</strong></span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Service Type:</span>
                        <span class="info-value">{context['service_type']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Previous Status:</span>
                        <span class="info-value">{context['old_status']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Current Status:</span>
                        <span class="info-value"><strong style="color: {status_color};">{context['new_status']}</strong></span>
                    </div>
                </div>
                
                <div class="info-box">
                    <h3 style="margin-top: 0;">🏢 Garage Information</h3>
                    <div class="info-item">
                        <span class="info-label">Assigned Garage:</span>
                        <span class="info-value">{context['garage_name']}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Location:</span>
                        <span class="info-value">{context['location']}</span>
                    </div>
                </div>
                
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                
                <div style="text-align: center;">
                    <a href="{context['tracking_url']}" class="button">Track Your Request</a>
                </div>
                
                <div style="background-color: #e0f2fe; padding: 15px; border-radius: 10px; margin-top: 20px;">
                    <p style="margin: 0; color: #0891b2;">
                        <strong>💡 Need help?</strong><br>
                        Contact our support team for assistance.
                    </p>
                </div>
                
                <p>Best regards,<br>
                <strong>QuickFix Automotive Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; {context['current_year']} QuickFix Automotive. All rights reserved.</p>
                <p>Professional garage services at your doorstep</p>
            </div>
        </body>
        </html>
        """
    
    def send_confirmation_email(self, service_request):
        """Send confirmation email when service request is created"""
        try:
            if not service_request.email:
                logger.warning(f"No email for customer {service_request.full_name()}")
                return False
            
            context = {
                'customer_name': service_request.full_name(),
                'request_id': service_request.get_request_code(),
                'service_type': service_request.service_type or 'General Service',
                'location': service_request.location or 'Not specified',
                'experience': service_request.experience[:200] if service_request.experience else '',
                'submitted_date': service_request.submitted_at.strftime('%B %d, %Y at %I:%M %p') if service_request.submitted_at else 'N/A',
                'tracking_url': f"{getattr(settings, 'BASE_URL', 'https://autofix.pythonanywhere.com')}/track-request/{service_request.request_id}",
                'current_year': timezone.now().year
            }
            
            html_message = self.get_confirmation_html(context)
            plain_message = f"""
            QuickFix Automotive - Service Request Confirmation
            
            Dear {context['customer_name']},
            
            Your service request has been successfully submitted.
            
            Request ID: {context['request_id']}
            Service Type: {context['service_type']}
            Location: {context['location']}
            Submitted: {context['submitted_date']}
            
            Track your request: {context['tracking_url']}
            
            Best regards,
            QuickFix Automotive Team
            """
            
            send_mail(
                subject=f"✅ Service Request Confirmation - {context['request_id']}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[service_request.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Confirmation email sent to {service_request.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {str(e)}")
            return False
    
    def send_status_notification(self, service_request, old_status, new_status):
        """Send email notification to customer when status changes"""
        try:
            if not service_request.email:
                logger.warning(f"No email for customer {service_request.full_name()}")
                return False
            
            # Status display names
            status_display = {
                'pending': 'Pending',
                'received': 'Received by Garage',
                'in_progress': 'In Progress',
                'completed': 'Completed',
                'cancelled': 'Cancelled',
                'rejected': 'Rejected'
            }
            
            # Progress percentages
            progress_map = {
                'pending': 0,
                'received': 25,
                'in_progress': 50,
                'completed': 100,
                'cancelled': 0,
                'rejected': 0
            }
            
            context = {
                'customer_name': service_request.full_name(),
                'request_id': service_request.get_request_code(),
                'old_status': status_display.get(old_status, old_status),
                'new_status': status_display.get(new_status, new_status),
                'service_type': service_request.service_type or 'General Service',
                'garage_name': service_request.garage_name or 'To be assigned',
                'location': service_request.location or 'Not specified',
                'tracking_url': f"{getattr(settings, 'BASE_URL', 'https://autofix.pythonanywhere.com')}/track-request/{service_request.request_id}",
                'current_year': timezone.now().year,
                'progress_percentage': progress_map.get(new_status, 50)
            }
            
            # Subject based on new status
            subjects = {
                'received': f"✅ Service Request Received - {context['request_id']}",
                'in_progress': f"🔧 Service In Progress - {context['request_id']}",
                'completed': f"🎉 Service Completed - {context['request_id']}",
                'cancelled': f"❌ Service Cancelled - {context['request_id']}",
                'rejected': f"⚠️ Service Update - {context['request_id']}"
            }
            
            subject = subjects.get(new_status, f"📋 Status Update - {context['request_id']}")
            
            html_message = self.get_status_update_html(context)
            plain_message = f"""
            QuickFix Automotive - Service Request Status Update
            
            Dear {context['customer_name']},
            
            Your service request status has been updated.
            
            Request ID: {context['request_id']}
            Previous Status: {context['old_status']}
            Current Status: {context['new_status']}
            Garage: {context['garage_name']}
            
            Track your request: {context['tracking_url']}
            
            Best regards,
            QuickFix Automotive Team
            """
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[service_request.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Status notification email sent to {service_request.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send status notification email: {str(e)}")
            return False
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                service_request = serializer.save(
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    submitted_at=timezone.now()
                )
                
                response_serializer = ServiceRequestDetailSerializer(service_request)
                
                # Send confirmation email
                self.send_confirmation_email(service_request)
                
                return Response({
                    'success': True,
                    'message': 'Service request created successfully',
                    'data': response_serializer.data,
                    'request_code': service_request.get_request_code()
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error in create: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='change-status')
    @method_decorator(csrf_exempt)
    def change_status(self, request, pk=None):
        """
        Change status of service request and send email notification to customer
        URL: POST /api/service-requests/{id}/change-status/
        Body: {"status": "in_progress"}
        """
        try:
            # Validate that pk is a number
            try:
                request_id = int(pk)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': f'Invalid request ID: {pk}. ID must be a number.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the service request
            try:
                service_request = ServiceRequest.objects.get(id=request_id)
            except ServiceRequest.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Service request with ID {request_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get the new status from request
            new_status = None
            if request.body:
                try:
                    body = json.loads(request.body)
                    new_status = body.get('status')
                except:
                    pass
            
            if not new_status:
                new_status = request.data.get('status')
            
            logger.info(f"Status update request for request {request_id}: {new_status}")
            
            # Validate status is provided
            if not new_status:
                return Response({
                    'success': False,
                    'error': 'Status is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Valid status values
            valid_statuses = ['pending', 'received', 'in_progress', 'completed', 'cancelled', 'rejected']
            
            # Validate status is valid
            if new_status not in valid_statuses:
                return Response({
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Store old status
            old_status = service_request.status
            
            # If status hasn't changed, return early
            if old_status == new_status:
                return Response({
                    'success': True,
                    'message': 'Status is already set to this value',
                    'status': service_request.status,
                    'request_id': service_request.id,
                    'request_code': service_request.get_request_code()
                }, status=status.HTTP_200_OK)
            
            # Update the status
            service_request.status = new_status
            service_request.save()
            
            # Create update record
            ServiceRequestUpdate.objects.create(
                service_request=service_request,
                update_type='status_change',
                old_value=old_status,
                new_value=new_status,
                notes=f'Status changed from {old_status} to {new_status}'
            )
            
            # SEND EMAIL NOTIFICATION TO CUSTOMER
            email_sent = self.send_status_notification(service_request, old_status, new_status)
            
            logger.info(f"Status changed for request {request_id}: {old_status} -> {new_status}")
            
            # Return success response with email status
            return Response({
                'success': True,
                'message': f'Status changed from {old_status} to {new_status}',
                'status': service_request.status,
                'old_status': old_status,
                'new_status': new_status,
                'request_id': service_request.id,
                'request_code': service_request.get_request_code(),
                'email_notification_sent': email_sent,
                'customer_email': service_request.email if service_request.email else 'No email on file'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error changing status: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'count': queryset.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in list: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except ServiceRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Service request not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics"""
        try:
            queryset = ServiceRequest.objects.all()
            
            stats = {
                'total': queryset.count(),
                'pending': queryset.filter(status='pending').count(),
                'received': queryset.filter(status='received').count(),
                'in_progress': queryset.filter(status='in_progress').count(),
                'completed': queryset.filter(status='completed').count(),
                'cancelled': queryset.filter(status='cancelled').count(),
                'rejected': queryset.filter(status='rejected').count(),
                'urgent': queryset.filter(priority='urgent').count(),
                'high_priority': queryset.filter(priority='high').count(),
                'medium_priority': queryset.filter(priority='medium').count(),
                'low_priority': queryset.filter(priority='low').count(),
                'emergency': queryset.filter(is_emergency=True).count(),
                'avg_rating': queryset.filter(user_rating__isnull=False).aggregate(models.Avg('user_rating'))['user_rating__avg'] or 0,
                'today_requests': queryset.filter(created_at__date=timezone.now().date()).count(),
                'this_week_requests': queryset.filter(
                    created_at__gte=timezone.now() - timezone.timedelta(days=7)
                ).count(),
            }
            
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in stats: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = ServiceType.objects.filter(is_active=True).order_by('name')
    serializer_class = ServiceTypeSerializer
    permission_classes = [AllowAny]