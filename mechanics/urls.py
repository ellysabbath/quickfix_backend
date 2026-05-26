# mechanics/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceRequestViewSet, ServiceTypeViewSet

router = DefaultRouter()
router.register(r'service-requests', ServiceRequestViewSet, basename='service-requests')
router.register(r'service-types', ServiceTypeViewSet, basename='service-types')

urlpatterns = [
    path('', include(router.urls)),
]