# payments/models.py

from django.db import models
from django.conf import settings  # Import settings instead of auth.User
from django.utils import timezone
import uuid

class PaymentMethod(models.TextChoices):
    MPESA = 'mpesa', 'Lipa Na M-Pesa'
    TIGO_PESA = 'tigo_pesa', 'Tigo Pesa'
    AIRTEL_MONEY = 'airtel_money', 'Airtel Money'
    HALO_PESA = 'halo_pesa', 'Halo Pesa'
    MANUAL = 'manual', 'Manual Payment'

class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'

# class Transaction(models.Model):
#     """Main transaction model for payments"""
#     transaction_id = models.CharField(max_length=100, unique=True, editable=False)

#     # Fix: Use settings.AUTH_USER_MODEL instead of auth.User
#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,  # Changed from 'auth.User'
#         on_delete=models.CASCADE,
#         related_name='transactions'
#     )

#     booking_id = models.IntegerField(null=True, blank=True)
#     service_request_id = models.IntegerField(null=True, blank=True)

#     # Payment details
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
#     payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

#     # Mobile money details
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     provider_reference = models.CharField(max_length=100, blank=True, null=True)

#     # Manual payment details
#     bank_reference = models.CharField(max_length=100, blank=True, null=True)
#     payment_proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True)

#     # Timestamps
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     completed_at = models.DateTimeField(blank=True, null=True)

#     # Metadata
#     notes = models.TextField(blank=True, null=True)
#     ip_address = models.GenericIPAddressField(blank=True, null=True)

#     class Meta:
#         ordering = ['-created_at']
#         verbose_name = 'Transaction'
#         verbose_name_plural = 'Transactions'

#     def save(self, *args, **kwargs):
#         if not self.transaction_id:
#             self.transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.transaction_id} - {self.user.username if hasattr(self.user, 'username') else str(self.user)} - {self.amount}"



class Transaction(models.Model):
    """Main transaction model for payments"""
    transaction_id = models.CharField(max_length=100, unique=True, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    booking_id = models.IntegerField(null=True, blank=True)
    service_request_id = models.IntegerField(null=True, blank=True)

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    # Mobile money details
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    provider_reference = models.CharField(max_length=100, blank=True, null=True)

    # Manual payment details
    bank_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    # Metadata
    notes = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

        # Update linked service request budget when payment is completed
        if self.payment_status == PaymentStatus.COMPLETED and self.service_request_id:
            try:
                from your_app.models import CustomerServiceRequest  # Replace 'your_app' with actual app name
                service_request = CustomerServiceRequest.objects.get(id=self.service_request_id)
                if service_request.budget_maximum != self.amount:
                    service_request.budget_maximum = self.amount
                    service_request.save(update_fields=['budget_maximum'])
            except Exception as e:
                print(f"Error updating service request budget: {e}")

    def __str__(self):
        return f"{self.transaction_id} - {self.user.username if hasattr(self.user, 'username') else str(self.user)} - {self.amount}"





class PaymentSession(models.Model):
    """Track payment sessions for STK Push and external payments"""
    session_id = models.CharField(max_length=100, unique=True)
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='session')
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    result_code = models.IntegerField(blank=True, null=True)
    result_desc = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.session_id


class PaymentWebhook(models.Model):
    """Store incoming payment webhooks from telcos"""
    webhook_id = models.CharField(max_length=100, unique=True, editable=False)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-received_at']

    def save(self, *args, **kwargs):
        if not self.webhook_id:
            self.webhook_id = f"WH-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.webhook_id} - Processed: {self.processed}"