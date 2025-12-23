from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from . import views



from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
# dashboard/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    ServiceViewSet, GarageViewSet, GarageServiceViewSet,
    ServiceDetailViewSet,
    AdminGarageViewSet, AdminServiceViewSet,
    AdminGarageServiceViewSet, AdminServiceDetailViewSet,
    AdminBookingViewSet
)

router = DefaultRouter()

# Regular endpoints
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'garages', GarageViewSet, basename='garage')
router.register(r'garage-services', GarageServiceViewSet, basename='garage-service')
router.register(r'service-details', ServiceDetailViewSet, basename='service-detail')


# ================================ // END PROJECT //================
router.register(r'api/bookings',views.BookingsViewSet, basename='bookings')
router.register(r'api/service', views.BookingServiceViewSet, basename='services')
router.register(r'api/garage', views.BookingGarageViewSet, basename='garages')






# Admin endpoints
router.register(r'api/garages', AdminGarageViewSet, basename='admin-garages')
router.register(r'api/services', AdminServiceViewSet, basename='admin-services')
router.register(r'api/garage-services', AdminGarageServiceViewSet, basename='admin-garage-services')
router.register(r'admin/service-details', AdminServiceDetailViewSet, basename='admin-service-details')
router.register(r'bookings', AdminBookingViewSet, basename='admin-bookings')



# ===============================//   MANAGE USERS  //=================
router.register(r'users', views.UserViewSet, basename='user')


@ensure_csrf_cookie
def get_csrf_token(request):
    from django.middleware.csrf import get_token
    return JsonResponse({'csrfToken': get_token(request)})

urlpatterns = [
    path('test/', views.TestView.as_view(), name='test_api'),
    path('api/auth/csrf/', get_csrf_token, name='csrf_token'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/stage1/personal-info/', views.Stage1PersonalInfoView.as_view(), name='stage1'),
    path('auth/stage2/contact-details/', views.Stage2ContactDetailsView.as_view(), name='stage2'),
    path('auth/stage3/location/', views.Stage3LocationView.as_view(), name='stage3'),
    path('auth/stage4/security/', views.Stage4SecurityView.as_view(), name='stage4'),
    path('auth/verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),

 # Password Reset Endpoints
    path('auth/password-reset/request/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/verify-otp/', views.VerifyPasswordResetOTPView.as_view(), name='verify_password_reset_otp'),
    path('auth/password-reset/complete/', views.CompletePasswordResetView.as_view(), name='complete_password_reset'),
    path('', include(router.urls)),



       
]