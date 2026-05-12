# users/models.py
# from django.db import models
# from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# from django.utils import timezone
# import uuid

# class CustomUserManager(BaseUserManager):
#     def create_user(self, email, password=None, **extra_fields):
#         if not email:
#             raise ValueError('Email is required')
#         email = self.normalize_email(email)

#         # Set default role to 'customer' if not provided
#         if 'role' not in extra_fields:
#             extra_fields['role'] = 'customer'

#         user = self.model(email=email, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, email, password=None, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         extra_fields.setdefault('role', 'admin')  # Superuser gets admin role by default
#         return self.create_user(email, password, **extra_fields)

# class CustomUser(AbstractBaseUser, PermissionsMixin):
#     # Role choices
#     ROLE_CHOICES = [
#         ('mechanic', 'Mechanic'),
#         ('garage_owner', 'Garage Owner'),
#         ('customer', 'Customer'),
#         ('admin', 'Admin'),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     email = models.EmailField(unique=True)
#     phone = models.CharField(max_length=15)
#     first_name = models.CharField(max_length=30)
#     last_name = models.CharField(max_length=30)

#     # Role field with default as 'customer'
#     role = models.CharField(
#         max_length=20,
#         choices=ROLE_CHOICES,
#         default='customer'
#     )

#     city = models.CharField(max_length=100, blank=True)
#     state = models.CharField(max_length=100, blank=True)

#     # Registration tracking
#     registration_stage = models.IntegerField(default=1)
#     is_email_verified = models.BooleanField(default=False)
#     is_phone_verified = models.BooleanField(default=False)

#     # Timestamps
#     personal_info_completed_at = models.DateTimeField(null=True, blank=True)
#     contact_details_completed_at = models.DateTimeField(null=True, blank=True)
#     location_completed_at = models.DateTimeField(null=True, blank=True)
#     security_completed_at = models.DateTimeField(null=True, blank=True)

#     # Django defaults
#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=False)
#     date_joined = models.DateTimeField(default=timezone.now)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['first_name', 'last_name']

#     objects = CustomUserManager()

#     def __str__(self):
#         return self.email

#     # Helper properties
#     @property
#     def is_mechanic(self):
#         return self.role == 'mechanic'

#     @property
#     def is_garage_owner(self):
#         return self.role == 'garage_owner'

#     @property
#     def is_customer(self):
#         return self.role == 'customer'

#     @property
#     def is_admin(self):
#         return self.role == 'admin' or self.is_superuser















# from django.db import models
# from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# from django.utils import timezone
# from django.utils.translation import gettext_lazy as _
# import uuid
# import re

# class CustomUserManager(BaseUserManager):
#     def create_user(self, email=None, phone=None, password=None, **extra_fields):
#         """
#         Create and save a user with either email, phone, or both.
#         At least one of email or phone must be provided.
#         """
#         if not email and not phone:
#             raise ValueError(_('Either email or phone must be provided'))

#         if email:
#             email = self.normalize_email(email)

#         # Set default role
#         if 'role' not in extra_fields:
#             extra_fields['role'] = 'customer'

#         user = self.model(email=email, phone=phone, **extra_fields)

#         if password:
#             user.set_password(password)
#         else:
#             # Django requires a password, so set unusable password if none provided
#             user.set_unusable_password()

#         user.save(using=self._db)
#         return user

#     def create_superuser(self, email, phone, password=None, **extra_fields):
#         """Superuser must have both email and phone"""
#         if not email or not phone:
#             raise ValueError(_('Superuser must have both email and phone'))

#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         extra_fields.setdefault('role', 'admin')

#         return self.create_user(email, phone, password, **extra_fields)

#     def get_by_natural_key(self, username):
#         """Override to allow login with either email or phone"""
#         # Try email first
#         user = self.filter(email__iexact=username).first()
#         if user:
#             return user
#         # Try phone (normalized)
#         from .utils import normalize_phone
#         normalized_phone = normalize_phone(username)
#         if normalized_phone:
#             user = self.filter(phone=normalized_phone).first()
#             if user:
#                 return user
#         raise self.model.DoesNotExist


# class CustomUser(AbstractBaseUser, PermissionsMixin):
#     # Role choices
#     ROLE_CHOICES = [
#         ('mechanic', 'Mechanic'),
#         ('garage_owner', 'Garage Owner'),
#         ('customer', 'Customer'),
#         ('admin', 'Admin'),
#     ]

