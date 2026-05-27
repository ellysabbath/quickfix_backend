# members_serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class MemberSerializer(serializers.ModelSerializer):
    """Serializer for Member (User) model with role"""
    role_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'mobile_number', 'email', 'full_name', 'role', 'role_display',
            'is_active', 'is_staff', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_role_display(self, obj):
        return obj.get_role_display_name()


class CreateMemberSerializer(serializers.ModelSerializer):
    """Serializer for creating a new member"""
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'mobile_number', 'email', 'full_name', 'role', 'password', 'confirm_password'
        ]
    
    def validate_mobile_number(self, value):
        if User.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError("User with this mobile number already exists")
        return value
    
    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value
    
    def validate_role(self, value):
        valid_roles = ['customer', 'mechanic', 'garage_owner', 'admin']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(valid_roles)}")
        return value
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        if len(data['password']) < 6:
            raise serializers.ValidationError({"password": "Password must be at least 6 characters"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UpdateMemberSerializer(serializers.ModelSerializer):
    """Serializer for updating a member"""
    class Meta:
        model = User
        fields = ['mobile_number', 'email', 'full_name', 'role', 'is_active', 'is_staff']
    
    def validate_mobile_number(self, value):
        instance = self.instance
        if instance and instance.mobile_number != value:
            if User.objects.filter(mobile_number=value).exists():
                raise serializers.ValidationError("User with this mobile number already exists")
        return value
    
    def validate_email(self, value):
        instance = self.instance
        if value and instance and instance.email != value:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("User with this email already exists")
        return value
    
    def validate_role(self, value):
        valid_roles = ['customer', 'mechanic', 'garage_owner', 'admin']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(valid_roles)}")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password"""
    new_password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class BulkRoleUpdateSerializer(serializers.Serializer):
    """Serializer for bulk role updates"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    role = serializers.ChoiceField(choices=['customer', 'mechanic', 'garage_owner', 'admin'])