# registration/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from .models import (
    AutoWorkshop, RepairService,
    WorkshopQuote, ServiceAppointment, Approve
)
from .serializers import (
    AutoWorkshopSerializer, RepairServiceSerializer,

    WorkshopQuoteSerializer, WorkshopQuoteCreateSerializer,
    ServiceAppointmentSerializer, ApproveSerializer
)


class AutoWorkshopViewSet(viewsets.ModelViewSet):
    """Complete CRUD for AutoWorkshop - PUBLIC ACCESS"""
    queryset = AutoWorkshop.objects.all().order_by('workshop_name')
    serializer_class = AutoWorkshopSerializer

    # CHANGE THIS - Allow all actions publicly
    permission_classes = [AllowAny]  # ← This makes all actions public
    authentication_classes = []  # ← Clear any authentication classes

    # OR if you want more control, override get_permissions:
    # def get_permissions(self):
    #     return [AllowAny()]  # Allow all actions

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search workshops by name or city"""
        query = request.query_params.get('q', '')
        workshops = self.queryset.filter(
            Q(workshop_name__icontains=query) |
            Q(workshop_city__icontains=query)
        )
        serializer = self.get_serializer(workshops, many=True)
        return Response(serializer.data)

class RepairServiceViewSet(viewsets.ModelViewSet):
    """Complete CRUD for RepairService - PUBLIC ACCESS"""
    queryset = RepairService.objects.all().order_by('service_title')
    serializer_class = RepairServiceSerializer
    permission_classes = [AllowAny]  # Allow all actions publicly
    authentication_classes = []  # Clear any authentication classes

    @action(detail=False, methods=['get'])
    def by_workshop(self, request):
        """Get services by workshop ID"""
        workshop_id = request.query_params.get('workshop_id')
        if workshop_id:
            services = RepairService.objects.filter(workshop_id=workshop_id, is_service_active=True)
            serializer = self.get_serializer(services, many=True)
            return Response(serializer.data)
        return Response([])


# registration/views.py - Add this viewset

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import CustomerServiceRequest
from .serializers import CustomerServiceRequestSerializer, CustomerServiceRequestCreateSerializer


# class CustomerServiceRequestViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for public Customer Service Requests - NO AUTHENTICATION REQUIRED
#     Anyone can create a service request
#     """
#     queryset = CustomerServiceRequest.objects.all().order_by('-request_created')
#     permission_classes = [AllowAny]  # No authentication required
#     authentication_classes = []  # No authentication

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return CustomerServiceRequestCreateSerializer
#         return CustomerServiceRequestSerializer

#     def get_queryset(self):
#         queryset = CustomerServiceRequest.objects.all().order_by('-request_created')

#         # Optional: filter by phone number to let users check their requests
#         phone = self.request.query_params.get('phone')
#         if phone:
#             queryset = queryset.filter(customer_phone__icontains=phone)

#         # Filter by request code
#         request_code = self.request.query_params.get('request_code')
#         if request_code:
#             queryset = queryset.filter(request_code__icontains=request_code)

#         return queryset

#     @action(detail=False, methods=['get'], permission_classes=[AllowAny])
#     def track(self, request):
#         """Track a request by phone number or request code"""
#         phone = request.query_params.get('phone')
#         request_code = request.query_params.get('request_code')

#         if phone:
#             requests = CustomerServiceRequest.objects.filter(customer_phone=phone).order_by('-request_created')
#             serializer = self.get_serializer(requests, many=True)
#             return Response({'success': True, 'count': requests.count(), 'data': serializer.data})

#         if request_code:
#             try:
#                 req = CustomerServiceRequest.objects.get(request_code=request_code)
#                 serializer = self.get_serializer(req)
#                 return Response({'success': True, 'data': serializer.data})
#             except CustomerServiceRequest.DoesNotExist:
#                 return Response({'success': False, 'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

#         return Response({'success': False, 'error': 'Please provide phone or request_code'},
#                       status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=False, methods=['post'], permission_classes=[AllowAny])
#     def submit(self, request):
#         """Public endpoint to submit a service request"""
#         serializer = CustomerServiceRequestCreateSerializer(data=request.data)

