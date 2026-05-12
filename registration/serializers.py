# registration/serializers.py
from rest_framework import serializers
from users.models import CustomUser
from django.contrib.auth import get_user_model
User = get_user_model()

# ========================// JWT TOKEN==================
# Add this to users/serializers.py (at the end of the file)

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     """Custom JWT token serializer with additional user data"""

#     def validate(self, attrs):
#         data = super().validate(attrs)

#         # Add custom user data to the token response
#         user = self.user

#         # Add user data to response
#         data.update({
#             'user': {
#                 'id': user.id,
#                 'email': user.email,
#                 'first_name': user.first_name,
#                 'last_name': user.last_name,
#                 'role': user.role,
#                 'is_email_verified': user.is_email_verified,
#                 'is_phone_verified': user.is_phone_verified,
#                 'registration_stage': user.registration_stage,
#                 'is_admin': user.is_admin,
#                 'is_mechanic': user.is_mechanic,
#                 'is_garage_owner': user.is_garage_owner,
#                 'is_customer': user.is_customer,
#             }
#         })

#         return data



















# =====================================//CUSTOM//=============================================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that works with email/phone login"""

    username_field = 'identifier'  # Change from default 'username'

    def validate(self, attrs):
        # Get identifier from request
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        # Validate identifier
        is_valid, error_message, identifier_type = validate_identifier(identifier)
        if not is_valid:
            raise serializers.ValidationError({'identifier': error_message})

        # Find user by identifier
        user = find_user_by_identifier(identifier)

        if not user:
            raise serializers.ValidationError({
                'identifier': 'No account found with this email or phone number'
            })

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError({
                'identifier': 'This account has been deactivated'
            })

        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': 'Incorrect password'
            })

        # Set user attribute for token generation
        self.user = user

        # Generate tokens
        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        # Add user data to response
        data.update({
            'user': {
                'id': user.id,
                'email': user.email,
                'phone': user.phone,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'role': user.role,
                'is_email_verified': user.is_email_verified,
                'is_phone_verified': user.is_phone_verified,
                'registration_stage': user.registration_stage,
                'registration_method': user.registration_method,
                'is_admin': user.is_admin,
                'is_mechanic': user.is_mechanic,
                'is_garage_owner': user.is_garage_owner,
                'is_customer': user.is_customer,
            }
        })

        return data
# ====================================================//CUSTOM SERIALIZER//=============================================
























# ===========================//END JWT TOKEN//===============================

class PersonalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name']





# class ContactDetailsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ['email', 'phone']

#     def validate_email(self, value):
#         if CustomUser.objects.filter(email=value).exists():
#             user = CustomUser.objects.get(email=value)
#             if user.registration_stage >= 4:
#                 raise serializers.ValidationError("Email already registered")
#         return value





# ==================================//CUSTOM SERIALIZERS//================================
class ContactDetailsSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'phone']

    def validate(self, data):
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()

        # At least one must be provided
        if not email and not phone:
            raise serializers.ValidationError(
                "Either email or phone number must be provided"
            )

        # Validate email if provided
        if email:
            from .utils import is_email
            if not is_email(email):
                raise serializers.ValidationError({
                    "email": "Please enter a valid email address"
                })

            # Check if email already exists
            if CustomUser.objects.filter(email__iexact=email).exists():
                user = CustomUser.objects.get(email__iexact=email)
                if user.registration_stage >= 4:
                    raise serializers.ValidationError({
                        "email": "This email is already registered"
                    })

        # Validate phone if provided
        if phone:
            from .utils import normalize_phone
            normalized_phone = normalize_phone(phone)
            if not normalized_phone:
                raise serializers.ValidationError({
                    "phone": "Please enter a valid phone number"
                })

            # Check if phone already exists
            if CustomUser.objects.filter(phone=normalized_phone).exists():
                user = CustomUser.objects.get(phone=normalized_phone)
                if user.registration_stage >= 4:
                    raise serializers.ValidationError({
                        "phone": "This phone number is already registered"
                    })

            # Update with normalized phone
            data['phone'] = normalized_phone

        return data
