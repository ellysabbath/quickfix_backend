# registration/views.py
# Add this import at the top of views.py
from django.db.models import Q
import django.db.models as models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from users.models import CustomUser, OTP
from django.contrib.auth.hashers import check_password
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from .serializers import *
from django.utils import timezone
from datetime import timedelta
import random

class Stage1PersonalInfoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes=[]
    
    def post(self, request):
        serializer = PersonalInfoSerializer(data=request.data)
        if serializer.is_valid():
            # Store in session for multi-step registration
            request.session['personal_info'] = serializer.validated_data
            request.session.modified = True
            
            return Response({
                'success': True,
                'message': 'Personal info saved',
                'next_step': 'contact',
                'data': serializer.validated_data
            })
        return Response(serializer.errors, status=400)

class Stage2ContactDetailsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes=[]
    
    def post(self, request):
        serializer = ContactDetailsSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            phone = serializer.validated_data['phone']
            
            # Get personal info from session
            personal_info = request.session.get('personal_info', {})
            
            # Check if user exists
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': personal_info.get('first_name', ''),
                    'last_name': personal_info.get('last_name', ''),
                    'phone': phone,
                    'registration_stage': 2,
                    'contact_details_completed_at': timezone.now()
                }
            )
            
            if not created:
                # Update existing user
                user.phone = phone
                user.registration_stage = 2
                user.contact_details_completed_at = timezone.now()
                user.save()
            
            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            OTP.objects.create(
                user=user,
                code=otp_code,
                purpose='email_verification',
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            
            print(f"📧 OTP for {email}: {otp_code}")  # Remove in production
            
            request.session['user_id'] = str(user.id)
            request.session.modified = True
            
            return Response({
                'success': True,
                'message': 'Contact details saved',
                'user_id': str(user.id),
                'requires_otp': True,
                'next_step': 'verify_email'
            })
        return Response(serializer.errors, status=400)

class Stage3LocationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes=[]
    
    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            user_id = request.session.get('user_id')
            if not user_id:
                return Response({'error': 'Session expired'}, status=400)
            
            try:
                user = CustomUser.objects.get(id=user_id)
                user.city = serializer.validated_data['city']
                user.state = serializer.validated_data['state']
                user.registration_stage = 3
                user.location_completed_at = timezone.now()
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Location saved',
                    'next_step': 'security'
                })
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
        return Response(serializer.errors, status=400)

class Stage4SecurityView(APIView):
    permission_classes = [AllowAny]
    authentication_classes=[]
    
    def post(self, request):
        serializer = SecuritySerializer(data=request.data)
        if serializer.is_valid():
            user_id = request.session.get('user_id')
            if not user_id:
                return Response({'error': 'Session expired'}, status=400)
            
            try:
                user = CustomUser.objects.get(id=user_id)
                user.set_password(serializer.validated_data['password'])
                user.registration_stage = 4
                user.security_completed_at = timezone.now()
                user.save()
                
                # Generate phone OTP
                otp_code = str(random.randint(100000, 999999))
                OTP.objects.create(
                    user=user,
                    code=otp_code,
                    purpose='phone_verification',
                    expires_at=timezone.now() + timedelta(minutes=10)
                )
                
                print(f"📱 OTP for phone {user.phone}: {otp_code}")
                
                # Clear session
                request.session.flush()
                
                return Response({
                    'success': True,
                    'message': 'Account created! Verify phone',
                    'requires_otp': True,
                    'next_step': 'verify_phone'
                })
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)
        return Response(serializer.errors, status=400)

class VerifyOTPView(APIView):

    permission_classes = [AllowAny]
    authentication_classes=[]



    def post(self, request):
        otp_code = request.data.get('otp')
        purpose = request.data.get('purpose')
        user_id = request.session.get('user_id')
        
        if not all([otp_code, purpose, user_id]):
            return Response({'error': 'Missing data'}, status=400)
        
        try:
            user = CustomUser.objects.get(id=user_id)
            otp = OTP.objects.filter(
                user=user,
                code=otp_code,
                purpose=purpose,
                is_used=False
            ).order_by('-created_at').first()
            
            if not otp or not otp.is_valid():
                return Response({'error': 'Invalid OTP'}, status=400)
            
            # Mark OTP as used
            otp.is_used = True
            otp.save()
            
            # Update user verification
            if purpose == 'email_verification':
                user.is_email_verified = True
            elif purpose == 'phone_verification':
                user.is_phone_verified = True
            
            user.save()
            
            return Response({
                'success': True,
                'message': 'Verification successful',
                'next_step': 'complete'
            })
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

class TestView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'online',
            'message': 'Django API is working!',
            'timestamp': timezone.now().isoformat()
        })




# =======================//    LOGIN-LOGOUT VIEW    =======================
# views.py - Add these views
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import UserSerializer