#         if serializer.is_valid():
#             service_request = serializer.save()
#             return Response({
#                 'success': True,
#                 'message': 'Service request submitted successfully',
#                 'request_code': service_request.request_code,
#                 'data': CustomerServiceRequestSerializer(service_request).data
#             }, status=status.HTTP_201_CREATED)

#         return Response({
#             'success': False,
#             'errors': serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)







# class CustomerServiceRequestViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for public Customer Service Requests - NO AUTHENTICATION REQUIRED
#     Anyone can create a service request
#     """
#     queryset = CustomerServiceRequest.objects.all().order_by('-request_created')
#     permission_classes = [AllowAny]  # No authentication required
#     authentication_classes = []  # No authentication

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return CustomerServiceRequestCreateSerializer
#         return CustomerServiceRequestSerializer

#     def get_queryset(self):
#         queryset = CustomerServiceRequest.objects.all().order_by('-request_created')

#         # Optional: filter by phone number to let users check their requests
#         phone = self.request.query_params.get('phone')
#         if phone:
#             queryset = queryset.filter(customer_phone__icontains=phone)

#         # Filter by request code
#         request_code = self.request.query_params.get('request_code')
#         if request_code:
#             queryset = queryset.filter(request_code__icontains=request_code)

#         return queryset

#     @action(detail=False, methods=['get'], permission_classes=[AllowAny])
#     def track(self, request):
#         """Track a request by phone number or request code"""
#         phone = request.query_params.get('phone')
#         request_code = request.query_params.get('request_code')

#         if phone:
#             requests = CustomerServiceRequest.objects.filter(customer_phone=phone).order_by('-request_created')
#             serializer = self.get_serializer(requests, many=True)
#             return Response({'success': True, 'count': requests.count(), 'data': serializer.data})

#         if request_code:
#             try:
#                 req = CustomerServiceRequest.objects.get(request_code=request_code)
#                 serializer = self.get_serializer(req)
#                 return Response({'success': True, 'data': serializer.data})
#             except CustomerServiceRequest.DoesNotExist:
#                 return Response({'success': False, 'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

#         return Response({'success': False, 'error': 'Please provide phone or request_code'},
#                       status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=False, methods=['post'], permission_classes=[AllowAny])
#     def submit(self, request):
#         """Public endpoint to submit a service request"""
#         serializer = CustomerServiceRequestCreateSerializer(data=request.data)

#         if serializer.is_valid():
#             service_request = serializer.save()
#             return Response({
#                 'success': True,
#                 'message': 'Service request submitted successfully',
#                 'request_code': service_request.request_code,
#                 'data': CustomerServiceRequestSerializer(service_request).data
#             }, status=status.HTTP_201_CREATED)

#         return Response({
#             'success': False,
#             'errors': serializer.errors
#         }, status=status.HTTP_400_BAD_REQUEST)

#     # ============ ADD THIS ACTION FOR STATUS UPDATE ============
#     @action(detail=True, methods=['patch'], permission_classes=[AllowAny])
#     def update_status(self, request, pk=None):
#         """
#         Update the status of a service request
#         PATCH /api/public-requests/{id}/update-status/
#         """
#         try:
#             service_request = self.get_object()
#             new_status = request.data.get('request_status')

#             if not new_status:
#                 return Response({
#                     'success': False,
#                     'message': 'request_status is required'
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Validate status
#             valid_statuses = dict(CustomerServiceRequest.REQUEST_STATUS).keys()
#             if new_status not in valid_statuses:
#                 return Response({
#                     'success': False,
#                     'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Update the status
#             service_request.request_status = new_status

#             # Update approval/fixing fields if provided
#             if 'approved_by' in request.data:
#                 service_request.approved_by = request.data['approved_by']
#             if 'approved_at' in request.data:
#                 service_request.approved_at = request.data['approved_at']
#             if 'fixed_by' in request.data:
#                 service_request.fixed_by = request.data['fixed_by']
#             if 'fixed_at' in request.data:
#                 service_request.fixed_at = request.data['fixed_at']

#             service_request.save()

