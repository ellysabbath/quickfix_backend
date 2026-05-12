from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

# ======================= SERVICE PROVIDER MODEL =======================
class AutoWorkshop(models.Model):
    """Auto Workshop (formerly Garage) model"""
    workshop_name = models.CharField(max_length=255)
    workshop_owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_workshops',
        null=True,
        blank=True
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
    """Repair Service (formerly Service) model"""
    service_title = models.CharField(max_length=255)
    service_description = models.TextField(blank=True, null=True)
    service_category = models.CharField(max_length=100, blank=True, null=True)
    service_base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    workshop = models.ForeignKey(
        AutoWorkshop,
        on_delete=models.CASCADE,
        related_name='provided_services',
        null=True,
        blank=True
    )
    is_service_active = models.BooleanField(default=True)
    service_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Repair Service"
        verbose_name_plural = "Repair Services"

    def __str__(self):
        return self.service_title


# ======================= SERVICE REQUEST MODEL =======================
class CustomerRequest(models.Model):
    """
    Customer Service Request (formerly PublicServiceRequest)
    Posted by customers without workshop selection
    """
    REQUEST_STATUS = [
        ('awaiting', 'Awaiting Offers'),
        ('viewed', 'Viewed by Workshops'),
        ('offers_received', 'Offers Received'),
        ('accepted', 'Offer Accepted'),
        ('in_progress', 'Service in Progress'),
        ('completed', 'Service Completed'),
        ('cancelled', 'Request Cancelled'),
        ('expired', 'Request Expired'),
    ]

    URGENCY_LEVELS = [
        ('standard', 'Standard'),
        ('priority', 'Priority'),
        ('emergency', 'Emergency'),
    ]

    CONTACT_METHODS = [
        ('phone_call', 'Phone Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
    ]

    # Core identification
    request_code = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='service_requests'
    )

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
    request_urgency = models.CharField(
        max_length=20,
        choices=URGENCY_LEVELS,
        default='standard'
    )

    # Budget
    budget_minimum = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    budget_maximum = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_budget_flexible = models.BooleanField(default=True)

    # Request status
    request_status = models.CharField(max_length=20, choices=REQUEST_STATUS, default='awaiting')

    # Accepted workshop
    accepted_workshop = models.ForeignKey(
        AutoWorkshop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_customer_requests'
    )
    offer_accepted_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    times_viewed = models.IntegerField(default=0)

    # Additional notes
    customer_notes = models.TextField(blank=True, null=True)

    # Communication preference
    preferred_contact = models.CharField(
        max_length=20,
        choices=CONTACT_METHODS,
        default='phone_call'
    )

    # Expiry
    request_expires = models.DateTimeField()

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

        if not self.request_expires:
            # Set expiry 72 hours from creation
            self.request_expires = timezone.now() + timezone.timedelta(hours=72)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_code} - {self.requested_service}"

    def is_request_expired(self):
        return timezone.now() > self.request_expires

    def can_receive_offers(self):
        return self.request_status in ['awaiting', 'viewed', 'offers_received'] and not self.is_request_expired()

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
        return " ".join(parts) if parts else "Vehicle details not provided"

    def increment_view_count(self):
        self.times_viewed += 1
        self.save(update_fields=['times_viewed'])


# ======================= WORKSHOP QUOTE MODEL =======================
class WorkshopQuote(models.Model):
    """
    Quote/Offer made by workshop for a customer request
    """
    QUOTE_STATUS = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted by Customer'),
        ('declined', 'Declined by Customer'),
        ('withdrawn', 'Withdrawn by Workshop'),
    ]

    customer_request = models.ForeignKey(
        CustomerRequest,
        on_delete=models.CASCADE,
        related_name='received_quotes'
    )
    workshop = models.ForeignKey(
        AutoWorkshop,
        on_delete=models.CASCADE,
        related_name='provided_quotes'
    )

    # Quote details
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_duration = models.PositiveIntegerField(default=1)  # in hours
    workshop_notes = models.TextField(blank=True, null=True)
    quote_status = models.CharField(max_length=20, choices=QUOTE_STATUS, default='pending')

    # Timestamps
    quote_created = models.DateTimeField(auto_now_add=True)
    quote_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['customer_request', 'workshop']
        ordering = ['quoted_price', 'quote_created']
        verbose_name = "Workshop Quote"
        verbose_name_plural = "Workshop Quotes"

    def __str__(self):
        return f"Quote #{self.id} from {self.workshop.workshop_name}"

    def accept_quote(self):
        """Accept this quote and update all related records"""
        # Mark all other quotes as declined
        WorkshopQuote.objects.filter(customer_request=self.customer_request).exclude(id=self.id).update(quote_status='declined')

        # Update this quote
        self.quote_status = 'accepted'
        self.save()

        # Update the customer request
        self.customer_request.request_status = 'accepted'
        self.customer_request.accepted_workshop = self.workshop
        self.customer_request.offer_accepted_at = timezone.now()
        self.customer_request.save()

        # Create a service appointment
        return ServiceAppointment.objects.create_from_quote(self)


