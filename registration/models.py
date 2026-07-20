# registration/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
from django.conf import settings

User = get_user_model()

# ======================= SERVICE PROVIDER MODEL =======================
class AutoWorkshop(models.Model):
    workshop_name = models.CharField(max_length=255)
    workshop_owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='owned_workshops',
        null=True, blank=True
    )
    workshop_email = models.EmailField()
    workshop_phone = models.CharField(max_length=20)
    workshop_address = models.TextField()
    workshop_city = models.CharField(max_length=100, blank=True, null=True)
    workshop_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    workshop_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_workshop_verified = models.BooleanField(default=False)
    is_workshop_active = models.BooleanField(default=True)
    workshop_created = models.DateTimeField(auto_now_add=True)
    workshop_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Auto Workshop"
        verbose_name_plural = "Auto Workshops"

    def __str__(self):
        return self.workshop_name


# ======================= SERVICE CATALOG MODEL =======================
class RepairService(models.Model):
    service_title = models.CharField(max_length=255)
    service_description = models.TextField(blank=True, null=True)
    service_category = models.CharField(max_length=100, blank=True, null=True)
    service_base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    workshop = models.ForeignKey(
        AutoWorkshop, on_delete=models.CASCADE,
        related_name='provided_services', null=True, blank=True
    )
    is_service_active = models.BooleanField(default=True)
    service_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Repair Service"
        verbose_name_plural = "Repair Services"

    def __str__(self):
        return self.service_title


class CustomerServiceRequest(models.Model):
    """
    Customer Service Request - Public form without authentication
    """
    # Complete status options for the frontend
    REQUEST_STATUS = [
        ('pending', 'Pending'),
        ('viewed', 'Viewed'),
        ('offers_received', 'Offers Received'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    URGENCY_LEVELS = [
        ('standard', 'Standard'),
        ('priority', 'Priority'),
        ('emergency', 'Emergency'),
    ]

    # Core identification
    request_code = models.CharField(max_length=20, unique=True, editable=False)

    # Customer information (no authentication required)
    customer_name = models.CharField(max_length=255, help_text="Full name of customer")
    customer_phone = models.CharField(max_length=20, help_text="Phone number for contact")
    customer_email = models.EmailField(blank=True, null=True, help_text="Optional email address")

    # Service information
    requested_service = models.CharField(max_length=255)
    request_description = models.TextField(blank=True, null=True)

    # Vehicle information
    vehicle_brand = models.CharField(max_length=100, blank=True, null=True)
    vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    vehicle_year = models.CharField(max_length=4, blank=True, null=True)
    vehicle_color = models.CharField(max_length=50, blank=True, null=True)
    license_plate = models.CharField(max_length=20, blank=True, null=True)

    # Location details
    service_location = models.TextField()
    location_maps_link = models.URLField(blank=True, null=True)
    location_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    location_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # Scheduling
    preferred_service_date = models.DateField()
    preferred_service_time = models.TimeField()
    is_urgent_request = models.BooleanField(default=False)
    request_urgency = models.CharField(max_length=20, choices=URGENCY_LEVELS, default='standard')

    # Budget - minimum defaults to 0, maximum comes from transaction
    budget_minimum = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
    budget_maximum = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Automatically set from payment transaction")
    is_budget_flexible = models.BooleanField(default=True)

    # Request status
    request_status = models.CharField(max_length=20, choices=REQUEST_STATUS, default='pending')

    # Approval and tracking fields (for admin actions)
    approved_by = models.CharField(max_length=255, blank=True, null=True, help_text="Who approved this request")
    approved_at = models.DateTimeField(blank=True, null=True, help_text="When the request was approved")
    fixed_by = models.CharField(max_length=255, blank=True, null=True, help_text="Who fixed/completed this request")
    fixed_at = models.DateTimeField(blank=True, null=True, help_text="When the request was fixed/completed")
    updated_by = models.CharField(max_length=255, blank=True, null=True, help_text="Last person who updated the request")

    # ================================================================
    # FIXED: Transaction relation - Using a simple CharField instead
    # of a foreign key to avoid the missing Transaction model error
    # ================================================================
    
    # Option 1: Store transaction ID as a simple field
    transaction_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Associated payment transaction ID"
    )
    transaction_reference = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Payment transaction reference"
    )
    payment_status = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending',
        help_text="Status of the associated payment"
    )
    
    # Option 2: If you want to keep the relation but use a different model
    # Uncomment this if you have a Payment model in the same app
    # payment = models.ForeignKey(
    #     'registration.Payment',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True,
    #     related_name='service_requests',
    #     help_text="Associated payment"
    # )
    
    # Option 3: Link to PaymentRecord in payments app (if it exists)
    # Uncomment this if you have a PaymentRecord model in payments app
    # payment_record = models.ForeignKey(
    #     'payments.PaymentRecord',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True,
    #     related_name='service_requests',
    #     help_text="Associated payment record"
    # )

    # Additional notes
    customer_notes = models.TextField(blank=True, null=True)

    # Timestamps
    request_created = models.DateTimeField(auto_now_add=True)
    request_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-request_created']
        verbose_name = "Customer Service Request"
        verbose_name_plural = "Customer Service Requests"

    def save(self, *args, **kwargs):
        if not self.request_code:
            self.request_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        # Set budget_minimum to 0 if not set
        if self.budget_minimum is None:
            self.budget_minimum = 0.00

        # Update budget_maximum from linked transaction
        if self.transaction_id and self.payment_status == 'completed':
            # If you have amount stored in transaction, you'd set it here
            # For now, we'll just keep the existing budget_maximum
            pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_code} - {self.customer_name} - {self.requested_service}"

    def get_vehicle_details(self):
        parts = []
        if self.vehicle_brand:
            parts.append(self.vehicle_brand)
        if self.vehicle_model:
            parts.append(self.vehicle_model)
        if self.vehicle_year:
            parts.append(self.vehicle_year)
        if self.license_plate:
            parts.append(f"({self.license_plate})")
        return " ".join(parts) if parts else "Not specified"

    def get_budget_range(self):
        """Get formatted budget range"""
        if self.budget_minimum and self.budget_maximum:
            return f"TZS {self.budget_minimum:,.0f} - {self.budget_maximum:,.0f}"
        elif self.budget_maximum:
            return f"Up to TZS {self.budget_maximum:,.0f}"
        elif self.budget_minimum:
            return f"From TZS {self.budget_minimum:,.0f}"
        return "Budget not specified"


