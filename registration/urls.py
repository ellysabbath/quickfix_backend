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
# =========================// JWT TOKEN SETTINGS//===========================

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# ============================//JWT TOKEN SETTINGS//===========================

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
router.register(r'api/approve', views.ApproveViewSet, basename='approve')

@ensure_csrf_cookie
def get_csrf_token(request):
    from django.middleware.csrf import get_token
    return JsonResponse({'csrfToken': get_token(request)})

urlpatterns = [
    path('test/', views.TestView.as_view(), name='test_api'),
    path('api/auth/csrf/', get_csrf_token, name='csrf_token'),
    path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path('api/auth/debug-login/', views.DebugLoginView.as_view(), name='debug-login'),
    path('api/auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/test/', views.TestView.as_view(), name='test'),

    path('api/auth/logout-all/', views.LogoutAllView.as_view(), name='logout_all'),
    path('auth/stage1/personal-info/', views.Stage1PersonalInfoView.as_view(), name='stage1'),
    path('auth/stage2/contact-details/', views.Stage2ContactDetailsView.as_view(), name='stage2'),
    path('auth/stage3/location/', views.Stage3LocationView.as_view(), name='stage3'),
    path('auth/stage4/security/', views.Stage4SecurityView.as_view(), name='stage4'),
    path('auth/verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('auth/resend-otp/', views.ResendOTPView.as_view(), name='resend_otp'),
     path('api/send-otp/', views.SendOTPView.as_view(), name='send-otp'),




    # ===================================//JWT TOKEN SETTINGS//==============================
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # =================================//JWT TOKEN SETTINGS//================================

 # Password Reset Endpoints
    path('auth/password-reset/request/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/verify-otp/', views.VerifyPasswordResetOTPView.as_view(), name='verify_password_reset_otp'),
    path('auth/password-reset/complete/', views.CompletePasswordResetView.as_view(), name='complete_password_reset'),
    path('', include(router.urls)),




]