# ===========================================//END  VALIDATION   FOR  PHONE//====================

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['city', 'state']

class SecuritySerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data

# class UserSerializer(serializers.ModelSerializer):
#     role_display = serializers.CharField(source='get_role_display', read_only=True)

#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'email', 'phone', 'first_name', 'last_name',
#             'role', 'role_display', 'city', 'state',
#             'registration_stage', 'is_email_verified'
#         ]
#         read_only_fields = ['id', 'registration_stage', 'is_email_verified']



# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

CustomUser = get_user_model()

# class UserSerializer(serializers.ModelSerializer):
#     role_display = serializers.CharField(source='get_role_display', read_only=True)

#     # Remove the source parameter since it matches the property name
#     is_admin = serializers.BooleanField(read_only=True)
#     is_mechanic = serializers.BooleanField(read_only=True)
#     is_garage_owner = serializers.BooleanField(read_only=True)
#     is_customer = serializers.BooleanField(read_only=True)

#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'email', 'phone', 'first_name', 'last_name',
#             'role', 'role_display', 'city', 'state',
#             'registration_stage', 'is_email_verified', 'is_phone_verified',
#             'is_active', 'date_joined',
#             'is_admin', 'is_mechanic', 'is_garage_owner', 'is_customer',
#             'personal_info_completed_at', 'contact_details_completed_at',
#             'location_completed_at', 'security_completed_at'
#         ]
#         read_only_fields = [
#             'id', 'registration_stage', 'is_email_verified', 'is_phone_verified',
#             'date_joined', 'is_admin', 'is_mechanic', 'is_garage_owner', 'is_customer'
#         ]


# ==============================//USER   SERIALIZER//====================================
class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    username = serializers.SerializerMethodField(read_only=True)

    is_admin = serializers.BooleanField(read_only=True)
    is_mechanic = serializers.BooleanField(read_only=True)
    is_garage_owner = serializers.BooleanField(read_only=True)
    is_customer = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'phone', 'username', 'full_name',
            'first_name', 'last_name', 'role', 'role_display',
            'city', 'state', 'registration_stage',
            'is_email_verified', 'is_phone_verified',
            'registration_method', 'is_active', 'date_joined',
            'is_admin', 'is_mechanic', 'is_garage_owner', 'is_customer',
            'personal_info_completed_at', 'contact_details_completed_at',
            'location_completed_at', 'security_completed_at'
        ]
        read_only_fields = [
            'id', 'registration_stage', 'is_email_verified',
            'is_phone_verified', 'date_joined', 'registration_method',
            'is_admin', 'is_mechanic', 'is_garage_owner', 'is_customer'
        ]

    def get_username(self, obj):
        return obj.username



# class UserCreateSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(
#         write_only=True,
#         required=True,
#         style={'input_type': 'password'},
#         validators=[validate_password]
#     )
#     password2 = serializers.CharField(
#         write_only=True,
#         required=True,
#         style={'input_type': 'password'}
#     )

#     class Meta:
#         model = CustomUser
#         fields = [
#             'email', 'password', 'password2',
#             'first_name', 'last_name', 'phone', 'role',
#             'city', 'state', 'is_active'
#         ]
#         extra_kwargs = {
#             'role': {'required': False},
#             'is_active': {'required': False, 'default': True}
#         }

#     def validate(self, attrs):
#         if attrs['password'] != attrs['password2']:
#             raise serializers.ValidationError({"password": "Password fields didn't match."})

#         # Check if email already exists
#         email = attrs.get('email')
#         if CustomUser.objects.filter(email__iexact=email).exists():
#             raise serializers.ValidationError({"email": "A user with this email already exists."})

#         return attrs

#     def create(self, validated_data):
#         validated_data.pop('password2')
#         password = validated_data.pop('password')

#         # Set default role if not provided
#         if 'role' not in validated_data:
#             validated_data['role'] = 'customer'

#         user = CustomUser.objects.create_user(
#             password=password,
#             **validated_data
#         )
#         return user





