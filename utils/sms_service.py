# utils/africastalking_sms.py
import africastalking
import logging
import re
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class AfricaTalkingSMSService:
    """Africa's Talking SMS Service"""
    
    def __init__(self):
        self.config = settings.AFRICAS_TALKING_CONFIG
        self.enabled = self.config.get('ENABLED', False)
        
        if self.enabled:
            try:
                # Initialize Africa's Talking
                username = self.config.get('USERNAME', 'sandbox')  # 'sandbox' for testing
                api_key = self.config.get('API_KEY', '')
                
                africastalking.initialize(username, api_key)
                self.sms = africastalking.SMS
                logger.info("✅ Africa's Talking SMS service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Africa's Talking: {str(e)}")
                self.enabled = False
    
    def format_phone_number(self, phone: str) -> Optional[str]:
        """
        Format phone number to international format for Africa's Talking
        Africa's Talking expects: +254XXXXXXXXX or 254XXXXXXXXX
        """
        if not phone:
            return None
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        if not digits:
            return None
        
        # If number starts with 0, replace with country code
        if digits.startswith('0'):
            # Default to Tanzania (+255) if no country code specified
            country_code = self.config.get('DEFAULT_COUNTRY_CODE', '255')
            digits = country_code + digits[1:]
        
        # If number doesn't have country code, add default
        if len(digits) == 9:  # Local number without 0
            country_code = self.config.get('DEFAULT_COUNTRY_CODE', '255')
            digits = country_code + digits
        
        # Ensure number has country code (not starting with 0)
        if digits.startswith('0'):
            country_code = self.config.get('DEFAULT_COUNTRY_CODE', '255')
            digits = country_code + digits[1:]
        
        # Add + if not present (Africa's Talking accepts both formats)
        if not digits.startswith('+'):
            # Some Africa's Talking implementations prefer without +
            if self.config.get('USE_PLUS_PREFIX', True):
                digits = '+' + digits
        
        return digits
    
    def send_sms(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        """
        Send SMS using Africa's Talking
        
        Args:
            phone_number: Recipient phone number
            message: SMS message content
            sender_id: Optional sender ID (default from config)
        
        Returns:
            Dict with status and response
        """
        if not self.enabled:
            logger.warning("SMS service is disabled")
            return {'success': False, 'error': 'SMS service disabled'}
        
        try:
            # Format phone number
            formatted_number = self.format_phone_number(phone_number)
            if not formatted_number:
                return {'success': False, 'error': 'Invalid phone number'}
            
            # Get sender ID
            sender = sender_id or self.config.get('SENDER_ID', 'QuickFix')
            
            # Set Africa's Talking sender ID format
            if sender == 'QuickFix':
                # For sandbox, use 'AFRICASTKNG' as sender ID
                sender = self.config.get('SANDBOX_SENDER_ID', 'AFRICASTKNG')
            
            # Prepare recipients
            to = [formatted_number]
            
            # Send SMS
            response = self.sms.send(message, to, sender)
            
            logger.info(f"SMS sent to {formatted_number}: {response}")
            
            return {
                'success': True,
                'data': response,
                'to': formatted_number,
                'message': message,
                'timestamp': str(timezone.now())
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'to': phone_number
            }
    
    def send_bulk_sms(self, phone_numbers: list, message: str, sender_id: str = None) -> Dict[str, Any]:
        """
        Send bulk SMS to multiple recipients
        
        Args:
            phone_numbers: List of recipient phone numbers
            message: SMS message content
            sender_id: Optional sender ID
        
        Returns:
            Dict with status and response
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        try:
            # Format all phone numbers
            formatted_numbers = []
            invalid_numbers = []
            
            for number in phone_numbers:
                formatted = self.format_phone_number(number)
                if formatted:
                    formatted_numbers.append(formatted)
                else:
                    invalid_numbers.append(number)
            
            if not formatted_numbers:
                return {'success': False, 'error': 'No valid phone numbers'}
            
            # Get sender ID
            sender = sender_id or self.config.get('SENDER_ID', 'QuickFix')
            if sender == 'QuickFix':
                sender = self.config.get('SANDBOX_SENDER_ID', 'AFRICASTKNG')
            
            # Send SMS
            response = self.sms.send(message, formatted_numbers, sender)
            
            logger.info(f"Bulk SMS sent to {len(formatted_numbers)} recipients")
            
            return {
                'success': True,
                'data': response,
                'recipients': formatted_numbers,
                'invalid_numbers': invalid_numbers,
                'timestamp': str(timezone.now())
            }
            
        except Exception as e:
            logger.error(f"Failed to send bulk SMS: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_balance(self) -> Dict[str, Any]:
        """Get SMS balance"""
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        try:
            # Africa's Talking application endpoint
            response = self.sms.get_balance()
            return {
                'success': True,
                'balance': response
            }
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
africastalking_sms = AfricaTalkingSMSService()