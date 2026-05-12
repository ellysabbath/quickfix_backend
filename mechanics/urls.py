# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GarageViewSet, ServiceTypeViewSet, ServiceRequestViewSet,
    ServiceRequestUpdateViewSet, ServiceRequestAttachmentViewSet
)

router = DefaultRouter()

# Register all ViewSets with updated base names
router.register(r'garage-select', GarageViewSet, basename='garage')
router.register(r'service-types', ServiceTypeViewSet, basename='service-type')
router.register(r'service-requests', ServiceRequestViewSet, basename='service-request')
router.register(r'request-updates', ServiceRequestUpdateViewSet, basename='request-update')
router.register(r'request-attachments', ServiceRequestAttachmentViewSet, basename='request-attachment')

urlpatterns = [
    path('', include(router.urls)),
    
    # Additional custom endpoints
    path('garage-select/cities/', 
         GarageViewSet.as_view({'get': 'cities'}), 
         name='garage-cities'),
    
    path('garage-select/statistics/', 
         GarageViewSet.as_view({'get': 'statistics'}), 
         name='garage-statistics'),
    
    path('service-requests/statistics/', 
         ServiceRequestViewSet.as_view({'get': 'statistics'}), 
         name='service-request-statistics'),
    
    path('service-requests/search-by-name/', 
         ServiceRequestViewSet.as_view({'get': 'search_by_name'}), 
         name='service-request-search'),
    
    # Individual garage endpoints
    path('garage-select/<int:pk>/service-requests/', 
         GarageViewSet.as_view({'get': 'service_requests'}), 
         name='garage-service-requests'),
]