# ======================= WORKSHOP QUOTE MODEL =======================
class WorkshopQuote(models.Model):
    QUOTE_STATUS = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted by Customer'),
        ('declined', 'Declined by Customer'),
        ('withdrawn', 'Withdrawn by Workshop'),
    ]

    customer_request = models.ForeignKey(CustomerServiceRequest, on_delete=models.CASCADE, related_name='quotes')
    workshop = models.ForeignKey(AutoWorkshop, on_delete=models.CASCADE, related_name='provided_quotes')
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_duration = models.PositiveIntegerField(default=1)
    workshop_notes = models.TextField(blank=True, null=True)
    quote_status = models.CharField(max_length=20, choices=QUOTE_STATUS, default='pending')
    quote_created = models.DateTimeField(auto_now_add=True)
    quote_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['customer_request', 'workshop']
        ordering = ['quoted_price', 'quote_created']

    def __str__(self):
        return f"Quote #{self.id} from {self.workshop.workshop_name}"

    def accept_quote(self):
        WorkshopQuote.objects.filter(customer_request=self.customer_request).exclude(id=self.id).update(quote_status='declined')
        self.quote_status = 'accepted'
        self.save()
        self.customer_request.request_status = 'accepted'
        self.customer_request.save()
        return ServiceAppointment.objects.create_from_quote(self)


