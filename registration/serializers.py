# registration/serializers.py
from rest_framework import serializers
from users.models import CustomUser

class PersonalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name']

class ContactDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'phone']
    
    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            user = CustomUser.objects.get(email=value)
            if user.registration_stage >= 4:
                raise serializers.ValidationError("Email already registered")
        return value

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

class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    # Remove the source parameter since it matches the property name
    is_admin = serializers.BooleanField(read_only=True)
    is_mechanic = serializers.BooleanField(read_only=True)
    is_garage_owner = serializers.BooleanField(read_only=True)
    is_customer = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name', 
            'role', 'role_display', 'city', 'state', 
            'registration_stage', 'is_email_verified', 'is_phone_verified',
            'is_active', 'date_joined',
            'is_admin', 'is_mechanic', 'is_garage_owner', 'is_customer',
            'personal_info_completed_at', 'contact_details_completed_at',
            'location_completed_at', 'security_completed_at'
        ]
        read_only_fields = [
            'id', 'registration_stage', 'is_email_verified', 'is_phone_verified',
            'date_joined', 'is_admin', 'is_mechanic', 'is_garage_owner', 'is_customer'
        ]


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
            'email', 'password', 'password2', 
            'first_name', 'last_name', 'phone', 'role',
            'city', 'state', 'is_active'
        ]
        extra_kwargs = {
            'role': {'required': False},
            'is_active': {'required': False, 'default': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Check if email already exists
        email = attrs.get('email')
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        
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

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'role',
            'city', 'state', 'is_active', 'is_email_verified',
            'is_phone_verified', 'registration_stage'
        ]
        read_only_fields = ['email']  # Email shouldn't be changed via update
    
    def validate_email(self, value):
        # Check if email already exists (except for current user)
        user = self.instance
        if CustomUser.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

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






# serializers.py
from rest_framework import serializers
from users.models import Booking, Service, Garage, GarageService, User
from django.contrib.auth import get_user_model

User = get_user_model()

class BookingSerializer(serializers.ModelSerializer):
    # Read-only fields for related objects
    garage_name = serializers.CharField(source='garage.name', read_only=True)
    garage_address = serializers.CharField(source='garage.address', read_only=True)
    garage_phone = serializers.CharField(source='garage.phone', read_only=True)
    garage_city = serializers.CharField(source='garage.city', read_only=True)
    
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category', read_only=True)
    service_description = serializers.CharField(source='service.description', read_only=True)
    service_icon = serializers.CharField(source='service.icon', read_only=True)
    service_color = serializers.CharField(source='service.color', read_only=True)
    service_base_price = serializers.DecimalField(source='service.base_price', max_digits=10, decimal_places=2, read_only=True)
    
    # Write-only fields for creating/updating
    garage_id = serializers.PrimaryKeyRelatedField(
        queryset=Garage.objects.all(),
        source='garage',
        write_only=True,
        required=True
    )
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='service',
        write_only=True,
        required=True
    )
    
    # Price fields (auto-calculated)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, read_only=True)
    
    # Formatted date fields
    scheduled_date_formatted = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            # Basic fields
            'id', 'booking_number',
            
            # Customer info
            'full_name', 'mobile_number',
            
            # Garage info
            'garage_id', 'garage_name', 'garage_address', 'garage_phone', 'garage_city',
            
            # Service info
            'service_id', 'service_name', 'service_category', 'service_description',
            'service_icon', 'service_color', 'service_base_price',
            
            # Price info
            'price', 'total_price',
            
            # Location info
            'location', 'google_maps_link',
            
            # Booking details
            'scheduled_date', 'scheduled_date_formatted', 'notes',
            
            # Timestamps
            'created_at', 'created_at_formatted', 'updated_at'
        ]
        read_only_fields = ['booking_number', 'price', 'total_price', 'created_at', 'updated_at']
    
    def get_scheduled_date_formatted(self, obj):
        """Format scheduled date for display"""
        return obj.scheduled_date.strftime('%Y-%m-%d %H:%M') if obj.scheduled_date else None
    
    def get_created_at_formatted(self, obj):
        """Format created_at date for display"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else None
    
    def create(self, validated_data):
        """
        Create booking with auto-calculation of prices from service
        """
        # Auto-set full name if not provided
        if not validated_data.get('full_name') and validated_data.get('garage'):
            garage = validated_data['garage']
            if garage.owner:
                user = garage.owner
                validated_data['full_name'] = f"{user.first_name} {user.last_name}".strip() or user.username
        
        # Auto-set price from service
        if 'service' in validated_data:
            service = validated_data['service']
            validated_data['price'] = service.base_price
            validated_data['total_price'] = service.base_price
        
        return super().create(validated_data)  # REMOVED EXTRA COMMA
    
    def update(self, instance, validated_data):
        """
        Update booking - auto-update prices if service changes
        """
        # Update price if service changed
        if 'service' in validated_data:
            service = validated_data['service']
            validated_data['price'] = service.base_price
            validated_data['total_price'] = service.base_price
        
        return super().update(instance, validated_data)

class BookingCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating bookings"""
    garage_id = serializers.IntegerField(write_only=True, required=True)
    service_id = serializers.IntegerField(write_only=True, required=True)
    
    class Meta:
        model = Booking
        fields = [
            'garage_id',
            'service_id',
            'full_name',
            'mobile_number',
            'location',
            'google_maps_link',
            'scheduled_date',
            'notes'
        ]
    
    def create(self, validated_data):
        # Get garage and service objects
        garage_id = validated_data.pop('garage_id')
        service_id = validated_data.pop('service_id')
        
        try:
            garage = Garage.objects.get(id=garage_id)
            service = Service.objects.get(id=service_id)
        except (Garage.DoesNotExist, Service.DoesNotExist) as e:
            raise serializers.ValidationError(f"Invalid garage or service ID: {str(e)}")
        
        # Auto-set prices from service
        validated_data['garage'] = garage
        validated_data['service'] = service
        validated_data['price'] = service.base_price
        validated_data['total_price'] = service.base_price
        
        # Auto-set full name if not provided
        if not validated_data.get('full_name') and garage.owner:
            user = garage.owner
            validated_data['full_name'] = f"{user.first_name} {user.last_name}".strip() or user.username
        
        return super().create(validated_data)  # REMOVED EXTRA COMMA