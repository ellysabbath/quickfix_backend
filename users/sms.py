# users/sms.py
import re
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class BaseSMSService:
    """Base class for SMS services"""
    
    def __init__(self):
        self.config = settings.SMS_CONFIG
        self.enabled = self.config['ENABLED']
    
    def format_message(self, template_name: str, context: Dict[str, Any]) -> str:
        """Format message using template and context"""
        template = self.config['MESSAGE_TEMPLATES'].get(template_name, '')
        
        # Replace placeholders with context values
        message = template.format(**context)
        
        # Clean up whitespace
        message = '\n'.join(line.strip() for line in message.strip().split('\n'))
        
        # Truncate if too long
        max_length = self.config['MAX_SMS_LENGTH']
        if len(message) > max_length:
            message = message[:max_length-3] + '...'
        
        return message
    
    def format_phone_number(self, phone: str) -> Optional[str]:
        """Format phone number to E.164 format"""
        if not phone:
            return None
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        if not digits:
            return None
        
        # Get country code from config
        country_code = self.config.get('DEFAULT_COUNTRY_CODE', '+255')
        country_digits = re.sub(r'\D', '', country_code)
        
        # If number starts with 0, remove it
        if digits.startswith('0'):
            digits = digits[1:]
        
        # Check if number already has country code
        if digits.startswith(country_digits):
            return f"+{digits}"
        
        # Add country code
        return f"{country_code}{digits}"
    
    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        formatted = self.format_phone_number(phone)
        if not formatted:
            return False
        
        # E.164 format: +[country code][number], 8-15 digits total
        pattern = r'^\+\d{8,15}$'
        return bool(re.match(pattern, formatted))
    
    def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Send SMS - to be implemented by subclasses"""
        raise NotImplementedError


class ConsoleSMSService(BaseSMSService):
    """SMS service that prints to console (for testing)"""
    
    def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Print SMS to console instead of sending"""
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        formatted_phone = self.format_phone_number(phone)
        
        print("\n" + "="*60)
        print("📱 SMS NOTIFICATION (Console Mode)")
        print("="*60)
        print(f"To: {formatted_phone}")
        print(f"Time: {timezone.now()}")
        print("-"*60)
        print(message)
        print("="*60 + "\n")
        
        logger.info(f"Console SMS sent to {formatted_phone}")
        
        return {
            'success': True,
            'test_mode': True,
            'to': formatted_phone,
            'message': message,
            'timestamp': str(timezone.now()),
            'note': 'Console mode - no actual SMS sent'
        }


class TwilioSMSService(BaseSMSService):
    """Twilio SMS service implementation"""
    
    def __init__(self):
        super().__init__()
        
        if self.enabled:
            try:
                from twilio.rest import Client
                self.account_sid = self.config['TWILIO_ACCOUNT_SID']
                self.auth_token = self.config['TWILIO_AUTH_TOKEN']
                self.twilio_number = self.config['TWILIO_PHONE_NUMBER']
                
                if not all([self.account_sid, self.auth_token, self.twilio_number]):
                    logger.error("Twilio credentials not configured")
                    self.enabled = False
                    return
                
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio SMS service initialized")
                
            except ImportError:
                logger.error("Twilio package not installed. Run: pip install twilio")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Twilio: {str(e)}")
                self.enabled = False
    
    def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Send SMS using Twilio API"""
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        formatted_phone = self.format_phone_number(phone)
        if not formatted_phone:
            return {'success': False, 'error': 'Invalid phone number format'}
        
        try:
            # Send SMS via Twilio
            message_obj = self.client.messages.create(
                body=message,
                from_=self.twilio_number,
                to=formatted_phone
            )
            
            logger.info(f"SMS sent to {formatted_phone}. SID: {message_obj.sid}")
            
            return {
                'success': True,
                'sid': message_obj.sid,
                'to': formatted_phone,
                'status': message_obj.status,
                'price': str(message_obj.price) if message_obj.price else None,
                'timestamp': str(timezone.now())
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {formatted_phone}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'to': formatted_phone
            }


class LogOnlySMSService(BaseSMSService):
    """Service that only logs SMS (for development)"""
    
    def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Log SMS without sending"""
        formatted_phone = self.format_phone_number(phone)
        
        logger.info(f"📱 SMS would be sent to {formatted_phone}")
        logger.info(f"Message: {message[:100]}..." if len(message) > 100 else f"Message: {message}")
        
        return {
            'success': True,
            'log_only': True,
            'to': formatted_phone,
            'message_length': len(message),
            'timestamp': str(timezone.now())
        }


class SMSManager:
    """Main SMS manager"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the SMS service based on configuration"""
        provider = settings.SMS_CONFIG['PROVIDER']
        
        if provider == 'twilio':
            self.service = TwilioSMSService()
        elif provider == 'console':
            self.service = ConsoleSMSService()
        elif provider == 'log_only':
            self.service = LogOnlySMSService()
        else:
            logger.warning(f"Unknown SMS provider: {provider}. Using console mode.")
            self.service = ConsoleSMSService()
        
        self.enabled = settings.SMS_CONFIG['ENABLED']
    
    def send_booking_confirmation(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send booking confirmation SMS"""
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        # Prepare message context
        context = {
            'full_name': booking_data.get('full_name', 'Customer'),
            'booking_number': booking_data.get('booking_number', 'N/A'),
            'service_name': booking_data.get('service_name', 'Service'),
            'garage_name': booking_data.get('garage_name', 'Garage'),
            'garage_city': booking_data.get('garage_city', 'City'),
            'garage_phone': booking_data.get('garage_phone', ''),
            'scheduled_date': booking_data.get('scheduled_date_formatted', 'Date'),
            'total_price': booking_data.get('total_price', '0.00'),
        }
        
        # Format message
        message = self.service.format_message('BOOKING_CONFIRMATION', context)
        
        # Get phone number
        phone = booking_data.get('mobile_number')
        if not phone:
            return {'success': False, 'error': 'No phone number provided'}
        
        # Send SMS
        return self.service.send_sms(phone, message)
    
    def send_status_update(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send status update SMS"""
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        # Prepare context
        context = {
            'booking_number': booking_data.get('booking_number', ''),
            'status_display': booking_data.get('status_display', 'Updated'),
            'service_name': booking_data.get('service_name', 'Service'),
            'scheduled_date': booking_data.get('scheduled_date_formatted', 'Date'),
        }
        
        # Format message
        message = self.service.format_message('STATUS_UPDATE', context)
        
        # Get phone number
        phone = booking_data.get('mobile_number')
        if not phone:
            return {'success': False, 'error': 'No phone number provided'}
        
        # Send SMS
        return self.service.send_sms(phone, message)
    
    def send_reminder(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send booking reminder SMS"""
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        # Prepare context
        context = {
            'booking_number': booking_data.get('booking_number', ''),
            'scheduled_time': booking_data.get('scheduled_time_formatted', 'Time'),
            'service_name': booking_data.get('service_name', 'Service'),
            'garage_name': booking_data.get('garage_name', 'Garage'),
        }
        
        # Format message
        message = self.service.format_message('REMINDER', context)
        
        # Get phone number
        phone = booking_data.get('mobile_number')
        if not phone:
            return {'success': False, 'error': 'No phone number provided'}
        
        # Send SMS
        return self.service.send_sms(phone, message)
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        return self.service.validate_phone_number(phone)


# Global instance
sms_manager = SMSManager()