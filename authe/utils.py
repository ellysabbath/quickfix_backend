# utils.py - With HTML email and embedded styles
import random
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework_simplejwt.tokens import RefreshToken
import logging

logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def send_otp_email(email, otp_code, mobile_number):
    """Send OTP via email with HTML template and embedded styles"""
    try:
        subject = 'Your Verification Code'
        
        # HTML content with embedded styles
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    padding: 20px;
                    background-color: #ffffff;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    padding-bottom: 20px;
                    border-bottom: 2px solid #4CAF50;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #4CAF50;
                }}
                .content {{
                    padding: 20px 0;
                }}
                .otp-code {{
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    padding: 20px;
                    background-color: #f0f0f0;
                    border-radius: 8px;
                    letter-spacing: 5px;
                    color: #2c3e50;
                    margin: 20px 0;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 10px;
                    margin: 20px 0;
                    font-size: 14px;
                }}
                .footer {{
                    text-align: center;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #777;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                @media only screen and (max-width: 480px) {{
                    .container {{
                        width: 100%;
                        margin: 10px;
                        padding: 15px;
                    }}
                    .otp-code {{
                        font-size: 24px;
                        padding: 15px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">QuickFix Auto</div>
                </div>
                
                <div class="content">
                    <h2>Hello!</h2>
                    <p>You requested to verify your mobile number: <strong>{mobile_number}</strong></p>
                    <p>Your verification code is:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p>This code will expire in <strong>10 minutes</strong>.</p>
                    
                    <div class="warning">
                        <strong>⚠️ Security Tip:</strong> Never share this code with anyone.
                    </div>
                    
                    <p>If you didn't request this verification, please ignore this email.</p>
                </div>
                
                <div class="footer">
                    <p>&copy; 2026 QuickFix Auto. All rights reserved.</p>
                    <p>Need help? Contact us at support@quickfixauto.com</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Plain text version as fallback
        text_content = f'''
Hello,

Your verification code is: {otp_code}

This code will expire in 10 minutes.

Use this code to complete your registration with mobile number: {mobile_number}

If you didn't request this, please ignore this email.

Best regards,
Your Team
'''
        
        # Send HTML email
        email_message = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()
        
        logger.info(f"HTML OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email OTP to {email}: {str(e)}")
        return False


def generate_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }