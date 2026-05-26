# registration/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import (
    AutoWorkshop, RepairService,CustomerServiceRequest,
    WorkshopQuote, ServiceAppointment, Approve
)
from django.contrib.auth import get_user_model

User = get_user_model()


class AutoWorkshopSerializer(serializers.ModelSerializer):
    workshop_owner_name = serializers.SerializerMethodField()
    workshop_owner_phone = serializers.SerializerMethodField()

    class Meta:
        model = AutoWorkshop
        fields = '__all__'
        read_only_fields = ['id', 'workshop_created', 'workshop_updated']

    def get_workshop_owner_name(self, obj):
        if obj.workshop_owner:
            return obj.workshop_owner.get_full_name() or obj.workshop_owner.mobile_number
        return None

    def get_workshop_owner_phone(self, obj):
        if obj.workshop_owner:
            return obj.workshop_owner.mobile_number
        return None


class RepairServiceSerializer(serializers.ModelSerializer):
    workshop_name = serializers.SerializerMethodField()

    class Meta:
        model = RepairService
        fields = '__all__'
        read_only_fields = ['id', 'service_created']

    def get_workshop_name(self, obj):
        return obj.workshop.workshop_name if obj.workshop else "All Workshops"


# registration/serializers.py - Add this serializer

# class CustomerServiceRequestSerializer(serializers.ModelSerializer):
#     """Serializer for public customer service requests (no auth)"""
#     vehicle_details = serializers.SerializerMethodField()
#     request_status_display = serializers.SerializerMethodField()
#     urgency_display = serializers.SerializerMethodField()
#     formatted_date = serializers.SerializerMethodField()
#     formatted_time = serializers.SerializerMethodField()

#     class Meta:
#         model = CustomerServiceRequest
#         fields = [
#             'id', 'request_code', 'customer_name', 'customer_phone', 'customer_email',
#             'requested_service', 'request_description', 'vehicle_brand', 'vehicle_model',
#             'vehicle_year', 'vehicle_color', 'license_plate', 'vehicle_details',
#             'service_location', 'location_maps_link', 'location_latitude', 'location_longitude',
#             'preferred_service_date', 'preferred_service_time', 'formatted_date', 'formatted_time',
#             'request_urgency', 'urgency_display', 'is_urgent_request',
#             'budget_minimum', 'budget_maximum', 'is_budget_flexible',
#             'request_status', 'request_status_display', 'customer_notes',
#             'request_created', 'request_updated'
#         ]
#         read_only_fields = ['id', 'request_code', 'request_created', 'request_updated', 'request_status']

#     def get_vehicle_details(self, obj):
#         return obj.get_vehicle_details()

#     def get_request_status_display(self, obj):
#         return dict(CustomerServiceRequest.REQUEST_STATUS).get(obj.request_status, obj.request_status)

#     def get_urgency_display(self, obj):
#         return dict(CustomerServiceRequest.URGENCY_LEVELS).get(obj.request_urgency, obj.request_urgency)

#     def get_formatted_date(self, obj):
#         return obj.preferred_service_date.strftime('%d %B %Y') if obj.preferred_service_date else None

#     def get_formatted_time(self, obj):
#         return obj.preferred_service_time.strftime('%I:%M %p') if obj.preferred_service_time else None






# registration/serializers.py - UPDATE the CustomerServiceRequestSerializer

