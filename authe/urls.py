# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Registration endpoints
    path('register/check-phone/', views.check_phone_number, name='check_phone'),
    path('register/send-otp/', views.send_otp, name='send_otp'),
    path('register/verify-otp/', views.verify_otp_and_register, name='verify_otp'),
    path('register/resend-otp/', views.resend_otp, name='resend_otp'),
    
    # Authentication endpoints
    path('login/', views.login_with_phone, name='login'),
    path('logout/', views.logout, name='logout'),
    
    # Profile endpoints
    path('profile/', views.get_user_profile, name='get_profile'),
    path('profile/update/', views.update_user_profile, name='update_profile'),
    path('profile/update-picture/', views.update_profile_picture, name='update_picture'),
    path('profile/field/<str:field_name>/', views.delete_profile_field, name='delete_field'),
    path('profile/delete-account/', views.delete_user_account, name='delete_account'),
    
    # Users endpoint
    path('users/all/', views.AllUsersView.as_view(), name='all_users'),
    
    # Test endpoint
    path('test/', views.test_api, name='test_api'),
]