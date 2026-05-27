# from rest_framework import serializers
# from django.utils import timezone
# from .models import User, OTPVerification, UserSession

# class PhoneNumberSerializer(serializers.Serializer):
#     mobile_number = serializers.CharField(max_length=20)

#     def validate_mobile_number(self, value):
#         cleaned = ''.join(filter(str.isdigit, value))
#         if len(cleaned) < 8:
#             raise serializers.ValidationError("Phone number must have at least 8 digits")
#         return value

# class RegisterEmailSerializer(serializers.Serializer):
#     mobile_number = serializers.CharField(max_length=20)
#     email = serializers.EmailField()

#     def validate(self, data):
#         if User.objects.filter(mobile_number=data['mobile_number']).exists():
#             raise serializers.ValidationError({"mobile_number": "User with this mobile number already exists"})

#         if User.objects.filter(email=data['email']).exists():
#             raise serializers.ValidationError({"email": "User with this email already exists"})

#         return data

# class VerifyOTPSerializer(serializers.Serializer):
#     mobile_number = serializers.CharField(max_length=20)
#     email = serializers.EmailField()
#     otp_code = serializers.CharField(max_length=6)

#     def validate(self, data):
#         try:
#             otp_record = OTPVerification.objects.get(
#                 email=data['email'],
#                 otp_code=data['otp_code'],
#                 is_verified=False,
#                 user__isnull=True
#             )

#             if not otp_record.is_valid():
#                 raise serializers.ValidationError({"otp_code": "OTP has expired. Please request a new one."})

#             data['otp_record'] = otp_record
#             return data

#         except OTPVerification.DoesNotExist:
#             raise serializers.ValidationError({"otp_code": "Invalid OTP code"})

# class LoginSerializer(serializers.Serializer):
#     mobile_number = serializers.CharField(max_length=20)

#     def validate(self, data):
#         try:
#             user = User.objects.get(mobile_number=data['mobile_number'])

#             if not user.is_active:
#                 raise serializers.ValidationError({"mobile_number": "Account is deactivated"})

#             data['user'] = user
#             return data

#         except User.DoesNotExist:
#             raise serializers.ValidationError({"mobile_number": "No account found with this phone number"})

# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['id', 'mobile_number', 'email', 'full_name', 'date_joined', 'is_active']
#         read_only_fields = ['id', 'date_joined']






# # =====================    MY PROFILE    =====================
# from .models import MyProfile
# class MyProfileSerializer(serializers.ModelSerializer):
#     """Serializer for MyProfile model"""
#     class Meta:
#         model = MyProfile
#         fields = ['id', 'profile_picture', 'bio', 'location', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'created_at', 'updated_at']

# class UserWithProfileSerializer(serializers.ModelSerializer):
#     """Serializer for User with profile data"""
#     profile = MyProfileSerializer(read_only=True)

#     class Meta:
#         model = User
#         fields = ['id', 'mobile_number', 'email', 'full_name', 'date_joined', 'is_active', 'profile']











# serializers.py - Add full_name to MyProfileSerializer
from rest_framework import serializers
from django.utils import timezone
from .models import User, OTPVerification, UserSession, MyProfile

class PhoneNumberSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=20)

    def validate_mobile_number(self, value):
        cleaned = ''.join(filter(str.isdigit, value))
        if len(cleaned) < 8:
            raise serializers.ValidationError("Phone number must have at least 8 digits")
        return value

class RegisterEmailSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=20)
    email = serializers.EmailField()

    def validate(self, data):
        if User.objects.filter(mobile_number=data['mobile_number']).exists():
            raise serializers.ValidationError({"mobile_number": "User with this mobile number already exists"})

        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "User with this email already exists"})

        return data

class VerifyOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            otp_record = OTPVerification.objects.get(
                email=data['email'],
                otp_code=data['otp_code'],
                is_verified=False,
                user__isnull=True
            )

            if not otp_record.is_valid():
                raise serializers.ValidationError({"otp_code": "OTP has expired. Please request a new one."})

            data['otp_record'] = otp_record
            return data

        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError({"otp_code": "Invalid OTP code"})

class LoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=20)

    def validate(self, data):
        try:
            user = User.objects.get(mobile_number=data['mobile_number'])

            if not user.is_active:
                raise serializers.ValidationError({"mobile_number": "Account is deactivated"})

            data['user'] = user
            return data

        except User.DoesNotExist:
            raise serializers.ValidationError({"mobile_number": "No account found with this phone number"})

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'mobile_number', 'email', 'full_name', 'date_joined', 'is_active']
        read_only_fields = ['id', 'date_joined']

# ===================== MY PROFILE SERIALIZERS =====================

class MyProfileSerializer(serializers.ModelSerializer):
    """Serializer for MyProfile model - UPDATED to include user fields"""
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_mobile = serializers.CharField(source='user.mobile_number', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = MyProfile
        fields = [
            'id', 'profile_picture', 'bio', 'location',
            'created_at', 'updated_at',
            'user_full_name', 'user_mobile', 'user_email'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_full_name', 'user_mobile', 'user_email']


class UpdateProfileSerializer(serializers.Serializer):
    """Serializer for updating both User and MyProfile"""
    full_name = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    profile_picture = serializers.CharField(required=False, allow_blank=True)


class UserWithProfileSerializer(serializers.ModelSerializer):
    """Serializer for User with profile data"""
    profile = MyProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'mobile_number', 'email', 'full_name', 'date_joined', 'is_active', 'profile']


