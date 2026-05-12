# users/authentication.py (create this file)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.tokens import AccessToken
import jwt
from django.conf import settings

class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that validates both access and refresh tokens
    against the blacklist
    """
    
    def authenticate(self, request):
        # Get the authorization header
        header = self.get_header(request)
        if header is None:
            return None

        # Get the raw token
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        # Validate token and check against blacklist
        try:
            validated_token = self.get_validated_token(raw_token)
            
            # Get the user from the validated token
            user = self.get_user(validated_token)
            
            return (user, validated_token)
            
        except InvalidToken:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')