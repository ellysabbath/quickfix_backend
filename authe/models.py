# from django.db import models
# from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# from django.utils import timezone
# from datetime import timedelta
# import random

# class UserManager(BaseUserManager):
#     def create_user(self, mobile_number, email=None, password=None, **extra_fields):
#         if not mobile_number:
#             raise ValueError('Mobile number is required')

#         user = self.model(
#             mobile_number=mobile_number,
#             email=self.normalize_email(email) if email else None,
#             **extra_fields
#         )
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, mobile_number, email=None, password=None, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         extra_fields.setdefault('is_active', True)

#         if email is None:
#             raise ValueError('Superuser must have an email')

#         return self.create_user(mobile_number, email, password, **extra_fields)

# class User(AbstractBaseUser, PermissionsMixin):
#     mobile_number = models.CharField(max_length=20, unique=True)
#     email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
#     full_name = models.CharField(max_length=255, blank=True)
#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=False)
#     date_joined = models.DateTimeField(default=timezone.now)
#     last_login = models.DateTimeField(null=True, blank=True)

#     objects = UserManager()

#     USERNAME_FIELD = 'mobile_number'
#     REQUIRED_FIELDS = ['email']

#     def __str__(self):
#         return self.mobile_number

#     def get_full_name(self):
#         return self.full_name or self.mobile_number

#     def get_short_name(self):
#         return self.mobile_number

#     class Meta:
#         db_table = 'users'
#         verbose_name = 'User'
#         verbose_name_plural = 'Users'






# models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import random

class UserManager(BaseUserManager):
    def create_user(self, mobile_number, email=None, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError('Mobile number is required')

        # Set default role if not provided
        if 'role' not in extra_fields:
            extra_fields['role'] = 'customer'

        user = self.model(
            mobile_number=mobile_number,
            email=self.normalize_email(email) if email else None,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_number, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')

        if email is None:
            raise ValueError('Superuser must have an email')

        return self.create_user(mobile_number, email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    # Role choices
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('mechanic', 'Mechanic'),
        ('garage_owner', 'Garage Owner'),
        ('admin', 'Admin'),
    ]

    mobile_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer', db_index=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.mobile_number

    def get_full_name(self):
        return self.full_name or self.mobile_number

    def get_short_name(self):
        return self.mobile_number

    def get_role_display_name(self):
        """Get the display name for the role"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'






class OTPVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps', null=True, blank=True)
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_verified and timezone.now() < self.expires_at

    @staticmethod
    def generate_otp():
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    def __str__(self):
        return f"OTP for {self.email} - {self.otp_code}"

    class Meta:
        db_table = 'otp_verifications'
        ordering = ['-created_at']

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    device_info = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    # Add to your User model
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session for {self.user.mobile_number}"

    class Meta:
        db_table = 'user_sessions'






# ========================   MY PROFILE   ========================
class MyProfile(models.Model):
    """Profile model for additional user information"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='User'
    )
    profile_picture = models.TextField(null=True, blank=True, help_text='Base64 or URL of profile picture')
    bio = models.TextField(max_length=500, blank=True, default='', help_text='User biography')
    location = models.CharField(max_length=255, blank=True, default='', help_text='User location')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.mobile_number}"

    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

# Signals to auto-create profile
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a profile when a new user is created"""
    if created:
        MyProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()