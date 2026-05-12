# utils/africastalking_sms.py
"""
Africa's Talking SMS Integration
"""
import africastalking
import re
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class AfricaTalkingSMS:
    """Africa's Talking SMS Service"""
    
    def __init__(self):
        self.config = settings.AFRICAS_TALKING_CONFIG
        self.enabled = self.config.get('ENABLED', False)
        
        if self.enabled:
            try:
                username = self.config.get('USERNAME', 'sandbox')
                api_key = self.config.get('API_KEY', '')
                
                africastalking.initialize(username, api_key)
                self.sms = africastalking.SMS
                logger.info("✅ Africa's Talking SMS initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Africa's Talking: {e}")
                self.enabled = False
    
    def format_phone(self, phone: str) -> Optional[str]:
        """Format phone number for Tanzania"""
        if not phone:
            return None
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', str(phone))
        
        if not digits:
            return None
        
        # Handle different formats for Tanzania (+255)
        if digits.startswith('0'):
            digits = '255' + digits[1:]
        elif digits.startswith('255'):
            pass
        elif len(digits) == 9:
            digits = '255' + digits
        else:
            digits = '255' + digits.lstrip('0')
        
        # Add + if configured
        if self.config.get('USE_PLUS_PREFIX', True):
            if not digits.startswith('+'):
                digits = '+' + digits
        
        return digits
    
    def send_sms(self, phone_number: str, message: str, sender_id: str = None) -> Dict[str, Any]:
        """Send SMS via Africa's Talking"""
        if not self.enabled:
            logger.warning("SMS service disabled")
            return {'success': False, 'error': 'SMS service disabled'}
        
        try:
            formatted_number = self.format_phone(phone_number)
            if not formatted_number:
                return {'success': False, 'error': 'Invalid phone number'}
            
            sender = sender_id or self.config.get('SENDER_ID', 'QuickFix')
            if sender == 'QuickFix':
                sender = self.config.get('SANDBOX_SENDER_ID', 'AFRICASTKNG')
            
            response = self.sms.send(message, [formatted_number], sender)
            
            logger.info(f"SMS sent to {formatted_number}")
            
            return {
                'success': True,
                'data': response,
                'to': formatted_number
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return {'success': False, 'error': str(e)}

# Global instance
africastalking_sms = AfricaTalkingSMS()