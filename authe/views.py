# views.py - CORRECTED VERSION
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.http import JsonResponse
from .models import User, OTPVerification, UserSession, MyProfile
from .serializers import (
    PhoneNumberSerializer, RegisterEmailSerializer, 
    VerifyOTPSerializer, LoginSerializer, UserSerializer,
    MyProfileSerializer, UserWithProfileSerializer
)
from .utils import send_otp_email, generate_tokens_for_user


# ==================== REGISTRATION ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def check_phone_number(request):
    """Step 1: Check if phone number is valid"""
    serializer = PhoneNumberSerializer(data=request.data)
    
    if serializer.is_valid():
        mobile_number = serializer.validated_data['mobile_number']
        user_exists = User.objects.filter(mobile_number=mobile_number).exists()
        
        return Response({
            'valid': True,
            'user_exists': user_exists,
            'mobile_number': mobile_number
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """Step 2: Send OTP to email for new registration"""
    serializer = RegisterEmailSerializer(data=request.data)
    
    if serializer.is_valid():
        mobile_number = serializer.validated_data['mobile_number']
        email = serializer.validated_data['email']
        
        otp_code = OTPVerification.generate_otp()
        
        OTPVerification.objects.filter(
            email=email,
            is_verified=False,
            user__isnull=True
        ).delete()
        
        otp_record = OTPVerification.objects.create(
            email=email,
            otp_code=otp_code
        )
        
        email_sent = send_otp_email(email, otp_code, mobile_number)
        
        if email_sent:
            return Response({
                'success': True,
                'message': 'OTP sent successfully',
                'email': email,
                'expires_in': 600
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_and_register(request):
    """Step 3: Verify OTP and create user account"""
    serializer = VerifyOTPSerializer(data=request.data)
    
    if serializer.is_valid():
        mobile_number = serializer.validated_data['mobile_number']
        email = serializer.validated_data['email']
        otp_record = serializer.validated_data['otp_record']
        
        user = User.objects.create_user(
            mobile_number=mobile_number,
            email=email,
            password=otp_record.otp_code
        )
        
        otp_record.is_verified = True
        otp_record.user = user
        otp_record.save()
        
        tokens = generate_tokens_for_user(user)
        
        UserSession.objects.create(
            user=user,
            device_info=request.headers.get('User-Agent', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'success': True,
            'message': 'Account created successfully',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    """Resend OTP to email"""
    email = request.data.get('email')
    mobile_number = request.data.get('mobile_number')
    
    if not email or not mobile_number:
        return Response({
            'success': False,
            'error': 'Email and mobile number are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Delete old unverified OTPs
    OTPVerification.objects.filter(
        email=email,
        is_verified=False,
        user__isnull=True
    ).delete()
    
    # Generate new OTP
    otp_code = OTPVerification.generate_otp()
    
    # Create new OTP record
    otp_record = OTPVerification.objects.create(
        email=email,
        otp_code=otp_code
    )
    
    # Send OTP
    email_sent = send_otp_email(email, otp_code, mobile_number)
    
    if email_sent:
        return Response({
            'success': True,
            'message': 'OTP resent successfully',
            'expires_in': 600
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'message': 'Failed to send OTP'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== AUTHENTICATION ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_phone(request):
    """Login using phone number only"""
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        tokens = generate_tokens_for_user(user)
        
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        UserSession.objects.create(
            user=user,
            device_info=request.headers.get('User-Agent', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        UserSession.objects.filter(
            user=request.user,
            is_active=True
        ).update(is_active=False)
        
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== PROFILE ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    Get user profile including both User and MyProfile data
    GET /api/profile/
    """
    try:
        # Get or create profile if it doesn't exist
        profile, created = MyProfile.objects.get_or_create(user=request.user)
        
        # Serialize user with profile
        serializer = UserWithProfileSerializer(request.user)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """
    Update user profile (profile_picture, bio, location)
    PUT /api/profile/update/
    """
    try:
        # Get or create profile
        profile, created = MyProfile.objects.get_or_create(user=request.user)
        
        # Update profile fields
        serializer = MyProfileSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated user with profile
            user_serializer = UserWithProfileSerializer(request.user)
            
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': user_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile_picture(request):
    """
    Update user profile picture only
    POST /api/profile/update-picture/
    Expects: form-data with 'profile_picture' field containing image file
    """
    try:
        # Get or create profile
        profile, created = MyProfile.objects.get_or_create(user=request.user)
        
        # Check if file was uploaded
        if 'profile_picture' not in request.FILES:
            # Try to get from request.data (for base64 string)
            profile_picture_data = request.data.get('profile_picture')
            if not profile_picture_data:
                return Response({
                    'success': False,
                    'error': 'No profile picture provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # If it's a base64 string, store it directly
            profile.profile_picture = profile_picture_data
            profile.save()
            
            return Response({
                'success': True,
                'message': 'Profile picture updated successfully',
                'profile_picture': profile.profile_picture
            }, status=status.HTTP_200_OK)
        
        # Handle file upload
        uploaded_file = request.FILES['profile_picture']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if uploaded_file.content_type not in allowed_types:
            return Response({
                'success': False,
                'error': 'Invalid file type. Only JPEG, PNG, GIF, and WEBP are allowed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size (max 5MB)
        if uploaded_file.size > 5 * 1024 * 1024:
            return Response({
                'success': False,
                'error': 'File too large. Maximum size is 5MB.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Import base64 for encoding
        import base64
        
        # Read file and convert to base64
        file_content = uploaded_file.read()
        base64_image = base64.b64encode(file_content).decode('utf-8')
        
        # Create data URL
        content_type = uploaded_file.content_type
        data_url = f"data:{content_type};base64,{base64_image}"
        
        # Save to database
        profile.profile_picture = data_url
        profile.save()
        
        return Response({
            'success': True,
            'message': 'Profile picture updated successfully',
            'profile_picture': data_url
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error updating profile picture: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_profile_field(request, field_name):
    """
    Delete a specific profile field
    DELETE /api/profile/field/<field_name>/
    """
    try:
        profile, created = MyProfile.objects.get_or_create(user=request.user)
        
        if hasattr(profile, field_name):
            setattr(profile, field_name, '')
            profile.save()
            
            return Response({
                'success': True,
                'message': f'{field_name} has been deleted'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': f'Field {field_name} does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_account(request):
    """
    Delete user account and all related data
    DELETE /api/profile/delete-account/
    """
    try:
        user = request.user
        # Deactivate user instead of hard delete
        user.is_active = False
        user.save()
        
        # Delete profile
        if hasattr(user, 'profile'):
            user.profile.delete()
        
        return Response({
            'success': True,
            'message': 'Account deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== TEST ENDPOINT ====================

@api_view(['GET', 'POST', 'OPTIONS'])
@permission_classes([AllowAny])
def test_api(request):
    """Test endpoint to verify API is working"""
    return JsonResponse({
        'status': 'success',
        'message': 'API is working!',
        'method': request.method,
        'available_endpoints': [
            '/api/register/check-phone/',
            '/api/register/send-otp/',
            '/api/register/verify-otp/',
            '/api/register/resend-otp/',
            '/api/login/',
            '/api/logout/',
            '/api/profile/',
            '/api/profile/update/',
            '/api/profile/update-picture/',
            '/api/profile/field/<field_name>/',
            '/api/profile/delete-account/',
        ]
    }, status=200)


# ==================== ALL USERS VIEW - FIXED ====================

class AllUsersView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Get all users except the current user
            users = User.objects.exclude(id=request.user.id).only(
                'id', 'mobile_number', 'full_name'
            )
        else:
            # For unauthenticated users, show all users (or you can return empty list)
            users = User.objects.all().only(
                'id', 'mobile_number', 'full_name'
            )
        
        # Format the response
        data = []
        for user in users:
            profile_picture = None
            if hasattr(user, 'profile') and user.profile:
                profile_picture = user.profile.profile_picture
            
            data.append({
                'id': user.id,
                'mobile_number': user.mobile_number,
                'full_name': user.full_name or user.mobile_number,
                'profile_picture': profile_picture,
                'is_online': getattr(user, 'is_online', False),
            })
        
        return Response(data)