# ===============================//WITH   MOBILE  NUMBER//=======================
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'phone', 'password', 'password2',
            'first_name', 'last_name', 'role',
            'city', 'state', 'is_active'
        ]
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
            'phone': {'required': False, 'allow_blank': True},
            'role': {'required': False},
            'is_active': {'required': False, 'default': True}
        }

    def validate(self, attrs):
        email = attrs.get('email', '').strip()
        phone = attrs.get('phone', '').strip()

        # At least one must be provided
        if not email and not phone:
            raise serializers.ValidationError({
                "email": "Either email or phone must be provided",
                "phone": "Either email or phone must be provided"
            })

        # Validate email
        if email:
            from .utils import is_email
            if not is_email(email):
                raise serializers.ValidationError({
                    "email": "Please enter a valid email address"
                })

            # Check if email exists
            if CustomUser.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError({
                    "email": "A user with this email already exists."
                })

        # Validate phone
        if phone:
            from .utils import normalize_phone
            normalized_phone = normalize_phone(phone)
            if not normalized_phone:
                raise serializers.ValidationError({
                    "phone": "Please enter a valid phone number"
                })

            attrs['phone'] = normalized_phone

            # Check if phone exists
            if CustomUser.objects.filter(phone=normalized_phone).exists():
                raise serializers.ValidationError({
                    "phone": "A user with this phone number already exists."
                })

        # Validate passwords
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        # Set default role if not provided
        if 'role' not in validated_data:
            validated_data['role'] = 'customer'

        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )
        return user
# ===============================//END  WITH  MOBILE  NUMBER//===================================

# class UserUpdateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = [
#             'email', 'first_name', 'last_name', 'phone', 'role',
#             'city', 'state', 'is_active', 'is_email_verified',
#             'is_phone_verified', 'registration_stage'
#         ]
#         read_only_fields = ['email']  # Email shouldn't be changed via update





# ============================================// ABOUT  MOBILE  NUMBER//==============================
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'email', 'phone', 'first_name', 'last_name', 'role',
            'city', 'state', 'is_active', 'is_email_verified',
            'is_phone_verified', 'registration_stage'
        ]
        read_only_fields = ['email', 'phone']  # Prevent changing identifiers via update

    def validate(self, data):
        # Ensure at least one identifier remains
        email = data.get('email', self.instance.email if self.instance else None)
        phone = data.get('phone', self.instance.phone if self.instance else None)

        if not email and not phone:
            raise serializers.ValidationError({
                "email": "Either email or phone must be provided",
                "phone": "Either email or phone must be provided"
            })

        return data
# ========================================//ABOUT  WITH  MOBILE  NUMBER//================================

    # def validate_email(self, value):
    #     # Check if email already exists (except for current user)
    #     user = self.instance
    #     if CustomUser.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
    #         raise serializers.ValidationError("A user with this email already exists.")
    #     return value

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs



# =======================// Dashboard //=============
# serializers.py
from rest_framework import serializers
from users.models import Garage, Service, GarageService, ServiceDetail, Booking
from django.contrib.auth import get_user_model




class GarageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Garage
        fields = '__all__'


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
class GarageServiceSerializer(serializers.ModelSerializer):
    garage_name = serializers.CharField(source='garage.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    # Use only ID fields for writing
    garage_id = serializers.PrimaryKeyRelatedField(
        queryset=Garage.objects.all(),
        source='garage',
        write_only=True
    )
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='service',
        write_only=True
    )

    class Meta:
        model = GarageService
        fields = [
            'id', 'price', 'duration', 'description', 'is_available',
            'created_at', 'garage_name', 'service_name', 'garage_id', 'service_id'
        ]
        read_only_fields = ['created_at']
        # Remove 'garage' and 'service' from fields list



class ServiceDetailSerializer(serializers.ModelSerializer):
    garage_name = serializers.ReadOnlyField(source='garage_service.garage.name')
    service_name = serializers.ReadOnlyField(source='garage_service.service.name')

    class Meta:
        model = ServiceDetail
        fields = '__all__'











# ==============================//PHONE NUMBER   FIELD   //===================================
from rest_framework import serializers

import phonenumbers
import re

