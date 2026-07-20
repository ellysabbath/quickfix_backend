# payments/models.py

from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
import base64

# Import the CustomerServiceRequest from registration app
from registration.models import CustomerServiceRequest

# ============================================================================
# SERVICE REQUEST MODEL - Using the existing model from registration
# ============================================================================

# We'll use the CustomerServiceRequest from registration app directly
# No need to redefine ServiceRequest here

# ============================================================================
# BANK DETAILS MODEL - Matches frontend BankDetails interface
# ============================================================================

class BankDetails(models.Model):
    """
    Model for bank details - matches frontend BankDetails interface
    """
    bank_name = models.CharField(max_length=100, default='CRDB Bank PLC')
    account_name = models.CharField(max_length=200, default='QuickFix Services')
    account_number = models.CharField(max_length=50, default='01-1234567890')
    branch = models.CharField(max_length=100, default='Kariakoo Branch')
    swift_code = models.CharField(max_length=20, default='CORUTZTZ')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Bank Details"
        verbose_name_plural = "Bank Details"
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_name}"


# ============================================================================
# PAYMENT METHOD MODEL - Matches frontend PaymentMethod interface
# ============================================================================

class PaymentMethod(models.Model):
    """
    Model for payment methods - matches frontend PaymentMethod interface
    """
    METHOD_TYPES = [
        ('mpesa', 'M-Pesa'),
        ('tigo_pesa', 'Tigo Pesa'),
        ('airtel_money', 'Airtel Money'),
        ('halo_pesa', 'Halo Pesa'),
        ('manual', 'Manual Payment'),
    ]
    
    # Primary key is the method ID (e.g., 'mpesa', 'tigo_pesa')
    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default='#4CAF50')
    description = models.TextField()
    api_method = models.CharField(max_length=50, default='mpesa')
    is_active = models.BooleanField(default=True)
    
    # Transaction info as JSON - matches frontend transactionInfo
    transaction_info = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
    
    def __str__(self):
        return self.name


# ============================================================================
# PAYMENT RECORD MODEL - References CustomerServiceRequest from registration
# ============================================================================

class PaymentRecord(models.Model):
    """
    Model for payment records - references CustomerServiceRequest from registration app
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('verified', 'Verified'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # ===== Payment Identification =====
    id = models.AutoField(primary_key=True)
    payment_id = models.CharField(max_length=50, unique=True, editable=False)
    
    # ===== Relations - Using CustomerServiceRequest from registration =====
    service_request = models.ForeignKey(
        CustomerServiceRequest,  # From registration.models
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    payment_method = models.CharField(max_length=20, default='mpesa')
    
    # ===== Sender Information (matches frontend) =====
    sender_name = models.CharField(max_length=200)
    sender_phone = models.CharField(max_length=20)
    sender_email = models.EmailField(null=True, blank=True)
    sender_account = models.CharField(max_length=50, null=True, blank=True)
    
    # ===== Receiver Information (matches frontend) =====
    receiver_name = models.CharField(max_length=200)
    receiver_phone = models.CharField(max_length=20)
    receiver_account = models.CharField(max_length=50, null=True, blank=True)
    
    # ===== Payment Details =====
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_reference = models.CharField(max_length=100, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    
    # ===== Screenshot (base64) =====
    screenshot_base64 = models.TextField(null=True, blank=True)
    screenshot_filename = models.CharField(max_length=255, null=True, blank=True)
    screenshot_content_type = models.CharField(max_length=100, null=True, blank=True)
    
    # ===== Proof (for manual payments) =====
    proof_uri = models.TextField(null=True, blank=True)
    proof_filename = models.CharField(max_length=255, null=True, blank=True)
    
    # ===== Status =====
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_display = models.CharField(max_length=50, null=True, blank=True)
    whatsapp_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    
    # ===== Timestamps =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment Record"
        verbose_name_plural = "Payment Records"
    
    def __str__(self):
        return f"{self.payment_id} - {self.sender_name} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4()).upper()[:8]}"
        if not self.status_display:
            self.status_display = dict(self.STATUS_CHOICES).get(self.status, self.status)
        super().save(*args, **kwargs)
    
    def set_screenshot_from_base64(self, base64_string, filename=None, content_type='image/jpeg'):
        """Set screenshot from base64 string"""
        if base64_string.startswith('data:image'):
            header, base64_data = base64_string.split(',', 1)
            content_type = header.split(';')[0].replace('data:', '')
            self.screenshot_content_type = content_type
            self.screenshot_base64 = base64_data
        else:
            self.screenshot_base64 = base64_string
            self.screenshot_content_type = content_type
        
        if filename:
            self.screenshot_filename = filename
        else:
            self.screenshot_filename = f"screenshot_{int(timezone.now().timestamp())}.jpg"
    
    def get_screenshot_base64(self):
        """Get full base64 data URL"""
        if self.screenshot_base64:
            content_type = self.screenshot_content_type or 'image/jpeg'
            return f"data:{content_type};base64,{self.screenshot_base64}"
        return None
    
    def has_screenshot(self):
        """Check if screenshot exists"""
        return bool(self.screenshot_base64)


# ============================================================================
# PAYMENT NOTIFICATION MODEL
# ============================================================================

class PaymentNotification(models.Model):
    """
    Model for payment notifications
    """
    NOTIFICATION_TYPES = [
        ('payment_initiated', 'Payment Initiated'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('payment_verified', 'Payment Verified'),
        ('payment_completed', 'Payment Completed'),
        ('payment_failed', 'Payment Failed'),
        ('status_update', 'Status Update'),
    ]
    
    payment_record = models.ForeignKey(
        PaymentRecord,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    email_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment Notification"
        verbose_name_plural = "Payment Notifications"
    
    def __str__(self):
        return f"{self.payment_record.payment_id} - {self.notification_type}"