class LoginView(APIView):
    """
    Login endpoint with CSRF protection and session management
    Endpoint: POST /api/login/
    """
    permission_classes = [AllowAny]
    
    @method_decorator(csrf_exempt)  # Disable CSRF for this view since we handle it manually
    def post(self, request):
        """
        Handle user login with email and password
        Request body: {"email": "user@example.com", "password": "password123"}
        """
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '').strip()
        
        # Validate required fields
        if not email or not password:
            return Response(
                {
                    'success': False,
                    'error': 'Email and password are required',
                    'error_type': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return Response(
                {
                    'success': False,
                    'error': 'Please enter a valid email address',
                    'error_type': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get user by email (case-insensitive)
            user = CustomUser.objects.get(email__iexact=email)
            
            # Check if user is active
            if not user.is_active:
                return Response(
                    {
                        'success': False,
                        'error': 'Your account has been deactivated. Please contact support.',
                        'error_type': 'account_inactive'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if email is verified (you might want to make this optional based on role)
            if not user.is_email_verified:
                return Response(
                    {
                        'success': False,
                        'error': 'Email not verified. Please check your email for verification link.',
                        'error_type': 'email_not_verified',
                        'user_id': str(user.id),
                        'role': user.role  # Include role in response
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify password
            if not check_password(password, user.password):
                # Track failed attempts (you can implement this)
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid email or password',
                        'error_type': 'invalid_credentials'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Password is correct - log the user in
            try:
                # Use Django's login function to create session
                login(request, user)
                
                # Generate CSRF token for subsequent requests
                csrf_token = get_token(request)
                
                # Serialize user data
                serializer = UserSerializer(user)
                
                # Prepare response data
                response_data = {
                    'success': True,
                    'message': 'Login successful',
                    'user': serializer.data,
                    'session_id': request.session.session_key,
                    'csrf_token': csrf_token,
                    'user_role': user.role,  # Explicitly include role
                    'is_admin': user.is_admin,
                    'is_mechanic': user.is_mechanic,
                    'is_garage_owner': user.is_garage_owner,
                    'is_customer': user.is_customer
                }
                
                # Create response
                response = Response(response_data, status=status.HTTP_200_OK)
                
                # Set session cookie for browser clients (optional for React Native)
                # For React Native, we'll return the CSRF token in the response body
                # and the session ID for tracking
                
                return response
                
            except Exception as login_error:
                # Log this error for debugging
                print(f"Login session error: {str(login_error)}")
                return Response(
                    {
                        'success': False,
                        'error': 'Login process failed. Please try again.',
                        'error_type': 'session_error'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except CustomUser.DoesNotExist:
            # User not found - don't reveal if email exists for security
            return Response(
                {
                    'success': False,
                    'error': 'Invalid email or password',
                    'error_type': 'invalid_credentials'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except Exception as e:
            # Catch any other unexpected errors
            print(f"Unexpected login error: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'An unexpected error occurred. Please try again.',
                    'error_type': 'server_error'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({'success': True, 'message': 'Logged out successfully'})

class CheckAuthView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'user': serializer.data
        })


# =========================== // PASSWORD RESET //=============================
"""
Password reset views with email functionality.
Includes OTP generation, email sending, and password reset flow.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
import random
import hashlib
import json
from django.core.cache import cache

# Email imports
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from users.models import CustomUser, OTP


class PasswordResetRequestView(APIView):
    """
    Request password reset OTP
    Endpoint: POST /api/auth/password-reset/request/
    Request body: {"email": "user@example.com"}
    """
    permission_classes = [AllowAny]
    authentication_classes = [] 

    @method_decorator(csrf_exempt)     
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(email=email)
            
            # Generate 6-digit OTP
            otp_code = str(random.randint(100000, 999999))
            
            # Clean up old OTPs for this user
            OTP.objects.filter(user=user, purpose='password_reset').delete()
            
            # Create new OTP record
            otp = OTP.objects.create(
                user=user,
                code=otp_code,
                purpose='password_reset',
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Send email with OTP
            email_sent = self.send_password_reset_email(user, otp_code)
            
            if not email_sent:
                # If email fails, still return success but log it
                print(f"⚠️ Email failed, but OTP generated: {otp_code}")
            
            # Generate secure reset token
            token_data = {
                'user_id': str(user.id),
                'email': email,
                'otp_id': str(otp.id),
                'timestamp': timezone.now().isoformat()
            }
            reset_token = hashlib.sha256(
                json.dumps(token_data, sort_keys=True).encode()
            ).hexdigest()
            
            # Store token in cache (15 minutes)
            cache.set(f'pwd_reset_{reset_token}', token_data, 900)
            
            response_data = {
                'success': True,
                'message': 'Password reset OTP has been sent to your email',
                'reset_token': reset_token,
                'otp_expires_in': 15,
            }
            
            # For development only - include OTP in response
            if settings.DEBUG:
                response_data['debug_otp'] = otp_code
            
            return Response(response_data)
            
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists (security best practice)
            return Response({
                'success': True,
                'message': 'If your email is registered, you will receive instructions shortly'
            })
    
    def send_password_reset_email(self, user, otp_code):
        """
        Send password reset email with OTP
        Returns: True if email sent successfully, False otherwise
        """
        try:
            # Prepare email context
            context = {
                'user': user,
                'otp_code': otp_code,
                'app_name': getattr(settings, 'APP_NAME', 'QuickFix Automotive'),
                'expiry_minutes': 15,
                'support_email': getattr(settings, 'APP_SUPPORT_EMAIL', 'support@quickfixauto.com'),
            }
            
            # Try to render HTML template
            try:
                html_content = render_to_string('emails/password_reset-otp.html', context)
            except:
                # Fallback to simple HTML if template doesn't exist
                html_content = f"""
                <html>
                <body>
                    <h2>Password Reset Request</h2>
                    <p>Hello {user.first_name} {user.last_name},</p>
                    <p>Your password reset OTP is: <strong>{otp_code}</strong></p>
                    <p>This code expires in 15 minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </body>
                </html>
                """
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Build email subject
            subject = f'Password Reset OTP - {context["app_name"]}'
            
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            print(f"✅ Password reset email sent to: {user.email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {user.email}: {str(e)}")
            return False


class VerifyPasswordResetOTPView(APIView):
    """
    Verify password reset OTP
    Endpoint: POST /api/auth/password-reset/verify-otp/
    Request body: {"reset_token": "abc123", "otp": "123456"}
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        reset_token = request.data.get('reset_token')
        otp = request.data.get('otp')
        
        print(f"🔍 DEBUG - Received OTP: {otp}, Reset Token: {reset_token}")
        
        if not reset_token or not otp:
            return Response(
                {'error': 'Reset token and OTP are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate OTP format
        if not otp.isdigit() or len(otp) != 6:
            print(f"⚠️ DEBUG - Invalid OTP format: {otp}")
            return Response(
                {'error': 'OTP must be a 6-digit number'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Retrieve token from cache
        cache_key = f'pwd_reset_{reset_token}'
        token_data = cache.get(cache_key)
        
        if not token_data:
            print(f"⚠️ DEBUG - Cache miss for key: {cache_key}")
            return Response(
                {'error': 'Invalid or expired reset token. Please request a new OTP.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f"✅ DEBUG - Token data found: {token_data}")
        
        try:
            user = CustomUser.objects.get(id=token_data['user_id'])
            
            # Find matching OTP
            otp_record = OTP.objects.filter(
                user=user,
                code=otp,
                purpose='password_reset',
                is_used=False
            ).order_by('-created_at').first()
            
            # DEBUG: Check all available OTPs for this user
            all_otps = OTP.objects.filter(
                user=user,
                purpose='password_reset',
                is_used=False
            ).values('code', 'created_at', 'expires_at')
            
            print(f"🔍 DEBUG - All available OTPs for user {user.email}:")
            for o in all_otps:
                print(f"  Code: {o['code']}, Created: {o['created_at']}, Expires: {o['expires_at']}")
            
            print(f"🔍 DEBUG - Looking for OTP: {otp}")
            print(f"🔍 DEBUG - Found OTP record: {otp_record}")
            
            # Validate OTP
            if not otp_record:
                print(f"❌ DEBUG - No matching OTP found")
                return Response(
                    {'error': 'Invalid OTP code'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not otp_record.is_valid():
                print(f"❌ DEBUG - OTP expired: {otp_record.expires_at}")
                return Response(
                    {'error': 'OTP has expired. Please request a new one.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print(f"✅ DEBUG - OTP verified successfully!")
            
            # Mark OTP as used
            otp_record.is_used = True
            otp_record.used_at = timezone.now()
            otp_record.save()
            
            # Update token with verification timestamp
            token_data['otp_verified'] = True
            token_data['verified_at'] = timezone.now().isoformat()
            token_data['otp_record_id'] = str(otp_record.id)
            
            # Extend token validity
            cache.set(cache_key, token_data, 900)  # Another 15 minutes
            
            return Response({
                'success': True,
                'message': 'OTP verified successfully',
                'reset_token': reset_token,
                'next_step': 'reset_password'
            })
            
        except CustomUser.DoesNotExist:
            print(f"❌ DEBUG - User not found: {token_data.get('user_id')}")
            return Response(
                {'error': 'User account not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CompletePasswordResetView(APIView):
    """
    Complete password reset with new password
    Endpoint: POST /api/auth/password-reset/complete/
    Request body: {
        "reset_token": "abc123",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123"
    }
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        # Validate all fields exist
        if not all([reset_token, new_password, confirm_password]):
            return Response(
                {'error': 'All fields are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check password match
        if new_password != confirm_password:
            return Response(
                {'error': 'Passwords do not match'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate password strength
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Retrieve and validate token
        cache_key = f'pwd_reset_{reset_token}'
        token_data = cache.get(cache_key)
        
        if not token_data:
            return Response(
                {'error': 'Invalid or expired reset session. Please start over.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not token_data.get('otp_verified'):
            return Response(
                {'error': 'OTP not verified. Please verify OTP first.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(id=token_data['user_id'])
            
            # Verify OTP was actually used (check if exists and is_used=True)
            try:
                otp_record = OTP.objects.get(
                    id=token_data.get('otp_record_id'),
                    user=user,
                    is_used=True
                )
                
                # Check if verification was recent (using created_at timestamp from token_data)
                # We stored verified_at in token_data during OTP verification
                if 'verified_at' in token_data:
                    # Parse the timestamp from token_data
                    from datetime import datetime
                    verified_time = datetime.fromisoformat(token_data['verified_at'])
                    time_diff = timezone.now() - verified_time
                    
                    if time_diff.total_seconds() > 1800:  # 30 minutes
                        return Response(
                            {'error': 'Reset session expired. Please start over.'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                        
            except OTP.DoesNotExist:
                return Response(
                    {'error': 'Invalid reset session'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update user password
            user.set_password(new_password)
            user.save()
            
            # Cleanup: remove token from cache
            cache.delete(cache_key)
            
            # Cleanup: remove all password reset OTPs for this user
            OTP.objects.filter(user=user, purpose='password_reset').delete()
            
            # Send confirmation email (optional)
            try:
                self.send_password_changed_email(user)
            except:
                pass  # Don't fail if email confirmation fails
            
            return Response({
                'success': True,
                'message': 'Password has been reset successfully. You can now log in with your new password.'
            })
            
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User account not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def send_password_changed_email(self, user):
        """Send confirmation email after password change"""
        try:
            context = {
                'user': user,
                'app_name': getattr(settings, 'APP_NAME', 'QuickFix Automotive'),
                'support_email': getattr(settings, 'APP_SUPPORT_EMAIL', 'support@quickfixauto.com'),
            }
            
            # Simple HTML email
            html_content = f"""
            <html>
            <body>
                <h2>Password Changed Successfully</h2>
                <p>Hello {user.first_name} {user.last_name},</p>
                <p>Your password has been successfully changed.</p>
                <p>If you did not make this change, please contact our support team immediately.</p>
                <p><strong>Security Tip:</strong> Use a strong, unique password and enable two-factor authentication if available.</p>
            </body>
            </html>
            """
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=f'Password Changed - {context["app_name"]}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            print(f"✅ Password change confirmation sent to: {user.email}")
            
        except Exception as e:
            print(f"⚠️ Could not send password change confirmation: {str(e)}")

class TestEmailView(APIView):
    """
    Test endpoint for email configuration
    Endpoint: GET /api/test-email/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Test email to yourself
            from django.core.mail import send_mail
            
            send_mail(
                subject='Test Email from Django - QuickFix',
                message='This is a test email to verify your Django email configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],  # Send to yourself
                fail_silently=False,
            )
            
            return Response({
                'success': True,
                'message': 'Test email sent successfully!',
                'to': settings.EMAIL_HOST_USER,
                'from': settings.DEFAULT_FROM_EMAIL,
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to send test email: {str(e)}',
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Optional: Helper view to check email template
class CheckTemplateView(APIView):
    """
    Check if email template exists
    Endpoint: GET /api/check-template/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Try to render template
            html = render_to_string('emails/password_reset-otp.html', {
                'user': {'first_name': 'Test', 'last_name': 'User', 'email': 'test@example.com'},
                'otp_code': '123456',
                'app_name': 'QuickFix Automotive',
                'expiry_minutes': 15,
            })
            
            return Response({
                'success': True,
                'message': 'Email template exists and can be rendered',
                'template_length': len(html),
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Template error: {str(e)}',
                'suggestion': 'Create file at: registration/templates/emails/password_reset-otp.html',
            }, status=status.HTTP_404_NOT_FOUND)
        


# =======================//    DASHBOARD MODELS    =======================
# dashboard/views.py (simplified version)
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from users.models import Service, Garage, GarageService, ServiceDetail, Booking
from .serializers import (
    ServiceSerializer, GarageSerializer, GarageServiceSerializer,
    ServiceDetailSerializer, BookingSerializer
)

class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# Regular ViewSets
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    pagination_class = AdminPagination
    permission_classes = [permissions.AllowAny]

class GarageViewSet(viewsets.ModelViewSet):
    queryset = Garage.objects.all()
    serializer_class = GarageSerializer
    pagination_class = AdminPagination
    permission_classes = [permissions.AllowAny]

class GarageServiceViewSet(viewsets.ModelViewSet):
    queryset = GarageService.objects.all()
    serializer_class = GarageServiceSerializer
    permission_classes = [AllowAny]

class ServiceDetailViewSet(viewsets.ModelViewSet):
    queryset = ServiceDetail.objects.all()
    serializer_class = ServiceDetailSerializer
    permission_classes = [AllowAny]

# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from users.models import Booking, Service, Garage
from .serializers import BookingSerializer, BookingCreateSerializer, ServiceSerializer, GarageSerializer

@method_decorator(csrf_exempt, name='dispatch')
class BookingsViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Bookings with auto-loading of service price
    """
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer
    
    # Remove ALL authentication for development
    authentication_classes = []  # Empty list = no authentication at all
    permission_classes = [permissions.AllowAny]  # Allow unauthenticated access to everything
    
    def get_serializer_class(self):
        """Use different serializer for creation"""
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=start.date())
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=end.date())
            except ValueError:
                pass
        
        # Filter by scheduled date
        scheduled_date = self.request.query_params.get('scheduled_date', None)
        if scheduled_date:
            try:
                scheduled = datetime.strptime(scheduled_date, '%Y-%m-%d')
                queryset = queryset.filter(scheduled_date__date=scheduled.date())
            except ValueError:
                pass
        
        # Filter by garage
        garage_id = self.request.query_params.get('garage_id', None)
        if garage_id:
            queryset = queryset.filter(garage_id=garage_id)
        
        # Filter by service
        service_id = self.request.query_params.get('service_id', None)
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            try:
                queryset = queryset.filter(total_price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                queryset = queryset.filter(total_price__lte=float(max_price))
            except ValueError:
                pass
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(booking_number__icontains=search) |
                Q(full_name__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(location__icontains=search) |
                Q(notes__icontains=search) |
                Q(garage__name__icontains=search) |
                Q(service__name__icontains=search)
            )
        
        # Ordering
        order_by = self.request.query_params.get('order_by', '-created_at')
        if order_by in ['created_at', '-created_at', 'scheduled_date', '-scheduled_date', 
                       'total_price', '-total_price', 'full_name', '-full_name']:
            queryset = queryset.order_by(order_by)
        
        return queryset.select_related('garage', 'service', 'garage__owner')
    
    def create(self, request, *args, **kwargs):
        """
        Create booking with location processing
        """
        data = request.data.copy()
        
        # Process Google Maps link if coordinates are provided
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude and longitude and not data.get('google_maps_link'):
            data['google_maps_link'] = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        try:
            booking = serializer.save()
            
            # Return full booking details
            full_serializer = BookingSerializer(booking)
            headers = self.get_success_headers(full_serializer.data)
            
            return Response(
                {
                    'success': True,
                    'message': 'Booking created successfully',
                    'booking': full_serializer.data,
                    'booking_number': booking.booking_number
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'message': 'Failed to create booking'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """
        Update booking - auto-update price if service changes
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        data = request.data.copy()
        
        # If service is being updated, auto-update price
        if 'service_id' in data and data['service_id'] != str(instance.service_id):
            try:
                service = Service.objects.get(id=data['service_id'])
                data['price'] = str(service.base_price)
                data['total_price'] = str(service.base_price)
            except Service.DoesNotExist:
                return Response(
                    {'error': 'Service not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_update(serializer)
            return Response(
                {
                    'success': True,
                    'message': 'Booking updated successfully',
                    'booking': serializer.data
                }
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'message': 'Failed to update booking'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get comprehensive booking statistics
        """
        # Date range for stats
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Basic counts
        total_bookings = Booking.objects.count()
        today_bookings = Booking.objects.filter(created_at__date=today).count()
        week_bookings = Booking.objects.filter(created_at__date__gte=week_ago).count()
        month_bookings = Booking.objects.filter(created_at__date__gte=month_ago).count()
        
        # Revenue stats
        total_revenue = Booking.objects.aggregate(total=Sum('total_price'))['total'] or 0
        today_revenue = Booking.objects.filter(created_at__date=today).aggregate(
            total=Sum('total_price'))['total'] or 0
        week_revenue = Booking.objects.filter(created_at__date__gte=week_ago).aggregate(
            total=Sum('total_price'))['total'] or 0
        month_revenue = Booking.objects.filter(created_at__date__gte=month_ago).aggregate(
            total=Sum('total_price'))['total'] or 0
        
        # Service stats
        popular_services = Service.objects.annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')[:5]
        
        service_stats = [
            {
                'id': service.id,
                'name': service.name,
                'booking_count': service.booking_count,
                'revenue': Booking.objects.filter(service=service).aggregate(
                    total=Sum('total_price'))['total'] or 0
            }
            for service in popular_services
        ]
        
        # Garage stats
        popular_garages = Garage.objects.annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')[:5]
        
        garage_stats = [
            {
                'id': garage.id,
                'name': garage.name,
                'city': garage.city,
                'booking_count': garage.booking_count,
                'revenue': Booking.objects.filter(garage=garage).aggregate(
                    total=Sum('total_price'))['total'] or 0
            }
            for garage in popular_garages
        ]
        
        # Recent bookings
        recent_bookings = Booking.objects.select_related('garage', 'service').order_by('-created_at')[:10]
        recent_serializer = BookingSerializer(recent_bookings, many=True)
        
        return Response({
            'counts': {
                'total': total_bookings,
                'today': today_bookings,
                'week': week_bookings,
                'month': month_bookings
            },
            'revenue': {
                'total': float(total_revenue),
                'today': float(today_revenue),
                'week': float(week_revenue),
                'month': float(month_revenue),
                'average': float(total_revenue / total_bookings) if total_bookings > 0 else 0
            },
            'popular_services': service_stats,
            'popular_garages': garage_stats,
            'recent_bookings': recent_serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming bookings (next 7 days)
        """
        today = timezone.now().date()
        next_week = today + timedelta(days=7)
        
        upcoming = Booking.objects.filter(
            scheduled_date__date__gte=today,
            scheduled_date__date__lte=next_week
        ).select_related('garage', 'service').order_by('scheduled_date')
        
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        """
        Update booking location with Google Maps link
        """
        booking = self.get_object()
        location = request.data.get('location', '')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if location:
            booking.location = location
        
        if latitude and longitude:
            booking.google_maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response({
            'success': True,
            'message': 'Location updated successfully',
            'booking': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create multiple bookings at once
        """
        bookings_data = request.data
        if not isinstance(bookings_data, list):
            return Response(
                {'error': 'Expected a list of bookings'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_bookings = []
        errors = []
        
        for booking_data in bookings_data:
            serializer = BookingCreateSerializer(data=booking_data)
            if serializer.is_valid():
                try:
                    booking = serializer.save()
                    created_bookings.append(booking.booking_number)
                except Exception as e:
                    errors.append({
                        'data': booking_data,
                        'error': str(e)
                    })
            else:
                errors.append({
                    'data': booking_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'success': True if not errors else False,
            'created_count': len(created_bookings),
            'failed_count': len(errors),
            'created_bookings': created_bookings,
            'errors': errors if errors else None
        })

@method_decorator(csrf_exempt, name='dispatch')
class BookingServiceViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Services
    """
    queryset = Service.objects.all().order_by('-created_at')
    serializer_class = ServiceSerializer
    
    # Remove ALL authentication for development
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['get'])
    def with_bookings(self, request):
        """
        Get services with booking count
        """
        services = Service.objects.annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')
        
        data = []
        for service in services:
            service_data = ServiceSerializer(service).data
            service_data['booking_count'] = service.booking_count
            data.append(service_data)
        
        return Response(data)

@method_decorator(csrf_exempt, name='dispatch')
class   BookingGarageViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Garages
    """
    queryset = Garage.objects.all().order_by('-created_at')
    serializer_class = GarageSerializer
    
    # Remove ALL authentication for development
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['get'])
    def with_bookings(self, request):
        """
        Get garages with booking count
        """
        garages = Garage.objects.annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')
        
        data = []
        for garage in garages:
            garage_data = GarageSerializer(garage).data
            garage_data['booking_count'] = garage.booking_count
            data.append(garage_data)
        
        return Response(data)

@method_decorator(csrf_exempt, name='dispatch')
class AdminServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by('-created_at')
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

@method_decorator(csrf_exempt, name='dispatch')
class AdminGarageViewSet(viewsets.ModelViewSet):
    queryset = Garage.objects.all().order_by('-created_at')
    serializer_class = GarageSerializer
    permission_classes = [permissions.AllowAny]

# registration/views.py
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q



@method_decorator(csrf_exempt, name='dispatch') 
class AdminGarageViewSet(viewsets.ModelViewSet):
    """
    COMPLETELY OPEN API ENDPOINT - No authentication required for ANY operation
    WARNING: This is highly insecure for production! Use only for development/testing.
    """
    
    queryset = Garage.objects.all().order_by('-created_at')
    serializer_class = GarageSerializer
    pagination_class = AdminPagination
    
    # 1. Remove ALL authentication
    authentication_classes = []  # Empty list = no authentication at all
    
    # 2. Allow ANYONE for ALL operations
    permission_classes = [AllowAny]  # Allow unauthenticated access to everything
    
    # 3. Disable CSRF protection completely
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    # 4. Override get_permissions to ensure AllowAny for everything
    def get_permissions(self):
        """
        Force AllowAny for all actions including create, update, delete
        """
        return [AllowAny()]
    
    # 5. Override get_authenticators to remove ALL authentication
    def get_authenticators(self):
        """
        Remove all authentication classes
        """
        return []
    
    # 6. Optional: Add custom filtering/search for public access
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Add search functionality for public users
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(city__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Filter by city
        city = self.request.query_params.get('city', None)
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Filter by status
        is_open = self.request.query_params.get('is_open', None)
        if is_open is not None:
            queryset = queryset.filter(is_open=is_open.lower() == 'true')
        
        return queryset.select_related('owner').prefetch_related('garage_services')
    
    # 7. Keep your existing create method (now accessible to anyone)
    def create(self, request, *args, **kwargs):
        """Handle garage creation - accessible to ANYONE"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            garage = serializer.save()
            
            # If services are provided, create them
            if 'services' in request.data and request.data['services']:
                services_data = request.data['services']
                if isinstance(services_data, str):
                    services_list = [s.strip() for s in services_data.split(',')]
                else:
                    services_list = services_data
                
                for service_name in services_list:
                    try:
                        service = Service.objects.get(name__iexact=service_name)
                        GarageService.objects.create(
                            garage=garage,
                            service=service,
                            price=service.base_price,
                            duration='1 hour'
                        )
                    except Service.DoesNotExist:
                        pass
            
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED,
                headers=self.get_success_headers(serializer.data)
            )
            
        except Exception as e:
            return Response(
                {
                    'error': str(e), 
                    'message': 'Failed to create garage',
                    'detail': 'This endpoint is open to everyone for testing'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # 8. Keep your existing update method (now accessible to anyone)
    def update(self, request, *args, **kwargs):
        """Handle garage update - accessible to ANYONE"""
        instance = self.get_object()
        
        # Allow partial updates
        partial = kwargs.pop('partial', True)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            garage = serializer.save()
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e), 'message': 'Failed to update garage'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # 9. Add public stats endpoint
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def public_stats(self, request):
        """Public statistics accessible to anyone"""
        stats = {
            'total_garages': Garage.objects.count(),
            'active_garages': Garage.objects.filter(is_active=True).count(),
            'verified_garages': Garage.objects.filter(is_verified=True).count(),
            'open_now': Garage.objects.filter(is_open=True).count(),
            'with_delivery': Garage.objects.filter(delivery_available=True).count(),
            'cities': list(Garage.objects.exclude(city='').values_list('city', flat=True).distinct()),
        }
        return Response(stats)
    
    # 10. Add bulk create endpoint (accessible to anyone)
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def bulk_create(self, request):
        """Create multiple garages at once - accessible to ANYONE"""
        garages_data = request.data
        if not isinstance(garages_data, list):
            return Response(
                {'error': 'Expected a list of garages'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_garages = []
        errors = []
        
        for garage_data in garages_data:
            serializer = self.get_serializer(data=garage_data)
            if serializer.is_valid():
                try:
                    garage = serializer.save()
                    created_garages.append(serializer.data)
                except Exception as e:
                    errors.append({
                        'data': garage_data,
                        'error': str(e)
                    })
            else:
                errors.append({
                    'data': garage_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'created': len(created_garages),
            'failed': len(errors),
            'garages': created_garages,
            'errors': errors if errors else None
        })


        

# views.py - Update ALL your viewsets to include csrf_exempt decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class AdminServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by('-created_at')
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_authenticators(self):
        return []
  

@method_decorator(csrf_exempt, name='dispatch')
class AdminGarageServiceViewSet(viewsets.ModelViewSet):
    queryset = GarageService.objects.all().order_by('-created_at')
    serializer_class = GarageServiceSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_authenticators(self):
        return []
    

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

@method_decorator(csrf_exempt, name='dispatch')
class AdminServiceDetailViewSet(viewsets.ModelViewSet):
    queryset = ServiceDetail.objects.all().order_by('-created_at')
    serializer_class = ServiceDetailSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_authenticators(self):
        return []
    
    def get_queryset(self):
        queryset = ServiceDetail.objects.all()
        garage_service = self.request.query_params.get('garage_service', None)
        if garage_service is not None:
            queryset = queryset.filter(garage_service=garage_service)
        return queryset
    

@method_decorator(csrf_exempt, name='dispatch')
class AdminBookingViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Bookings with auto-loading of service price
    """
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer
    pagination_class = AdminPagination
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        """Use different serializer for creation"""
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            try:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=start.date())
            except ValueError:
                pass
        
        if end_date:
            try:
                from datetime import datetime
                end = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=end.date())
            except ValueError:
                pass
        
        # Filter by scheduled date
        scheduled_date = self.request.query_params.get('scheduled_date', None)
        if scheduled_date:
            try:
                from datetime import datetime
                scheduled = datetime.strptime(scheduled_date, '%Y-%m-%d')
                queryset = queryset.filter(scheduled_date__date=scheduled.date())
            except ValueError:
                pass
        
        # Filter by garage
        garage_id = self.request.query_params.get('garage_id', None)
        if garage_id:
            queryset = queryset.filter(garage_id=garage_id)
        
        # Filter by service
        service_id = self.request.query_params.get('service_id', None)
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            try:
                queryset = queryset.filter(total_price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                queryset = queryset.filter(total_price__lte=float(max_price))
            except ValueError:
                pass
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(booking_number__icontains=search) |
                Q(full_name__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(location__icontains=search) |
                Q(notes__icontains=search) |
                Q(garage__name__icontains=search) |
                Q(service__name__icontains=search)
            )
        
        # Ordering
        order_by = self.request.query_params.get('order_by', '-created_at')
        if order_by in ['created_at', '-created_at', 'scheduled_date', '-scheduled_date', 
                       'total_price', '-total_price', 'full_name', '-full_name']:
            queryset = queryset.order_by(order_by)
        
        return queryset.select_related('garage', 'service', 'garage__owner')
    
    def create(self, request, *args, **kwargs):
        """
        Create booking with location processing
        """
        data = request.data.copy()
        
        # Process Google Maps link if coordinates are provided
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude and longitude and not data.get('google_maps_link'):
            data['google_maps_link'] = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        try:
            booking = serializer.save()
            
            # Return full booking details
            full_serializer = BookingSerializer(booking)
            headers = self.get_success_headers(full_serializer.data)
            
            return Response(
                {
                    'success': True,
                    'message': 'Booking created successfully',
                    'booking': full_serializer.data,
                    'booking_number': booking.booking_number
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'message': 'Failed to create booking'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
   



# ===============================// MANAGE USERS //================
# users/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from django.shortcuts import get_object_or_404
from .serializers import (
    UserSerializer, UserCreateSerializer, 
    UserUpdateSerializer, ChangePasswordSerializer
)

CustomUser = get_user_model()

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit, but allow anyone to view.
    """
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Only allow admin users for POST, PUT, PATCH, DELETE
        return request.user and request.user.is_authenticated and request.user.is_admin

class IsAdminOrSelf(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit any user, or users to edit themselves.
    """
    def has_object_permission(self, request, view, obj):
        # Allow admins to do anything
        if request.user.is_admin:
            return True
        
        # Allow users to view/edit their own profile
        if request.method in permissions.SAFE_METHODS:
            return request.user == obj
        
        # For write operations, users can only edit themselves
        return request.user == obj




        
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.shortcuts import get_object_or_404
from users.models import CustomUser
from .serializers import (
    UserSerializer, 
    UserCreateSerializer, 
    UserUpdateSerializer,
    ChangePasswordSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    
    list:
    Return all users, ordered by date joined.
    
    retrieve:
    Return a specific user by UUID.
    
    create:
    Create a new user.
    
    update:
    Update a user.
    
    partial_update:
    Partially update a user.
    
    destroy:
    Delete a user (soft delete by deactivating).
    """
    queryset = CustomUser.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    lookup_field = 'id'
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on action.
        """
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        """
        Optionally restricts the returned users based on query parameters.
        """
        queryset = CustomUser.objects.all().order_by('-date_joined')
        
        # Filter by role if provided
        role = self.request.query_params.get('role', None)
        if role is not None:
            queryset = queryset.filter(role=role)
        
        # Filter by active status if provided
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active_bool)
        
        # Filter by search query
        search = self.request.query_params.get('search', None)
        if search is not None:
            queryset = queryset.filter(
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(phone__icontains=search)
            )
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        Override to add pagination and metadata.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'users': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's profile.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_me(self, request):
        """
        Update current user's profile.
        """
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, id=None):
        """
        Change user password.
        """
        user = self.get_object()
        
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            # Verify old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({"detail": "Password updated successfully."})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, id=None):
        """
        Activate a user account.
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response({
            "detail": f"User {user.email} has been activated.",
            "is_active": user.is_active
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, id=None):
        """
        Deactivate a user account.
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        
        return Response({
            "detail": f"User {user.email} has been deactivated.",
            "is_active": user.is_active
        })
    
    @action(detail=True, methods=['post'])
    def verify_email(self, request, id=None):
        """
        Manually verify a user's email.
        """
        user = self.get_object()
        user.is_email_verified = True
        user.save()
        
        return Response({
            "detail": f"Email for {user.email} has been verified.",
            "is_email_verified": user.is_email_verified
        })
    
    @action(detail=True, methods=['post'])
    def verify_phone(self, request, id=None):
        """
        Manually verify a user's phone.
        """
        user = self.get_object()
        user.is_phone_verified = True
        user.save()
        
        return Response({
            "detail": f"Phone for {user.email} has been verified.",
            "is_phone_verified": user.is_phone_verified
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get user statistics.
        """
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        verified_users = CustomUser.objects.filter(is_email_verified=True).count()
        
        # Count by role
        role_counts = {}
        for role_code, role_name in CustomUser.ROLE_CHOICES:
            count = CustomUser.objects.filter(role=role_code).count()
            role_counts[role_name] = count
        
        # Count by registration stage
        stage_counts = {}
        for stage in range(1, 5):
            count = CustomUser.objects.filter(registration_stage=stage).count()
            stage_counts[f'stage_{stage}'] = count
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'role_distribution': role_counts,
            'registration_stages': stage_counts,
            'recent_users': CustomUser.objects.order_by('-date_joined')[:5].count()
        })
    
    def perform_create(self, serializer):
        """
        Create a new user with additional logic if needed.
        """
        user = serializer.save()
        return user
    
    def perform_update(self, serializer):
        """
        Update user with additional logic if needed.
        """
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Instead of hard delete, deactivate the user (safer).
        """
        instance.is_active = False
        instance.save()

# ============================= // END MANAGE USERS //=======================
# router.register(r'users', UserViewSet, basename='user')