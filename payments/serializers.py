# payments/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import PaymentMethod, PaymentRecord, BankDetails, PaymentNotification
from registration.models import CustomerServiceRequest


class CustomerServiceRequestSerializer(serializers.ModelSerializer):
    """Serializer for CustomerServiceRequest from registration app"""
    
    class Meta:
        model = CustomerServiceRequest
        fields = [
            'id', 'request_code', 'customer_name', 'customer_phone',
            'customer_email', 'requested_service', 'request_description',
            'vehicle_brand', 'vehicle_model', 'vehicle_year',
            'license_plate', 'service_location', 'location_maps_link',
            'location_latitude', 'location_longitude',
            'preferred_service_date', 'preferred_service_time',
            'formatted_date', 'formatted_time',
            'request_urgency', 'urgency_display', 'is_urgent_request',
            'budget_minimum', 'budget_maximum', 'is_budget_flexible',
            'request_status', 'request_status_display',
            'customer_notes', 'request_created', 'request_updated',
            'approved_by', 'approved_at', 'fixed_by', 'fixed_at', 'updated_by'
        ]
        read_only_fields = ['request_code', 'request_created', 'request_updated']


class BankDetailsSerializer(serializers.ModelSerializer):
    """Serializer for BankDetails"""
    
    class Meta:
        model = BankDetails
        fields = [
            'id', 'bank_name', 'account_name', 'account_number',
            'branch', 'swift_code', 'is_active'
        ]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod - matches frontend interface"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'icon', 'color', 'description',
            'api_method', 'is_active', 'transaction_info',
            'created_at', 'updated_at'
        ]


class PaymentRecordSerializer(serializers.ModelSerializer):
    """Serializer for PaymentRecord - matches frontend interface"""
    
    # Get fields from CustomerServiceRequest
    request_code = serializers.CharField(
        source='service_request.request_code',
        read_only=True,
        allow_null=True
    )
    customer_name = serializers.CharField(
        source='service_request.customer_name',
        read_only=True,
        allow_null=True
    )
    customer_phone = serializers.CharField(
        source='service_request.customer_phone',
        read_only=True,
        allow_null=True
    )
    payment_method_name = serializers.SerializerMethodField()
    amount_formatted = serializers.SerializerMethodField()
    screenshot_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentRecord
        fields = [
            'id', 'payment_id', 'service_request', 'request_code',
            'customer_name', 'customer_phone',
            'payment_method', 'payment_method_name',
            'sender_name', 'sender_phone', 'sender_email', 'sender_account',
            'receiver_name', 'receiver_phone', 'receiver_account',
            'amount', 'amount_formatted',
            'transaction_reference', 'transaction_id',
            'screenshot_base64', 'screenshot_filename', 'screenshot_content_type',
            'screenshot_url', 'proof_uri', 'proof_filename',
            'status', 'status_display',
            'created_at', 'updated_at', 'confirmed_at', 'verified_at'
        ]
        read_only_fields = [
            'payment_id', 'created_at', 'updated_at', 'confirmed_at', 'verified_at',
            'status_display', 'request_code', 'customer_name', 'customer_phone'
        ]
    
    def get_payment_method_name(self, obj):
        method_names = {
            'mpesa': 'Lipa Na M-Pesa',
            'tigo_pesa': 'Tigo Pesa',
            'airtel_money': 'Airtel Money',
            'halo_pesa': 'Halo Pesa',
            'manual': 'Manual Payment',
        }
        return method_names.get(obj.payment_method, obj.payment_method)
    
    def get_amount_formatted(self, obj):
        return f"TZS {obj.amount:,.2f}"
    
    def get_screenshot_url(self, obj):
        return obj.get_screenshot_base64()


class PaymentRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PaymentRecord"""
    
    class Meta:
        model = PaymentRecord
        fields = [
            'service_request', 'payment_method',
            'sender_name', 'sender_phone', 'sender_email', 'sender_account',
            'receiver_name', 'receiver_phone', 'receiver_account',
            'amount', 'transaction_reference', 'transaction_id',
            'screenshot_base64', 'screenshot_filename', 'screenshot_content_type',
            'proof_uri', 'proof_filename'
        ]
        extra_kwargs = {
            'sender_email': {'required': False, 'allow_blank': True, 'allow_null': True},
            'sender_account': {'required': False, 'allow_blank': True, 'allow_null': True},
            'receiver_account': {'required': False, 'allow_blank': True, 'allow_null': True},
            'transaction_reference': {'required': False, 'allow_blank': True, 'allow_null': True},
            'transaction_id': {'required': False, 'allow_blank': True, 'allow_null': True},
            'screenshot_base64': {'required': False, 'allow_blank': True, 'allow_null': True},
            'screenshot_filename': {'required': False, 'allow_blank': True, 'allow_null': True},
            'screenshot_content_type': {'required': False, 'allow_blank': True, 'allow_null': True},
            'proof_uri': {'required': False, 'allow_blank': True, 'allow_null': True},
            'proof_filename': {'required': False, 'allow_blank': True, 'allow_null': True},
        }
    
    def create(self, validated_data):
        # Handle screenshot base64
        screenshot_base64 = validated_data.pop('screenshot_base64', None)
        screenshot_filename = validated_data.pop('screenshot_filename', None)
        screenshot_content_type = validated_data.pop('screenshot_content_type', None)
        
        # Set default receiver info if not provided
        if not validated_data.get('receiver_name'):
            validated_data['receiver_name'] = 'QuickFix Services'
        if not validated_data.get('receiver_phone'):
            validated_data['receiver_phone'] = '+255 742 5786 91'
        
        # Create payment record
        payment = PaymentRecord.objects.create(**validated_data)
        
        # Handle screenshot if provided
        if screenshot_base64:
            payment.set_screenshot_from_base64(
                screenshot_base64,
                screenshot_filename,
                screenshot_content_type or 'image/jpeg'
            )
            payment.save()
        
        return payment


class PaymentRecordUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating PaymentRecord"""
    
    class Meta:
        model = PaymentRecord
        fields = [
            'transaction_reference', 'transaction_id',
            'screenshot_base64', 'screenshot_filename', 'screenshot_content_type',
            'proof_uri', 'proof_filename',
            'status', 'status_display'
        ]
        extra_kwargs = {
            'transaction_reference': {'required': False, 'allow_blank': True, 'allow_null': True},
            'transaction_id': {'required': False, 'allow_blank': True, 'allow_null': True},
            'screenshot_base64': {'required': False, 'allow_blank': True, 'allow_null': True},
            'screenshot_filename': {'required': False, 'allow_blank': True, 'allow_null': True},
            'screenshot_content_type': {'required': False, 'allow_blank': True, 'allow_null': True},
            'proof_uri': {'required': False, 'allow_blank': True, 'allow_null': True},
            'proof_filename': {'required': False, 'allow_blank': True, 'allow_null': True},
        }
    
    def update(self, instance, validated_data):
        # Handle screenshot base64
        screenshot_base64 = validated_data.pop('screenshot_base64', None)
        screenshot_filename = validated_data.pop('screenshot_filename', None)
        screenshot_content_type = validated_data.pop('screenshot_content_type', None)
        
        # Update status
        if 'status' in validated_data:
            status_value = validated_data['status']
            validated_data['status_display'] = dict(PaymentRecord.STATUS_CHOICES).get(
                status_value, 
                status_value
            )
            if status_value == 'confirmed' and not instance.confirmed_at:
                validated_data['confirmed_at'] = timezone.now()
            elif status_value == 'verified' and not instance.verified_at:
                validated_data['verified_at'] = timezone.now()
        
        # Handle screenshot
        if screenshot_base64:
            instance.set_screenshot_from_base64(
                screenshot_base64,
                screenshot_filename,
                screenshot_content_type or 'image/jpeg'
            )
        
        return super().update(instance, validated_data)