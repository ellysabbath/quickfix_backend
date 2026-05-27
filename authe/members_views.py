# members_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db import models
from .members_serializers import (
    MemberSerializer, CreateMemberSerializer, UpdateMemberSerializer,
    ChangePasswordSerializer, BulkRoleUpdateSerializer
)

User = get_user_model()


@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_members(request):
    """
    GET ALL MEMBERS - NO PERMISSION REQUIRED
    Endpoint: GET /api/members/
    """
    try:
        members = User.objects.all().order_by('-date_joined')
        serializer = MemberSerializer(members, many=True)
        
        return Response({
            'success': True,
            'members': serializer.data,
            'total': members.count()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_member_by_id(request, member_id):
    """
    GET MEMBER BY ID - NO PERMISSION REQUIRED
    Endpoint: GET /api/members/<member_id>/
    """
    try:
        member = User.objects.get(id=member_id)
        serializer = MemberSerializer(member)
        return Response({
            'success': True,
            'member': serializer.data
        })
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Member not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_member(request):
    """
    CREATE NEW MEMBER - NO PERMISSION REQUIRED
    Endpoint: POST /api/members/create/
    """
    serializer = CreateMemberSerializer(data=request.data)
    
    if serializer.is_valid():
        member = serializer.save()
        return Response({
            'success': True,
            'message': 'Member created successfully',
            'member': MemberSerializer(member).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([AllowAny])
def update_member(request, member_id):
    """
    UPDATE MEMBER - NO PERMISSION REQUIRED
    Endpoint: PUT /api/members/update/<member_id>/
    """
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Member not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UpdateMemberSerializer(member, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Member updated successfully',
            'member': MemberSerializer(member).data
        })
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_member(request, member_id):
    """
    DELETE MEMBER - NO PERMISSION REQUIRED
    Endpoint: DELETE /api/members/delete/<member_id>/
    """
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Member not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    member.delete()
    
    return Response({
        'success': True,
        'message': f'Member deleted successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def change_member_password(request, member_id):
    """
    CHANGE MEMBER PASSWORD - NO PERMISSION REQUIRED
    Endpoint: POST /api/members/change-password/<member_id>/
    """
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Member not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        member.set_password(serializer.validated_data['new_password'])
        member.save()
        return Response({
            'success': True,
            'message': 'Password changed successfully'
        })
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_update_roles(request):
    """
    BULK UPDATE ROLES FOR MULTIPLE MEMBERS - NO PERMISSION REQUIRED
    Endpoint: POST /api/members/bulk-update-roles/
    """
    serializer = BulkRoleUpdateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user_ids = serializer.validated_data['user_ids']
    role = serializer.validated_data['role']
    
    with transaction.atomic():
        updated_count = User.objects.filter(id__in=user_ids).update(role=role)
    
    return Response({
        'success': True,
        'message': f'Updated {updated_count} member(s) to role: {role}',
        'updated_count': updated_count
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_members_by_role(request, role):
    """
    GET MEMBERS BY ROLE - NO PERMISSION REQUIRED
    Endpoint: GET /api/members/role/<role>/
    """
    valid_roles = ['customer', 'mechanic', 'garage_owner', 'admin']
    
    if role not in valid_roles:
        return Response({
            'success': False,
            'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    members = User.objects.filter(role=role).order_by('-date_joined')
    serializer = MemberSerializer(members, many=True)
    
    return Response({
        'success': True,
        'role': role,
        'members': serializer.data,
        'count': members.count()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_role_statistics(request):
    """
    GET ROLE STATISTICS - NO PERMISSION REQUIRED
    Endpoint: GET /api/members/statistics/
    """
    stats = {
        'customer': User.objects.filter(role='customer').count(),
        'mechanic': User.objects.filter(role='mechanic').count(),
        'garage_owner': User.objects.filter(role='garage_owner').count(),
        'admin': User.objects.filter(role='admin').count(),
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count()
    }
    
    return Response({
        'success': True,
        'statistics': stats
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def deactivate_member(request, member_id):
    """
    DEACTIVATE MEMBER - NO PERMISSION REQUIRED
    Endpoint: POST /api/members/deactivate/<member_id>/
    """
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Member not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    member.is_active = False
    member.save()
    
    return Response({
        'success': True,
        'message': f'Member deactivated successfully',
        'member': MemberSerializer(member).data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def activate_member(request, member_id):
    """
    ACTIVATE MEMBER - NO PERMISSION REQUIRED
    Endpoint: POST /api/members/activate/<member_id>/
    """
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Member not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    member.is_active = True
    member.save()
    
    return Response({
        'success': True,
        'message': f'Member activated successfully',
        'member': MemberSerializer(member).data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def search_members(request):
    """
    SEARCH MEMBERS - NO PERMISSION REQUIRED
    Endpoint: GET /api/members/search/?q=john
    """
    query = request.query_params.get('q', '')
    
    if not query:
        return get_all_members(request)
    
    members = User.objects.filter(
        models.Q(mobile_number__icontains=query) |
        models.Q(full_name__icontains=query) |
        models.Q(email__icontains=query)
    ).order_by('-date_joined')
    
    serializer = MemberSerializer(members, many=True)
    
    return Response({
        'success': True,
        'query': query,
        'members': serializer.data,
        'count': members.count()
    })