#     # Core identification fields
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     email = models.EmailField(
#         unique=True,
#         blank=True,
#         null=True,
#         help_text="User's email address (optional if phone is provided)"
#     )
#     phone = models.CharField(
#         max_length=15,
#         unique=True,
#         help_text="User's phone number (optional if email is provided)"
#     )

#     # Personal information
#     first_name = models.CharField(max_length=30)
#     last_name = models.CharField(max_length=30)

#     # Role
#     role = models.CharField(
#         max_length=20,
#         choices=ROLE_CHOICES,
#         default='customer'
#     )

#     # Location
#     city = models.CharField(max_length=100, blank=True)
#     state = models.CharField(max_length=100, blank=True)

#     # Registration tracking
#     registration_stage = models.IntegerField(default=1)
#     is_email_verified = models.BooleanField(default=False)
#     is_phone_verified = models.BooleanField(default=False)

#     # Timestamps
#     personal_info_completed_at = models.DateTimeField(null=True, blank=True)
#     contact_details_completed_at = models.DateTimeField(null=True, blank=True)
#     location_completed_at = models.DateTimeField(null=True, blank=True)
#     security_completed_at = models.DateTimeField(null=True, blank=True)

#     # Django defaults
#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=False)
#     date_joined = models.DateTimeField(default=timezone.now)

#     # Track registration method
#     registration_method = models.CharField(
#         max_length=10,
#         choices=[
#             ('email', 'Email Only'),
#             ('phone', 'Phone Only'),
#             ('both', 'Both Email & Phone')
#         ],
#         default='both'
#     )

#     # For Django authentication
#     USERNAME_FIELD = 'email'  # Default for admin
#     REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']

#     objects = CustomUserManager()

#     def __str__(self):
#         if self.email:
#             return self.email
#         return f"{self.phone} (Mobile)"

#     @property
#     def username(self):
#         """Return the primary identifier for the user"""
#         return self.email if self.email else self.phone

#     @property
#     def full_name(self):
#         """Return the full name of the user"""
#         return f"{self.first_name} {self.last_name}".strip()

#     # Role helper properties
#     @property
#     def is_mechanic(self):
#         return self.role == 'mechanic'

#     @property
#     def is_garage_owner(self):
#         return self.role == 'garage_owner'

#     @property
#     def is_customer(self):
#         return self.role == 'customer'

#     @property
#     def is_admin(self):
#         return self.role == 'admin' or self.is_superuser

#     def clean(self):
#         """Validate that at least one of email or phone is provided"""
#         super().clean()
#         if not self.email and not self.phone:
#             raise ValidationError(_('Either email or phone must be provided'))

#     def save(self, *args, **kwargs):
#         # Determine registration method before saving
#         if self.email and self.phone:
#             self.registration_method = 'both'
#         elif self.email:
#             self.registration_method = 'email'
#         elif self.phone:
#             self.registration_method = 'phone'

#         # Normalize phone number before saving
#         if self.phone:
#             from .utils import normalize_phone
#             self.phone = normalize_phone(self.phone)

#         super().save(*args, **kwargs)













from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import uuid
import re

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        """
        Create and save a regular user with either email or phone.
        Default role is 'customer' unless specified.
        """
        if not email and not phone:
            raise ValueError(_('Either email or phone must be provided'))

        # Normalize email if provided
        if email:
            email = self.normalize_email(email)

        # Set default role to 'customer' if not provided
        if 'role' not in extra_fields:
            extra_fields['role'] = 'customer'

        user = self.model(email=email, phone=phone, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone, password=None, **extra_fields):
        """Create superuser - must have both email and phone"""
        if not email or not phone:
            raise ValueError(_('Superuser must have both email and phone'))

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        return self.create_user(email, phone, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('mechanic', 'Mechanic'),
        ('garage_owner', 'Garage Owner'),
        ('admin', 'Admin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authentication fields
    email = models.EmailField(
        _('email address'),
        unique=True,
        blank=True,
        null=True,
        help_text=_("User's email address")
    )
    phone = models.CharField(
        _('phone number'),
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        help_text=_("User's phone number")
    )

    # Personal info
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)

    # Role and status
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )

    # Location
    city = models.CharField(_('city'), max_length=100, blank=True)
    state = models.CharField(_('state'), max_length=100, blank=True)

    # Registration tracking
    registration_stage = models.IntegerField(default=1)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Timestamps for registration stages
    personal_info_completed_at = models.DateTimeField(null=True, blank=True)
    contact_details_completed_at = models.DateTimeField(null=True, blank=True)
    location_completed_at = models.DateTimeField(null=True, blank=True)
    security_completed_at = models.DateTimeField(null=True, blank=True)

    # Django auth fields
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    # Registration method tracking
    registration_method = models.CharField(
        max_length=10,
        choices=[
            ('email', 'Email Only'),
            ('phone', 'Phone Only'),
            ('both', 'Both Email & Phone')
        ],
        default='both'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        if self.email:
            return self.email
        return f"{self.phone}"

    def clean(self):
        """Validate model before saving"""
        super().clean()
        if not self.email and not self.phone:
            raise ValidationError(_('Either email or phone must be provided'))

    def save(self, *args, **kwargs):
        # Determine registration method
        if self.email and self.phone:
            self.registration_method = 'both'
        elif self.email:
            self.registration_method = 'email'
        elif self.phone:
            self.registration_method = 'phone'

        # Normalize phone if provided
        if self.phone:
            from .utils import normalize_phone
            normalized = normalize_phone(self.phone)
            if normalized:
                self.phone = normalized

        super().save(*args, **kwargs)

    @property
    def username(self):
        return self.email if self.email else self.phone

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_mechanic(self):
        return self.role == 'mechanic'

    @property
    def is_garage_owner(self):
        return self.role == 'garage_owner'

    @property
    def is_customer(self):
        return self.role == 'customer'

    @property
    def is_admin_user(self):
        return self.role == 'admin'

    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)



















class OTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=[
        ('email_verification', 'Email Verification'),
        ('phone_verification', 'Phone Verification'),
        ('password_reset', 'Password Reset'),
    ])
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at









