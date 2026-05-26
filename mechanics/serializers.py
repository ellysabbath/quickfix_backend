# mechanics/serializers.py - COMPLETE CORRECTED VERSION

from rest_framework import serializers
from .models import (
    ServiceRequest, ServiceRequestUpdate,
    ServiceRequestNote, ServiceType
)


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating service requests"""

    class Meta:
        model = ServiceRequest
        fields = [
            'first_name', 'last_name', 'middle_name', 'email', 'phone',
            'location', 'city', 'state', 'address', 'experience',
            'service_type', 'vehicle_type', 'vehicle_year', 'vehicle_make',
            'vehicle_model', 'license_plate', 'priority', 'is_emergency',
            'garage_name', 'garage_phone', 'garage_email',
            'agreed_to_terms', 'profile_picture',
        ]

    def validate(self, data):
        if not data.get('agreed_to_terms'):
            raise serializers.ValidationError({
                "agreed_to_terms": "You must agree to the terms and conditions"
            })
        
        if len(data.get('experience', '').strip()) < 10:
            raise serializers.ValidationError({
                "experience": "Experience description must be at least 10 characters"
            })
        
        return data


class ServiceRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating service requests (admin/garage use)"""

    class Meta:
        model = ServiceRequest
        fields = [
            'status', 'priority', 'estimated_cost', 'actual_cost',
            'estimated_completion_date', 'garage_notes', 'quote_approved',
            'user_rating', 'user_feedback', 'garage_name', 'garage_phone', 'garage_email'
        ]

    def validate_status(self, value):
        valid_statuses = ['pending', 'received', 'in_progress', 'completed', 'cancelled', 'rejected']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Choose from: {', '.join(valid_statuses)}"
            )
        return value

    def validate_user_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class ServiceRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for service requests"""
    request_code = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    garage_name_display = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = '__all__'

    def get_request_code(self, obj):
        return obj.get_request_code()

    def get_full_name(self, obj):
        return obj.full_name()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_priority_display(self, obj):
        return obj.get_priority_display()

    def get_garage_name_display(self, obj):
        return obj.garage_name or 'Not assigned'


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """List serializer for service requests"""
    request_code = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'request_code', 'full_name', 'email', 'phone', 'location',
            'service_type', 'status', 'status_display', 'priority', 'priority_display',
            'created_at', 'submitted_at', 'garage_name', 'is_emergency', 'experience'
        ]

    def get_request_code(self, obj):
        return obj.get_request_code()

    def get_full_name(self, obj):
        return obj.full_name()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_priority_display(self, obj):
        return obj.get_priority_display()


class ServiceRequestUpdateHistorySerializer(serializers.ModelSerializer):
    """Serializer for update history"""
    update_type_display = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequestUpdate
        fields = '__all__'

    def get_update_type_display(self, obj):
        return obj.get_update_type_display()

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return 'System'

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d %B %Y, %I:%M %p')


class ServiceRequestNoteSerializer(serializers.ModelSerializer):
    """Serializer for notes"""
    author_name = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequestNote
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return 'System'

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d %B %Y, %I:%M %p')


class ServiceTypeSerializer(serializers.ModelSerializer):
    """Serializer for service types"""

    class Meta:
        model = ServiceType
        fields = '__all__'