#             return Response({
#                 'success': True,
#                 'message': f'Status updated to {new_status}',
#                 'data': CustomerServiceRequestSerializer(service_request).data
#             }, status=status.HTTP_200_OK)

#         except CustomerServiceRequest.DoesNotExist:
#             return Response({
#                 'success': False,
#                 'message': 'Request not found'
#             }, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({
#                 'success': False,
#                 'message': str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





# registration/views.py - UPDATE the CustomerServiceRequestViewSet

class CustomerServiceRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for public Customer Service Requests - NO AUTHENTICATION REQUIRED
    Anyone can create a service request
    """
    queryset = CustomerServiceRequest.objects.all().order_by('-request_created')
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomerServiceRequestCreateSerializer
        return CustomerServiceRequestSerializer

    def get_queryset(self):
        queryset = CustomerServiceRequest.objects.all().order_by('-request_created')

        phone = self.request.query_params.get('phone')
        if phone:
            queryset = queryset.filter(customer_phone__icontains=phone)

        request_code = self.request.query_params.get('request_code')
        if request_code:
            queryset = queryset.filter(request_code__icontains=request_code)

        return queryset

    def partial_update(self, request, *args, **kwargs):
        """
        Partial update - used for status updates and budget updates
        This is the same approach you use for updating budget
        """
        instance = self.get_object()

        # Make request.data mutable if needed
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True

        # Add updated_by if not present
        if 'updated_by' not in request.data:
            request.data['updated_by'] = request.data.get('updated_by', 'Admin User')

        # Handle status update with approval fields
        if 'request_status' in request.data:
            new_status = request.data['request_status']
            valid_statuses = dict(CustomerServiceRequest.REQUEST_STATUS).keys()

            if new_status not in valid_statuses:
                return Response({
                    'success': False,
                    'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # If status is changing to accepted, add approval info
            if new_status == 'accepted' and 'approved_by' not in request.data:
                request.data['approved_by'] = request.data.get('updated_by', 'Admin User')
                request.data['approved_at'] = timezone.now().isoformat()

            # If status is changing to in_progress or completed, add fixing info
            if new_status in ['in_progress', 'completed'] and 'fixed_by' not in request.data:
                request.data['fixed_by'] = request.data.get('updated_by', 'Admin User')
                request.data['fixed_at'] = timezone.now().isoformat()

        # Use the serializer for partial update
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return updated data
        return Response({
            'success': True,
            'message': f'Request updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def track(self, request):
        """Track a request by phone number or request code"""
        phone = request.query_params.get('phone')
        request_code = request.query_params.get('request_code')

        if phone:
            requests = CustomerServiceRequest.objects.filter(customer_phone=phone).order_by('-request_created')
            serializer = self.get_serializer(requests, many=True)
            return Response({'success': True, 'count': requests.count(), 'data': serializer.data})

        if request_code:
            try:
                req = CustomerServiceRequest.objects.get(request_code=request_code)
                serializer = self.get_serializer(req)
                return Response({'success': True, 'data': serializer.data})
            except CustomerServiceRequest.DoesNotExist:
                return Response({'success': False, 'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'success': False, 'error': 'Please provide phone or request_code'},
                       status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def submit(self, request):
        """Public endpoint to submit a service request"""
        serializer = CustomerServiceRequestCreateSerializer(data=request.data)

        if serializer.is_valid():
            service_request = serializer.save()
            return Response({
                'success': True,
                'message': 'Service request submitted successfully',
                'request_code': service_request.request_code,
                'data': CustomerServiceRequestSerializer(service_request).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



class WorkshopQuoteViewSet(viewsets.ModelViewSet):
    """Complete CRUD for WorkshopQuote"""
    queryset = WorkshopQuote.objects.all().order_by('-quote_created')

    def get_serializer_class(self):
        if self.action == 'create':
            return WorkshopQuoteCreateSerializer
        return WorkshopQuoteSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a quote"""
        quote = self.get_object()

        if quote.quote_status != 'pending':
            return Response({'error': 'Quote cannot be accepted'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            quote.accept_quote()
            return Response({'success': True, 'message': 'Quote accepted'})

    @action(detail=False, methods=['get'])
    def by_request(self, request):
        """Get quotes by request code"""
        request_code = request.query_params.get('request_code')
        if request_code:
            quotes = WorkshopQuote.objects.filter(customer_request__request_code=request_code)
            serializer = self.get_serializer(quotes, many=True)
            return Response(serializer.data)
        return Response([])


class ServiceAppointmentViewSet(viewsets.ModelViewSet):
    """Complete CRUD for ServiceAppointment"""
    queryset = ServiceAppointment.objects.all().order_by('-appointment_created')
    serializer_class = ServiceAppointmentSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = ServiceAppointment.objects.all().order_by('-appointment_created')

        # Filter by client if authenticated
        if self.request.user.is_authenticated:
            client_id = self.request.query_params.get('client_id')
            if client_id:
                queryset = queryset.filter(client_id=client_id)
            elif self.action != 'create':
                queryset = queryset.filter(client=self.request.user)

        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(appointment_status=status)

        return queryset

    @action(detail=False, methods=['get'])
    def my_appointments(self, request):
        """Get current user's appointments"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        appointments = ServiceAppointment.objects.filter(client=request.user).order_by('-appointment_date')
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update appointment status"""
        appointment = self.get_object()
        new_status = request.data.get('appointment_status')

        if not new_status:
            return Response({'error': 'status required'}, status=status.HTTP_400_BAD_REQUEST)

        appointment.appointment_status = new_status
        appointment.save()

        return Response({'success': True, 'status': new_status})

    @action(detail=True, methods=['delete'])
    def cancel(self, request, pk=None):
        """Cancel appointment"""
        appointment = self.get_object()

        if appointment.client != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        appointment.appointment_status = 'cancelled'
        appointment.save()

        return Response({'success': True, 'message': 'Appointment cancelled'})


class ApproveViewSet(viewsets.ModelViewSet):
    """Complete CRUD for Approve records"""
    queryset = Approve.objects.all().order_by('-created_at')
    serializer_class = ApproveSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]









# =================================//FIX  PROVIDERS//============================
# workshop/views.py - Add Garage ViewSet with FULL PUBLIC ACCESS

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # IMPORTANT: Public access
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import Garage
from .serializers import (
    GarageSerializer, GarageCreateUpdateSerializer
)
from django.core.paginator import Paginator
import logging

logger = logging.getLogger(__name__)


# ======================= GARAGE VIEWSET - FULL PUBLIC CRUD =======================
class GarageViewSet(viewsets.ModelViewSet):
    """
    Garage ViewSet - COMPLETE PUBLIC CRUD OPERATIONS
    No authentication required for any operation
    """
    queryset = Garage.objects.all().order_by('-created_at')
    permission_classes = [AllowAny]  # Public access for all actions
    authentication_classes = []  # No authentication

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action in ['create', 'update', 'partial_update']:
            return GarageCreateUpdateSerializer
        return GarageSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = Garage.objects.all().order_by('-created_at')

        # Search by name, address, city, phone, email
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(city__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )

        # Filter by city
        city = self.request.query_params.get('city', '')
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Filter by open status
        is_open = self.request.query_params.get('is_open', '')
        if is_open:
            queryset = queryset.filter(is_open=is_open.lower() == 'true')

        # Filter by active status
        is_active = self.request.query_params.get('is_active', '')
        if is_active:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by delivery available
        delivery = self.request.query_params.get('delivery_available', '')
        if delivery:
            queryset = queryset.filter(delivery_available=delivery.lower() == 'true')

        # Filter by verified
        verified = self.request.query_params.get('is_verified', '')
        if verified:
            queryset = queryset.filter(is_verified=verified.lower() == 'true')

        # Filter by minimum rating
        min_rating = self.request.query_params.get('min_rating', '')
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except ValueError:
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        """List all garages with pagination"""
        queryset = self.get_queryset()

        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))

        paginator = Paginator(queryset, page_size)

        if page > paginator.num_pages:
            return Response({
                'count': paginator.count,
                'next': None,
                'previous': None,
                'results': []
            })

        page_obj = paginator.page(page)
        serializer = self.get_serializer(page_obj, many=True)

        return Response({
            'count': paginator.count,
            'next': paginator.page(page).has_next() and f"?page={page + 1}&page_size={page_size}" or None,
            'previous': page > 1 and f"?page={page - 1}&page_size={page_size}" or None,
            'results': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """Create a new garage - FULL PUBLIC ACCESS"""
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            garage = serializer.save()
            return Response({
                'success': True,
                'message': 'Garage created successfully',
                'data': GarageSerializer(garage).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update a garage - FULL PUBLIC ACCESS"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            garage = serializer.save()
            return Response({
                'success': True,
                'message': 'Garage updated successfully',
                'data': GarageSerializer(garage).data
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Delete a garage - FULL PUBLIC ACCESS"""
        instance = self.get_object()
        instance.delete()
        return Response({
            'success': True,
            'message': 'Garage deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def stats(self, request):
        """Get garage statistics"""
        queryset = Garage.objects.all()

        stats = {
            'total_garages': queryset.count(),
            'active_garages': queryset.filter(is_active=True).count(),
            'open_now': queryset.filter(is_open=True, is_active=True).count(),
            'verified_garages': queryset.filter(is_verified=True).count(),
            'delivery_available': queryset.filter(delivery_available=True).count(),
            'average_rating': queryset.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
            'cities': queryset.exclude(city__isnull=True).exclude(city__exact='').values_list('city', flat=True).distinct().count()
        }

        return Response({'success': True, 'stats': stats})

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def cities(self, request):
        """Get list of all cities with garages"""
        cities = Garage.objects.exclude(
            city__isnull=True
        ).exclude(
            city__exact=''
        ).values_list('city', flat=True).distinct().order_by('city')

        return Response({'success': True, 'cities': list(cities)})

    @action(detail=True, methods=['patch'], permission_classes=[AllowAny])
    def toggle_status(self, request, pk=None):
        """Toggle garage open status"""
        garage = self.get_object()
        garage.is_open = not garage.is_open
        garage.save()

        return Response({
            'success': True,
            'message': f'Garage is now {"open" if garage.is_open else "closed"}',
            'is_open': garage.is_open
        })

    @action(detail=True, methods=['patch'], permission_classes=[AllowAny])
    def verify(self, request, pk=None):
        """Verify a garage"""
        garage = self.get_object()
        garage.is_verified = True
        garage.save()

        return Response({
            'success': True,
            'message': 'Garage verified successfully',
            'is_verified': True
        })

    @action(detail=True, methods=['patch'], permission_classes=[AllowAny])
    def activate(self, request, pk=None):
        """Activate/deactivate a garage"""
        garage = self.get_object()
        garage.is_active = not garage.is_active
        garage.save()

        return Response({
            'success': True,
            'message': f'Garage is now {"active" if garage.is_active else "inactive"}',
            'is_active': garage.is_active
        })

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def nearby(self, request):
        """Find nearby garages based on coordinates"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = float(request.query_params.get('radius', 10))  # km

        if not lat or not lng:
            return Response({
                'success': False,
                'error': 'Please provide latitude and longitude'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return Response({
                'success': False,
                'error': 'Invalid coordinates'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Simple distance calculation (approximate)
        from math import radians, sin, cos, sqrt, atan2

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c

        garages = Garage.objects.filter(is_active=True)
        nearby_garages = []

        for garage in garages:
            if garage.latitude and garage.longitude:
                distance = haversine(lat, lng, float(garage.latitude), float(garage.longitude))
                if distance <= radius:
                    garage_data = GarageSerializer(garage).data
                    garage_data['distance_km'] = round(distance, 2)
                    nearby_garages.append(garage_data)

        nearby_garages.sort(key=lambda x: x['distance_km'])

        return Response({
            'success': True,
            'count': len(nearby_garages),
            'results': nearby_garages
        })


# ======================= EXISTING VIEWSETS (Keep your existing ones) =======================
# AutoWorkshopViewSet, RepairServiceViewSet, etc...
# Make sure to add permission_classes = [AllowAny] and authentication_classes = [] to all if you want public access