class CustomerServiceRequestSerializer(serializers.ModelSerializer):
    """Serializer for public customer service requests (no auth)"""
    vehicle_details = serializers.SerializerMethodField()
    request_status_display = serializers.SerializerMethodField()
    urgency_display = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()

    class Meta:
        model = CustomerServiceRequest
        fields = [
            'id', 'request_code', 'customer_name', 'customer_phone', 'customer_email',
            'requested_service', 'request_description', 'vehicle_brand', 'vehicle_model',
            'vehicle_year', 'vehicle_color', 'license_plate', 'vehicle_details',
            'service_location', 'location_maps_link', 'location_latitude', 'location_longitude',
            'preferred_service_date', 'preferred_service_time', 'formatted_date', 'formatted_time',
            'request_urgency', 'urgency_display', 'is_urgent_request',
            'budget_minimum', 'budget_maximum', 'is_budget_flexible',
            'request_status', 'request_status_display', 'customer_notes',
            'request_created', 'request_updated', 'approved_by', 'approved_at',
            'fixed_by', 'fixed_at', 'updated_by'
        ]
        # REMOVE 'request_status' from read_only_fields to make it writable
        read_only_fields = ['id', 'request_code', 'request_created', 'request_updated']

    def get_vehicle_details(self, obj):
        return obj.get_vehicle_details()

    def get_request_status_display(self, obj):
        return dict(CustomerServiceRequest.REQUEST_STATUS).get(obj.request_status, obj.request_status)

    def get_urgency_display(self, obj):
        return dict(CustomerServiceRequest.URGENCY_LEVELS).get(obj.request_urgency, obj.request_urgency)

    def get_formatted_date(self, obj):
        return obj.preferred_service_date.strftime('%d %B %Y') if obj.preferred_service_date else None

    def get_formatted_time(self, obj):
        return obj.preferred_service_time.strftime('%I:%M %p') if obj.preferred_service_time else None


class CustomerServiceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating public customer service requests"""

    class Meta:
        model = CustomerServiceRequest
        fields = [
            'customer_name', 'customer_phone', 'customer_email',
            'requested_service', 'request_description',
            'vehicle_brand', 'vehicle_model', 'vehicle_year', 'vehicle_color', 'license_plate',
            'service_location', 'location_maps_link', 'location_latitude', 'location_longitude',
            'preferred_service_date', 'preferred_service_time',
            'request_urgency', 'budget_minimum', 'budget_maximum', 'is_budget_flexible',
            'customer_notes'
        ]

    def validate_customer_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Customer name is required")
        return value.strip()

    def validate_customer_phone(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Phone number is required")
        # Basic phone validation
        cleaned = ''.join(filter(str.isdigit, value))
        if len(cleaned) < 8:
            raise serializers.ValidationError("Please enter a valid phone number")
        return value.strip()

    def validate_preferred_service_date(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Preferred date cannot be in the past")
        return value

    def validate_requested_service(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Please specify the service you need")
        return value.strip()

    def validate_service_location(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Service location is required")
        return value.strip()




class WorkshopQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopQuote
        fields = ['customer_request', 'workshop', 'quoted_price', 'estimated_duration', 'workshop_notes']

    def validate_quoted_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quoted price must be greater than 0")
        return value


class WorkshopQuoteSerializer(serializers.ModelSerializer):
    workshop_name = serializers.SerializerMethodField()
    workshop_phone = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    quote_status_display = serializers.SerializerMethodField()

    class Meta:
        model = WorkshopQuote
        fields = '__all__'
        read_only_fields = ['id', 'quote_created', 'quote_updated']

    def get_workshop_name(self, obj):
        return obj.workshop.workshop_name

    def get_workshop_phone(self, obj):
        return obj.workshop.workshop_phone

    def get_customer_name(self, obj):
        return obj.customer_request.customer.get_full_name() or obj.customer_request.customer.mobile_number

    def get_customer_phone(self, obj):
        return obj.customer_request.customer.mobile_number

    def get_quote_status_display(self, obj):
        return dict(WorkshopQuote.QUOTE_STATUS).get(obj.quote_status, obj.quote_status)


class ServiceAppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.SerializerMethodField()
    workshop_name = serializers.SerializerMethodField()
    workshop_phone = serializers.SerializerMethodField()
    appointment_status_display = serializers.SerializerMethodField()
    vehicle_info = serializers.SerializerMethodField()
    is_today = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()

    class Meta:
        model = ServiceAppointment
        fields = '__all__'
        read_only_fields = ['id', 'appointment_code', 'appointment_created', 'appointment_updated']

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.mobile_number

    def get_client_phone(self, obj):
        return obj.client.mobile_number

    def get_workshop_name(self, obj):
        return obj.service_workshop.workshop_name

    def get_workshop_phone(self, obj):
        return obj.service_workshop.workshop_phone

    def get_appointment_status_display(self, obj):
        return dict(ServiceAppointment.APPOINTMENT_STATUS).get(obj.appointment_status, obj.appointment_status)

    def get_vehicle_info(self, obj):
        parts = []
        if obj.appointment_vehicle_brand: parts.append(obj.appointment_vehicle_brand)
        if obj.appointment_vehicle_model: parts.append(obj.appointment_vehicle_model)
        if obj.appointment_vehicle_year: parts.append(obj.appointment_vehicle_year)
        if obj.appointment_license_plate: parts.append(f"({obj.appointment_license_plate})")
        return " ".join(parts) if parts else "Not specified"

    def get_is_today(self, obj):
        return obj.appointment_date == timezone.now().date()

    def get_formatted_date(self, obj):
        return obj.appointment_date.strftime('%d %B %Y')

    def get_formatted_time(self, obj):
        return obj.appointment_time.strftime('%I:%M %p')


class ApproveSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Approve
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d %B %Y, %I:%M %p')







# =====================// FIX PROVIDERS//============================
# workshop/serializers.py - Add Garage serializers

from rest_framework import serializers
from .models import Garage
from django.utils import timezone


# ======================= GARAGE SERIALIZERS =======================
class GarageSerializer(serializers.ModelSerializer):
    """Serializer for Garage model - Full CRUD access"""

    class Meta:
        model = Garage
        fields = [
            'id', 'name', 'address', 'city', 'phone', 'email',
            'rating', 'rating_count', 'is_open', 'delivery_available',
            'is_verified', 'is_active', 'estimated_time', 'services',
            'latitude', 'longitude', 'opening_hours', 'owner',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_rating(self, value):
        """Validate rating is between 0 and 5"""
        if value is not None and (value < 0 or value > 5):
            raise serializers.ValidationError("Rating must be between 0 and 5")
        return value

    def validate_rating_count(self, value):
        """Validate rating count is non-negative"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Rating count cannot be negative")
        return value

    def validate_phone(self, value):
        """Basic phone validation"""
        if value and len(value) < 8:
            raise serializers.ValidationError("Please enter a valid phone number")
        return value

    def validate_email(self, value):
        """Email validation"""
        if value and '@' not in value:
            raise serializers.ValidationError("Please enter a valid email address")
        return value

    def validate_services(self, value):
        """Ensure services is a list"""
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Services must be a list")
        return value

    def validate_opening_hours(self, value):
        """Ensure opening_hours is a dict"""
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Opening hours must be a JSON object")
        return value


class GarageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Garage"""

    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'city', 'phone', 'email',
            'rating', 'rating_count', 'is_open', 'delivery_available',
            'is_verified', 'is_active', 'estimated_time', 'services',
            'latitude', 'longitude', 'opening_hours', 'owner'
        ]

    def create(self, validated_data):
        """Create garage with default values for missing fields"""
        if 'services' not in validated_data or validated_data['services'] is None:
            validated_data['services'] = []
        if 'opening_hours' not in validated_data or validated_data['opening_hours'] is None:
            validated_data['opening_hours'] = {
                'monday': '9:00 AM - 6:00 PM',
                'tuesday': '9:00 AM - 6:00 PM',
                'wednesday': '9:00 AM - 6:00 PM',
                'thursday': '9:00 AM - 6:00 PM',
                'friday': '9:00 AM - 6:00 PM',
                'saturday': '10:00 AM - 4:00 PM',
                'sunday': 'Closed'
            }
        if 'rating' not in validated_data:
            validated_data['rating'] = 0.00
        if 'rating_count' not in validated_data:
            validated_data['rating_count'] = 0

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update garage with partial data"""
        # Handle partial updates
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ======================= EXISTING SERIALIZERS (Keep your existing ones) =======================
# AutoWorkshopSerializer, RepairServiceSerializer, etc...