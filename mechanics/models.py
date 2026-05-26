# mechanics/models.py - Complete Rewrite

from django.db import models
from django.conf import settings
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


class ServiceRequest(models.Model):
    """
    Service Request model with complete CRUD operations and email notifications
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

    # Garage information (store directly)
    garage_name = models.CharField(max_length=255, blank=True, default='', help_text="Garage name")
    garage_phone = models.CharField(max_length=20, blank=True, default='', help_text="Garage phone")
    garage_email = models.EmailField(blank=True, default='', help_text="Garage email (will receive notifications)")
    profile_picture = models.TextField(
        null=True,
        blank=True,
        help_text='Base64 or URL of profile picture'
    )
    
    # User relationship (FK to auth user)
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
    address = models.TextField(blank=True, default='', help_text="Full address")

    # Service Details
    experience = models.TextField(
        validators=[MinLengthValidator(10)],
        help_text="User's description of their experience and service needs"
    )

    # Service request details
    service_type = models.CharField(max_length=100, blank=True, default='')
    vehicle_type = models.CharField(max_length=100, blank=True, default='')
    vehicle_year = models.IntegerField(null=True, blank=True)
    vehicle_make = models.CharField(max_length=100, blank=True, default='')
    vehicle_model = models.CharField(max_length=100, blank=True, default='')
    license_plate = models.CharField(max_length=20, blank=True, default='')

    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
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
    user_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
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
    email_to_garage_sent = models.BooleanField(default=False)
    email_to_garage_sent_at = models.DateTimeField(null=True, blank=True)

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
            models.Index(fields=['created_at']),
            models.Index(fields=['garage_email']),
            models.Index(fields=['email']),
        ]
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"

    def __str__(self):
        return f"SR-{self.request_id.hex[:8].upper()} - {self.first_name} {self.last_name}"

    # ==================== HELPER METHODS ====================

    def get_request_code(self):
        """Get formatted request code"""
        return f"SR-{self.request_id.hex[:8].upper()}"

    def full_name(self):
        """Get customer full name"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def get_status_display(self):
        """Get status display value"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def get_priority_display(self):
        """Get priority display value"""
        return dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)

    def populate_from_user(self, user):
        """Populate fields from user object"""
        if user:
            self.first_name = user.first_name or self.first_name
            self.last_name = user.last_name or self.last_name
            self.email = user.email or self.email
            self.phone = getattr(user, 'phone', '') or self.phone
            if hasattr(user, 'city') and user.city:
                self.city = user.city
                self.location = user.city

    def get_contact_source(self):
        """Get contact source type"""
        if self.user:
            return 'User Profile'
        return 'Manual Entry'

    # ==================== GARAGE EMAILS METHODS ====================

    def get_all_garage_emails(self):
        """
        Returns a list of all garage email addresses associated with this service request.
        Used to send notifications to all relevant garages.
        """
        garage_emails = []
        
        # Add the primary garage email if it exists and is not empty
        if self.garage_email and self.garage_email.strip():
            garage_emails.append(self.garage_email.strip())
        
        # Remove duplicates while preserving order
        unique_emails = []
        for email in garage_emails:
            if email not in unique_emails:
                unique_emails.append(email)
        
        return unique_emails

    def add_garage_email(self, email):
        """
        Add a garage email to the list (if you want to support multiple garages)
        """
        if email and email.strip() and email not in self.get_all_garage_emails():
            if not self.garage_email:
                self.garage_email = email.strip()
            # For multiple garages, you would need a ManyToMany field
            # This is a placeholder for future enhancement
            pass

    # ==================== EMAIL NOTIFICATION METHODS ====================

    def send_email_notification(self, notification_type, context=None, recipient_type='customer', to_email=None):
        """
        Send email notification to user or garage
        
        Args:
            notification_type: 'created', 'status_update', 'quote_ready', 'completed', 
                              'cancelled', 'garage_response', 'garage_assigned', 'new_request'
            context: Dictionary with template context data
            recipient_type: 'customer' or 'garage'
            to_email: Optional specific email address (overrides auto-detection)
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        from mechanics.utils import send_service_request_email
        
        if context is None:
            context = {}
        
        # Prepare context data with all relevant information
        context.update({
            'request_id': self.get_request_code(),
            'customer_name': self.full_name(),
            'service_type': self.service_type or 'N/A',
            'status': self.get_status_display(),
            'status_code': self.status,
            'priority': self.get_priority_display(),
            'garage_name': self.garage_name or 'Not assigned yet',
            'garage_phone': self.garage_phone or 'N/A',
            'garage_email': self.garage_email or 'N/A',
            'estimated_cost': str(self.estimated_cost) if self.estimated_cost else 'Pending',
            'actual_cost': str(self.actual_cost) if self.actual_cost else 'N/A',
            'created_at': self.created_at,
            'submitted_at': self.submitted_at,
            'vehicle_info': f"{self.vehicle_year} {self.vehicle_make} {self.vehicle_model}".strip() or 'Not specified',
            'experience': self.experience[:300] if self.experience else '',
            'phone': self.phone or 'N/A',
            'email': self.email or 'N/A',
            'location': self.location or 'N/A',
            'city': self.city or 'N/A',
            'address': self.address or 'N/A',
        })
        
        # Determine recipient email
        if to_email:
            recipient_email = to_email
        elif recipient_type == 'customer':
            recipient_email = self.email
        else:  # garage
            recipient_email = self.garage_email
        
        if not recipient_email or not recipient_email.strip():
            logger.warning(f"No {recipient_type} email found for request {self.get_request_code()}")
            return False
        
        # Send the email
        try:
            result = send_service_request_email(
                to_email=recipient_email,
                notification_type=notification_type,
                context=context,
                recipient_type=recipient_type
            )
            
            # Track email sent
            if result:
                if recipient_type == 'customer':
                    if notification_type == 'created':
                        self.email_confirmation_sent = True
                        self.email_confirmation_sent_at = timezone.now()
                    elif notification_type == 'status_update':
                        self.email_status_update_sent = True
                        self.email_status_update_sent_at = timezone.now()
                else:
                    self.email_to_garage_sent = True
                    self.email_to_garage_sent_at = timezone.now()
                
                self.save(update_fields=[
                    'email_confirmation_sent', 'email_confirmation_sent_at',
                    'email_status_update_sent', 'email_status_update_sent_at',
                    'email_to_garage_sent', 'email_to_garage_sent_at'
                ])
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

    def send_email_to_all_garages(self, notification_type, context=None):
        """
        Send email notification to all garages associated with this request
        
        Args:
            notification_type: 'new_request', 'status_update', etc.
            context: Dictionary with template context data
        
        Returns:
            int: Number of emails successfully sent
        """
        if context is None:
            context = {}
        
        garage_emails = self.get_all_garage_emails()
        sent_count = 0
        
        for garage_email in garage_emails:
            if garage_email and garage_email.strip():
                try:
                    result = self.send_email_notification(
                        notification_type, 
                        context=context,
                        recipient_type='garage',
                        to_email=garage_email
                    )
                    if result:
                        sent_count += 1
                        logger.info(f"Notification sent to garage: {garage_email}")
                    else:
                        logger.warning(f"Failed to send notification to garage: {garage_email}")
                except Exception as e:
                    logger.error(f"Error sending to {garage_email}: {str(e)}")
        
        return sent_count

    # ==================== SMS NOTIFICATION METHODS ====================

    def send_sms_notification(self, action_type, context=None):
        """
        Send SMS notification to user
        
        Args:
            action_type: 'created', 'status_update', 'garage_response', 'quote_ready'
            context: Dictionary with context data
        
        Returns:
            bool: True if SMS was sent successfully, False otherwise
        """
        try:
            from utils.africastalking_sms import africastalking_sms
        except ImportError:
            logger.warning("Africastalking SMS module not available")
            return False

        if not self.phone:
            logger.warning(f"No phone number for request {self.get_request_code()}")
            return False

        if context is None:
            context = {}

        # SMS templates
        templates = {
            'created': f"✅ Service Request Created\nRequest: {self.get_request_code()}\nService: {self.service_type}\nWe'll notify you when a garage responds.\nThank you for choosing QuickFix!",
            'status_update': f"📋 Status Update\nRequest: {self.get_request_code()}\nNew Status: {self.get_status_display()}\nGarage: {self.garage_name or 'Pending'}\nThank you for choosing QuickFix!",
            'garage_response': f"🔧 Garage Response\nRequest: {self.get_request_code()}\n{self.garage_name} has responded.\nThey will contact you soon.\nThank you for choosing QuickFix!",
            'quote_ready': f"💰 Quote Ready\nRequest: {self.get_request_code()}\nAmount: ${self.estimated_cost}\nA quote is ready for your review.\nThank you for choosing QuickFix!",
            'completed': f"✅ Service Completed\nRequest: {self.get_request_code()}\nYour service is complete.\nPlease rate your experience.\nThank you for choosing QuickFix!",
            'cancelled': f"❌ Service Cancelled\nRequest: {self.get_request_code()}\nYour service request has been cancelled.\nThank you for choosing QuickFix!",
        }

        message = templates.get(action_type, f"Update for your service request: {self.get_request_code()}")

        try:
            result = africastalking_sms.send_sms(
                phone_number=self.phone,
                message=message,
                sender_id='QuickFix'
            )

            if result.get('success'):
                if action_type == 'created':
                    self.sms_confirmation_sent = True
                    self.sms_confirmation_sent_at = timezone.now()
                    self.save(update_fields=['sms_confirmation_sent', 'sms_confirmation_sent_at'])
                elif action_type == 'status_update':
                    self.sms_status_update_sent = True
                    self.sms_status_update_sent_at = timezone.now()
                    self.save(update_fields=['sms_status_update_sent', 'sms_status_update_sent_at'])

                logger.info(f"SMS sent to {self.phone} for {action_type}")
                return True
            else:
                logger.warning(f"SMS failed to {self.phone}: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS to {self.phone}: {str(e)}")
            return False

    # ==================== VALIDATION AND SAVE METHODS ====================

    def clean(self):
        """Validate the model before saving."""
        super().clean()

        if not self.user and (not self.first_name or not self.last_name or not self.email):
            raise ValidationError(
                "For non-registered users, first name, last name, and email are required."
            )

        if self.email and self.email.strip():
            from django.core.validators import validate_email
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError("Please enter a valid email address.")

        if len(self.experience.strip()) < 10:
            raise ValidationError("Experience description must be at least 10 characters.")

        # Validate garage email format if provided
        if self.garage_email and self.garage_email.strip():
            from django.core.validators import validate_email
            try:
                validate_email(self.garage_email)
            except ValidationError:
                raise ValidationError("Please enter a valid garage email address.")

    def save(self, *args, **kwargs):
        """Save the model with additional logic"""
        # Populate from user if available
        if self.user_id:
            try:
                user = settings.AUTH_USER_MODEL.objects.get(pk=self.user_id)
                self.populate_from_user(user)
            except:
                pass

        # Set submitted_at for new records
        if not self.pk and not self.submitted_at:
            self.submitted_at = timezone.now()

        # Set terms agreement date
        if self.agreed_to_terms and not self.terms_agreement_date:
            self.terms_agreement_date = timezone.now()

        # Validate experience length
        if len(self.experience.strip()) < 10:
            raise ValidationError("Experience description must be at least 10 characters.")

        # Validate email for non-registered users
        if not self.user and (not self.email or not self.email.strip()):
            raise ValidationError("Email is required for non-registered users.")

        super().save(*args, **kwargs)


