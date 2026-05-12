import re
from django.core.exceptions import ValidationError

def is_email(value):
    """
    Check if a value is a valid email address.
    
    Args:
        value: The string to check
        
    Returns:
        bool: True if value is a valid email
    """
    if not value:
        return False
    
    # Simple but effective email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, value.strip()))

def is_phone_number(value):
    """
    Check if a value is a valid phone number.
    
    Args:
        value: The string to check
        
    Returns:
        bool: True if value is a valid phone number
    """
    if not value:
        return False
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', value)
    
    # Check if we have 10-15 digits (international format)
    return 10 <= len(digits) <= 15

def normalize_phone(phone):
    """
    Normalize phone number by removing all non-digit characters.
    
    Args:
        phone: The phone number to normalize
        
    Returns:
        str: Normalized phone number or None if invalid
    """
    if not phone:
        return None
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Validate length
    if 10 <= len(digits) <= 15:
        return digits
    
    return None

def get_user_identifier_type(identifier):
    """
    Determine if an identifier is an email or phone number.
    
    Args:
        identifier: The string to identify
        
    Returns:
        str: 'email', 'phone', or None
    """
    identifier = str(identifier).strip()
    
    if is_email(identifier):
        return 'email'
    elif is_phone_number(identifier):
        return 'phone'
    
    return None

def find_user_by_identifier(identifier):
    """
    Find a user by either email or phone number.
    
    Args:
        identifier: Email or phone number
        
    Returns:
        CustomUser or None
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    identifier_type = get_user_identifier_type(identifier)
    
    if identifier_type == 'email':
        # Try to find by email (case-insensitive)
        try:
            return User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            return None
    elif identifier_type == 'phone':
        # Try to find by phone (normalized)
        normalized_phone = normalize_phone(identifier)
        if normalized_phone:
            try:
                return User.objects.get(phone=normalized_phone)
            except User.DoesNotExist:
                return None
    
    return None

def validate_identifier(identifier):
    """
    Validate that an identifier is either a valid email or phone number.
    
    Args:
        identifier: The identifier to validate
        
    Returns:
        tuple: (is_valid, error_message, identifier_type)
    """
    identifier = str(identifier).strip()
    
    if not identifier:
        return False, 'Identifier is required', None
    
    identifier_type = get_user_identifier_type(identifier)
    
    if not identifier_type:
        return False, 'Please enter a valid email or phone number', None
    
    return True, None, identifier_type