# ======================= SERVICE APPOINTMENT MODEL =======================
class ServiceAppointment(models.Model):
    APPOINTMENT_STATUS = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed by Workshop'),
        ('in_progress', 'Service in Progress'),
        ('completed', 'Service Completed'),
        ('cancelled', 'Appointment Cancelled'),
    ]

    appointment_code = models.CharField(max_length=20, unique=True, editable=False)
    customer_request = models.OneToOneField(CustomerServiceRequest, on_delete=models.CASCADE, related_name='service_appointment')
    accepted_quote = models.OneToOneField(WorkshopQuote, on_delete=models.CASCADE, related_name='appointment')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_appointments', null=True, blank=True)
    service_workshop = models.ForeignKey(AutoWorkshop, on_delete=models.CASCADE, related_name='appointments')
    appointment_service = models.CharField(max_length=255)
    service_details = models.TextField(blank=True, null=True)
    agreed_price = models.DecimalField(max_digits=10, decimal_places=2)
    appointment_vehicle_brand = models.CharField(max_length=100, blank=True, null=True)
    appointment_vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    appointment_vehicle_year = models.CharField(max_length=4, blank=True, null=True)
    appointment_license_plate = models.CharField(max_length=20, blank=True, null=True)
    appointment_location = models.TextField()
    appointment_maps_link = models.URLField(blank=True, null=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    appointment_status = models.CharField(max_length=20, choices=APPOINTMENT_STATUS, default='scheduled')
    appointment_notes = models.TextField(blank=True, null=True)
    sms_confirmation_sent = models.BooleanField(default=False)
    sms_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    sms_reminder_sent = models.BooleanField(default=False)
    sms_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    appointment_created = models.DateTimeField(auto_now_add=True)
    appointment_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_created']

    def save(self, *args, **kwargs):
        if not self.appointment_code:
            self.appointment_code = f"APT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.appointment_code} - {self.appointment_service}"

    @classmethod
    def create_from_quote(cls, quote):
        customer_request = quote.customer_request
        appointment = cls(
            customer_request=customer_request,
            accepted_quote=quote,
            client=None,  # Will need to be set properly
            service_workshop=quote.workshop,
            appointment_service=customer_request.requested_service,
            service_details=customer_request.request_description,
            agreed_price=quote.quoted_price,
            appointment_vehicle_brand=customer_request.vehicle_brand,
            appointment_vehicle_model=customer_request.vehicle_model,
            appointment_vehicle_year=customer_request.vehicle_year,
            appointment_license_plate=customer_request.license_plate,
            appointment_location=customer_request.service_location,
            appointment_maps_link=customer_request.location_maps_link,
            appointment_date=customer_request.preferred_service_date,
            appointment_time=customer_request.preferred_service_time,
            appointment_notes=f"Created from request {customer_request.request_code}. Workshop notes: {quote.workshop_notes}",
            appointment_status='confirmed'
        )
        appointment.save()
        return appointment


# ======================= APPROVE MODEL (FOR STATUS TRACKING) =======================
class Approve(models.Model):
    updated_by = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    location_address = models.TextField(blank=True, null=True)
    location_city = models.CharField(max_length=100, blank=True, null=True)
    location_country = models.CharField(max_length=100, blank=True, null=True)
    request_code = models.CharField(max_length=50, blank=True, null=True)
    appointment_code = models.CharField(max_length=50, blank=True, null=True)
    previous_status = models.CharField(max_length=50, blank=True, null=True)
    new_status = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Approval by {self.updated_by or 'Unknown'} on {self.created_at}"


# ======================= GARAGE/WORKSHOP MODEL =======================
class Garage(models.Model):
    """
    Garage/Auto Workshop Model - Public CRUD operations
    """
    # Core Information
    name = models.CharField(max_length=255, help_text="Garage/Workshop name")
    address = models.TextField(help_text="Full address of the garage")
    city = models.CharField(max_length=100, blank=True, null=True, help_text="City name")

    # Contact Information
    phone = models.CharField(max_length=20, help_text="Contact phone number")
    email = models.EmailField(help_text="Contact email address")

    # Ratings
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text="Average rating (0-5)")
    rating_count = models.IntegerField(default=0, help_text="Number of ratings received")

    # Status Flags
    is_open = models.BooleanField(default=True, help_text="Currently open for business")
    delivery_available = models.BooleanField(default=False, help_text="Offers mobile/delivery service")
    is_verified = models.BooleanField(default=False, help_text="Verified by admin")
    is_active = models.BooleanField(default=True, help_text="Active garage")

    # Service Information
    estimated_time = models.CharField(max_length=100, default="15-30 mins", help_text="Estimated service time")
    services = models.JSONField(default=list, blank=True, help_text="List of services offered")

    # Location Coordinates
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, help_text="Longitude coordinate")

    # Operating Hours (JSON format)
    opening_hours = models.JSONField(default=dict, blank=True, help_text="Operating hours for each day")

    # Owner reference (optional, for future authentication)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_garages',
        help_text="Garage owner (optional)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Garage"
        verbose_name_plural = "Garages"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['city']),
            models.Index(fields=['is_active', 'is_open']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return self.name

    def get_rating_float(self):
        """Return rating as float"""
        return float(self.rating) if self.rating else 0.0

    def get_services_list(self):
        """Return services as list"""
        if isinstance(self.services, list):
            return self.services
        return []

    def get_opening_hours_dict(self):
        """Return opening hours as dict"""
        if isinstance(self.opening_hours, dict):
            return self.opening_hours
        return {}