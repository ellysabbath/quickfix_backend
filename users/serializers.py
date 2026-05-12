# users/serializers.py
from rest_framework import serializers
from registration.models import (
    CustomerRequest,
    WorkshopQuote,
    ServiceAppointment,
    AutoWorkshop,
    RepairService
)
from django.utils import timezone
from .models import CustomUser


# ======================= USER SERIALIZERS =======================
class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email', 'phone']


# ======================= WORKSHOP SERIALIZERS =======================
class AutoWorkshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoWorkshop
        fields = ['id', 'workshop_name', 'workshop_email', 'workshop_phone',
                 'workshop_address', 'workshop_city', 'is_workshop_verified']


# ======================= SERVICE SERIALIZERS =======================
class RepairServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairService
        fields = ['id', 'service_title', 'service_description', 'service_category',
                 'service_base_price', 'workshop', 'is_service_active', 'service_created']


# ======================= WORKSHOP QUOTE SERIALIZERS =======================
class WorkshopQuoteSerializer(serializers.ModelSerializer):
    workshop_details = AutoWorkshopSerializer(source='workshop', read_only=True)

    class Meta:
        model = WorkshopQuote
        fields = [
            'id',
            'customer_request',
            'workshop',
            'workshop_details',
            'quoted_price',
            'estimated_duration',
            'workshop_notes',
            'quote_status',
            'quote_created',
        ]
        read_only_fields = ['quote_status', 'quote_created', 'quote_updated']


class WorkshopQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopQuote
        fields = ['quoted_price', 'estimated_duration', 'workshop_notes']

    def validate_quoted_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value


# ======================= CUSTOMER REQUEST SERIALIZERS =======================
class CustomerRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRequest
        fields = [
            'requested_service',
            'request_description',
            'vehicle_brand',
            'vehicle_model',
            'vehicle_year',
            'vehicle_color',
            'license_plate',
            'service_location',
            'location_maps_link',
            'location_latitude',
            'location_longitude',
            'preferred_service_date',
            'preferred_service_time',
            'is_urgent_request',
            'request_urgency',
            'budget_minimum',
            'budget_maximum',
            'is_budget_flexible',
            'customer_notes',
            'preferred_contact',
        ]

    def validate_preferred_service_date(self, value):
        """Validate preferred date is not in the past"""
        if value < timezone.now().date():
            raise serializers.ValidationError("Preferred service date cannot be in the past")
        return value

    def create(self, validated_data):
        # Get the user from the request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['customer'] = request.user
        else:
            raise serializers.ValidationError({"detail": "Authentication required to create service request"})
        return super().create(validated_data)


class CustomerRequestUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating customer requests.
    Limited fields that can be updated to prevent abuse.
    """
    class Meta:
        model = CustomerRequest
        fields = [
            'request_description',
            'preferred_service_date',
            'preferred_service_time',
            'service_location',
            'location_maps_link',
            'location_latitude',
            'location_longitude',
            'budget_minimum',
            'budget_maximum',
            'is_budget_flexible',
            'customer_notes',
            'preferred_contact',
        ]

    def validate_preferred_service_date(self, value):
        """Validate preferred date is not in the past"""
        if value < timezone.now().date():
            raise serializers.ValidationError("Preferred service date cannot be in the past")
        return value

    def validate(self, data):
        """
        Validate that the request can still be updated
        """
        instance = self.instance

        # Check if request is expired
        if instance.is_request_expired():
            raise serializers.ValidationError(
                "Cannot update an expired request"
            )

        # Check if request already has accepted offers
        if instance.request_status in ['accepted', 'completed', 'in_progress']:
            raise serializers.ValidationError(
                f"Cannot update request with status: {instance.get_request_status_display()}"
            )

        return data


class CustomerRequestDetailSerializer(serializers.ModelSerializer):
    customer_info = UserBasicSerializer(source='customer', read_only=True)
    received_quotes = WorkshopQuoteSerializer(many=True, read_only=True)
    quotes_count = serializers.IntegerField(source='received_quotes.count', read_only=True)
    vehicle_details = serializers.SerializerMethodField()
    is_request_expired = serializers.SerializerMethodField()
    can_receive_offers = serializers.SerializerMethodField()
    formatted_budget = serializers.SerializerMethodField()
    formatted_service_date = serializers.SerializerMethodField()
    formatted_service_time = serializers.SerializerMethodField()
    accepted_workshop_info = AutoWorkshopSerializer(source='accepted_workshop', read_only=True)

    class Meta:
        model = CustomerRequest
        fields = [
            'id',
            'request_code',
            'customer_info',
            'requested_service',
            'request_description',
            'vehicle_brand',
            'vehicle_model',
            'vehicle_year',
            'vehicle_color',
            'license_plate',
            'vehicle_details',
            'service_location',
            'location_maps_link',
            'preferred_service_date',
            'formatted_service_date',
            'preferred_service_time',
            'formatted_service_time',
            'is_urgent_request',
            'request_urgency',
            'budget_minimum',
            'budget_maximum',
            'formatted_budget',
            'is_budget_flexible',
            'request_status',
            'times_viewed',
            'received_quotes',
            'quotes_count',
            'accepted_workshop',
            'accepted_workshop_info',
            'offer_accepted_at',
            'customer_notes',
            'preferred_contact',
            'request_expires',
            'is_request_expired',
            'can_receive_offers',
            'request_created',
            'request_updated',
        ]
        read_only_fields = ['request_code', 'request_created', 'request_updated']

    def get_vehicle_details(self, obj):
        return obj.get_vehicle_details()

    def get_is_request_expired(self, obj):
        return obj.is_request_expired()

    def get_can_receive_offers(self, obj):
        return obj.can_receive_offers()

    def get_formatted_budget(self, obj):
        if obj.budget_minimum and obj.budget_maximum:
            return f"TZS {obj.budget_minimum:,.2f} - TZS {obj.budget_maximum:,.2f}"
        elif obj.budget_minimum:
            return f"Min: TZS {obj.budget_minimum:,.2f}"
        elif obj.budget_maximum:
            return f"Max: TZS {obj.budget_maximum:,.2f}"
        return "Negotiable"

    def get_formatted_service_date(self, obj):
        if obj.preferred_service_date:
            return obj.preferred_service_date.strftime('%A, %d %B %Y')
        return None

    def get_formatted_service_time(self, obj):
        if obj.preferred_service_time:
            return obj.preferred_service_time.strftime('%I:%M %p')
        return None


# ======================= SERVICE APPOINTMENT SERIALIZERS =======================
class ServiceAppointmentSerializer(serializers.ModelSerializer):
    request_code = serializers.CharField(source='customer_request.request_code', read_only=True)
    client_info = UserBasicSerializer(source='client', read_only=True)
    workshop_info = AutoWorkshopSerializer(source='service_workshop', read_only=True)

    class Meta:
        model = ServiceAppointment
        fields = [
            'id',
            'appointment_code',
            'customer_request',
            'request_code',
            'accepted_quote',
            'client',
            'client_info',
            'service_workshop',
            'workshop_info',
            'appointment_service',
            'service_details',
            'agreed_price',
            'appointment_vehicle_brand',
            'appointment_vehicle_model',
            'appointment_vehicle_year',
            'appointment_license_plate',
            'appointment_location',
            'appointment_maps_link',
            'appointment_date',
            'appointment_time',
            'appointment_status',
            'appointment_notes',
            'sms_confirmation_sent',
            'sms_confirmation_sent_at',
            'sms_reminder_sent',
            'sms_reminder_sent_at',
            'appointment_created',
            'appointment_updated',
        ]
        read_only_fields = ['appointment_code', 'appointment_created', 'appointment_updated']


class ServiceAppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceAppointment
        fields = ['appointment_notes']

    def create(self, validated_data):
        # Get the request context
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError({"detail": "Request context is required"})

        # Get customer request from URL or request data
        customer_request_id = request.parser_context.get('kwargs', {}).get('pk')
        if customer_request_id:
            try:
                customer_request = CustomerRequest.objects.get(id=customer_request_id)
                validated_data['customer_request'] = customer_request
                validated_data['client'] = customer_request.customer
            except CustomerRequest.DoesNotExist:
                raise serializers.ValidationError({"detail": "Customer request not found"})

        return super().create(validated_data)






# =====================================//UPDATE  STATUS//====================================



# ===========================================//UPDATE  STATUS//=================================
# serializers.py
from rest_framework import serializers
# from .models import CustomerRequest
from django.contrib.auth.models import User

class CustomerReqSerializer(serializers.ModelSerializer):
    vehicle_details = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    can_receive_offers = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source='customer.email', read_only=True)

    class Meta:
        model = CustomerRequest
        fields = [
            'id',
            'request_code',
            'customer',
            'customer_email',
            'requested_service',
            'request_description',
            'vehicle_brand',
            'vehicle_model',
            'vehicle_year',
            'vehicle_color',
            'license_plate',
            'vehicle_details',
            'service_location',
            'location_maps_link',
            'location_latitude',
            'location_longitude',
            'preferred_service_date',
            'preferred_service_time',
            'is_urgent_request',
            'request_urgency',
            'budget_minimum',
            'budget_maximum',
            'is_budget_flexible',
            'request_status',
            'accepted_workshop',
            'offer_accepted_at',
            'times_viewed',
            'customer_notes',
            'preferred_contact',
            'request_expires',
            'request_created',
            'request_updated',
            'is_expired',
            'can_receive_offers'
        ]
        read_only_fields = [
            'request_code',
            'request_created',
            'request_updated',
            'times_viewed',
            'offer_accepted_at'
        ]

    def get_vehicle_details(self, obj):
        return obj.get_vehicle_details()

    def get_is_expired(self, obj):
        return obj.is_request_expired()

    def get_can_receive_offers(self, obj):
        return obj.can_receive_offers()

    def validate_request_status(self, value):
        """Validate status transitions"""
        instance = getattr(self, 'instance', None)
        if instance:
            valid_transitions = {
                'awaiting': ['viewed', 'cancelled', 'expired'],
                'viewed': ['offers_received', 'cancelled', 'expired'],
                'offers_received': ['accepted', 'cancelled', 'expired'],
                'accepted': ['in_progress', 'cancelled'],
                'in_progress': ['completed', 'cancelled'],
                'completed': [],  # terminal state
                'cancelled': [],  # terminal state
                'expired': []     # terminal state
            }

            current_status = instance.request_status
            if value != current_status and value not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from '{current_status}' to '{value}'"
                )
        return value
# ========================================//END   UPDATE  STATUS //=================================
# ===========================================//END  UPDATE STATUS//================================









