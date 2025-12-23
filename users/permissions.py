# users/permissions.py
from rest_framework import permissions
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to super admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users (is_staff=True).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to authenticated users,
    but write access only to admin users.
    """
    def has_permission(self, request, view):
        # Allow read-only access for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Allow write access only for admin users
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allows access to object owners or admin users.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if object has user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object is the user itself
        if isinstance(obj, CustomUser):
            return obj == request.user
        
        return False


class IsMechanic(permissions.BasePermission):
    """
    Allows access only to mechanics.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            from .models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            return profile.is_mechanic
        except:
            return False


class IsGarageOwner(permissions.BasePermission):
    """
    Allows access only to garage owners.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            from .models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            return profile.is_garage_owner
        except:
            return False


class IsMechanicOrGarageOwner(permissions.BasePermission):
    """
    Allows access to mechanics or garage owners.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            from .models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            return profile.is_mechanic or profile.is_garage_owner
        except:
            return False


class CanManageUsers(permissions.BasePermission):
    """
    Allows access to users who can manage other users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admins and admins can manage users
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Garage owners might be able to manage their garage staff
        try:
            from .models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            return profile.is_garage_owner
        except:
            return False


class CanManageBookings(permissions.BasePermission):
    """
    Allows access to users who can manage bookings.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users can manage all bookings
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Mechanics and garage owners can manage bookings
        try:
            from .models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            return profile.is_mechanic or profile.is_garage_owner
        except:
            return False


class CanManageServices(permissions.BasePermission):
    """
    Allows access to users who can manage services.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin users can manage all services
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Garage owners can manage their garage services
        try:
            from .models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            return profile.is_garage_owner
        except:
            return False


class CanViewDashboard(permissions.BasePermission):
    """
    Allows access to dashboard based on user role.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Everyone can view some form of dashboard
        return True