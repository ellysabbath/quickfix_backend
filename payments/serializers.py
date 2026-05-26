# serializers.py

from rest_framework import serializers
from .models import Transaction, PaymentMethod, PaymentStatus

class TransactionSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.SerializerMethodField()
    payment_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'amount', 'payment_method', 'payment_method_display',
            'payment_status', 'payment_status_display', 'phone_number', 'bank_reference',
            'provider_reference', 'created_at', 'completed_at', 'notes'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at', 'completed_at']
    
    def get_payment_method_display(self, obj):
        return dict(PaymentMethod.choices).get(obj.payment_method, obj.payment_method)
    
    def get_payment_status_display(self, obj):
        return dict(PaymentStatus.choices).get(obj.payment_status, obj.payment_status)


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating a payment"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    phone_number = serializers.CharField(max_length=15, required=False)
    booking_id = serializers.IntegerField(required=False)
    service_request_id = serializers.IntegerField(required=False)


class ManualPaymentSerializer(serializers.Serializer):
    """Serializer for manual payment submission"""
    transaction_id = serializers.CharField()
    bank_reference = serializers.CharField()
    payment_proof = serializers.FileField(required=False)
    notes = serializers.CharField(required=False)


class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for checking payment status"""
    transaction_id = serializers.CharField()


class PaymentWebhookSerializer(serializers.Serializer):
    """Serializer for incoming webhooks"""
    transaction_id = serializers.CharField(required=False)
    checkout_request_id = serializers.CharField(required=False)
    merchant_request_id = serializers.CharField(required=False)
    result_code = serializers.IntegerField()
    result_desc = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    phone_number = serializers.CharField(required=False)