class ServiceRequestUpdate(models.Model):
    """Model to track updates/changes to service requests."""

    UPDATE_TYPE_CHOICES = [
        ('created', 'Request Created'),
        ('status_change', 'Status Change'),
        ('priority_change', 'Priority Change'),
        ('quote_provided', 'Quote Provided'),
        ('quote_approved', 'Quote Approved'),
        ('note_added', 'Note Added'),
        ('completion', 'Service Completed'),
        ('cancellation', 'Cancellation'),
        ('assignment', 'Assigned to Garage'),
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

    old_value = models.CharField(max_length=255, blank=True, default='')
    new_value = models.CharField(max_length=255, blank=True, default='')

    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'mechanics'
        ordering = ['-created_at']
        verbose_name = "Service Request Update"
        verbose_name_plural = "Service Request Updates"

    def __str__(self):
        return f"Update #{self.id} for {self.service_request} - {self.get_update_type_display()}"


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


class ServiceType(models.Model):
    """Model for different types of services."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
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


# ==================== SIGNALS ====================

@receiver(post_save, sender=ServiceRequest)
def handle_service_request_notifications(sender, instance, created, **kwargs):
    """
    Automatically handle notifications when service request is created or updated
    """
    if created:
        logger.info(f"🎉 New Service Request Created: {instance.get_request_code()}")
        
        # Create update record
        ServiceRequestUpdate.objects.create(
            service_request=instance,
            update_type='created',
            notes='Service request created'
        )
        
        # Send email to customer
        instance.send_email_notification('created', recipient_type='customer')
        
        # Send email to all garages
        garage_count = instance.send_email_to_all_garages('new_request')
        logger.info(f"📧 Notifications sent to customer and {garage_count} garages")
        
        # Send SMS to customer if phone available
        if instance.phone:
            instance.send_sms_notification('created')
        
    else:
        try:
            old_instance = ServiceRequest.objects.get(pk=instance.pk)
            
            # Track status changes
            if old_instance.status != instance.status:
                logger.info(f"📊 Status Changed: {instance.get_request_code()} - {old_instance.status} → {instance.status}")
                
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='status_change',
                    old_value=old_instance.status,
                    new_value=instance.status,
                    notes=f'Status changed from {old_instance.get_status_display()} to {instance.get_status_display()}'
                )
                
                # Notify customer via email
                instance.send_email_notification('status_update', {
                    'old_status': old_instance.get_status_display(),
                    'new_status': instance.get_status_display()
                }, recipient_type='customer')
                
                # Notify garages about status update
                if instance.garage_email:
                    instance.send_email_to_all_garages('status_update', {
                        'old_status': old_instance.get_status_display(),
                        'new_status': instance.get_status_display()
                    })
                
                # Send SMS to customer
                if instance.phone:
                    instance.send_sms_notification('status_update')
            
            # Track priority changes
            if old_instance.priority != instance.priority:
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='priority_change',
                    old_value=old_instance.priority,
                    new_value=instance.priority,
                    notes=f'Priority changed from {old_instance.get_priority_display()} to {instance.get_priority_display()}'
                )
            
            # Track quote approval
            if not old_instance.quote_approved and instance.quote_approved:
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='quote_approved',
                    old_value='not_approved',
                    new_value='approved',
                    notes='Quote approved by customer'
                )
                instance.send_email_notification('quote_approved', recipient_type='customer')
            
            # Track garage assignment
            if not old_instance.garage_email and instance.garage_email:
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='assignment',
                    old_value='',
                    new_value=instance.garage_name,
                    notes=f'Garage assigned: {instance.garage_name}'
                )
                instance.send_email_notification('garage_assigned', {
                    'garage_name': instance.garage_name,
                    'garage_phone': instance.garage_phone,
                    'garage_email': instance.garage_email
                }, recipient_type='customer')
            
            # Track completion
            if not old_instance.actual_completion_date and instance.actual_completion_date:
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='completion',
                    old_value='',
                    new_value='completed',
                    notes='Service marked as completed'
                )
                instance.send_email_notification('completed', recipient_type='customer')
                if instance.phone:
                    instance.send_sms_notification('completed')
            
            # Track cancellation
            if old_instance.status != 'cancelled' and instance.status == 'cancelled':
                ServiceRequestUpdate.objects.create(
                    service_request=instance,
                    update_type='cancellation',
                    old_value=old_instance.status,
                    new_value='cancelled',
                    notes='Service request cancelled'
                )
                instance.send_email_notification('cancelled', recipient_type='customer')
                if instance.phone:
                    instance.send_sms_notification('cancelled')
                    
        except ServiceRequest.DoesNotExist:
            logger.error(f"ServiceRequest with pk={instance.pk} not found in post_save signal")
            pass