# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import (
    ServiceRequest, ServiceRequestUpdate, 
    ServiceRequestAttachment, ServiceType
)
from users.models import Garage
from django.utils import timezone

User = get_user_model()

class GarageSerializer(serializers.ModelSerializer):
    """Serializer for Garage model (simplified for service requests)"""
    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'city', 'phone', 'email', 'rating', 'is_open']
        read_only_fields = ['id', 'rating']

class ServiceTypeSerializer(serializers.ModelSerializer):
    """Serializer for Service Types"""
    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'description', 'estimated_duration', 'base_price', 'is_active']
        read_only_fields = ['id']

class ServiceRequestAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Service Request Attachments"""
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequestAttachment
        fields = [
            'id', 'file', 'file_url', 'file_type', 'description', 
            'uploaded_by', 'uploaded_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'file_url']
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}"
        return "System"

class ServiceRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for Service Request Updates"""
    updated_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequestUpdate
        fields = [
            'id', 'update_type', 'old_value', 'new_value', 'notes', 
            'updated_by', 'updated_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'updated_by', 'created_at']
    
    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}"
        return "System"

class ServiceRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing service requests (shorter version)"""
    garage_name = serializers.CharField(source='garage.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    user_info_source = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'request_id', 'full_name', 'user_info_source', 'location', 
            'garage', 'garage_name', 'status', 'status_display', 'priority', 
            'priority_display', 'estimated_cost', 'actual_cost', 'created_at', 
            'submitted_at', 'user'
        ]
        read_only_fields = ['id', 'request_id', 'created_at']
    
    def get_full_name(self, obj):
        return obj.full_name()
    
    def get_user_info_source(self, obj):
        return 'User Profile' if obj.user else 'Manual Entry'
        
        
        
        

class CreateServiceRequestSerializer(serializers.ModelSerializer):
    """Serializer for creating new service requests with auto-population"""
    garage_id = serializers.PrimaryKeyRelatedField(
        queryset=Garage.objects.filter(is_active=True, is_open=True),
        write_only=True,
        source='garage',
        required=True
    )
    
    class Meta:
        model = ServiceRequest
        fields = [
            # Personal info (will be auto-populated for logged-in users)
            'first_name', 'last_name', 'middle_name', 'email', 'phone',
            # Location
            'location',
            # Service details
            'garage_id', 'experience',
            # Vehicle info (optional)
            'service_type', 'vehicle_type', 'vehicle_year', 'vehicle_make', 'vehicle_model',
            # Terms
            'agreed_to_terms'
        ]
        extra_kwargs = {
            'experience': {
                'required': True,
                'min_length': 10,
                'error_messages': {
                    'min_length': 'Please provide more details (minimum 10 characters)',
                    'required': 'Please describe your service needs'
                }
            },
            'agreed_to_terms': {
                'required': True,
                'error_messages': {
                    'required': 'You must agree to the terms and conditions'
                }
            },
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
            'phone': {'required': False, 'allow_blank': True},
            'location': {'required': False, 'allow_blank': True},
            'service_type': {'required': False, 'allow_blank': True},
            'vehicle_type': {'required': False, 'allow_blank': True},
            'vehicle_year': {'required': False, 'allow_null': True},
            'vehicle_make': {'required': False, 'allow_blank': True},
            'vehicle_model': {'required': False, 'allow_blank': True},
            'middle_name': {'required': False, 'allow_blank': True},
        }
    
    def validate(self, data):
        """Validate the service request data with user context"""
        request = self.context.get('request')
        user = request.user if request else None
        
        # Check if user is authenticated
        if user and user.is_authenticated:
            # For authenticated users, personal info will be auto-populated
            # So we don't require it in the form data
            pass
        else:
            # For non-authenticated users, require all personal info
            required_fields = ['first_name', 'last_name', 'email', 'phone']
            for field in required_fields:
                field_value = data.get(field)
                if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                    raise serializers.ValidationError({
                        field: "This field is required for non-registered users"
                    })
            
            # Validate email format for non-users
            email = data.get('email', '').strip()
            if email:
                try:
                    validate_email(email)
                except ValidationError:
                    raise serializers.ValidationError({
                        'email': 'Please enter a valid email address'
                    })
        
        # Validate terms agreement
        if not data.get('agreed_to_terms'):
            raise serializers.ValidationError({
                'agreed_to_terms': 'You must agree to the terms and conditions'
            })
        
        # Validate experience length
        experience = data.get('experience', '')
        if len(experience.strip()) < 10:
            raise serializers.ValidationError({
                'experience': 'Please provide more details (minimum 10 characters)'
            })
        
        # Validate garage selection
        if not data.get('garage'):
            raise serializers.ValidationError({
                'garage_id': 'Please select a garage'
            })
        
        return data
    
    def create(self, validated_data):
        """Create a new service request with automatic user data population"""
        request = self.context.get('request')
        user = request.user if request else None
        
        # Extract optional fields
        service_type = validated_data.pop('service_type', '').strip()
        vehicle_type = validated_data.pop('vehicle_type', '').strip()
        vehicle_year = validated_data.pop('vehicle_year', None)
        vehicle_make = validated_data.pop('vehicle_make', '').strip()
        vehicle_model = validated_data.pop('vehicle_model', '').strip()
        
        # If user is authenticated, populate from user profile
        if user and user.is_authenticated:
            # Add user to validated_data
            validated_data['user'] = user
            
            # Populate user data (override any provided data with user profile data)
            validated_data['first_name'] = user.first_name or ''
            validated_data['last_name'] = user.last_name or ''
            validated_data['email'] = user.email or ''
            validated_data['phone'] = user.phone or ''
            
            # Populate location from user profile if available
            if hasattr(user, 'city') and user.city:
                validated_data['city'] = user.city
                if not validated_data.get('location'):
                    validated_data['location'] = user.city
            if hasattr(user, 'state') and user.state:
                validated_data['state'] = user.state
        
        # Set submitted_at timestamp
        validated_data['submitted_at'] = timezone.now()
        
        # Track IP and User Agent if available
        if request:
            validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        # Add optional vehicle fields back
        if service_type:
            validated_data['service_type'] = service_type
        if vehicle_type:
            validated_data['vehicle_type'] = vehicle_type
        if vehicle_year:
            validated_data['vehicle_year'] = vehicle_year
        if vehicle_make:
            validated_data['vehicle_make'] = vehicle_make
        if vehicle_model:
            validated_data['vehicle_model'] = vehicle_model
        
        # Create the service request
        try:
            service_request = ServiceRequest.objects.create(**validated_data)
            
            # Create initial status update
            ServiceRequestUpdate.objects.create(
                service_request=service_request,
                update_type='status_change',
                old_value='',
                new_value='pending',
                notes='Service request submitted'
            )
            
            return service_request
            
        except Exception as e:
            raise serializers.ValidationError({
                'non_field_errors': f'Failed to create service request: {str(e)}'
            })
            
            
            
            
            
            
            
            

class ServiceRequestSerializer(serializers.ModelSerializer):
    """Main serializer for Service Request CRUD operations"""
    # Nested serializers for related objects
    updates = ServiceRequestUpdateSerializer(source='service_updates', many=True, read_only=True)
    attachments = ServiceRequestAttachmentSerializer(source='service_attachments', many=True, read_only=True)
    garage_details = GarageSerializer(source='garage', read_only=True)
    user_details = serializers.SerializerMethodField()
    
    # For write operations
    garage_id = serializers.PrimaryKeyRelatedField(
        queryset=Garage.objects.filter(is_active=True, is_open=True),
        write_only=True,
        source='garage',
        required=False  # Not required for updates
    )
    
    # Computed fields
    full_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    days_since_submission = serializers.SerializerMethodField()
    user_info_source = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            # Basic Info
            'id', 'request_id', 'full_name', 'user_info_source',
            
            # Personal Information
            'first_name', 'middle_name', 'last_name', 'location', 'city', 'state',
            
            # Service Details
            'garage_id', 'garage_details', 'experience',
            'service_type', 'vehicle_type', 'vehicle_year', 
            'vehicle_make', 'vehicle_model',
            
            # Status and Tracking
            'status', 'status_display', 'priority', 'priority_display',
            'estimated_completion_date', 'actual_completion_date',
            
            # Contact Information
            'email', 'phone', 'user', 'user_details',
            
            # Terms
            'agreed_to_terms', 'terms_agreement_date',
            
            # Financial
            'estimated_cost', 'actual_cost', 'quote_approved', 'quote_approved_date',
            
            # Feedback
            'user_rating', 'user_feedback', 'garage_notes',
            
            # Attachments
            'vehicle_photos', 'invoice_document', 'attachments',
            
            # Updates
            'updates',
            
            # Metadata
            'created_at', 'updated_at', 'submitted_at', 'days_since_submission',
            'is_archived', 'requires_follow_up', 'is_emergency',
            'ip_address', 'user_agent'
        ]
        read_only_fields = [
            'id', 'request_id', 'created_at', 'updated_at', 'submitted_at',
            'user', 'garage_details', 'user_details', 'updates', 'attachments',
            'status_display', 'priority_display', 'days_since_submission',
            'user_info_source', 'terms_agreement_date', 'quote_approved_date',
            'ip_address', 'user_agent'
        ]
        extra_kwargs = {
            'experience': {'min_length': 10},
        }
    
    def get_full_name(self, obj):
        return obj.full_name()
    
    def get_user_details(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'email': obj.user.email,
                'first_name': obj.user.first_name,
                'last_name': obj.user.last_name,
                'phone': obj.user.phone,
                'city': obj.user.city,
                'state': obj.user.state,
                'role': obj.user.role
            }
        return None
    
    def get_days_since_submission(self, obj):
        if obj.submitted_at:
            return (timezone.now() - obj.submitted_at).days
        return None
    
    def get_user_info_source(self, obj):
        """Return where the user info came from"""
        return 'User Profile' if obj.user else 'Manual Entry'
    
    def update(self, instance, validated_data):
        """Update a service request with change tracking"""
        # Store old values for tracking
        old_status = instance.status
        old_priority = instance.priority
        
        # Prevent updating user info if user is associated (it should come from user profile)
        if instance.user:
            # Remove user info fields from validated_data as they come from user profile
            for field in ['first_name', 'last_name', 'email', 'phone', 'city', 'state']:
                validated_data.pop(field, None)
        
        # Update the instance
        updated_instance = super().update(instance, validated_data)
        
        # Create update records for significant changes
        request = self.context.get('request')
        user = request.user if request else None
        
        if old_status != updated_instance.status:
            ServiceRequestUpdate.objects.create(
                service_request=updated_instance,
                updated_by=user if user and user.is_authenticated else None,
                update_type='status_change',
                old_value=old_status,
                new_value=updated_instance.status,
                notes=f"Status changed from {old_status} to {updated_instance.status}"
            )
        
        if old_priority != updated_instance.priority:
            ServiceRequestUpdate.objects.create(
                service_request=updated_instance,
                updated_by=user if user and user.is_authenticated else None,
                update_type='priority_change',
                old_value=old_priority,
                new_value=updated_instance.priority,
                notes=f"Priority changed from {old_priority} to {updated_instance.priority}"
            )
        
        return updated_instance

class UpdateServiceRequestStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating service request status only"""
    status = serializers.ChoiceField(choices=ServiceRequest.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = ServiceRequest
        fields = ['status', 'notes']
    
    def update(self, instance, validated_data):
        """Update status with tracking"""
        old_status = instance.status
        new_status = validated_data.get('status')
        notes = validated_data.get('notes', '')
        
        # Update instance
        instance.status = new_status
        instance.save()
        
        # Create update record
        request = self.context.get('request')
        user = request.user if request else None
        
        ServiceRequestUpdate.objects.create(
            service_request=instance,
            updated_by=user if user and user.is_authenticated else None,
            update_type='status_change',
            old_value=old_status,
            new_value=new_status,
            notes=notes or f"Status changed from {old_status} to {new_status}"
        )
        
        return instance