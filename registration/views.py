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
# Add these imports at the top of views.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import threading

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
                    'role': 'customer',  # FIX: EXPLICITLY SET ROLE TO CUSTOMER
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

            print(f"📧 OTP for {email}: {otp_code}")

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








# ===========================// SEND OTP VIEW //===================================
# ===========================// SEND OTP VIEW (Initial Send) //===================================
class SendOTPView(APIView):
    """
    API View to send INITIAL OTP to user's email or phone after registration
    This is for FIRST-TIME sending, not resending
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """
        Handle INITIAL OTP send request (first time after registration)
        """
        user_id = request.data.get('user_id')
        purpose = request.data.get('purpose', 'email_verification')

        # Validate required fields
        if not user_id:
            return Response({
                'success': False,
                'error': 'User ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get user
            user = CustomUser.objects.get(id=user_id)

            # For initial send, don't check recent OTPs - just send immediately
            # Mark any existing unused OTPs as expired for this user/purpose
            OTP.objects.filter(
                user=user,
                purpose=purpose,
                is_used=False
            ).update(is_used=True)

            # Generate new 6-digit OTP
            otp_code = str(random.randint(100000, 999999))

            # Set expiry time (10 minutes from now)
            expires_at = timezone.now() + timedelta(minutes=10)

            # Create new OTP record
            otp = OTP.objects.create(
                user=user,
                code=otp_code,
                purpose=purpose,
                expires_at=expires_at
            )

            # Send OTP based on purpose
            if purpose == 'email_verification':
                return self._send_email_otp(user, otp_code, expires_at, is_initial=True)
            elif purpose == 'phone_verification':
                return self._send_sms_otp(user, otp_code, expires_at, is_initial=True)
            elif purpose == 'password_reset':
                return self._send_password_reset_otp(user, otp_code, expires_at, is_initial=True)
            else:
                return Response({
                    'success': False,
                    'error': f'Unknown purpose: {purpose}'
                }, status=status.HTTP_400_BAD_REQUEST)

        except CustomUser.DoesNotExist:
            logger.warning(f"User not found with ID: {user_id}")
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Unexpected error in SendOTPView: {str(e)}")
            logger.error(traceback.format_exc())

            return Response({
                'success': False,
                'error': 'Internal server error. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _send_email_otp(self, user, otp_code, expires_at, is_initial=True):
        """
        Send INITIAL OTP via email with embedded HTML template
        """
        subject = 'Welcome to QuickFix Automotive - Verify Your Email'

        # Get user name or use generic greeting
        user_name = user.first_name if user.first_name else 'User'

        # Create HTML email template (EMBEDDED) - Initial welcome version
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to QuickFix Automotive</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #10b981;
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    padding: 30px;
                }}
                .welcome-message {{
                    background-color: #f0fdf4;
                    border-left: 4px solid #10b981;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .otp-container {{
                    background-color: #f0f9ff;
                    border: 2px dashed #3b82f6;
                    border-radius: 8px;
                    padding: 25px;
                    text-align: center;
                    margin: 25px 0;
                }}
                .otp-code {{
                    font-size: 42px;
                    font-weight: bold;
                    color: #1d4ed8;
                    letter-spacing: 10px;
                    margin: 15px 0;
                    font-family: 'Courier New', monospace;
                }}
                .expiry-info {{
                    background-color: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .footer {{
                    background-color: #f8fafc;
                    padding: 20px;
                    text-align: center;
                    color: #64748b;
                    font-size: 14px;
                    border-top: 1px solid #e2e8f0;
                }}
                .cta-button {{
                    display: inline-block;
                    background-color: #10b981;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .steps {{
                    background-color: #f8fafc;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .step {{
                    display: flex;
                    margin-bottom: 15px;
                }}
                .step-number {{
                    background-color: #3b82f6;
                    color: white;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-right: 15px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to QuickFix Automotive! 🚗</h1>
                    <p style="margin-top: 10px; opacity: 0.9;">Complete Your Registration</p>
                </div>

                <div class="content">
                    <h2 style="color: #1e293b; margin-top: 0;">Hello {user_name},</h2>

                    <div class="welcome-message">
                        <strong>🎉 Welcome to the QuickFix Automotive family!</strong>
                        <p>We're excited to have you on board. To complete your registration and start using our services, please verify your email address.</p>
                    </div>

                    <p>Here's your verification code:</p>

                    <div class="otp-container">
                        <div class="otp-code">{otp_code}</div>
                        <p style="color: #64748b; margin: 0;">Enter this code to verify your email address</p>
                    </div>

                    <div class="steps">
                        <h3 style="margin-top: 0;">📋 How to Verify:</h3>
                        <div class="step">
                            <div class="step-number">1</div>
                            <div>Copy the 6-digit code above: <strong>{otp_code}</strong></div>
                        </div>
                        <div class="step">
                            <div class="step-number">2</div>
                            <div>Go to the verification page in the QuickFix app</div>
                        </div>
                        <div class="step">
                            <div class="step-number">3</div>
                            <div>Enter the code and click "Verify Email"</div>
                        </div>
                    </div>

                    <div class="expiry-info">
                        <strong>⏰ This code expires in 10 minutes</strong><br>
                        Expires at: {expires_at.strftime('%I:%M %p')}
                    </div>

                    <p>This is your initial verification email. Once verified, you'll have full access to:</p>
                    <ul>
                        <li>✅ Book garage services</li>
                        <li>✅ Track your vehicle repairs</li>
                        <li>✅ Receive service notifications</li>
                        <li>✅ And much more!</li>
                    </ul>

                    <div style="text-align: center;">
                        <a href="#" class="cta-button">Verify Email Now</a>
                    </div>

                    <p style="margin-top: 25px;">Need help? Contact our support team at <a href="mailto:support@quickfixautomotive.com" style="color: #2563eb;">support@quickfixautomotive.com</a></p>
                </div>

                <div class="footer">
                    <p>© 2025 QuickFix Automotive. All rights reserved.</p>
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p style="font-size: 12px; opacity: 0.7;">For security, never share this code with anyone.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Create plain text version for email clients that don't support HTML
        plain_message = f"""
        Welcome to QuickFix Automotive!

        Hello {user_name},

        🎉 Welcome to the QuickFix Automotive family!

        We're excited to have you on board. To complete your registration and start using our services, please verify your email address.

        Your verification code is: {otp_code}

        📋 How to Verify:
        1. Copy the 6-digit code above: {otp_code}
        2. Go to the verification page in the QuickFix app
        3. Enter the code and click "Verify Email"

        ⏰ This code expires in 10 minutes
        Expires at: {expires_at.strftime('%I:%M %p')}

        This is your initial verification email. Once verified, you'll have full access to:
        ✅ Book garage services
        ✅ Track your vehicle repairs
        ✅ Receive service notifications
        ✅ And much more!

        Need help? Contact our support team at support@quickfixautomotive.com

        © 2025 QuickFix Automotive. All rights reserved.
        This is an automated message. Please do not reply to this email.
        """

        # Send the email
        try:
            # Log email attempt
            logger.info(f"📧 Sending INITIAL OTP email to: {user.email}")
            logger.info(f"🔑 Initial OTP Code: {otp_code}")

            # Check email backend
            email_backend = getattr(settings, 'EMAIL_BACKEND', '')
            is_console_mode = 'console' in email_backend

            # Set from email
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@quickfixautomotive.com')

            # Send the email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )

            # Log success
            logger.info(f"✅ INITIAL OTP email sent successfully to {user.email}")

            # Prepare success response
            response_data = {
                'success': True,
                'message': f'Welcome email with OTP sent to {user.email}',
                'user_id': str(user.id),
                'purpose': 'email_verification',
                'expires_at': expires_at.isoformat(),
                'expires_in_seconds': 600,
                'delivery_method': 'email',
                'is_initial': True,
                'note': 'Check your inbox and spam folder for the welcome email'
            }

            # ALWAYS include OTP in response for debugging/testing
            response_data['otp_code'] = otp_code
            response_data['debug_info'] = {
                'email_backend': email_backend,
                'to_email': user.email,
                'from_email': from_email,
                'sent_at': timezone.now().isoformat(),
                'is_initial_send': True
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"❌ Failed to send initial email to {user.email}: {str(e)}")
            logger.error(traceback.format_exc())

            # Even if email fails, return success with OTP so user can continue
            return Response({
                'success': True,
                'message': f'Welcome OTP generated successfully.',
                'otp_code': otp_code,
                'user_id': str(user.id),
                'expires_at': expires_at.isoformat(),
                'expires_in_seconds': 600,
                'warning': 'Email delivery issue - OTP shown for testing',
                'error': str(e) if settings.DEBUG else 'Email service error',
                'delivery_method': 'debug',
                'instructions': 'Use the OTP code above to verify your email',
                'is_initial': True
            })

    def _send_sms_otp(self, user, otp_code, expires_at, is_initial=True):
        """
        Send INITIAL OTP via SMS
        """
        logger.info(f"📱 Sending INITIAL SMS OTP for {user.phone}: {otp_code}")

        response_data = {
            'success': True,
            'message': 'Initial OTP created successfully',
            'otp_code': otp_code,
            'user_id': str(user.id),
            'purpose': 'phone_verification',
            'expires_at': expires_at.isoformat(),
            'expires_in_seconds': 600,
            'delivery_method': 'sms',
            'is_initial': True,
            'note': 'SMS service integration required',
            'debug_info': 'SMS not implemented - OTP shown for testing'
        }

        return Response(response_data)

    def _send_password_reset_otp(self, user, otp_code, expires_at, is_initial=True):
        """
        Send INITIAL password reset OTP via email
        """
        subject = 'QuickFix Automotive - Password Reset Request'

        user_name = user.first_name if user.first_name else 'User'

        # Create HTML email template for initial password reset
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset - QuickFix Automotive</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #dc2626;
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    padding: 30px;
                }}
                .otp-container {{
                    background-color: #fef2f2;
                    border: 2px dashed #dc2626;
                    border-radius: 8px;
                    padding: 25px;
                    text-align: center;
                    margin: 25px 0;
                }}
                .otp-code {{
                    font-size: 42px;
                    font-weight: bold;
                    color: #b91c1c;
                    letter-spacing: 10px;
                    margin: 15px 0;
                    font-family: 'Courier New', monospace;
                }}
                .warning-box {{
                    background-color: #fef3c7;
                    border: 2px solid #f59e0b;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 6px;
                }}
                .footer {{
                    background-color: #f8fafc;
                    padding: 20px;
                    text-align: center;
                    color: #64748b;
                    font-size: 14px;
                    border-top: 1px solid #e2e8f0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 Password Reset Request</h1>
                    <p style="margin-top: 10px; opacity: 0.9;">QuickFix Automotive Account Security</p>
                </div>

                <div class="content">
                    <h2 style="color: #1e293b; margin-top: 0;">Hello {user_name},</h2>

                    <p>You've requested to reset your password. Use the code below to proceed:</p>

                    <div class="otp-container">
                        <div class="otp-code">{otp_code}</div>
                        <p style="color: #64748b; margin: 0;">Enter this code to reset your password</p>
                    </div>

                    <p>This code expires at <strong>{expires_at.strftime('%I:%M %p')}</strong> (10 minutes from now).</p>

                    <div class="warning-box">
                        <strong>⚠️ SECURITY WARNING</strong>
                        <p style="margin: 10px 0;">If you didn't request a password reset, please:</p>
                        <ol style="margin: 10px 0; padding-left: 20px;">
                            <li>Ignore this email</li>
                            <li>Check your account security</li>
                            <li>Contact support immediately if suspicious</li>
                        </ol>
                    </div>

                    <p>For security reasons, this code can only be used once and will expire in 10 minutes.</p>

                    <p>Need help? Contact our support team at <a href="mailto:support@quickfixautomotive.com" style="color: #2563eb;">support@quickfixautomotive.com</a></p>
                </div>

                <div class="footer">
                    <p>© 2025 QuickFix Automotive. All rights reserved.</p>
                    <p>This is an automated security message. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_message = f"""
        Password Reset Request - QuickFix Automotive

        Hello {user_name},

        You've requested to reset your password. Your password reset code is:

        {otp_code}

        This code expires at {expires_at.strftime('%I:%M %p')} (10 minutes from now).

        ⚠️ SECURITY WARNING:
        If you didn't request a password reset, please ignore this email and check your account security.

        For security reasons, this code can only be used once.

        Need help? Contact support: support@quickfixautomotive.com

        © 2025 QuickFix Automotive
        This is an automated security message.
        """

        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@quickfixautomotive.com')

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )

            logger.info(f"✅ INITIAL Password reset OTP sent to {user.email}")

            response_data = {
                'success': True,
                'message': f'Password reset OTP sent to {user.email}',
                'otp_code': otp_code,
                'user_id': str(user.id),
                'purpose': 'password_reset',
                'expires_at': expires_at.isoformat(),
                'expires_in_seconds': 600,
                'delivery_method': 'email',
                'is_initial': True,
                'note': 'Check your inbox for the password reset code',
                'debug_info': {
                    'email_backend': getattr(settings, 'EMAIL_BACKEND', ''),
                    'to_email': user.email
                }
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"❌ Initial password reset email failed: {str(e)}")

            return Response({
                'success': True,
                'message': 'Initial password reset OTP created',
                'otp_code': otp_code,
                'user_id': str(user.id),
                'expires_at': expires_at.isoformat(),
                'warning': 'Email delivery issue - OTP shown for testing',
                'instructions': 'Use the OTP code above to reset your password',
                'error': str(e) if settings.DEBUG else None,
                'is_initial': True
            })

# ===========================// RESEND OTP VIEW //===================================
"""
registration/views.py
Complete Africa's Talking SMS Integration for Tanzania
"""

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from datetime import timedelta
import random
import logging
import traceback
import africastalking

# Import your models (adjust these imports as needed)
from users.models import CustomUser, OTP

# Get logger
logger = logging.getLogger(__name__)

# ==============================================
# AFRICA'S TALKING CONFIGURATION FOR TANZANIA
# ==============================================
AFRICASTALKING_CONFIG = {
    'USERNAME': 'qfix',  # Your Africa's Talking username
    'API_KEY': 'atsk_4a2c0f51641708dd5b3287d86f7691673714af0230c72d9ca7fde0ba39e7ae7a7974d88a',  # Your API key
    'SENDER_ID': 'QuickFix',  # Max 11 characters
    'COUNTRY_CODE': 'TZ',  # Tanzania
}

# Initialize Africa's Talking SDK
africastalking.initialize(AFRICASTALKING_CONFIG['USERNAME'], AFRICASTALKING_CONFIG['API_KEY'])
SMS_SERVICE = africastalking.SMS

# ==============================================
# HELPER FUNCTIONS
# ==============================================

def format_tanzania_phone_number(phone_number):
    """
    Format phone number for Tanzania SMS delivery
    Converts: 0741234567 → +255741234567
    Converts: 255741234567 → +255741234567
    """
    import re

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone_number)

    # Handle Tanzanian numbers
    if digits.startswith('0'):
        # Local format (074...)
        return '+255' + digits[1:]
    elif digits.startswith('255'):
        # Already has country code
        return '+' + digits
    elif len(digits) == 9:
        # Just the local number (741234567)
        return '+255' + digits
    else:
        # Return as is (might be international format)
        return '+' + digits if not phone_number.startswith('+') else phone_number

def send_africastalking_sms(phone_number, message):
    """
    Send SMS via Africa's Talking API
    """
    try:
        # Format phone number for Tanzania
        formatted_number = format_tanzania_phone_number(phone_number)

        # Log the sending attempt
        logger.info(f"📱 Attempting to send SMS to: {formatted_number}")
        logger.info(f"📝 Message: {message[:50]}...")

        # Send SMS using Africa's Talking
        response = SMS_SERVICE.send(
            message=message,
            recipients=[formatted_number],
            sender_id=AFRICASTALKING_CONFIG['SENDER_ID']
        )

        # Parse response
        recipients = response.get('SMSMessageData', {}).get('Recipients', [])

        if recipients and recipients[0].get('status') == 'Success':
            logger.info(f"✅ SMS sent successfully to {formatted_number}")
            logger.info(f"💰 Cost: {recipients[0].get('cost', 'N/A')}")
            return {
                'success': True,
                'message': 'SMS sent successfully',
                'phone': formatted_number,
                'response': response
            }
        else:
            error_msg = recipients[0].get('status') if recipients else 'No recipients in response'
            logger.error(f"❌ SMS failed: {error_msg}")
            return {
                'success': False,
                'error': f'SMS delivery failed: {error_msg}',
                'phone': formatted_number,
                'response': response
            }

    except Exception as e:
        logger.error(f"❌ Africa's Talking API error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': f'API Error: {str(e)}',
            'phone': phone_number
        }

# ==============================================
# MAIN VIEW CLASS
# ==============================================

class ResendOTPView(APIView):
    """
    API View to resend OTP to user's email or phone
    Complete with Africa's Talking SMS integration for Tanzania
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """
        Handle OTP resend request
        """
        # Extract data from request
        user_id = request.data.get('user_id')
        purpose = request.data.get('purpose', 'email_verification')

        # Validate required fields
        if not user_id:
            return Response({
                'success': False,
                'error': 'User ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get user from database
            user = CustomUser.objects.get(id=user_id)

            # Check for recent OTP (prevent spam)
            recent_otp = OTP.objects.filter(
                user=user,
                purpose=purpose,
                created_at__gte=timezone.now() - timedelta(minutes=1)
            ).first()

            if recent_otp:
                seconds_since_last = int((timezone.now() - recent_otp.created_at).total_seconds())
                retry_after = max(60 - seconds_since_last, 1)

                return Response({
                    'success': False,
                    'error': 'Please wait at least 1 minute before requesting a new OTP',
                    'retry_after_seconds': retry_after
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Mark previous unused OTPs as expired
            OTP.objects.filter(
                user=user,
                purpose=purpose,
                is_used=False
            ).update(is_used=True)

            # Generate new 6-digit OTP
            otp_code = str(random.randint(100000, 999999))

            # Set expiry time (10 minutes from now)
            expires_at = timezone.now() + timedelta(minutes=10)

            # Create new OTP record
            otp = OTP.objects.create(
                user=user,
                code=otp_code,
                purpose=purpose,
                expires_at=expires_at
            )

            # Send OTP based on purpose
            if purpose == 'email_verification':
                return self._send_email_otp(user, otp_code, expires_at)
            elif purpose == 'phone_verification':
                return self._send_sms_otp(user, otp_code, expires_at)
            elif purpose == 'password_reset':
                return self._send_password_reset_otp(user, otp_code, expires_at)
            else:
                return Response({
                    'success': False,
                    'error': f'Unknown purpose: {purpose}'
                }, status=status.HTTP_400_BAD_REQUEST)

        except CustomUser.DoesNotExist:
            logger.warning(f"User not found with ID: {user_id}")
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Unexpected error in ResendOTPView: {str(e)}")
            logger.error(traceback.format_exc())

            return Response({
                'success': False,
                'error': 'Internal server error. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ==============================================
    # SMS OTP METHOD (COMPLETE AFRICA'S TALKING IMPLEMENTATION)
    # ==============================================

    def _send_sms_otp(self, user, otp_code, expires_at):
        """
        Send OTP via SMS using Africa's Talking
        Complete implementation for Tanzania
        """
        # Get user's phone number (adjust field name as needed)
        phone_number = getattr(user, 'phone_number', None) or getattr(user, 'phone', None)

        if not phone_number:
            logger.error(f"No phone number found for user {user.id}")
            return Response({
                'success': False,
                'error': 'Phone number not found for this user',
                'otp_code': otp_code,  # Still return OTP for debugging
                'user_id': str(user.id)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create SMS message for Tanzania
        user_name = user.first_name if user.first_name else 'User'

        # Message in English (add Swahili if needed)
        message = f"Hello {user_name}, your QuickFix-Automotive verification code is {otp_code}. Valid for 10 minutes. -QuickFix"

        # Send SMS via Africa's Talking
        sms_result = send_africastalking_sms(phone_number, message)

        # Prepare response based on SMS result
        if sms_result['success']:
            # SMS sent successfully
            response_data = {
                'success': True,
                'message': f'OTP sent to {sms_result["phone"]}',
                'otp_code': otp_code,  # For testing/debugging
                'user_id': str(user.id),
                'purpose': 'phone_verification',
                'expires_at': expires_at.isoformat(),
                'expires_in_seconds': 600,
                'delivery_method': 'sms',
                'phone_number': sms_result['phone'],
                'country': 'Tanzania',
                'timestamp': timezone.now().isoformat()
            }

            # Add cost information if available
            if 'response' in sms_result:
                recipients = sms_result['response'].get('SMSMessageData', {}).get('Recipients', [])
                if recipients:
                    response_data['sms_cost'] = recipients[0].get('cost', 'N/A')
                    response_data['message_id'] = recipients[0].get('messageId', 'N/A')

            return Response(response_data)

        else:
            # SMS failed to send
            return Response({
                'success': False,
                'error': 'Failed to send SMS. Please check phone number and try again.',
                'debug_error': sms_result.get('error', 'Unknown error'),
                'otp_code': otp_code,  # Return OTP for debugging
                'user_id': str(user.id),
                'phone_number': phone_number,
                'formatted_phone': sms_result.get('phone', phone_number),
                'instructions': 'Please verify the phone number is correct for Tanzania (+255XXXXXXXXX)',
                'retry_suggestion': 'You can request a new OTP in 1 minute'
            }, status=status.HTTP_502_BAD_GATEWAY)

    # ==============================================
    # EMAIL OTP METHODS (FROM YOUR ORIGINAL CODE)
    # ==============================================

    def _send_email_otp(self, user, otp_code, expires_at):
        """
        Send OTP via email (original code)
        """
        subject = 'QuickFix Automotive - Verification Code'

        # Get user name
        user_name = user.first_name if user.first_name else 'User'

        # Create HTML email template
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; }}
                .otp {{ font-size: 32px; font-weight: bold; color: #2563eb; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Hello {user_name},</h2>
                <p>Your QuickFix Automotive verification code is:</p>
                <div class="otp">{otp_code}</div>
                <p>This code expires at: {expires_at.strftime('%I:%M %p')}</p>
                <p>If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        plain_message = f"""
        QuickFix Automotive - Verification Code

        Hello {user_name},

        Your verification code is: {otp_code}

        This code expires at: {expires_at.strftime('%I:%M %p')}

        If you didn't request this, please ignore this email.
        """

        try:
            # Get email settings
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@quickfixautomotive.com')

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )

            logger.info(f"✅ Email OTP sent to {user.email}")

            return Response({
                'success': True,
                'message': f'OTP sent to {user.email}',
                'otp_code': otp_code,  # For debugging
                'user_id': str(user.id),
                'purpose': 'email_verification',
                'expires_at': expires_at.isoformat(),
                'delivery_method': 'email'
            })

        except Exception as e:
            logger.error(f"❌ Failed to send email: {str(e)}")

            return Response({
                'success': True,  # Still success because OTP was created
                'message': 'OTP generated successfully',
                'otp_code': otp_code,  # Return OTP anyway
                'user_id': str(user.id),
                'warning': 'Email delivery failed - OTP shown for testing',
                'error': str(e) if settings.DEBUG else 'Email service error'
            })

    def _send_password_reset_otp(self, user, otp_code, expires_at):
        """
        Send password reset OTP via email
        """
        subject = 'QuickFix Automotive - Password Reset Code'

        user_name = user.first_name if user.first_name else 'User'

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: auto; padding: 20px; border: 1px solid #dc2626; }}
                .otp {{ font-size: 32px; font-weight: bold; color: #dc2626; margin: 20px 0; }}
                .warning {{ background-color: #fef3c7; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>Hello {user_name},</p>
                <p>Your password reset code is:</p>
                <div class="otp">{otp_code}</div>
                <p>Expires at: {expires_at.strftime('%I:%M %p')}</p>
                <div class="warning">
                    <strong>Security Warning:</strong> If you didn't request this, please ignore this email and check your account security.
                </div>
            </div>
        </body>
        </html>
        """

        plain_message = f"""
        Password Reset - QuickFix Automotive

        Hello {user_name},

        Your password reset code is: {otp_code}

        Expires at: {expires_at.strftime('%I:%M %p')}

        Security Warning: If you didn't request this, please ignore this email.
        """

        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@quickfixautomotive.com')

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )

            logger.info(f"✅ Password reset email sent to {user.email}")

            return Response({
                'success': True,
                'message': f'Password reset OTP sent to {user.email}',
                'otp_code': otp_code,
                'user_id': str(user.id),
                'purpose': 'password_reset',
                'expires_at': expires_at.isoformat()
            })

        except Exception as e:
            logger.error(f"❌ Password reset email failed: {str(e)}")

            return Response({
                'success': True,
                'message': 'Password reset OTP created',
                'otp_code': otp_code,
                'user_id': str(user.id),
                'warning': 'Email delivery failed',
                'error': str(e) if settings.DEBUG else None
            })

# ==============================================
# ADDITIONAL UTILITY VIEW FOR TESTING
# ==============================================

class TestSMSView(APIView):
    """
    Simple test endpoint to verify Africa's Talking SMS is working
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """
        Test SMS sending to a specific phone number
        """
        test_phone = request.data.get('phone_number')
        test_message = request.data.get('message', 'Test SMS from QuickFix-Automotive')

        if not test_phone:
            return Response({
                'success': False,
                'error': 'phone_number is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Format for Tanzania
        formatted_phone = format_tanzania_phone_number(test_phone)

        # Send test SMS
        result = send_africastalking_sms(test_phone, test_message)

        if result['success']:
            return Response({
                'success': True,
                'message': 'Test SMS sent successfully',
                'phone_number': formatted_phone,
                'details': 'Check your phone for the test message'
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to send SMS'),
                'phone_number': formatted_phone,
                'suggestion': '1. Check your Africa\'s Talking balance\n2. Verify phone number format\n3. Check API credentials'
            }, status=status.HTTP_502_BAD_GATEWAY)
# =====================================// VERIFY OTP VIEW //====================================
class VerifyOTPView(APIView):
    """
    API View to verify OTP
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """
        Verify OTP code
        """
        otp_code = request.data.get('otp')
        purpose = request.data.get('purpose')
        user_id = request.data.get('user_id')

        # Validate required fields
        if not otp_code or not purpose or not user_id:
            return Response({
                'success': False,
                'error': 'Missing required fields: OTP, purpose, and user_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get user
            user = CustomUser.objects.get(id=user_id)

            # Find the latest valid OTP
            otp = OTP.objects.filter(
                user=user,
                code=otp_code,
                purpose=purpose,
                is_used=False
            ).order_by('-created_at').first()

            # Check if OTP exists and is valid
            if not otp:
                logger.warning(f"Invalid OTP attempt for user {user_id}, code: {otp_code}")
                return Response({
                    'success': False,
                    'error': 'Invalid OTP code. Please check and try again.'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not otp.is_valid():
                logger.warning(f"Expired OTP attempt for user {user_id}")
                return Response({
                    'success': False,
                    'error': 'OTP has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Mark OTP as used
            otp.is_used = True
            otp.used_at = timezone.now()
            otp.save()

            # Update user verification status based on purpose
            verification_updates = {}

            if purpose == 'email_verification':
                if not user.is_email_verified:
                    user.is_email_verified = True
                    verification_updates['email_verified'] = True
                    logger.info(f"✅ Email verified for user: {user.email}")
                else:
                    verification_updates['email_verified'] = 'already_verified'

            elif purpose == 'phone_verification':
                if not user.is_phone_verified:
                    user.is_phone_verified = True
                    verification_updates['phone_verified'] = True
                    logger.info(f"✅ Phone verified for user: {user.phone}")
                else:
                    verification_updates['phone_verified'] = 'already_verified'

            elif purpose == 'password_reset':
                verification_updates['password_reset_verified'] = True
                logger.info(f"✅ Password reset verified for user: {user.email}")

            # Save user updates
            user.save()

            # Prepare success response
            response_data = {
                'success': True,
                'message': 'Verification successful!',
                'verification_updates': verification_updates,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'phone': user.phone,
                    'is_email_verified': user.is_email_verified,
                    'is_phone_verified': user.is_phone_verified
                }
            }

            # Add next step guidance
            if purpose == 'email_verification' and not user.is_phone_verified:
                response_data['next_step'] = 'phone_verification'
                response_data['suggestion'] = 'You can now verify your phone number'
            elif purpose == 'phone_verification' and not user.is_email_verified:
                response_data['next_step'] = 'email_verification'
                response_data['suggestion'] = 'You can now verify your email'
            elif purpose == 'password_reset':
                response_data['next_step'] = 'reset_password'
                response_data['suggestion'] = 'You can now set a new password'
                response_data['reset_token'] = otp_code  # Use OTP as reset token
            else:
                response_data['next_step'] = 'complete'
                response_data['message'] = 'Account verification complete!'

            logger.info(f"✅ OTP verification successful for user {user_id}, purpose: {purpose}")

            return Response(response_data)

        except CustomUser.DoesNotExist:
            logger.warning(f"User not found during OTP verification: {user_id}")
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"❌ Error in VerifyOTPView: {str(e)}")
            logger.error(traceback.format_exc())

            return Response({
                'success': False,
                'error': 'Internal server error during verification'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =====================================// TEST EMAIL VIEW //====================================
class TestEmailView(APIView):
    """
    Test view to check email configuration
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Test email sending functionality
        """
        test_email = request.data.get('email', 'test@example.com')

        try:
            # Generate a test OTP
            test_otp = str(random.randint(100000, 999999))

            # Create simple test email
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #2563eb;">✅ QuickFix Automotive - Email Test</h2>
                <p>This is a test email to verify your email configuration is working.</p>
                <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <strong>Test OTP:</strong> <span style="font-size: 24px; font-weight: bold;">{test_otp}</span>
                </div>
                <p>If you receive this email, your Django email configuration is correct.</p>
                <p>Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </body>
            </html>
            """

            plain_message = f"""
            QuickFix Automotive - Email Test

            This is a test email to verify your email configuration.

            Test OTP: {test_otp}

            Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

            If you receive this, your email setup is working!
            """

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'test@quickfixautomotive.com')

            send_mail(
                subject='✅ QuickFix Automotive - Email Configuration Test',
                message=plain_message,
                from_email=from_email,
                recipient_list=[test_email],
                html_message=html_message,
                fail_silently=False,
            )

            return Response({
                'success': True,
                'message': f'Test email sent to {test_email}',
                'test_otp': test_otp,
                'email_config': {
                    'backend': settings.EMAIL_BACKEND,
                    'from': from_email,
                    'host': getattr(settings, 'EMAIL_HOST', 'Not set'),
                    'port': getattr(settings, 'EMAIL_PORT', 'Not set'),
                    'use_tls': getattr(settings, 'EMAIL_USE_TLS', 'Not set'),
                },
                'time_sent': timezone.now().isoformat()
            })

        except Exception as e:
            logger.error(f"❌ Test email failed: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'email_config': {
                    'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', 'Not set'),
                    'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'Not set'),
                    'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'Not set'),
                    'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')
                },
                'suggestion': 'Check your email settings in settings.py'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =====================================// TEST EMAIL VIEW //====================================











class TestEmailView(APIView):
    """
    Test view to check email configuration
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Test email sending functionality
        """
        try:
            test_email = request.GET.get('email', 'test@example.com')

            send_mail(
                subject='QuickFix Automotive - Test Email',
                message='This is a test email to verify your email configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[test_email],
                fail_silently=False,
            )

            return Response({
                'success': True,
                'message': f'Test email sent to {test_email}',
                'email_backend': settings.EMAIL_BACKEND,
                'from_email': settings.DEFAULT_FROM_EMAIL,
                'note': 'If you receive this email, your configuration is correct.'
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'email_config': {
                    'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', 'Not set'),
                    'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'Not set'),
                    'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'Not set'),
                    'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')
                },
                'suggestion': 'Check your email settings in settings.py and ensure SMTP credentials are correct.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# =======================================//  END OF OTP VERFY VIEWS //============================================













# class VerifyOTPView(APIView):

#     permission_classes = [AllowAny]
#     authentication_classes=[]



#     def post(self, request):
#         otp_code = request.data.get('otp')
#         purpose = request.data.get('purpose')
#         user_id = request.session.get('user_id')

#         if not all([otp_code, purpose, user_id]):
#             return Response({'error': 'Missing data'}, status=400)

#         try:
#             user = CustomUser.objects.get(id=user_id)
#             otp = OTP.objects.filter(
#                 user=user,
#                 code=otp_code,
#                 purpose=purpose,
#                 is_used=False
#             ).order_by('-created_at').first()

#             if not otp or not otp.is_valid():
#                 return Response({'error': 'Invalid OTP'}, status=400)

#             # Mark OTP as used
#             otp.is_used = True
#             otp.save()

#             # Update user verification
#             if purpose == 'email_verification':
#                 user.is_email_verified = True
#             elif purpose == 'phone_verification':
#                 user.is_phone_verified = True

#             user.save()

#             return Response({
#                 'success': True,
#                 'message': 'Verification successful',
#                 'next_step': 'complete'
#             })
#         except CustomUser.DoesNotExist:
#             return Response({'error': 'User not found'}, status=404)





class TestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'online',
            'message': 'Django API is working!',
            'timestamp': timezone.now().isoformat()
        })



# =======================//    LOGIN-LOGOUT VIEW    =======================
# # views.py - Add these views
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from django.contrib.auth import authenticate, login, logout
# from django.contrib.auth.hashers import check_password
# from django.middleware.csrf import get_token
# from rest_framework.permissions import AllowAny, IsAuthenticated
# from .serializers import UserSerializer
# # In views.py, update your LoginView
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth import get_user_model

# User = get_user_model()

# # In your views.py, update the LoginView
# class LoginView(APIView):
#     """
#     Login endpoint that accepts either email or phone number
#     """
#     permission_classes = [AllowAny]

#     def post(self, request):
#         identifier = request.data.get('identifier', '').strip()  # Can be email or phone
#         password = request.data.get('password', '').strip()

#         # Validate required fields
#         if not identifier or not password:
#             return Response(
#                 {
#                     'success': False,
#                     'error': 'Email/phone and password are required',
#                     'error_type': 'validation_error'
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             user = None

#             # Try to find user by email first
#             if '@' in identifier:
#                 user = User.objects.filter(email__iexact=identifier).first()
#             else:
#                 # Try to find by phone (normalized)
#                 from .utils import normalize_phone
#                 normalized_phone = normalize_phone(identifier)
#                 if normalized_phone:
#                     user = User.objects.filter(phone=normalized_phone).first()

#             if not user:
#                 return Response(
#                     {
#                         'success': False,
#                         'error': 'Invalid email or phone number',
#                         'error_type': 'invalid_credentials'
#                     },
#                     status=status.HTTP_401_UNAUTHORIZED
#                 )

#             # Check if user is active
#             if not user.is_active:
#                 return Response(
#                     {
#                         'success': False,
#                         'error': 'Your account has been deactivated.',
#                         'error_type': 'account_inactive'
#                     },
#                     status=status.HTTP_403_FORBIDDEN
#                 )

#             # Check password
#             if not check_password(password, user.password):
#                 return Response(
#                     {
#                         'success': False,
#                         'error': 'Invalid password',
#                         'error_type': 'invalid_credentials'
#                     },
#                     status=status.HTTP_401_UNAUTHORIZED
#                 )

#             # Generate JWT tokens
#             refresh = RefreshToken.for_user(user)
#             access_token = str(refresh.access_token)
#             refresh_token = str(refresh)

#             # Prepare user data
#             user_data = {
#                 'id': user.id,
#                 'email': user.email,
#                 'phone': user.phone,
#                 'first_name': user.first_name or '',
#                 'last_name': user.last_name or '',
#                 'full_name': user.full_name,
#                 'city': user.city or '',
#                 'state': user.state or '',
#                 'role': user.role,
#                 'is_email_verified': user.is_email_verified,
#                 'is_phone_verified': user.is_phone_verified,
#                 'registration_stage': user.registration_stage,
#                 'registration_method': user.registration_method,
#                 'role_display': user.get_role_display(),
#                 'is_admin': user.is_admin,
#                 'is_mechanic': user.is_mechanic,
#                 'is_garage_owner': user.is_garage_owner,
#                 'is_customer': user.is_customer,
#             }

#             return Response({
#                 'success': True,
#                 'message': 'Login successful',
#                 'access': access_token,
#                 'refresh': refresh_token,
#                 'user': user_data
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             print(f"Login error: {str(e)}")
#             return Response(
#                 {
#                     'success': False,
#                     'error': 'Login failed. Please try again.',
#                     'error_type': 'server_error'
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )







# # registration/views.py
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework_simplejwt.exceptions import TokenError
# from django.utils import timezone
# from django.contrib.auth import logout

# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             # Get refresh token from request
#             refresh_token = request.data.get('refresh')

#             if refresh_token:
#                 try:
#                     # Add refresh token to blacklist
#                     token = RefreshToken(refresh_token)
#                     token.blacklist()
#                 except TokenError as e:
#                     # Token might already be blacklisted or invalid
#                     print(f"Token blacklist error: {e}")
#                     # Continue with logout anyway

#             # Also try to blacklist current access token
#             auth_header = request.META.get('HTTP_AUTHORIZATION', '')
#             if auth_header.startswith('Bearer '):
#                 access_token = auth_header.split(' ')[1]
#                 # Note: Access tokens can't be blacklisted by default in simplejwt
#                 # But we can create a custom blacklist for them if needed

#             # Logout Django session
#             logout(request)

#             return Response({
#                 'success': True,
#                 'message': 'Logged out successfully. Token has been invalidated.'
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             print(f"Logout error: {e}")
#             return Response({
#                 'success': False,
#                 'error': 'Logout failed',
#                 'message': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)




# =============================================//LOGIN LOGOUT NEW VEIWS//================================================
# views.py - Complete fixed version
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# ========== UTILITY FUNCTIONS ==========
def normalize_phone(phone_str):
    """
    Normalize phone number by removing all non-digit characters
    and converting to Kenyan format if needed
    """
    if not phone_str:
        return None

    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone_str))

    if not digits:
        return None

    # Convert to Kenyan format if needed
    # If 9 digits starting with 7, add 0
    if len(digits) == 9 and digits.startswith('7'):
        return '0' + digits
    # If 12 digits starting with 254, convert to 0 format
    elif len(digits) == 12 and digits.startswith('254'):
        return '0' + digits[3:]
    # If 10 digits starting with 0, keep as is
    elif len(digits) == 10 and digits.startswith('0'):
        return digits
    # If other formats, just return digits
    else:
        return digits

# ========== LOGIN VIEW ==========
class LoginView(APIView):
    """
    Login endpoint that accepts either email or phone number
    """
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get('identifier', '').strip()  # Can be email or phone
        password = request.data.get('password', '').strip()

        # Log the login attempt
        logger.info(f"Login attempt for identifier: {identifier}")

        # Validate required fields
        if not identifier:
            logger.warning("Login failed: Missing identifier")
            return Response(
                {
                    'success': False,
                    'error': 'Email or phone number is required',
                    'error_type': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not password:
            logger.warning("Login failed: Missing password")
            return Response(
                {
                    'success': False,
                    'error': 'Password is required',
                    'error_type': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = None
            search_type = None

            # Try to find user by email first
            if '@' in identifier:
                search_type = 'email'
                user = User.objects.filter(email__iexact=identifier).first()
                logger.info(f"Email search for {identifier}: {'Found' if user else 'Not found'}")
            else:
                # Try to find by phone
                search_type = 'phone'
                normalized_phone = normalize_phone(identifier)
                logger.info(f"Phone normalization: {identifier} -> {normalized_phone}")

                if normalized_phone:
                    # First try exact match
                    user = User.objects.filter(phone=normalized_phone).first()

                    # If not found, try other formats
                    if not user:
                        # Try with 254 format
                        if normalized_phone.startswith('0') and len(normalized_phone) == 10:
                            with_254 = '254' + normalized_phone[1:]
                            user = User.objects.filter(phone=with_254).first()
                            if user:
                                logger.info(f"Found user with 254 format: {with_254}")

                        # Try without leading 0
                        if not user and normalized_phone.startswith('0'):
                            without_zero = normalized_phone[1:]
                            user = User.objects.filter(phone=without_zero).first()
                            if user:
                                logger.info(f"Found user without leading 0: {without_zero}")

                    logger.info(f"Phone search for {normalized_phone}: {'Found' if user else 'Not found'}")
                else:
                    logger.warning(f"Invalid phone format: {identifier}")

            if not user:
                logger.warning(f"No user found for {search_type}: {identifier}")
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid email or phone number',
                        'error_type': 'invalid_credentials'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Check if user is active
            if not user.is_active:
                logger.warning(f"Inactive user login attempt: {user.id}")
                return Response(
                    {
                        'success': False,
                        'error': 'Your account has been deactivated.',
                        'error_type': 'account_inactive'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if user has password set
            if not user.password:
                logger.warning(f"User {user.id} has no password set")
                return Response(
                    {
                        'success': False,
                        'error': 'Account has no password set. Please reset your password.',
                        'error_type': 'no_password'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Check password
            if not check_password(password, user.password):
                logger.warning(f"Invalid password for user: {user.id}")
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid password',
                        'error_type': 'invalid_credentials'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            logger.info(f"Password valid for user: {user.id}")

            # Generate JWT tokens
            try:
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                logger.info(f"Tokens generated for user: {user.id}")
            except Exception as token_error:
                logger.error(f"Token generation error: {str(token_error)}", exc_info=True)
                return Response(
                    {
                        'success': False,
                        'error': 'Authentication error',
                        'error_type': 'token_error'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Prepare user data
            user_data = {
                'id': str(user.id),  # Convert UUID to string
                'email': user.email or '',
                'phone': user.phone or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'full_name': user.full_name,
                'city': user.city or '',
                'state': user.state or '',
                'role': user.role,
                'is_email_verified': user.is_email_verified,
                'is_phone_verified': user.is_phone_verified,
                'registration_stage': user.registration_stage,
                'registration_method': user.registration_method,
                'role_display': user.get_role_display(),
                'is_admin': user.is_admin_user,  # Changed from is_admin
                'is_mechanic': user.is_mechanic,
                'is_garage_owner': user.is_garage_owner,
                'is_customer': user.is_customer,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }

            logger.info(f"Login successful for user: {user.id}")

            return Response({
                'success': True,
                'message': 'Login successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': user_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Login failed. Please try again.',
                    'error_type': 'server_error',
                    'detail': str(e) if __debug__ else None  # Include detail in debug mode
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ========== DEBUG VIEWS ==========
class TestView(APIView):
    """Test endpoint to verify API is working"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'success': True,
            'message': 'API is working',
            'endpoints': {
                'login': '/api/auth/login/',
                'logout': '/api/auth/logout/',
                'test': '/api/test/'
            }
        })

class DebugLoginView(APIView):
    """Debug endpoint to test user lookup without authentication"""
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get('identifier', '').strip()
        logger.info(f"Debug login check for: {identifier}")

        try:
            user = None

            if '@' in identifier:
                user = User.objects.filter(email__iexact=identifier).first()
                logger.info(f"Email lookup: {identifier} -> {user}")
            else:
                normalized = normalize_phone(identifier)
                logger.info(f"Normalized phone: {identifier} -> {normalized}")

                if normalized:
                    # Check all phone formats
                    formats_to_try = [normalized]

                    if normalized.startswith('0') and len(normalized) == 10:
                        formats_to_try.append('254' + normalized[1:])
                        formats_to_try.append(normalized[1:])
                    elif len(normalized) == 9 and normalized.startswith('7'):
                        formats_to_try.append('0' + normalized)

                    for phone_format in formats_to_try:
                        user = User.objects.filter(phone=phone_format).first()
                        if user:
                            logger.info(f"Found with format {phone_format}: {user.id}")
                            break

                if not user:
                    # Try contains search
                    if normalized:
                        user = User.objects.filter(phone__contains=normalized).first()
                        if user:
                            logger.info(f"Found with contains search: {user.id}")

            if user:
                return Response({
                    'success': True,
                    'found': True,
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'phone': user.phone,
                        'has_password': bool(user.password),
                        'is_active': user.is_active,
                        'role': user.role,
                    }
                })
            else:
                return Response({
                    'success': True,
                    'found': False,
                    'message': 'User not found',
                    'identifier': identifier,
                    'normalized': normalized if '@' not in identifier else None
                })

        except Exception as e:
            logger.error(f"Debug error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'traceback': str(e.__traceback__) if __debug__ else None
            })

# ========== LOGOUT VIEW ==========
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get refresh token from request
            refresh_token = request.data.get('refresh')

            if refresh_token:
                try:
                    # Add refresh token to blacklist
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    # Token might already be blacklisted or invalid
                    logger.warning(f"Token blacklist error: {e}")

            # Logout Django session
            logout(request)

            return Response({
                'success': True,
                'message': 'Logged out successfully.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({
                'success': False,
                'error': 'Logout failed',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)



# =========================================================//END  NEW VIEW FOR LOGIN LOGOUT//==============================================





class LogoutAllView(APIView):
    """Logout from all devices by blacklisting all user's refresh tokens"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get all outstanding refresh tokens for user
            # We need to store issued refresh tokens somewhere to do this properly
            # For now, we'll just clear the user's session and JWT secret

            # Django session logout
            logout(request)

            # Invalidate all tokens by changing user's JWT secret
            # Add this to your CustomUser model if you want to implement
            # request.user.jwt_secret_key = generate_new_secret()
            # request.user.save()

            return Response({
                'success': True,
                'message': 'Logged out from all devices successfully.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': 'Logout failed',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)








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








# views.py - Updated BookingsViewSet with SMS
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import logging

# Email imports
from django.core.mail import EmailMultiAlternatives, send_mail
from django.utils.html import strip_tags
from django.conf import settings

# Models and SMS service
from users.models import Booking, Service, Garage
from .serializers import BookingSerializer, BookingCreateSerializer
from utils.africastalking_sms import africastalking_sms as sms_service

logger = logging.getLogger(__name__)

class BookingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling all booking operations with email notifications and SMS integration
    """
    queryset = Booking.objects.all().select_related('garage', 'service', 'user')
    serializer_class = BookingSerializer

    def get_permissions(self):
        """
        Custom permission handling
        - Create: User must be authenticated
        - Other actions: Allow any (for admin)
        """
        if self.action == 'create':
            return [IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by authenticated user for their own bookings
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        # Filter by garage
        garage_id = self.request.query_params.get('garage_id')
        if garage_id:
            queryset = queryset.filter(garage_id=garage_id)

        # Filter by service
        service_id = self.request.query_params.get('service_id')
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id and self.request.user.is_staff:
            queryset = queryset.filter(user_id=user_id)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                date = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(scheduled_date__date__gte=date)
            except ValueError:
                pass

        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                date = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(scheduled_date__date__lte=date)
            except ValueError:
                pass

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(booking_number__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(garage__name__icontains=search) |
                Q(service__name__icontains=search) |
                Q(location__icontains=search)
            )

        # Ordering
        order_by = self.request.query_params.get('order_by', '-scheduled_date')
        if order_by.lstrip('-') in ['scheduled_date', 'created_at', 'total_price']:
            queryset = queryset.order_by(order_by)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create a new booking with email and SMS notifications
        """
        # Set context for serializer
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            # Save booking
            booking = serializer.save()

            # Send SMS confirmation to customer
            sms_result = self.send_booking_sms_confirmation(booking)

            # Send email notification to garage
            email_result = self.send_booking_email(booking)

            # Prepare response
            response_data = {
                'success': True,
                'message': 'Booking created successfully',
                'booking': BookingSerializer(booking).data,
                'sms_sent': sms_result['success'],
                'sms_message': sms_result['message'],
                'email_sent': email_result['success'],
                'email_message': email_result['message'],
                'booking_number': booking.booking_number
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to create booking: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'message': 'Failed to create booking'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    def send_booking_sms_confirmation(self, booking):
        """
        Send booking confirmation SMS to customer via Africa's Talking
        Returns: {'success': bool, 'message': str}
        """
        try:
            # Check if user has phone number and it's verified
            if not booking.user or not booking.user.phone:
                logger.warning(f"No phone number for user in booking #{booking.booking_number}")
                return {
                    'success': False,
                    'message': 'User phone number not available'
                }

            if not booking.user.is_phone_verified:
                logger.warning(f"Phone not verified for booking #{booking.booking_number}")
                return {
                    'success': False,
                    'message': 'User phone number not verified'
                }

            # Check if SMS can be sent
            can_send, reason = booking.can_send_sms()
            if not can_send:
                logger.warning(f"Cannot send SMS for booking #{booking.booking_number}: {reason}")
                return {
                    'success': False,
                    'message': reason
                }

            # Get service name
            service_name = booking.service.name if booking.service else booking.custom_service_name

            # Format scheduled time
            scheduled_time = booking.scheduled_date.strftime('%Y-%m-%d at %I:%M %p')

            # Create SMS message
            message = (
                f"Hello {booking.user.first_name},\n\n"
                f"✅ Your booking #{booking.booking_number} has been confirmed!\n"
                f"📍 Service: {service_name}\n"
                f"🏢 Garage: {booking.garage.name}\n"
                f"📅 Date: {scheduled_time}\n"
                f"💰 Amount: TZS {booking.total_price:,.2f}\n"
                f"📞 Garage Contact: {booking.garage.phone}\n\n"
                f"Thank you for choosing QuickFix Automotive!"
            )

            # Send SMS via Africa's Talking
            sms_sent = sms_service.send_sms(
                phone_number=booking.user.phone,
                message=message,
                purpose='booking_confirmation'
            )

            if sms_sent:
                # Mark SMS as sent in booking
                booking.mark_sms_sent('confirmation', 'sent')
                logger.info(f"✅ SMS sent for booking #{booking.booking_number} to {booking.user.phone}")

                return {
                    'success': True,
                    'message': f'SMS sent to {booking.user.phone}'
                }
            else:
                booking.log_sms_error("Failed to send SMS via Africa's Talking API")
                logger.error(f"❌ SMS failed for booking #{booking.booking_number}")

                return {
                    'success': False,
                    'message': 'Failed to send SMS'
                }

        except Exception as e:
            error_msg = f"Error sending booking SMS: {str(e)}"
            logger.error(error_msg, exc_info=True)

            if booking:
                booking.log_sms_error(error_msg)

            return {
                'success': False,
                'message': f'SMS error: {str(e)}'
            }

    def send_booking_email(self, booking):
        """
        Send booking confirmation email to garage
        Returns: {'success': bool, 'message': str}
        """
        try:
            # Check if garage has email
            if not booking.garage or not booking.garage.email:
                logger.warning(f"No email for garage in booking #{booking.booking_number}")
                return {
                    'success': False,
                    'message': 'Garage email not available'
                }

            recipient_email = booking.garage.email
            logger.info(f"Sending booking email to garage: {recipient_email}")

            # DEBUG: Check email configuration
            self._debug_email_config()

            # Prepare email content
            subject = f"📋 New Booking #{booking.booking_number} - {booking.garage.name}"

            # Generate email content with try-catch
            try:
                html_content = self._generate_booking_email_content(booking)
                text_content = strip_tags(html_content)
                logger.debug(f"Generated email content of length: {len(html_content)}")
            except Exception as e:
                logger.error(f"Failed to generate email content: {str(e)}", exc_info=True)
                # Fallback to simple content
                html_content = self._generate_simple_email_content(booking)
                text_content = strip_tags(html_content)

            # Send email
            email_sent = self._send_email_with_fallback(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                recipient_email=recipient_email,
                booking=booking
            )

            if email_sent:
                # Update booking notes
                self._update_booking_email_sent(booking, recipient_email)

                return {
                    'success': True,
                    'message': f'Email sent to {recipient_email}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to send email'
                }

        except Exception as e:
            logger.error(f"Error sending booking email: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Email error: {str(e)}'
            }

    def _send_email_with_fallback(self, subject, html_content, text_content, recipient_email, booking):
        """
        Try to send email with primary method, fallback to simple method
        """
        # Method 1: EmailMultiAlternatives (HTML + Text)
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                reply_to=[getattr(settings, 'DEFAULT_REPLY_TO', settings.DEFAULT_FROM_EMAIL)]
            )

            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

            logger.info(f"✅ Email sent via EmailMultiAlternatives to {recipient_email}")
            return True

        except Exception as e1:
            logger.warning(f"Method 1 failed: {str(e1)}")

            # Method 2: Simple send_mail (text only)
            try:
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )

                logger.info(f"✅ Email sent via send_mail to {recipient_email}")
                return True

            except Exception as e2:
                logger.error(f"Method 2 also failed: {str(e2)}")

                # Method 3: Console backend (for debugging)
                if settings.DEBUG:
                    try:
                        from django.core.mail import mail_admins
                        mail_admins(
                            subject=f"[DEBUG] Booking Email Failed - #{booking.booking_number}",
                            message=f"Failed to send to {recipient_email}\n\nError1: {e1}\nError2: {e2}"
                        )
                    except:
                        pass

                return False

    def _update_booking_email_sent(self, booking, recipient_email):
        """
        Update booking record that email was sent
        """
        try:
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            email_note = f"📧 Booking confirmation email sent to garage ({recipient_email}) at {timestamp}"

            # Append to existing notes or create new
            if booking.notes:
                booking.notes = f"{booking.notes}\n\n{email_note}"
            else:
                booking.notes = email_note

            booking.save(update_fields=['notes'])
            logger.info(f"Updated booking #{booking.booking_number} with email sent note")

        except Exception as e:
            logger.error(f"Failed to update booking notes: {str(e)}")

    def _generate_booking_email_content(self, booking):
        """
        Generate HTML email content for booking notification
        """
        # Get customer info from user - FIXED: Handle missing get_full_name()
        customer_name = "Customer"
        if booking.user:
            # Try different methods to get full name
            if hasattr(booking.user, 'get_full_name'):
                customer_name = booking.user.get_full_name()
            elif booking.user.first_name and booking.user.last_name:
                customer_name = f"{booking.user.first_name} {booking.user.last_name}"
            elif booking.user.first_name:
                customer_name = booking.user.first_name
            elif booking.user.username:
                customer_name = booking.user.username
            elif booking.user.email:
                customer_name = booking.user.email.split('@')[0]

        customer_phone = booking.user.phone if booking.user and hasattr(booking.user, 'phone') else "N/A"
        customer_email = booking.user.email if booking.user else "N/A"

        # Phone verification status
        phone_status = "✅ Verified" if booking.user and hasattr(booking.user, 'is_phone_verified') and booking.user.is_phone_verified else "⚠️ Not Verified"

        # Service name
        service_name = booking.service.name if booking.service else booking.custom_service_name

        # Google Maps link
        maps_link_section = ""
        if booking.google_maps_link:
            maps_link_section = f"""
            <tr>
                <td><strong>Google Maps:</strong></td>
                <td><a href="{booking.google_maps_link}" target="_blank"
                       style="color: #2196F3; text-decoration: none;">
                    View Location
                </a></td>
            </tr>
            """

        # Customer notes
        customer_notes_section = ""
        if booking.notes and len(booking.notes.strip()) > 0:
            customer_notes_section = f"""
            <div style="background-color: #f0f7ff; padding: 15px; margin: 20px 0;
                        border-left: 4px solid #2196F3; border-radius: 4px;">
                <h4 style="margin-top: 0; color: #2196F3;">📝 Customer Notes:</h4>
                <p style="white-space: pre-line; margin-bottom: 0;">{booking.notes}</p>
            </div>
            """

        # SMS status
        sms_status_section = ""
        if booking.sms_confirmation_sent:
            sms_time = booking.sms_confirmation_sent_at.strftime('%Y-%m-%d %H:%M') if booking.sms_confirmation_sent_at else "Unknown"
            sms_status_section = f"""
            <div style="background-color: #e8f5e9; padding: 15px; margin: 20px 0;
                        border-left: 4px solid #4CAF50; border-radius: 4px;">
                <h4 style="margin-top: 0; color: #2E7D32;">📱 SMS Confirmation:</h4>
                <p>✅ SMS confirmation sent to customer at {sms_time}</p>
                <p><strong>Phone:</strong> {customer_phone} ({phone_status})</p>
            </div>
            """

        # User registration date
        registration_date = ""
        if booking.user and hasattr(booking.user, 'date_joined'):
            registration_date = booking.user.date_joined.strftime('%Y-%m-%d')
        elif booking.user and hasattr(booking.user, 'created_at'):
            registration_date = booking.user.created_at.strftime('%Y-%m-%d')
        else:
            registration_date = "N/A"

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Booking #{booking.booking_number}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 700px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .content {{
                    padding: 30px;
                }}
                .info-box {{
                    background: #f0f7ff;
                    padding: 20px;
                    margin: 20px 0;
                    border-left: 4px solid #2196F3;
                    border-radius: 4px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: 600;
                }}
                .total-row {{
                    background-color: #e8f5e9;
                    font-weight: bold;
                }}
                .action-box {{
                    background-color: #e8f5e8;
                    padding: 20px;
                    margin: 30px 0;
                    border-radius: 5px;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                }}
                .user-info {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .user-icon {{
                    background: #2196F3;
                    color: white;
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-right: 15px;
                    font-size: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 28px;">📋 New Booking Received!</h1>
                    <p style="margin: 10px 0 0; font-size: 18px; opacity: 0.9;">
                        Booking #{booking.booking_number}
                    </p>
                </div>

                <div class="content">
                    <div class="user-info">
                        <div>
                            <h3 style="margin: 0; color: #2196F3;">Customer Information</h3>
                            <p style="margin: 5px 0 0; color: #666;">
                                Registered User • {phone_status}
                            </p>
                        </div>
                    </div>

                    <div class="info-box">
                        <p><strong>Name:</strong> {customer_name}</p>
                        <p><strong>Mobile:</strong> {customer_phone}</p>
                        <p><strong>Email:</strong> {customer_email}</p>
                        <p><strong>Registered Since:</strong> {registration_date}</p>
                    </div>

                    {sms_status_section}

                    <h3 style="color: #333; margin-top: 30px;">📋 Booking Details</h3>
                    <table>
                        <tr>
                            <td><strong>Booking Number:</strong></td>
                            <td><strong style="color: #667eea;">{booking.booking_number}</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Service:</strong></td>
                            <td>{service_name}</td>
                        </tr>
                        <tr>
                            <td><strong>Scheduled Date & Time:</strong></td>
                            <td>{booking.scheduled_date.strftime('%Y-%m-%d at %I:%M %p')}</td>
                        </tr>
                        <tr>
                            <td><strong>Service Price:</strong></td>
                            <td>TZS {booking.price:,.2f}</td>
                        </tr>
                        <tr class="total-row">
                            <td><strong>Total Price:</strong></td>
                            <td>TZS {booking.total_price:,.2f}</td>
                        </tr>
                        <tr>
                            <td><strong>Location:</strong></td>
                            <td>{booking.location}</td>
                        </tr>
                        {maps_link_section}
                    </table>

                    {customer_notes_section}

                    <div class="action-box">
                        <h4 style="margin-top: 0; color: #2E7D32;">🛠️ Action Required:</h4>
                        <ol style="margin-bottom: 0;">
                            <li>Contact customer to confirm booking details</li>
                            <li>Prepare necessary equipment and parts</li>
                            <li>Update booking status in your dashboard</li>
                            <li>Send reminder 24 hours before service</li>
                        </ol>
                    </div>

                    <div class="footer">
                        <p>This is an automated message from <strong>QuickFix Automotive</strong></p>
                        <p>Booking created: {timezone.now().strftime('%Y-%m-%d at %H:%M')}</p>
                        <p>Need support? Contact: support@quickfixauto.com</p>
                        <p style="font-size: 12px; margin-top: 10px;">
                            Please do not reply to this automated email.
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return html_template

    def _debug_email_config(self):
        """Debug email configuration"""
        logger.info("=== EMAIL CONFIG DEBUG ===")
        logger.info(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not set')}")
        logger.info(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}")
        logger.info(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
        logger.info(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not set')}")
        logger.info(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Not set')}")
        logger.info(f"EMAIL_USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', 'Not set')}")
        logger.info("=========================")

    def _generate_simple_email_content(self, booking):
        """Simple fallback email content"""
        return f"""
        <html>
        <body>
            <h2>New Booking #{booking.booking_number}</h2>
            <p>A new booking has been created for your garage.</p>
            <p><strong>Service:</strong> {booking.service.name if booking.service else booking.custom_service_name}</p>
            <p><strong>Date:</strong> {booking.scheduled_date}</p>
            <p><strong>Customer:</strong> {booking.user.email if booking.user else 'Customer'}</p>
            <p><strong>Location:</strong> {booking.location}</p>
            <p>Please check your dashboard for more details.</p>
        </body>
        </html>
        """

    def update(self, request, *args, **kwargs):
        """
        Update booking and send status change notifications
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_update(serializer)
            booking = serializer.instance

            # Check if status changed
            if old_status != booking.status:
                # Send status update email to garage
                self.send_status_email(booking, old_status)

                # Send status update SMS to customer if phone is verified
                if booking.user and booking.user.is_phone_verified:
                    self.send_status_sms(booking, old_status)

            return Response({
                'success': True,
                'message': 'Booking updated successfully',
                'status_changed': old_status != booking.status,
                'booking': serializer.data
            })

        except Exception as e:
            logger.error(f"Failed to update booking: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to update booking'
            }, status=status.HTTP_400_BAD_REQUEST)

    def send_status_email(self, booking, old_status):
        """
        Send status update email to garage
        """
        try:
            if not booking.garage or not booking.garage.email:
                return

            recipient_email = booking.garage.email
            old_status_display = dict(booking.STATUS_CHOICES).get(old_status, old_status)
            new_status_display = dict(booking.STATUS_CHOICES).get(booking.status, booking.status)

            subject = f"📊 Booking Status Updated: #{booking.booking_number} - {new_status_display}"

            html_content = self._generate_status_email_content(booking, old_status_display, new_status_display)
            text_content = strip_tags(html_content)

            self._send_email_with_fallback(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                recipient_email=recipient_email,
                booking=booking
            )

        except Exception as e:
            logger.error(f"Error sending status email: {str(e)}")

    def send_status_sms(self, booking, old_status):
        """
        Send status update SMS to customer
        """
        try:
            if not booking.user or not booking.user.phone or not booking.user.is_phone_verified:
                return

            old_status_display = dict(booking.STATUS_CHOICES).get(old_status, old_status)
            new_status_display = dict(booking.STATUS_CHOICES).get(booking.status, booking.status)

            service_name = booking.service.name if booking.service else booking.custom_service_name

            message = (
                f"Hello {booking.user.first_name},\n\n"
                f"📋 Update for booking #{booking.booking_number}\n"
                f"📍 Service: {service_name}\n"
                f"🏢 Garage: {booking.garage.name}\n"
                f"🔄 Status changed from {old_status_display} to {new_status_display}\n\n"
                f"Contact garage for details: {booking.garage.phone}"
            )

            # Send SMS
            sms_sent = sms_service.send_sms(
                phone_number=booking.user.phone,
                message=message,
                purpose='status_update'
            )

            if sms_sent:
                logger.info(f"✅ Status SMS sent for booking #{booking.booking_number}")
            else:
                logger.warning(f"⚠️ Failed to send status SMS for booking #{booking.booking_number}")

        except Exception as e:
            logger.error(f"Error sending status SMS: {str(e)}")

    def _generate_status_email_content(self, booking, old_status, new_status):
        """
        Generate HTML content for status update email
        """
        # Get customer name with same logic
        customer_name = "Customer"
        if booking.user:
            if booking.user.first_name and booking.user.last_name:
                customer_name = f"{booking.user.first_name} {booking.user.last_name}"
            elif booking.user.first_name:
                customer_name = booking.user.first_name
            elif booking.user.username:
                customer_name = booking.user.username
            elif booking.user.email:
                customer_name = booking.user.email.split('@')[0]

        service_name = booking.service.name if booking.service else booking.custom_service_name

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .status-change {{ background: #f0f7ff; padding: 20px; margin: 20px 0; border-left: 4px solid #2196F3; }}
                .details {{ background: white; padding: 20px; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Booking Status Updated</h2>
                <p>Booking #{booking.booking_number}</p>
            </div>

            <div class="status-change">
                <h3 style="margin-top: 0;">📊 Status Changed:</h3>
                <p><strong>From:</strong> {old_status}</p>
                <p><strong>To:</strong> {new_status}</p>
                <p><strong>Date:</strong> {timezone.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>

            <div class="details">
                <h3 style="margin-top: 0;">📋 Booking Details:</h3>
                <p><strong>Customer:</strong> {customer_name}</p>
                <p><strong>Phone:</strong> {booking.user.phone if booking.user and hasattr(booking.user, 'phone') else 'N/A'}</p>
                <p><strong>Service:</strong> {service_name}</p>
                <p><strong>Scheduled:</strong> {booking.scheduled_date.strftime('%Y-%m-%d at %I:%M %p')}</p>
                <p><strong>Amount:</strong> TZS {booking.total_price:,.2f}</p>
                <p><strong>Location:</strong> {booking.location}</p>
            </div>

            <div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9;
                        border-radius: 5px; text-align: center; color: #666; font-size: 14px;">
                <p>QuickFix Automotive | Support: support@quickfixauto.com</p>
            </div>
        </body>
        </html>
        """

        return html_template

    # Additional actions
    @action(detail=True, methods=['post'])
    def resend_sms(self, request, pk=None):
        """
        Manually resend booking SMS to customer
        """
        booking = self.get_object()

        if not booking.user or not booking.user.phone:
            return Response({
                'success': False,
                'message': 'Customer phone number not available'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not booking.user.is_phone_verified:
            return Response({
                'success': False,
                'message': 'Customer phone number not verified'
            }, status=status.HTTP_400_BAD_REQUEST)

        sms_result = self.send_booking_sms_confirmation(booking)

        return Response({
            'success': sms_result['success'],
            'message': sms_result['message']
        })

    @action(detail=True, methods=['post'])
    def send_reminder(self, request, pk=None):
        """
        Send reminder SMS to customer (24 hours before)
        """
        booking = self.get_object()

        try:
            if not booking.user or not booking.user.phone or not booking.user.is_phone_verified:
                return Response({
                    'success': False,
                    'message': 'Customer phone not verified'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if reminder already sent recently
            if booking.sms_reminder_sent:
                time_since = timezone.now() - booking.sms_reminder_sent_at
                if time_since.total_seconds() < 86400:  # 24 hours
                    return Response({
                        'success': False,
                        'message': 'Reminder already sent within 24 hours'
                    })

            # Check if booking is tomorrow
            scheduled_date = booking.scheduled_date.date()
            tomorrow = timezone.now().date() + timedelta(days=1)

            if scheduled_date != tomorrow:
                return Response({
                    'success': False,
                    'message': f'Reminder should be sent 24 hours before appointment (scheduled: {scheduled_date})'
                })

            service_name = booking.service.name if booking.service else booking.custom_service_name
            scheduled_time = booking.scheduled_date.strftime('%I:%M %p')

            message = (
                f"Reminder: Your booking #{booking.booking_number} is tomorrow at {scheduled_time}\n"
                f"📍 Service: {service_name}\n"
                f"🏢 Garage: {booking.garage.name}\n"
                f"📞 Contact: {booking.garage.phone}\n\n"
                f"Please be on time!"
            )

            sms_sent = sms_service.send_sms(
                phone_number=booking.user.phone,
                message=message,
                purpose='reminder'
            )

            if sms_sent:
                booking.mark_sms_sent('reminder', 'sent')
                return Response({
                    'success': True,
                    'message': 'Reminder SMS sent successfully'
                })
            else:
                booking.log_sms_error("Failed to send reminder SMS")
                return Response({
                    'success': False,
                    'message': 'Failed to send reminder SMS'
                })

        except Exception as e:
            logger.error(f"Error sending reminder SMS: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error sending reminder SMS'
            })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get booking statistics
        """
        # Base queryset
        queryset = Booking.objects.all()

        # Apply user filter for non-staff
        if request.user.is_authenticated and not request.user.is_staff:
            queryset = queryset.filter(user=request.user)

        total = queryset.count()
        by_status = queryset.values('status').annotate(count=Count('id'))
        today = queryset.filter(created_at__date=timezone.now().date()).count()

        return Response({
            'total_bookings': total,
            'today_bookings': today,
            'by_status': list(by_status),
            'upcoming_tomorrow': queryset.filter(
                scheduled_date__date=timezone.now().date() + timedelta(days=1)
            ).count()
        })

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming bookings
        """
        # Base queryset
        queryset = Booking.objects.filter(
            scheduled_date__gte=timezone.now(),
            status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
        )

        # Apply user filter for non-staff
        if request.user.is_authenticated and not request.user.is_staff:
            queryset = queryset.filter(user=request.user)

        upcoming = queryset.order_by('scheduled_date')[:10]
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """
        Get bookings for the currently authenticated user
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)

        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
        serializer = self.get_serializer(bookings, many=True)

        return Response({
            'success': True,
            'count': bookings.count(),
            'bookings': serializer.data
        })
        # ===============================//   BOOKING VIEWSET//=============================





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





# ==============================// BOOKING VIEWSET //========================================

# views.py
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from users.models import Booking, Garage, Service
from .serializers import BookingCreateSerializer, BookingSerializer
from utils.africastalking_sms import africastalking_sms as sms_service
from django.db.models import Q

@method_decorator(csrf_exempt, name='dispatch')
class AdminBookingViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Bookings with auto-loading of service price and SMS integration
    """
    queryset = Booking.objects.all().order_by('-created_at')
    pagination_class = None  # You can set your AdminPagination here
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

        # Filter by user
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

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
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(location__icontains=search) |
                Q(notes__icontains=search) |
                Q(garage__name__icontains=search) |
                Q(service__name__icontains=search)
            )

        # Ordering
        order_by = self.request.query_params.get('order_by', '-created_at')
        if order_by in ['created_at', '-created_at', 'scheduled_date', '-scheduled_date',
                       'total_price', '-total_price']:
            queryset = queryset.order_by(order_by)

        return queryset.select_related('garage', 'service', 'user')

    def create(self, request, *args, **kwargs):
        """
        Create booking with location processing and send SMS confirmation
        """
        data = request.data.copy()

        # Process Google Maps link if coordinates are provided
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude and longitude and not data.get('google_maps_link'):
            data['google_maps_link'] = f"https://www.google.com/maps?q={latitude},{longitude}"

        serializer = self.get_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            booking = serializer.save()

            # Send SMS confirmation using Africa's Talking
            self._send_booking_confirmation_sms(booking)

            # Return full booking details
            full_serializer = BookingSerializer(booking)
            headers = self.get_success_headers(full_serializer.data)

            return Response(
                {
                    'success': True,
                    'message': 'Booking created successfully. SMS confirmation sent.',
                    'booking': full_serializer.data,
                    'booking_number': booking.booking_number,
                    'sms_sent': booking.sms_confirmation_sent
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

    def _send_booking_confirmation_sms(self, booking):
        """Send booking confirmation SMS using Africa's Talking"""
        try:
            # Check if SMS can be sent
            can_send, reason = booking.can_send_sms()
            if not can_send:
                booking.log_sms_error(f"Cannot send SMS: {reason}")
                return False

            # Create the SMS message
            service_name = booking.service.name if booking.service else booking.custom_service_name
            scheduled_time = booking.scheduled_date.strftime('%Y-%m-%d %H:%M')
            garage_name = booking.garage.name

            message = (
                f"Hello {booking.full_name},\n\n"
                f"Your booking #{booking.booking_number} has been confirmed!\n"
                f"📍 Service: {service_name}\n"
                f"🏢 Garage: {garage_name}\n"
                f"📅 Date: {scheduled_time}\n"
                f"💰 Price: TZS {booking.total_price:,.2f}\n"
                f"📌 Location: {booking.location}\n\n"
                f"Thank you for choosing us!"
            )

            # Send SMS using Africa's Talking
            sms_sent = sms_service.send_sms(
                phone_number=booking.mobile_number,
                message=message,
                purpose='booking_confirmation'
            )

            if sms_sent:
                booking.mark_sms_sent('confirmation', 'sent')
            else:
                booking.log_sms_error("Failed to send SMS via Africa's Talking API")

            return sms_sent

        except Exception as e:
            booking.log_sms_error(f"Error sending SMS: {str(e)}")
            return False

    @action(detail=True, methods=['post'])
    def resend_confirmation(self, request, pk=None):
        """Resend booking confirmation SMS"""
        booking = self.get_object()

        success = self._send_booking_confirmation_sms(booking)

        if success:
            return Response({
                'success': True,
                'message': 'SMS confirmation resent successfully'
            })
        else:
            return Response({
                'success': False,
                'message': 'Failed to resend SMS confirmation'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def send_reminder(self, request, pk=None):
        """Send booking reminder SMS (24 hours before scheduled time)"""
        booking = self.get_object()

        try:
            # Create reminder message
            service_name = booking.service.name if booking.service else booking.custom_service_name
            scheduled_time = booking.scheduled_date.strftime('%Y-%m-%d %H:%M')

            message = (
                f"Reminder: Your booking #{booking.booking_number} is tomorrow at {scheduled_time}\n"
                f"📍 Service: {service_name}\n"
                f"🏢 Garage: {booking.garage.name}\n"
                f"📌 Don't forget your appointment!"
            )

            # Send SMS using Africa's Talking
            sms_sent = sms_service.send_sms(
                phone_number=booking.mobile_number,
                message=message,
                purpose='booking_reminder'
            )

            if sms_sent:
                booking.mark_sms_sent('reminder', 'sent')
                return Response({
                    'success': True,
                    'message': 'Reminder SMS sent successfully'
                })
            else:
                booking.log_sms_error("Failed to send reminder SMS")
                return Response({
                    'success': False,
                    'message': 'Failed to send reminder SMS'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            booking.log_sms_error(f"Error sending reminder SMS: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error sending reminder SMS'
            }, status=status.HTTP_400_BAD_REQUEST)


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


@method_decorator(csrf_exempt, name='dispatch')
class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    REMOVED AUTHENTICATION FOR DEVELOPMENT/TESTING
    """
    queryset = CustomUser.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    lookup_field = 'id'

    # REMOVE ALL AUTHENTICATION FOR DEVELOPMENT
    authentication_classes = []  # Empty list = no authentication
    permission_classes = [AllowAny]  # Allow anyone to access

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
            'success': True,
            'count': queryset.count(),
            'users': serializer.data,
            'message': 'Users retrieved successfully',
            'timestamp': timezone.now().isoformat()
        })

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def me(self, request):
        """
        Get current user's profile.
        Only works if user is authenticated
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'User not authenticated',
                'user': None
            }, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(request.user)
        return Response({
            'success': True,
            'user': serializer.data
        })

    @action(detail=False, methods=['put', 'patch'], permission_classes=[AllowAny])
    def update_me(self, request):
        """
        Update current user's profile.
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'User not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)

        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'user': serializer.data
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def change_password(self, request, id=None):
        """
        Change user password.
        """
        user = self.get_object()

        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            # Verify old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({
                    'success': False,
                    'errors': {"old_password": ["Wrong password."]}
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response({
                'success': True,
                'detail': "Password updated successfully."
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def activate(self, request, id=None):
        """
        Activate a user account.
        """
        user = self.get_object()
        user.is_active = True
        user.save()

        return Response({
            'success': True,
            'detail': f"User {user.email} has been activated.",
            'is_active': user.is_active
        })

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def deactivate(self, request, id=None):
        """
        Deactivate a user account.
        """
        user = self.get_object()
        user.is_active = False
        user.save()

        return Response({
            'success': True,
            'detail': f"User {user.email} has been deactivated.",
            'is_active': user.is_active
        })

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def verify_email(self, request, id=None):
        """
        Manually verify a user's email.
        """
        user = self.get_object()
        user.is_email_verified = True
        user.save()

        return Response({
            'success': True,
            'detail': f"Email for {user.email} has been verified.",
            'is_email_verified': user.is_email_verified
        })

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def verify_phone(self, request, id=None):
        """
        Manually verify a user's phone.
        """
        user = self.get_object()
        user.is_phone_verified = True
        user.save()

        return Response({
            'success': True,
            'detail': f"Phone for {user.email} has been verified.",
            'is_phone_verified': user.is_phone_verified
        })

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
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
            'success': True,
            'total_users': total_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'role_distribution': role_counts,
            'registration_stages': stage_counts,
            'recent_users': CustomUser.objects.order_by('-date_joined')[:5].count()
        })

    def create(self, request, *args, **kwargs):
        """
        Create a new user.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'message': 'User created successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Update a user.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'User updated successfully',
                'user': serializer.data
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete by deactivating the user.
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()

        return Response({
            'success': True,
            'message': f'User {instance.email} has been deactivated.',
            'is_active': instance.is_active
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def test(self, request):
        """
        Test endpoint to verify API is working.
        """
        return Response({
            'success': True,
            'message': 'User API is working!',
            'endpoint': '/users/',
            'timestamp': timezone.now().isoformat(),
            'authentication': 'Disabled for development',
            'csrf_enabled': True
        })











# registration/views.py
# registration/views.py

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Approve
from .serializers import ApproveSerializer

class ApproveViewSet(viewsets.ModelViewSet):
    queryset = Approve.objects.all()
    serializer_class = ApproveSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'], url_path='by-appointment/(?P<appointment_code>[^/.]+)')
    def get_by_appointment(self, request, appointment_code=None):
        """Get all approvals for a specific appointment code"""
        approvals = Approve.objects.filter(appointment_code=appointment_code).order_by('-created_at')
        serializer = self.get_serializer(approvals, many=True)
        return Response({
            'appointment_code': appointment_code,
            'total_updates': approvals.count(),
            'history': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='by-request/(?P<request_code>[^/.]+)')
    def get_by_request(self, request, request_code=None):
        """Get all approvals for a specific request code"""
        approvals = Approve.objects.filter(request_code=request_code).order_by('-created_at')
        serializer = self.get_serializer(approvals, many=True)
        return Response({
            'request_code': request_code,
            'total_updates': approvals.count(),
            'history': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='by-location')
    def get_by_location(self, request):
        """Get approvals by location (city or coordinates)"""
        city = request.query_params.get('city')
        country = request.query_params.get('country')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius_km = request.query_params.get('radius_km', 10)  # Default 10km radius

        queryset = Approve.objects.all()

        if city:
            queryset = queryset.filter(location_city__icontains=city)

        if country:
            queryset = queryset.filter(location_country__icontains=country)

        if lat and lng:
            # Simple bounding box filter for location within radius
            # For more accurate distance calculation, consider using PostGIS or geopy
            try:
                lat = float(lat)
                lng = float(lng)
                radius = float(radius_km) / 111.0  # Convert km to degrees (approx)

                queryset = queryset.filter(
                    latitude__isnull=False,
                    longitude__isnull=False,
                    latitude__range=(lat - radius, lat + radius),
                    longitude__range=(lng - radius, lng + radius)
                )
            except (ValueError, TypeError):
                pass

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total_records': queryset.count(),
            'data': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='location-stats')
    def get_location_stats(self, request):
        """Get location statistics for approvals"""
        total_with_location = Approve.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).count()

        city_stats = Approve.objects.filter(
            location_city__isnull=False
        ).exclude(
            location_city=''
        ).values('location_city', 'location_country').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]

        return Response({
            'total_records': Approve.objects.count(),
            'records_with_location': total_with_location,
            'top_cities': list(city_stats),
        })

    def create(self, request, *args, **kwargs):
        """Create approval record with location data"""
        updated_by = request.data.get('updated_by', '')
        phone_number = request.data.get('phone_number', '')
        request_code = request.data.get('request_code', '')
        appointment_code = request.data.get('appointment_code', '')
        previous_status = request.data.get('previous_status', '')
        new_status = request.data.get('new_status', '')
        notes = request.data.get('notes', '')

        # Location data
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        location_address = request.data.get('location_address', '')
        location_city = request.data.get('location_city', '')
        location_country = request.data.get('location_country', '')

        if not updated_by:
            return Response(
                {'error': 'updated_by field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate coordinates if provided
        if latitude and longitude:
            try:
                lat = float(latitude)
                lng = float(longitude)
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    return Response(
                        {'error': 'Invalid latitude or longitude values'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Latitude and longitude must be valid numbers'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        approval = Approve.objects.create(
            updated_by=updated_by.strip(),
            phone_number=phone_number,
            request_code=request_code,
            appointment_code=appointment_code,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
            latitude=latitude,
            longitude=longitude,
            location_address=location_address,
            location_city=location_city,
            location_country=location_country
        )

        serializer = self.get_serializer(approval)
        return Response({
            'message': 'Approval record created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update approval record with location data"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Update location fields if provided
        if 'latitude' in request.data:
            try:
                lat = float(request.data['latitude'])
                if -90 <= lat <= 90:
                    instance.latitude = lat
                else:
                    return Response({'error': 'Invalid latitude value'}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({'error': 'Latitude must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)

        if 'longitude' in request.data:
            try:
                lng = float(request.data['longitude'])
                if -180 <= lng <= 180:
                    instance.longitude = lng
                else:
                    return Response({'error': 'Invalid longitude value'}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({'error': 'Longitude must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)

        # Update other location fields
        location_fields = ['location_address', 'location_city', 'location_country']
        for field in location_fields:
            if field in request.data:
                setattr(instance, field, request.data[field])

        # Update other fields
        other_fields = ['updated_by', 'phone_number', 'request_code', 'appointment_code',
                       'previous_status', 'new_status', 'notes']
        for field in other_fields:
            if field in request.data:
                setattr(instance, field, request.data[field])

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)