class PhoneNumberField(serializers.CharField):
    """Custom field for phone number validation"""

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        # Clean the phone number
        phone = re.sub(r'\D', '', data)

        # Try to parse with phonenumbers
        try:
            parsed = phonenumbers.parse(phone, None)
            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError("Please enter a valid phone number.")

            # Format to E.164
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            # Fallback to simple validation
            if not re.match(r'^\+?255?\d{9,15}$', phone):
                raise serializers.ValidationError(
                    "Enter a valid phone number (e.g., +255234567890 or 255234567890)."
                )
            return phone

    def to_representation(self, value):
        # Format for display
        if not value:
            return value

        try:
            parsed = phonenumbers.parse(value, None)
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
        except:
            return value
# ==============================================// END PHONE NUMBER FIELD  //=========================================






# serializers.py
from rest_framework import serializers
from users.models import Booking, Service, Garage, GarageService
from django.contrib.auth import get_user_model



User = get_user_model()
# ======================= BOOKING SERIALIZERS =======================
class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings - user data comes from auth"""

    # These are populated from the authenticated user
    full_name = serializers.CharField(read_only=True)
    mobile_number = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)

    # Required fields for booking
    garage_id = serializers.IntegerField(write_only=True, required=True)
    service_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Booking
        fields = [
            'garage_id', 'service_id',
            'full_name', 'mobile_number', 'email',  # From user
            'location', 'scheduled_date', 'notes',
            'custom_service_name', 'custom_service_price'
        ]
        read_only_fields = ['full_name', 'mobile_number', 'email']

    def validate(self, data):
        """Ensure either service or custom service is provided"""
        if not data.get('service_id') and not data.get('custom_service_name'):
            raise serializers.ValidationError({
                'service_id': 'Select a service or provide custom service name'
            })
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")

        # Add authenticated user
        validated_data['user'] = request.user

        # Get garage
        garage_id = validated_data.pop('garage_id')
        try:
            garage = Garage.objects.get(id=garage_id)
            validated_data['garage'] = garage
        except Garage.DoesNotExist:
            raise serializers.ValidationError({
                'garage_id': f'Garage {garage_id} not found'
            })

        # Get service if provided
        service_id = validated_data.pop('service_id', None)
        if service_id:
            try:
                service = Service.objects.get(id=service_id)
                validated_data['service'] = service
                validated_data['price'] = service.base_price
                validated_data['total_price'] = service.base_price
            except Service.DoesNotExist:
                raise serializers.ValidationError({
                    'service_id': f'Service {service_id} not found'
                })
        elif validated_data.get('custom_service_name'):
            custom_price = validated_data.get('custom_service_price', 0)
            validated_data['price'] = custom_price
            validated_data['total_price'] = custom_price

        # Create booking
        return Booking.objects.create(**validated_data)
# =========================================// SERIALIZERS FOR USER CREATE  BOOKING  //================================





# ===============================//  THE FOLLOWING SERIALIZER  IS  FOR ADMIN  //========================================
class BookingSerializer(serializers.ModelSerializer):
    # User info (read-only)
    full_name = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    # Garage info
    garage_name = serializers.CharField(source='garage.name', read_only=True)
    garage_address = serializers.CharField(source='garage.address', read_only=True)
    garage_phone = serializers.CharField(source='garage.phone', read_only=True)

    # Service info
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category', read_only=True)

    # Status display
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # Formatted dates
    scheduled_date_formatted = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()

    # SMS status
    sms_status = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'user',
            'full_name', 'mobile_number', 'email',
            'garage_id', 'garage_name', 'garage_address', 'garage_phone',
            'service_id', 'service_name', 'service_category',
            'price', 'total_price',
            'location', 'scheduled_date', 'scheduled_date_formatted',
            'notes', 'status', 'status_display',
            'sms_confirmation_sent', 'sms_confirmation_sent_at',
            'sms_reminder_sent', 'sms_reminder_sent_at',
            'last_sms_status', 'sms_status',
            'created_at', 'created_at_formatted',
            'custom_service_name', 'custom_service_price'
        ]
        read_only_fields = ['booking_number', 'created_at', 'user']

    def get_full_name(self, obj):
        """Get user's full name"""
        if obj.user:
            first_name = obj.user.first_name or ""
            last_name = obj.user.last_name or ""
            name = f"{first_name} {last_name}".strip()
            return name if name else "Customer"
        return ""

    def get_mobile_number(self, obj):
        """Get user's phone number - FIXED VERSION"""
        if obj.user:
            # Check if phone field exists and has a value
            if hasattr(obj.user, 'phone') and obj.user.phone:
                # Clean up the phone number
                phone = str(obj.user.phone).strip()
                if phone:
                    return phone
        return ""

    def get_email(self, obj):
        """Get user's email"""
        if obj.user:
            email = obj.user.email
            return email if email else ""
        return ""

    def get_scheduled_date_formatted(self, obj):
        """Format scheduled date"""
        if obj.scheduled_date:
            try:
                # Use the timezone-aware formatting
                from django.utils import timezone
                local_time = timezone.localtime(obj.scheduled_date)
                return local_time.strftime('%Y-%m-%d %H:%M')
            except (AttributeError, ValueError, TypeError):
                # Fallback if there's an error
                try:
                    return obj.scheduled_date.strftime('%Y-%m-%d %H:%M')
                except:
                    return str(obj.scheduled_date)
        return None

    def get_created_at_formatted(self, obj):
        """Format created at date"""
        if obj.created_at:
            try:
                # Use the timezone-aware formatting
                from django.utils import timezone
                local_time = timezone.localtime(obj.created_at)
                return local_time.strftime('%Y-%m-%d %H:%M')
            except (AttributeError, ValueError, TypeError):
                # Fallback if there's an error
                try:
                    return obj.created_at.strftime('%Y-%m-%d %H:%M')
                except:
                    return str(obj.created_at)
        return None

    def get_sms_status(self, obj):
        """Get SMS status information"""
        sms_status = {
            'confirmation_sent': obj.sms_confirmation_sent,
            'reminder_sent': obj.sms_reminder_sent,
            'last_status': obj.last_sms_status or 'not_sent'
        }

        # Format timestamps if available
        if obj.sms_confirmation_sent_at:
            try:
                from django.utils import timezone
                local_time = timezone.localtime(obj.sms_confirmation_sent_at)
                sms_status['confirmation_time'] = local_time.strftime('%Y-%m-%d %H:%M')
            except:
                sms_status['confirmation_time'] = str(obj.sms_confirmation_sent_at)
        else:
            sms_status['confirmation_time'] = None

        if obj.sms_reminder_sent_at:
            try:
                from django.utils import timezone
                local_time = timezone.localtime(obj.sms_reminder_sent_at)
                sms_status['reminder_time'] = local_time.strftime('%Y-%m-%d %H:%M')
            except:
                sms_status['reminder_time'] = str(obj.sms_reminder_sent_at)
        else:
            sms_status['reminder_time'] = None

        return sms_status





# registration/serializers.py
# registration/serializers.py

from rest_framework import serializers
from .models import Approve

class ApproveSerializer(serializers.ModelSerializer):
    formatted_date = serializers.SerializerMethodField()
    has_location = serializers.SerializerMethodField()
    location_coordinates = serializers.SerializerMethodField()

    class Meta:
        model = Approve
        fields = [
            'id',
            'updated_by',
            'phone_number',
            # Location fields
            'latitude',
            'longitude',
            'location_address',
            'location_city',
            'location_country',
            'has_location',
            'location_coordinates',
            # Other fields
            'request_code',
            'appointment_code',
            'previous_status',
            'new_status',
            'notes',
            'created_at',
            'updated_at',
            'formatted_date',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_formatted_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

    def get_has_location(self, obj):
        """Check if location data exists"""
        return bool(obj.latitude and obj.longitude)

    def get_location_coordinates(self, obj):
        """Return location coordinates as a dict"""
        if obj.latitude and obj.longitude:
            return {
                'lat': float(obj.latitude),
                'lng': float(obj.longitude)
            }
        return None