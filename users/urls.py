from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerRequestViewSet,
    WorkshopQuoteViewSet,
    ServiceAppointmentViewSet,
    AutoWorkshopViewSet,
    RepairServiceViewSet,
    CustomerReqViewSet,
)

router = DefaultRouter()
router.register(r'customer-requests', CustomerRequestViewSet, basename='customer-request')
router.register(r'workshop-quotes', WorkshopQuoteViewSet, basename='workshop-quote')
router.register(r'service-appointments', ServiceAppointmentViewSet, basename='service-appointment')
router.register(r'auto-workshops', AutoWorkshopViewSet, basename='auto-workshop')
router.register(r'repair-services', RepairServiceViewSet, basename='repair-service')
router.register(r'customer-reqs', CustomerReqViewSet, basename='customerrequest')

urlpatterns = [
    path('', include(router.urls)),

    # Additional endpoints for customer requests
    path('customer-requests/<str:request_code>/submit-quote/',
         CustomerRequestViewSet.as_view({'post': 'submit_quote'}),
         name='submit-quote'),

    path('customer-requests/<str:request_code>/accept-quote/',
         CustomerRequestViewSet.as_view({'post': 'accept_quote'}),
         name='accept-quote'),

    # Statistics endpoints
    path('stats/requests/',
         CustomerRequestViewSet.as_view({'get': 'request_statistics'}),
         name='request-statistics'),

    path('stats/appointments/',
         ServiceAppointmentViewSet.as_view({'get': 'appointment_statistics'}),
         name='appointment-statistics'),
]







# # registration/urls.py
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import (
#     CustomerRequestViewSet,
#     WorkshopQuoteViewSet,
#     ServiceAppointmentViewSet,
#     AutoWorkshopViewSet,
#     RepairServiceViewSet,
# )

# router = DefaultRouter()
# router.register(r'customer-reqs', CustomerRequestViewSet, basename='customer-request')
# router.register(r'workshop-quotes', WorkshopQuoteViewSet, basename='workshop-quote')
# router.register(r'service-appointments', ServiceAppointmentViewSet, basename='service-appointment')
# router.register(r'auto-workshops', AutoWorkshopViewSet, basename='auto-workshop')
# router.register(r'repair-services', RepairServiceViewSet, basename='repair-service')

# urlpatterns = [
#     path('', include(router.urls)),

#     # Statistics endpoints
#     path('stats/requests/', CustomerRequestViewSet.as_view({'get': 'my_requests'}), name='request-stats'),
#     path('stats/appointments/', ServiceAppointmentViewSet.as_view({'get': 'upcoming'}), name='appointment-stats'),
# ]