# registration/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AutoWorkshopViewSet, RepairServiceViewSet, CustomerServiceRequestViewSet,
    WorkshopQuoteViewSet, ServiceAppointmentViewSet, ApproveViewSet,GarageViewSet
)

router = DefaultRouter()
router.register(r'auto-workshops', AutoWorkshopViewSet)
router.register(r'repair-services', RepairServiceViewSet)
router.register(r'public-requests', CustomerServiceRequestViewSet)
router.register(r'workshop-quotes', WorkshopQuoteViewSet)
router.register(r'service-appointments', ServiceAppointmentViewSet)
router.register(r'approvals', ApproveViewSet)
router.register(r'garages', GarageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]