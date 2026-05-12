# mechanics/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinLengthValidator
import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError


class ServiceRequest(models.Model):
    """
    Service Request model for mechanics app
    """
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Received by Garage'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]

    # Priority choices
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Unique identifier
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Relationships
    garage = models.ForeignKey(
        'users.Garage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='garage_service_requests',
        help_text="Selected garage from the form"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_service_requests',
        help_text="Registered user (if logged in)"
    )

    # Personal Information
    first_name = models.CharField(max_length=100, blank=True, default='')
    last_name = models.CharField(max_length=100, blank=True, default='')
    middle_name = models.CharField(max_length=100, blank=True, null=True)

    # Location info
    location = models.CharField(max_length=200, blank=True, default='', help_text="City/Location")
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')

    # Service Details
    experience = models.TextField(
        validators=[MinLengthValidator(10)],
        help_text="User's description of their experience and service needs"
    )

    # Service request details - Make them optional
    service_type = models.CharField(max_length=100, blank=True, default='')
    vehicle_type = models.CharField(max_length=100, blank=True, default='')
    vehicle_year = models.IntegerField(null=True, blank=True)
    vehicle_make = models.CharField(max_length=100, blank=True, default='')
    vehicle_model = models.CharField(max_length=100, blank=True, default='')

    # Status and tracking
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    priority = models.CharField(
        max_length=20, 
        choices=PRIORITY_CHOICES, 
        default='medium'
    )
    estimated_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)

    # Contact information
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')

    # Terms agreement
    agreed_to_terms = models.BooleanField(default=False)
    terms_agreement_date = models.DateTimeField(null=True, blank=True)

    # Quote and pricing
    estimated_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    actual_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    quote_approved = models.BooleanField(default=False)
    quote_approved_date = models.DateTimeField(null=True, blank=True)

    # Ratings and feedback
    user_rating = models.IntegerField(null=True, blank=True)
    user_feedback = models.TextField(blank=True, default='')
    garage_notes = models.TextField(blank=True, default='')

    # Attachments
    vehicle_photos = models.JSONField(default=list, blank=True)
    invoice_document = models.FileField(
        upload_to='service_invoices/', 
        null=True, 
        blank=True
    )

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # SMS Tracking Fields
    sms_confirmation_sent = models.BooleanField(default=False)
    sms_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    sms_status_update_sent = models.BooleanField(default=False)
    sms_status_update_sent_at = models.DateTimeField(null=True, blank=True)
    sms_reminder_sent = models.BooleanField(default=False)
    sms_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Email Tracking Fields
    email_confirmation_sent = models.BooleanField(default=False)
    email_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    email_status_update_sent = models.BooleanField(default=False)
    email_status_update_sent_at = models.DateTimeField(null=True, blank=True)

    # Flags
    is_archived = models.BooleanField(default=False)
    requires_follow_up = models.BooleanField(default=False)
    is_emergency = models.BooleanField(default=False)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'mechanics'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['garage', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"

    def clean(self):
        """Validate the model before saving."""
        super().clean()
        
        # Validate that either user is set OR personal info is provided
        if not self.user and (not self.first_name or not self.last_name or not self.email):
            raise ValidationError(
                "For non-registered users, first name, last name, and email are required."
            )
        
        # Validate email format if provided
        if self.email and self.email.strip():
            from django.core.validators import validate_email
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError("Please enter a valid email address.")
        
        # Validate experience length
        if len(self.experience.strip()) < 10:
            raise ValidationError("Experience description must be at least 10 characters.")

    def __str__(self):
        return f"SR-{self.request_id.hex[:8].upper()} - {self.first_name} {self.last_name}"

    def full_name(self):
        """Return full name of the requester."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def populate_from_user(self, user):
        """
        Populate user information from CustomUser model.
        This can be called manually when needed.
        """
        if user:
            # Personal information
            self.first_name = user.first_name or self.first_name
            self.last_name = user.last_name or self.last_name

            # Contact information
            self.email = user.email or self.email
            self.phone = getattr(user, 'phone', '') or self.phone

            # Location information
            if hasattr(user, 'city') and user.city:
                self.city = user.city
                self.location = user.city
            if hasattr(user, 'state') and user.state:
                self.state = user.state

    def get_contact_source(self):
        """Return where the contact info came from."""
        if self.user:
            return 'User Profile'
        return 'Manual Entry'

    def save(self, *args, **kwargs):
        """
        Override save to automatically populate from user and ensure data consistency.
        """
        # If user exists and is set, populate from user profile
        if self.user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(pk=self.user_id)
                self.populate_from_user(user)
            except User.DoesNotExist:
                pass  # User might have been deleted
        
        # Set submitted_at on creation if not set
        if not self.pk and not self.submitted_at:
            self.submitted_at = timezone.now()

        # Set terms agreement date if agreed
        if self.agreed_to_terms and not self.terms_agreement_date:
            self.terms_agreement_date = timezone.now()
        
        # Ensure required fields are not empty
        if not self.experience or len(self.experience.strip()) < 10:
            raise ValidationError("Experience description must be at least 10 characters.")
        
        # Ensure email is valid for non-users
        if not self.user and (not self.email or not self.email.strip()):
            raise ValidationError("Email is required for non-registered users.")
        
        super().save(*args, **kwargs)

    def send_sms_notification(self, action_type, context=None):
        """Send SMS notification for this service request"""
        from utils.africastalking_sms import africastalking_sms
        
        if not self.phone:
            return False
        
        if context is None:
            context = {}
        
        # Prepare SMS templates
        templates = {
            'created': f"✅ Service Request Created\nRequest: SR-{self.request_id.hex[:8].upper()}\nService: {self.service_type}\nWe'll notify you when a garage responds.",
            'status_update': f"📋 Status Update\nRequest: SR-{self.request_id.hex[:8].upper()}\nNew Status: {self.get_status_display()}\nThank you for choosing QuickFix!",
            'garage_response': f"🔧 Garage Response\nRequest: SR-{self.request_id.hex[:8].upper()}\nA garage has viewed your request. They will contact you soon.",
            'quote_ready': f"💰 Quote Ready\nRequest: SR-{self.request_id.hex[:8].upper()}\nA quote is ready for your review. Login to view.",
        }
        
        message = templates.get(action_type, f"Update for your service request: SR-{self.request_id.hex[:8].upper()}")
        
        result = africastalking_sms.send_sms(
            phone_number=self.phone,
            message=message,
            sender_id='QuickFix'
        )
        
        if result.get('success'):
            # Update tracking field
            if action_type == 'created':
                self.sms_confirmation_sent = True
                self.sms_confirmation_sent_at = timezone.now()
                self.save(update_fields=['sms_confirmation_sent', 'sms_confirmation_sent_at'])
            elif action_type == 'status_update':
                self.sms_status_update_sent = True
                self.sms_status_update_sent_at = timezone.now()
                self.save(update_fields=['sms_status_update_sent', 'sms_status_update_sent_at'])
        
        return result.get('success', False)


class ServiceRequestUpdate(models.Model):
    """Model to track updates/changes to service requests."""
    
    UPDATE_TYPE_CHOICES = [
        ('status_change', 'Status Change'),
        ('priority_change', 'Priority Change'),
        ('quote_provided', 'Quote Provided'),
        ('quote_approved', 'Quote Approved'),
        ('note_added', 'Note Added'),
        ('completion', 'Service Completed'),
        ('cancellation', 'Cancellation'),
        ('assignment', 'Assigned to Staff'),
        ('other', 'Other'),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='service_updates'
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    update_type = models.CharField(
        max_length=50,
        choices=UPDATE_TYPE_CHOICES,
        default='other'
    )

    old_value = models.CharField(max_length=255, default='')
    new_value = models.CharField(max_length=255, default='')

    notes = models.TextField(default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'mechanics'
        ordering = ['-created_at']
        verbose_name = "Service Request Update"
        verbose_name_plural = "Service Request Updates"

    def __str__(self):
        return f"Update #{self.id} for {self.service_request} - {self.get_update_type_display()}"


class ServiceRequestAttachment(models.Model):
    """Model for additional attachments to service requests."""
    
    FILE_TYPE_CHOICES = [
        ('photo', 'Photo'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='service_attachments'
    )

    file = models.FileField(upload_to='service_request_attachments/%Y/%m/%d/')
    file_type = models.CharField(
        max_length=50,
        choices=FILE_TYPE_CHOICES,
        default='document'
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    description = models.CharField(max_length=255, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'mechanics'
        verbose_name = "Service Request Attachment"
        verbose_name_plural = "Service Request Attachments"
        ordering = ['-created_at']

    def __str__(self):
        return f"Attachment: {self.get_file_name()} for {self.service_request}"

    def get_file_name(self):
        """Return just the filename without path."""
        if self.file:
            return self.file.name.split('/')[-1]
        return "No file"


class ServiceType(models.Model):
    """Model for different types of services offered by garages."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(default='')

    garages = models.ManyToManyField(
        'users.Garage',
        related_name='service_types',
        blank=True
    )

    estimated_duration = models.DurationField(null=True, blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'mechanics'
        ordering = ['name']
        verbose_name = "Service Type"
        verbose_name_plural = "Service Types"

    def __str__(self):
        return self.name

    def clean(self):
        """Validate service type."""
        if not self.name:
            raise ValidationError("Service type name is required.")
        
        # Ensure base price is positive if provided
        if self.base_price is not None and self.base_price < 0:
            raise ValidationError("Base price cannot be negative.")


class ServiceRequestNote(models.Model):
    """Additional model for internal notes/comments on service requests."""
    
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='internal_notes'
    )
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_notes'
    )
    
    note = models.TextField()
    is_internal = models.BooleanField(
        default=True,
        help_text="If True, note is visible only to staff/garage"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'mechanics'
        ordering = ['-created_at']
        verbose_name = "Service Request Note"
        verbose_name_plural = "Service Request Notes"
    
    def __str__(self):
        return f"Note by {self.author or 'System'} on {self.service_request}"


# Signal handlers for automatic logging
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=ServiceRequest)
def log_status_change(sender, instance, created, **kwargs):
    """Automatically create an update when status changes."""
    if created:
        # Log creation
        ServiceRequestUpdate.objects.create(
            service_request=instance,
            update_type='status_change',
            old_value='',
            new_value='pending',
            notes='Service request created'
        )
        
        # Send SMS for new request
        if instance.phone:
            instance.send_sms_notification('created')
            
    else:
        # Check if status changed
        try:
            old_instance = ServiceRequest.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='status_change',
                    old_value=old_instance.status,
                    new_value=instance.status,
                    notes=f'Status changed from {old_instance.status} to {instance.status}'
                )
                
                # Send SMS for status change
                if instance.phone:
                    instance.send_sms_notification('status_update', {
                        'old_status': old_instance.status,
                        'new_status': instance.status
                    })
                    
        except ServiceRequest.DoesNotExist:
            pass