# users/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class Service(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    description = models.TextField()
    category = models.CharField(max_length=50)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    garage = models.ForeignKey(
        'Garage',  # Assuming you have a Garage model
        on_delete=models.CASCADE,
        related_name='services',
        null=True,  # Make it optional if service can exist without a garage
        blank=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,  # Make it optional
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If price is not set, use base_price as default
        if not self.price and self.base_price:
            self.price = self.base_price
        super().save(*args, **kwargs)





class Garage(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    rating_count = models.IntegerField(default=0)
    is_open = models.BooleanField(default=True)
    delivery_available = models.BooleanField(default=False)
    estimated_time = models.CharField(max_length=50, blank=True)
    opening_hours = models.JSONField(default=dict, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_garages'
    )
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    city = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.city and self.address:
            try:
                parts = self.address.split(',')
                if len(parts) > 1:
                    self.city = parts[-2].strip()
            except:
                pass
        super().save(*args, **kwargs)

class GarageService(models.Model):
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='garage_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)  # ADDED
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['garage', 'service']

    def __str__(self):
        return f"{self.garage.name} - {self.service.name}"

class ServiceDetail(models.Model):
    garage_service = models.ForeignKey(GarageService, on_delete=models.CASCADE, related_name='details')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)  # ADDED
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import random
import string
import re
from phonenumbers import parse, is_valid_number, NumberParseException

# Your existing Garage and Service models should be defined above...

class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    # Link to CustomUser - user won't need to re-enter their info
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # References your CustomUser
        on_delete=models.CASCADE,
        blank=True,
        null= True,
        related_name='bookings'
    )

    # Service Information
    garage = models.ForeignKey(
        Garage,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='bookings',
        null=True,
        blank=True
    )

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Location
    location = models.TextField(blank=True)
    google_maps_link = models.URLField(max_length=500, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Booking Details
    scheduled_date = models.DateTimeField()
    notes = models.TextField(blank=True)
    booking_number = models.CharField(max_length=20, unique=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    # Custom Service
    custom_service_name = models.CharField(max_length=200, blank=True, null=True)
    custom_service_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)

    # SMS Tracking
    sms_confirmation_sent = models.BooleanField(default=False)
    sms_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    sms_reminder_sent = models.BooleanField(default=False)
    sms_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    last_sms_status = models.CharField(max_length=100, blank=True)
    sms_error_log = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date', '-created_at']
        indexes = [
            models.Index(fields=['booking_number']),
            models.Index(fields=['user']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['status']),
            models.Index(fields=['sms_confirmation_sent']),
            models.Index(fields=['created_at']),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    def __str__(self):
        return f"Booking #{self.booking_number} - {self.get_full_name()}"

    # Helper properties to access user info directly
    @property
    def full_name(self):
        """Get full name from linked CustomUser"""
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}"
        return ""

    @property
    def mobile_number(self):
        """Get mobile number from linked CustomUser"""
        if self.user:
            return self.user.phone
        return ""

    @property
    def email(self):
        """Get email from linked CustomUser"""
        if self.user:
            return self.user.email
        return ""

    def clean(self):
        """Validate model before saving"""
        super().clean()

        # Validate phone number from user's phone field
        if self.mobile_number:
            try:
                parsed = parse(self.mobile_number, None)
                if not is_valid_number(parsed):
                    raise ValidationError({
                        'user': 'Please update your profile with a valid phone number.'
                    })
            except NumberParseException:
                if not re.match(r'^\+?1?\d{9,15}$', self.mobile_number):
                    raise ValidationError({
                        'user': 'Please update your profile with a valid phone number (e.g., +255123456789).'
                    })

        # Validate scheduled date is in future
        if self.scheduled_date and self.scheduled_date < timezone.now():
            raise ValidationError({
                'scheduled_date': 'Scheduled date must be in the future.'
            })

        # Validate price is positive
        if self.price < 0:
            raise ValidationError({'price': 'Price cannot be negative.'})

        # Validate user has completed registration
        if self.user and self.user.registration_stage < 4:
            raise ValidationError({
                'user': 'User must complete registration before making bookings.'
            })

    def save(self, *args, **kwargs):
        """Override save method to handle auto-generation"""
        is_new = self._state.adding

        # Generate booking number if new
        if is_new and not self.booking_number:
            self.booking_number = self._generate_booking_number()

        # Set price from service if not set
        if self.price == 0.00 or not self.price:
            if self.service:
                self.price = self.service.base_price
                self.total_price = self.service.base_price
            elif self.custom_service_price and self.custom_service_price > 0:
                self.price = self.custom_service_price
                self.total_price = self.custom_service_price

        # Auto-update status based on date
        self._update_status_based_on_date()

        # Call parent save
        super().save(*args, **kwargs)

    def _generate_booking_number(self):
        """Generate unique booking number"""
        while True:
            date_part = timezone.now().strftime('%Y%m%d')
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            booking_number = f"BK-{date_part}-{random_part}"

            # Check if unique
            if not Booking.objects.filter(booking_number=booking_number).exists():
                return booking_number

    def _update_status_based_on_date(self):
        """Update status based on scheduled date"""
        now = timezone.now()

        if self.scheduled_date < now:
            if self.status == self.STATUS_PENDING:
                self.status = self.STATUS_CONFIRMED
            elif self.status == self.STATUS_CONFIRMED:
                self.status = self.STATUS_IN_PROGRESS

    def get_status_display_with_color(self):
        """Get status with HTML color for display"""
        colors = {
            self.STATUS_PENDING: 'warning',
            self.STATUS_CONFIRMED: 'info',
            self.STATUS_IN_PROGRESS: 'primary',
            self.STATUS_COMPLETED: 'success',
            self.STATUS_CANCELLED: 'danger',
        }
        return {
            'text': self.get_status_display(),
            'color': colors.get(self.status, 'secondary')
        }

    def can_send_sms(self):
        """Check if SMS can be sent for this booking"""
        if not self.mobile_number:
            return False, "No mobile number in user profile"

        if self.status == self.STATUS_CANCELLED:
            return False, "Booking is cancelled"

        # Don't send SMS if confirmation was sent less than 1 hour ago
        if self.sms_confirmation_sent_at:
            time_since = timezone.now() - self.sms_confirmation_sent_at
            if time_since.total_seconds() < 3600:  # 1 hour
                return False, "Confirmation sent recently"

        return True, ""

    def mark_sms_sent(self, sms_type='confirmation', status='sent'):
        """Mark SMS as sent"""
        if sms_type == 'confirmation':
            self.sms_confirmation_sent = True
            self.sms_confirmation_sent_at = timezone.now()
        elif sms_type == 'reminder':
            self.sms_reminder_sent = True
            self.sms_reminder_sent_at = timezone.now()

        self.last_sms_status = status
        self.save(update_fields=[
            'sms_confirmation_sent',
            'sms_confirmation_sent_at',
            'sms_reminder_sent',
            'sms_reminder_sent_at',
            'last_sms_status',
            'updated_at'
        ])

    def log_sms_error(self, error_message):
        """Log SMS error"""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        if not self.sms_error_log:
            self.sms_error_log = ""
        self.sms_error_log += f"\n[{timestamp}] {error_message}"
        self.last_sms_status = 'failed'
        self.save(update_fields=['sms_error_log', 'last_sms_status', 'updated_at'])






# # users/models.py
# from django.db import models
# from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# from django.utils import timezone
# from django.utils.translation import gettext_lazy as _
# from django.core.exceptions import ValidationError
# import uuid
# import re
# import random
# import string

# # Optional: Only import phonenumbers if you have it installed
# try:
#     from phonenumbers import parse, is_valid_number, NumberParseException
#     PHONENUMBERS_AVAILABLE = True
# except ImportError:
#     PHONENUMBERS_AVAILABLE = False


# # ======================= CUSTOM USER MANAGER =======================
# class CustomUserManager(BaseUserManager):
#     def create_user(self, email=None, phone=None, password=None, **extra_fields):
#         """
#         Create and save a regular user with either email or phone.
#         Default role is 'customer' unless specified.
#         """
#         if not email and not phone:
#             raise ValueError(_('Either email or phone must be provided'))

#         # Normalize email if provided
#         if email:
#             email = self.normalize_email(email)

#         # Set default role to 'customer' if not provided
#         if 'role' not in extra_fields:
#             extra_fields['role'] = 'customer'

#         user = self.model(email=email, phone=phone, **extra_fields)

#         if password:
#             user.set_password(password)
#         else:
#             user.set_unusable_password()

#         user.save(using=self._db)
#         return user

#     def create_superuser(self, email, phone, password=None, **extra_fields):
#         """Create superuser - must have both email and phone"""
#         if not email or not phone:
#             raise ValueError(_('Superuser must have both email and phone'))

#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         extra_fields.setdefault('role', 'admin')

#         return self.create_user(email, phone, password, **extra_fields)

#     def get_by_natural_key(self, username):
#         """Override to allow login with either email or phone"""
#         # Try email first
#         user = self.filter(email__iexact=username).first()
#         if user:
#             return user
#         # Try phone (normalized)
#         if username:
#             # Simple phone normalization
#             digits = re.sub(r'\D', '', username)
#             if digits:
#                 user = self.filter(phone=digits).first()
#                 if user:
#                     return user
#         raise self.model.DoesNotExist


# # ======================= CUSTOM USER MODEL =======================
# class CustomUser(AbstractBaseUser, PermissionsMixin):
#     ROLE_CHOICES = [
#         ('customer', 'Customer'),
#         ('mechanic', 'Mechanic'),
#         ('garage_owner', 'Garage Owner'),
#         ('admin', 'Admin'),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     # Authentication fields
#     email = models.EmailField(
#         _('email address'),
#         unique=True,
#         blank=True,
#         null=True,
#         help_text=_("User's email address")
#     )
#     phone = models.CharField(
#         _('phone number'),
#         max_length=15,
#         unique=True,
#         blank=True,
#         null=True,
#         help_text=_("User's phone number")
#     )

#     # Personal info
#     first_name = models.CharField(_('first name'), max_length=30, blank=True)
#     last_name = models.CharField(_('last name'), max_length=30, blank=True)

#     # Role and status
#     role = models.CharField(
#         _('role'),
#         max_length=20,
#         choices=ROLE_CHOICES,
#         default='customer'
#     )

#     # Location
#     city = models.CharField(_('city'), max_length=100, blank=True)
#     state = models.CharField(_('state'), max_length=100, blank=True)

#     # Registration tracking
#     registration_stage = models.IntegerField(default=1)
#     is_email_verified = models.BooleanField(default=False)
#     is_phone_verified = models.BooleanField(default=False)

#     # Timestamps for registration stages
#     personal_info_completed_at = models.DateTimeField(null=True, blank=True)
#     contact_details_completed_at = models.DateTimeField(null=True, blank=True)
#     location_completed_at = models.DateTimeField(null=True, blank=True)
#     security_completed_at = models.DateTimeField(null=True, blank=True)

#     # Django auth fields
#     is_active = models.BooleanField(_('active'), default=True)
#     is_staff = models.BooleanField(_('staff status'), default=False)
#     date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

#     # Registration method tracking
#     registration_method = models.CharField(
#         max_length=10,
#         choices=[
#             ('email', 'Email Only'),
#             ('phone', 'Phone Only'),
#             ('both', 'Both Email & Phone')
#         ],
#         default='both'
#     )

#     objects = CustomUserManager()

#     USERNAME_FIELD = 'email'
#     EMAIL_FIELD = 'email'
#     REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']

#     class Meta:
#         verbose_name = _('user')
#         verbose_name_plural = _('users')

#     def __str__(self):
#         if self.email:
#             return self.email
#         return f"{self.phone}"

#     def clean(self):
#         """Validate model before saving"""
#         super().clean()
#         if not self.email and not self.phone:
#             raise ValidationError(_('Either email or phone must be provided'))

#     def save(self, *args, **kwargs):
#         # Determine registration method
#         if self.email and self.phone:
#             self.registration_method = 'both'
#         elif self.email:
#             self.registration_method = 'email'
#         elif self.phone:
#             self.registration_method = 'phone'

#         # Normalize phone if provided
#         if self.phone:
#             # Simple phone normalization - remove all non-digits
#             digits = re.sub(r'\D', '', self.phone)
#             if digits:
#                 self.phone = digits

#         super().save(*args, **kwargs)

#     # ========== REQUIRED DJANGO METHODS ==========
#     def get_full_name(self):
#         """
#         Return the full name of the user.
#         This method is required by Django admin and many third-party apps.
#         """
#         full_name = f"{self.first_name} {self.last_name}".strip()
#         if not full_name:
#             # Fallback to email or phone if no name is set
#             if self.email:
#                 return self.email.split('@')[0]
#             elif self.phone:
#                 return f"User_{self.phone[-4:]}"
#             return "User"
#         return full_name

#     def get_short_name(self):
#         """
#         Return the short name of the user.
#         This method is required by Django admin.
#         """
#         if self.first_name:
#             return self.first_name
#         elif self.email:
#             return self.email.split('@')[0]
#         elif self.phone:
#             return f"User_{self.phone[-4:]}"
#         return "User"

#     # ========== PROPERTIES ==========
#     @property
#     def username(self):
#         return self.email if self.email else self.phone

#     @property
#     def full_name(self):
#         """Property to get full name - calls get_full_name()"""
#         return self.get_full_name()

#     @property
#     def is_mechanic(self):
#         return self.role == 'mechanic'

#     @property
#     def is_garage_owner(self):
#         return self.role == 'garage_owner'

#     @property
#     def is_customer(self):
#         return self.role == 'customer'

#     @property
#     def is_admin_user(self):
#         return self.role == 'admin'

#     def get_role_display(self):
#         return dict(self.ROLE_CHOICES).get(self.role, self.role)


# # ======================= OTP MODEL =======================
# class OTP(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otps')
#     code = models.CharField(max_length=6)
#     purpose = models.CharField(max_length=20, choices=[
#         ('email_verification', 'Email Verification'),
#         ('phone_verification', 'Phone Verification'),
#         ('password_reset', 'Password Reset'),
#     ])
#     is_used = models.BooleanField(default=False)
#     expires_at = models.DateTimeField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"OTP for {self.user} - {self.purpose}"

#     def is_valid(self):
#         return not self.is_used and timezone.now() < self.expires_at


# # ======================= SERVICE MODEL =======================
# class Service(models.Model):
#     name = models.CharField(max_length=100)
#     icon = models.CharField(max_length=50, blank=True)
#     color = models.CharField(max_length=50, blank=True)
#     description = models.TextField(blank=True)
#     category = models.CharField(max_length=50, blank=True)
#     base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     garage = models.ForeignKey(
#         'Garage',
#         on_delete=models.CASCADE,
#         related_name='services',
#         null=True,
#         blank=True
#     )
#     price = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         null=True,
#         blank=True
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.name

#     def save(self, *args, **kwargs):
#         # If price is not set, use base_price as default
#         if not self.price and self.base_price:
#             self.price = self.base_price
#         super().save(*args, **kwargs)


# # ======================= GARAGE MODEL =======================
# class Garage(models.Model):
#     name = models.CharField(max_length=100)
#     address = models.TextField(blank=True)
#     latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
#     longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
#     phone = models.CharField(max_length=20, blank=True)
#     email = models.EmailField(blank=True)
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
#     rating_count = models.IntegerField(default=0)
#     is_open = models.BooleanField(default=True)
#     delivery_available = models.BooleanField(default=False)
#     estimated_time = models.CharField(max_length=50, blank=True)
#     opening_hours = models.JSONField(default=dict, blank=True)

#     owner = models.ForeignKey(
#         CustomUser,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='owned_garages'
#     )
#     is_verified = models.BooleanField(default=False)
#     is_active = models.BooleanField(default=True)
#     city = models.CharField(max_length=100, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.name

#     def save(self, *args, **kwargs):
#         if not self.city and self.address:
#             try:
#                 parts = self.address.split(',')
#                 if len(parts) > 1:
#                     self.city = parts[-2].strip()
#             except:
#                 pass
#         super().save(*args, **kwargs)


# # ======================= GARAGE SERVICE MODEL =======================
# class GarageService(models.Model):
#     garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='garage_services')
#     service = models.ForeignKey(Service, on_delete=models.CASCADE)
#     price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     duration = models.CharField(max_length=50, blank=True)
#     description = models.TextField(blank=True)
#     is_available = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ['garage', 'service']

#     def __str__(self):
#         return f"{self.garage.name} - {self.service.name}"


# # ======================= SERVICE DETAIL MODEL =======================
# class ServiceDetail(models.Model):
#     garage_service = models.ForeignKey(GarageService, on_delete=models.CASCADE, related_name='details')
#     name = models.CharField(max_length=100)
#     description = models.TextField(blank=True)
#     price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     duration = models.CharField(max_length=50, blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name


# # ======================= BOOKING MODEL =======================
# class Booking(models.Model):
#     STATUS_PENDING = 'pending'
#     STATUS_CONFIRMED = 'confirmed'
#     STATUS_IN_PROGRESS = 'in_progress'
#     STATUS_COMPLETED = 'completed'
#     STATUS_CANCELLED = 'cancelled'

#     STATUS_CHOICES = [
#         (STATUS_PENDING, 'Pending'),
#         (STATUS_CONFIRMED, 'Confirmed'),
#         (STATUS_IN_PROGRESS, 'In Progress'),
#         (STATUS_COMPLETED, 'Completed'),
#         (STATUS_CANCELLED, 'Cancelled'),
#     ]

#     # Link to CustomUser
#     user = models.ForeignKey(
#         CustomUser,
#         on_delete=models.CASCADE,
#         blank=True,
#         null=True,
#         related_name='bookings'
#     )

#     # Service Information
#     garage = models.ForeignKey(
#         Garage,
#         on_delete=models.CASCADE,
#         related_name='bookings'
#     )
#     service = models.ForeignKey(
#         Service,
#         on_delete=models.CASCADE,
#         related_name='bookings',
#         null=True,
#         blank=True
#     )

#     # Pricing
#     price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

#     # Location
#     location = models.TextField(blank=True)
#     google_maps_link = models.URLField(max_length=500, blank=True)
#     latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
#     longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

#     # Booking Details
#     scheduled_date = models.DateTimeField()
#     notes = models.TextField(blank=True)
#     booking_number = models.CharField(max_length=20, unique=True, blank=True)

#     # Status
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default=STATUS_PENDING
#     )

#     # Custom Service
#     custom_service_name = models.CharField(max_length=200, blank=True, null=True)
#     custom_service_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)

#     # SMS Tracking
#     sms_confirmation_sent = models.BooleanField(default=False)
#     sms_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
#     sms_reminder_sent = models.BooleanField(default=False)
#     sms_reminder_sent_at = models.DateTimeField(null=True, blank=True)
#     last_sms_status = models.CharField(max_length=100, blank=True)
#     sms_error_log = models.TextField(blank=True)

#     # Timestamps
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['-scheduled_date', '-created_at']
#         indexes = [
#             models.Index(fields=['booking_number']),
#             models.Index(fields=['user']),
#             models.Index(fields=['scheduled_date']),
#             models.Index(fields=['status']),
#             models.Index(fields=['sms_confirmation_sent']),
#             models.Index(fields=['created_at']),
#         ]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self._original_status = self.status

#     # ========== FIXED: Use safe method instead of get_full_name ==========
#     def __str__(self):
#         return f"Booking #{self.booking_number} - {self.get_customer_name()}"

#     def get_customer_name(self):
#         """Safely get customer name without assuming get_full_name exists"""
#         if self.user:
#             # Try multiple ways to get the name
#             if hasattr(self.user, 'get_full_name') and callable(self.user.get_full_name):
#                 try:
#                     name = self.user.get_full_name()
#                     if name:
#                         return name
#                 except:
#                     pass

#             # Fallback methods
#             if self.user.first_name or self.user.last_name:
#                 return f"{self.user.first_name} {self.user.last_name}".strip()
#             if self.user.email:
#                 return self.user.email.split('@')[0]
#             if self.user.phone:
#                 return f"User_{self.user.phone[-4:]}"
#         return "Guest"

#     # Helper properties to access user info directly
#     @property
#     def full_name(self):
#         """Get full name from linked CustomUser"""
#         return self.get_customer_name()

#     @property
#     def mobile_number(self):
#         """Get mobile number from linked CustomUser"""
#         if self.user:
#             return self.user.phone
#         return ""

#     @property
#     def email(self):
#         """Get email from linked CustomUser"""
#         if self.user:
#             return self.user.email
#         return ""

#     def clean(self):
#         """Validate model before saving"""
#         super().clean()

#         # Validate phone number from user's phone field
#         if self.mobile_number:
#             # Simple validation
#             if not re.match(r'^\+?1?\d{9,15}$', self.mobile_number):
#                 raise ValidationError({
#                     'user': 'Please update your profile with a valid phone number (e.g., +255123456789).'
#                 })

#         # Validate scheduled date is in future
#         if self.scheduled_date and self.scheduled_date < timezone.now():
#             raise ValidationError({
#                 'scheduled_date': 'Scheduled date must be in the future.'
#             })

#         # Validate price is positive
#         if self.price < 0:
#             raise ValidationError({'price': 'Price cannot be negative.'})

#         # Validate user has completed registration
#         if self.user and self.user.registration_stage < 4:
#             raise ValidationError({
#                 'user': 'User must complete registration before making bookings.'
#             })

#     def save(self, *args, **kwargs):
#         """Override save method to handle auto-generation"""
#         is_new = self._state.adding

#         # Generate booking number if new
#         if is_new and not self.booking_number:
#             self.booking_number = self._generate_booking_number()

#         # Set price from service if not set
#         if self.price == 0.00 or not self.price:
#             if self.service:
#                 self.price = self.service.base_price
#                 self.total_price = self.service.base_price
#             elif self.custom_service_price and self.custom_service_price > 0:
#                 self.price = self.custom_service_price
#                 self.total_price = self.custom_service_price

#         # Auto-update status based on date
#         self._update_status_based_on_date()

#         # Call parent save
#         super().save(*args, **kwargs)

#     def _generate_booking_number(self):
#         """Generate unique booking number"""
#         while True:
#             date_part = timezone.now().strftime('%Y%m%d')
#             random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
#             booking_number = f"BK-{date_part}-{random_part}"

#             # Check if unique
#             if not Booking.objects.filter(booking_number=booking_number).exists():
#                 return booking_number

#     def _update_status_based_on_date(self):
#         """Update status based on scheduled date"""
#         now = timezone.now()

#         if self.scheduled_date < now:
#             if self.status == self.STATUS_PENDING:
#                 self.status = self.STATUS_CONFIRMED
#             elif self.status == self.STATUS_CONFIRMED:
#                 self.status = self.STATUS_IN_PROGRESS

#     def get_status_display_with_color(self):
#         """Get status with HTML color for display"""
#         colors = {
#             self.STATUS_PENDING: 'warning',
#             self.STATUS_CONFIRMED: 'info',
#             self.STATUS_IN_PROGRESS: 'primary',
#             self.STATUS_COMPLETED: 'success',
#             self.STATUS_CANCELLED: 'danger',
#         }
#         return {
#             'text': self.get_status_display(),
#             'color': colors.get(self.status, 'secondary')
#         }

#     def can_send_sms(self):
#         """Check if SMS can be sent for this booking"""
#         if not self.mobile_number:
#             return False, "No mobile number in user profile"

#         if self.status == self.STATUS_CANCELLED:
#             return False, "Booking is cancelled"

#         # Don't send SMS if confirmation was sent less than 1 hour ago
#         if self.sms_confirmation_sent_at:
#             time_since = timezone.now() - self.sms_confirmation_sent_at
#             if time_since.total_seconds() < 3600:  # 1 hour
#                 return False, "Confirmation sent recently"

#         return True, ""

#     def mark_sms_sent(self, sms_type='confirmation', status='sent'):
#         """Mark SMS as sent"""
#         if sms_type == 'confirmation':
#             self.sms_confirmation_sent = True
#             self.sms_confirmation_sent_at = timezone.now()
#         elif sms_type == 'reminder':
#             self.sms_reminder_sent = True
#             self.sms_reminder_sent_at = timezone.now()

#         self.last_sms_status = status
#         self.save(update_fields=[
#             'sms_confirmation_sent',
#             'sms_confirmation_sent_at',
#             'sms_reminder_sent',
#             'sms_reminder_sent_at',
#             'last_sms_status',
#             'updated_at'
#         ])

#     def log_sms_error(self, error_message):
#         """Log SMS error"""
#         timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
#         if not self.sms_error_log:
#             self.sms_error_log = ""
#         self.sms_error_log += f"\n[{timestamp}] {error_message}"
#         self.last_sms_status = 'failed'
#         self.save(update_fields=['sms_error_log', 'last_sms_status', 'updated_at'])