# ======================= SERVICE APPOINTMENT MODEL =======================
class ServiceAppointment(models.Model):
    """
    Service Appointment (formerly ServiceBooking)
    Created when a workshop quote is accepted
    """
    APPOINTMENT_STATUS = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed by Workshop'),
        ('in_progress', 'Service in Progress'),
        ('completed', 'Service Completed'),
        ('cancelled', 'Appointment Cancelled'),
    ]

    appointment_code = models.CharField(max_length=20, unique=True, editable=False)

    # References
    customer_request = models.OneToOneField(
        CustomerRequest,
        on_delete=models.CASCADE,
        related_name='service_appointment'
    )
    accepted_quote = models.OneToOneField(
        WorkshopQuote,
        on_delete=models.CASCADE,
        related_name='appointment'
    )

    # Customer
    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='service_appointments'
    )

    # Workshop
    service_workshop = models.ForeignKey(
        AutoWorkshop,
        on_delete=models.CASCADE,
        related_name='appointments'
    )

    # Service details
    appointment_service = models.CharField(max_length=255)
    service_details = models.TextField(blank=True, null=True)
    agreed_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Vehicle info
    appointment_vehicle_brand = models.CharField(max_length=100, blank=True, null=True)
    appointment_vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    appointment_vehicle_year = models.CharField(max_length=4, blank=True, null=True)
    appointment_license_plate = models.CharField(max_length=20, blank=True, null=True)

    # Location
    appointment_location = models.TextField()
    appointment_maps_link = models.URLField(blank=True, null=True)

    # Schedule
    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    # Status
    appointment_status = models.CharField(max_length=20, choices=APPOINTMENT_STATUS, default='scheduled')

    # Notes
    appointment_notes = models.TextField(blank=True, null=True)

    # SMS notifications
    sms_confirmation_sent = models.BooleanField(default=False)
    sms_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    sms_reminder_sent = models.BooleanField(default=False)
    sms_reminder_sent_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    appointment_created = models.DateTimeField(auto_now_add=True)
    appointment_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_created']
        verbose_name = "Service Appointment"
        verbose_name_plural = "Service Appointments"

    def save(self, *args, **kwargs):
        if not self.appointment_code:
            self.appointment_code = f"APT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.appointment_code} - {self.appointment_service}"

    @classmethod
    def create_from_quote(cls, quote):
        """Create an appointment from an accepted quote"""
        customer_request = quote.customer_request

        appointment = cls(
            customer_request=customer_request,
            accepted_quote=quote,
            client=customer_request.customer,
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

    def send_confirmation_notification(self):
        """Send confirmation SMS to client"""
        from utils.sms_service import sms_service

        try:
            if not self.client.phone:
                return False

            message = (
                f"✅ Service Appointment #{self.appointment_code} Confirmed!\n"
                f"📍 Service: {self.appointment_service}\n"
                f"🏢 Workshop: {self.service_workshop.workshop_name}\n"
                f"📞 Contact: {self.service_workshop.workshop_phone}\n"
                f"📅 Date: {self.appointment_date.strftime('%d/%m/%Y')}\n"
                f"⏰ Time: {self.appointment_time.strftime('%I:%M %p')}\n"
                f"💰 Price: TZS {self.agreed_price:,.2f}\n\n"
                f"Thank you for choosing our service!"
            )

            sms_service.send_sms(
                phone_number=self.client.phone,
                message=message,
                purpose='appointment_confirmation'
            )

            self.sms_confirmation_sent = True
            self.sms_confirmation_sent_at = timezone.now()
            self.save(update_fields=['sms_confirmation_sent', 'sms_confirmation_sent_at'])
            return True

        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False

    def send_reminder_notification(self):
        """Send reminder SMS to client"""
        from utils.sms_service import sms_service

        try:
            if not self.client.phone:
                return False

            message = (
                f"🔔 Reminder: Service Appointment #{self.appointment_code}\n"
                f"📍 Service: {self.appointment_service}\n"
                f"🏢 Workshop: {self.service_workshop.workshop_name}\n"
                f"📅 Tomorrow at: {self.appointment_time.strftime('%I:%M %p')}\n"
                f"📞 Contact: {self.service_workshop.workshop_phone}\n\n"
                f"Please be on time!"
            )

            sms_service.send_sms(
                phone_number=self.client.phone,
                message=message,
                purpose='appointment_reminder'
            )

            self.sms_reminder_sent = True
            self.sms_reminder_sent_at = timezone.now()
            self.save(update_fields=['sms_reminder_sent', 'sms_reminder_sent_at'])
            return True

        except Exception as e:
            print(f"Error sending reminder SMS: {e}")
            return False




# =========================================================// MODELS   WITH   SMS   SENDING  //=============================================






# ==================================================//  APPROVED  BY//==================================
# registration/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

class Approve(models.Model):
    """
    Approve model for tracking who updated request/appointment status
    """
    # Who performed the update
    updated_by = models.CharField(max_length=200, blank=True, null=True, help_text="Name of person who made the update")
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    # Location fields
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, help_text="Longitude coordinate")
    location_address = models.TextField(blank=True, null=True, help_text="Formatted address or location description")
    location_city = models.CharField(max_length=100, blank=True, null=True, help_text="City name")
    location_country = models.CharField(max_length=100, blank=True, null=True, help_text="Country name")

    # Auto-loaded codes from ServiceAppointment and CustomerRequest
    request_code = models.CharField(max_length=50, blank=True, null=True)
    appointment_code = models.CharField(max_length=50, blank=True, null=True)

    # Status tracking
    previous_status = models.CharField(max_length=50, blank=True, null=True)
    new_status = models.CharField(max_length=50, blank=True, null=True)

    # Additional context
    notes = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Approval Record'
        verbose_name_plural = 'Approval Records'
        indexes = [
            models.Index(fields=['request_code', '-created_at']),
            models.Index(fields=['appointment_code', '-created_at']),
            models.Index(fields=['updated_by']),
            models.Index(fields=['latitude', 'longitude']),  # Index for location queries
            models.Index(fields=['location_city']),
        ]

    def __str__(self):
        if self.appointment_code:
            return f"Appointment {self.appointment_code} updated by {self.updated_by or 'Unknown'}"
        elif self.request_code:
            return f"Request {self.request_code} updated by {self.updated_by or 'Unknown'}"
        return f"Approval by {self.updated_by or 'Unknown'} on {self.created_at}"

    @classmethod
    def create_from_appointment(cls, appointment, updated_by, previous_status, new_status, phone_number=None, notes=None, location_data=None):
        """Create approval record from a ServiceAppointment"""
        location_data = location_data or {}
        return cls.objects.create(
            updated_by=updated_by,
            phone_number=phone_number,
            appointment_code=appointment.appointment_code,
            request_code=appointment.customer_request.request_code if appointment.customer_request else None,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
            latitude=location_data.get('latitude'),
            longitude=location_data.get('longitude'),
            location_address=location_data.get('location_address'),
            location_city=location_data.get('location_city'),
            location_country=location_data.get('location_country')
        )

    @classmethod
    def create_from_request(cls, customer_request, updated_by, previous_status, new_status, phone_number=None, notes=None, location_data=None):
        """Create approval record from a CustomerRequest"""
        location_data = location_data or {}
        return cls.objects.create(
            updated_by=updated_by,
            phone_number=phone_number,
            request_code=customer_request.request_code,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
            latitude=location_data.get('latitude'),
            longitude=location_data.get('longitude'),
            location_address=location_data.get('location_address'),
            location_city=location_data.get('location_city'),
            location_country=location_data.get('location_country')
        )