# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        
        # Set default role to 'customer' if not provided
        if 'role' not in extra_fields:
            extra_fields['role'] = 'customer'
            
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # Superuser gets admin role by default
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    # Role choices
    ROLE_CHOICES = [
        ('mechanic', 'Mechanic'),
        ('garage_owner', 'Garage Owner'),
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    
    # Role field with default as 'customer'
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )
    
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    
    # Registration tracking
    registration_stage = models.IntegerField(default=1)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    
    # Timestamps
    personal_info_completed_at = models.DateTimeField(null=True, blank=True)
    contact_details_completed_at = models.DateTimeField(null=True, blank=True)
    location_completed_at = models.DateTimeField(null=True, blank=True)
    security_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Django defaults
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
    # Helper properties
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
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    

    

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
    








# dashboard/models.py
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




# models.py
from django.db import models
from django.conf import settings
import random
import string

class Booking(models.Model):
    # Status choices
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
    
    full_name = models.CharField(max_length=200, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    
    # Service and garage information
    garage = models.ForeignKey('Garage', on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey('Service', on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Location information
    location = models.TextField(blank=True)
    google_maps_link = models.URLField(blank=True, max_length=500)
    
    # Booking details
    scheduled_date = models.DateTimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    booking_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Status field - ADD THIS
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        blank=True
    )

    
    # Additional custom service option
    custom_service_name = models.CharField(max_length=200, blank=True, null=True)
    custom_service_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.booking_number} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        # Generate booking number if not exists
        if not self.booking_number:
            self.booking_number = f"BK-{random.randint(10000000, 99999999)}"
        
        # Set price from service if not provided
        if not self.price or self.price == 0.00:
            if self.service:
                self.price = self.service.base_price
            elif self.custom_service_price and self.custom_service_price > 0:
                self.price = self.custom_service_price
            else:
                self.price = 0.00
        
        # Set total price if not provided
        if not self.total_price or self.total_price == 0.00:
            self.total_price = self.price
        
        # Set completed status if scheduled date is in the past
        if self.scheduled_date and not self.status == self.STATUS_CANCELLED:
            from django.utils import timezone
            if self.scheduled_date < timezone.now() and self.status == self.STATUS_PENDING:
                self.status = self.STATUS_COMPLETED
        
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']





# ============================// USER PROFILE //===============
