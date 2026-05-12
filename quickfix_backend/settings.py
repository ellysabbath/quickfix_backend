# """
# Django settings for quickfix_backend project.
# Production-Ready Version for PythonAnywhere Deployment
# """

# from pathlib import Path
# from datetime import timedelta

# # ==================== BASE PATHS ====================
# BASE_DIR = Path(__file__).resolve().parent.parent

# # ==================== SECURITY SETTINGS ====================
# # Generate a new secure key before production: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# SECRET_KEY = 'django-insecure-33y6f00ami&7(3!f^fv4h&mh#o-2*8i9klsw6t)6)u%gg4z_9)'  # CHANGE FOR PRODUCTION
# DEBUG = True  # Set to True for initial testing, then False

# # Production domain - REPLACE WITH YOUR ACTUAL DOMAIN
# ALLOWED_HOSTS = [
#     'AutoFix.pythonanywhere.com',
#     'www.AutoFix.pythonanywhere.com',
# ]

# # ==================== CORS CONFIGURATION ====================
# # Disable open CORS in production
# CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOW_CREDENTIALS = True

# # Production trusted origins
# CSRF_TRUSTED_ORIGINS = [
#     'https://AutoFix.pythonanywhere.com',
#     'https://www.AutoFix.pythonanywhere.com',

# ]

# # Explicitly allowed origins for production
# CORS_ALLOWED_ORIGINS = [
#     'https://AutoFix.pythonanywhere.com',
#     'https://www.AutoFix.pythonanywhere.com',
# ]



# # Additional CORS settings for mobile apps
# CORS_ALLOW_METHODS = [
#     'DELETE',
#     'GET',
#     'OPTIONS',
#     'PATCH',
#     'POST',
#     'PUT',
# ]

# CORS_ALLOW_HEADERS = [
#     'accept',
#     'accept-encoding',
#     'authorization',
#     'content-type',
#     'dnt',
#     'origin',
#     'user-agent',
#     'x-csrftoken',
#     'x-requested-with',
# ]

# # ==================== APPLICATION DEFINITION ====================
# INSTALLED_APPS = [
#     # Django core apps
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',

#     # Third-party apps
#     'rest_framework',
#     'corsheaders',
#     'django_filters',
#     'rest_framework_simplejwt.token_blacklist',  # JWT token blacklist

#     # Your custom apps
#     'users',
#     'registration',
#     'mechanics',
# ]

# # Custom user model
# AUTH_USER_MODEL = 'users.CustomUser'

# # ==================== MIDDLEWARE ====================
# MIDDLEWARE = [
#     'corsheaders.middleware.CorsMiddleware',  # Must be first
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]

# ROOT_URLCONF = 'quickfix_backend.urls'

# # ==================== TEMPLATES ====================
# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [
#             BASE_DIR / 'templates',
#             BASE_DIR / 'registration/templates',
#         ],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]

# WSGI_APPLICATION = 'quickfix_backend.wsgi.application'

# # ==================== DATABASE ====================
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# # ==================== PASSWORD VALIDATION ====================
# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#         'OPTIONS': {'min_length': 6}
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]

# # ==================== INTERNATIONALIZATION ====================
# LANGUAGE_CODE = 'en-us'
# TIME_ZONE = 'UTC'
# USE_I18N = True
# USE_TZ = True

# # ==================== STATIC & MEDIA FILES ====================
# # CRITICAL: These settings must match your PythonAnywhere dashboard configuration
# STATIC_URL = '/static/'
# STATIC_ROOT = BASE_DIR / 'staticfiles'  # PythonAnywhere will serve files from here
# STATICFILES_DIRS = [BASE_DIR / 'static']  # Your development static files

# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'  # User uploaded files location

# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# # ==================== REST FRAMEWORK CONFIGURATION ====================
# REST_FRAMEWORK = {
#     'DEFAULT_AUTHENTICATION_CLASSES': [
#         'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT primary auth
#         # 'rest_framework.authentication.SessionAuthentication',       # Fallback
#     ],
#     'DEFAULT_PERMISSION_CLASSES': [
#         'rest_framework.permissions.IsAuthenticated',  # Default to authenticated
#     ],
#     'DEFAULT_PARSER_CLASSES': [
#         'rest_framework.parsers.JSONParser',
#         'rest_framework.parsers.FormParser',
#         'rest_framework.parsers.MultiPartParser',
#     ],
#     'DEFAULT_RENDERER_CLASSES': [
#         'rest_framework.renderers.JSONRenderer',
#         # 'rest_framework.renderers.BrowsableAPIRenderer',  # Optional: Disable in production
#     ],
# }

# # ==================== SIMPLE JWT CONFIGURATION ====================
# SIMPLE_JWT = {
#     'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
#     'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
#     'ROTATE_REFRESH_TOKENS': True,
#     'BLACKLIST_AFTER_ROTATION': True,
#     'UPDATE_LAST_LOGIN': True,

#     'ALGORITHM': 'HS256',
#     'SIGNING_KEY': SECRET_KEY,
#     'VERIFYING_KEY': None,

#     'AUTH_HEADER_TYPES': ('Bearer',),
#     'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
#     'USER_ID_FIELD': 'id',
#     'USER_ID_CLAIM': 'user_id',

#     'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
#     'TOKEN_TYPE_CLAIM': 'token_type',

#     # Custom claims serializer
#     'TOKEN_OBTAIN_SERIALIZER': 'registration.serializers.CustomTokenObtainPairSerializer',

# }

# # ==================== EMAIL CONFIGURATION ====================
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'qfix910@gmail.com'
# EMAIL_HOST_PASSWORD = 'sbntxflapmitoakx'  # Consider using app-specific password
# DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
# SERVER_EMAIL = EMAIL_HOST_USER
# EMAIL_TIMEOUT = 30

# # Always use production prefix since DEBUG=False
# EMAIL_SUBJECT_PREFIX = '[QuickFix] '

# # ==================== SESSION & CSRF CONFIGURATION ====================
# SESSION_ENGINE = 'django.contrib.sessions.backends.db'
# SESSION_COOKIE_NAME = 'sessionid'
# SESSION_COOKIE_AGE = 86400  # 24 hours
# SESSION_COOKIE_SECURE = True  # HTTPS only in production
# SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_SAMESITE = 'Lax'
# SESSION_SAVE_EVERY_REQUEST = True

# # CSRF settings
# CSRF_COOKIE_NAME = 'csrftoken'
# CSRF_COOKIE_AGE = 31449600
# CSRF_COOKIE_SECURE = True  # HTTPS only in production
# CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript
# CSRF_COOKIE_SAMESITE = 'Lax'
# CSRF_USE_SESSIONS = False

# # ==================== LOGGING CONFIGURATION ====================
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '{levelname} {asctime} {module} {message}',
#             'style': '{',
#         },
#         'simple': {
#             'format': '{levelname} {message}',
#             'style': '{',
#         },
#     },
#     'handlers': {
#         'console': {
#             'level': 'INFO',
#             'class': 'logging.StreamHandler',
#             'formatter': 'simple'
#         },
#         'file': {
#             'level': 'INFO',
#             'class': 'logging.FileHandler',
#             'filename': BASE_DIR / 'logs/debug.log',
#             'formatter': 'verbose'
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#         'users': {
#             'handlers': ['console', 'file'],
#             'level': 'DEBUG',
#             'propagate': False,
#         },
#         'registration': {
#             'handlers': ['console', 'file'],
#             'level': 'DEBUG',
#             'propagate': False,
#         },
#     },
# }

# # ==================== APP SPECIFIC SETTINGS ====================
# # Registration settings
# REGISTRATION_STAGES = {
#     'PERSONAL_INFO': 1,
#     'CONTACT_DETAILS': 2,
#     'LOCATION': 3,
#     'SECURITY': 4,
#     'COMPLETE': 5,
# }

# # OTP settings
# OTP_EXPIRY_MINUTES = 10
# OTP_LENGTH = 6

# # Password reset settings
# PASSWORD_RESET_TIMEOUT = 900  # 15 minutes

# # App settings
# APP_NAME = 'QuickFix Automotive'
# APP_SUPPORT_EMAIL = 'support@quickfixauto.com'

# # ==================== CREATE NECESSARY DIRECTORIES ====================
# # Create directories if they don't exist
# directories = [
#     BASE_DIR / 'logs',
#     BASE_DIR / 'media',
#     BASE_DIR / 'media/profile_pictures',
#     BASE_DIR / 'staticfiles',  # Important for collectstatic
# ]

# for directory in directories:
#     directory.mkdir(parents=True, exist_ok=True)





# # ==================================// CONFIRMATIONS SMS//==========================
# # SMS Configuration
# SMS_CONFIG = {
#     # Set to False to disable SMS entirely
#     'ENABLED': True,

#     # Provider options: 'twilio', 'console' (for testing), 'log_only'
#     'PROVIDER': 'console',  # Change to 'twilio' for production

#     # For Twilio (only needed if PROVIDER = 'twilio')
#     'TWILIO_ACCOUNT_SID': 'ACa16171f7318a50e33ad44b103c03963a',
#     'TWILIO_AUTH_TOKEN': 'bc51942b6ebf9581e77956d4db348209',
#     'TWILIO_PHONE_NUMBER': '+12673231287',

#     # Message templates
#     'MESSAGE_TEMPLATES': {
#         'BOOKING_CONFIRMATION': """
# Hello {full_name},

# ✅ Booking Confirmed: #{booking_number}

# 🔧 Service: {service_name}
# 🏢 Garage: {garage_name}
# 📍 Location: {garage_city}
# 📅 Date: {scheduled_date}
# 💰 Total: ${total_price}

# Thank you for your booking!
# Contact: {garage_phone}
#         """,

#         'STATUS_UPDATE': """
# Booking #{booking_number} Update:

# 📊 Status: {status_display}

# Service: {service_name}
# Date: {scheduled_date}

# Contact your garage if needed.
#         """,

#         'REMINDER': """
# Reminder: Booking #{booking_number}

# Your appointment is tomorrow at {scheduled_time}.

# Service: {service_name}
# Garage: {garage_name}

# See you soon!
#         """
#     },

#     # Settings for reminders
#     'SEND_REMINDERS': True,
#     'REMINDER_HOURS_BEFORE': 24,  # Send reminders 24 hours before

#     # Country code for phone numbers (defaults to +1 for US/Canada)
#     'DEFAULT_COUNTRY_CODE': '+255',

#     # SMS character limits
#     'MAX_SMS_LENGTH': 1600,  # Twilio's limit
# }




# # =================================//  AFRICAS TALKING SMS  CONFIGURATIONS=====================
# # quickfix_backend/settings.py - Add this to your existing settings

# # ==================== AFRICA'S TALKING SMS CONFIGURATION ====================
# AFRICAS_TALKING_CONFIG = {
#     # Set to True to enable SMS sending
#     'ENABLED': True,

#     # Africa's Talking credentials
#     # For production, use your actual username and API key
#     # For testing/sandbox, use 'sandbox' as username
#     'USERNAME': 'sandbox',  # Change to your Africa's Talking username
#     'API_KEY': 'atsk_e110831994fd9b074822cef08519329f43758dda59202cfc9adb66d6e1d45740b3717673',  # Your API key

#     # Sender ID (must be registered with Africa's Talking)
#     'SENDER_ID': 'QuickFix',  # Your sender ID

#     # Sandbox settings
#     'SANDBOX_SENDER_ID': 'AFRICASTKNG',  # Default for sandbox

#     # Default country code for Tanzania
#     'DEFAULT_COUNTRY_CODE': '255',

#     # Whether to use + prefix (True = +255XXX, False = 255XXX)
#     'USE_PLUS_PREFIX': True,

#     # Message templates for different notification types
#     'MESSAGE_TEMPLATES': {
#         'APPOINTMENT_CONFIRMATION': """
# ✅ Appointment Confirmed!

# Request: {request_code}
# Service: {service_name}
# Workshop: {workshop_name}
# Date: {appointment_date}
# Time: {appointment_time}
# Price: TZS {price:,.2f}

# Contact: {workshop_phone}
# Thank you for choosing QuickFix!
#         """,

#         'APPOINTMENT_REMINDER': """
# 🔔 Appointment Reminder

# Your appointment is tomorrow!
# Request: {request_code}
# Service: {service_name}
# Workshop: {workshop_name}
# Time: {appointment_time}

# Please arrive on time.
# Contact: {workshop_phone}
#         """,

#         'APPOINTMENT_CANCELLED': """
# ❌ Appointment Cancelled

# Request: {request_code}
# Service: {service_name}
# Workshop: {workshop_name}

# This appointment has been cancelled.
# Contact support for assistance.
#         """,

#         'APPOINTMENT_STATUS_UPDATE': """
# 📋 Appointment Status Update

# Request: {request_code}
# Service: {service_name}
# Workshop: {workshop_name}
# New Status: {status}

# Thank you for using QuickFix!
#         """,

#         'OFFER_RECEIVED': """
# 💰 New Offer Received!

# Request: {request_code}
# Service: {service_name}
# Workshop: {workshop_name}
# Price: TZS {price:,.2f}

# Login to view and accept offer.
#         """,

#         'REQUEST_CREATED': """
# ✅ Service Request Created!

# Request: {request_code}
# Service: {service_name}
# Date: {preferred_date}
# Time: {preferred_time}

# We'll notify you when offers arrive.
#         """,
#     },

#     # SMS character limit (Africa's Talking supports up to 1600)
#     'MAX_SMS_LENGTH': 1600,
# }
# # =================================// END CONFIRMATION SMS//====================================

# # ==================== PRINT CONFIGURATION STATUS ====================
# # print("\n" + "="*70)
# # print("✅ Django Settings Loaded Successfully!")
# # print("="*70)
# # print(f"📡 PRODUCTION MODE: DEBUG = {DEBUG}")
# # print(f"🌐 Allowed Hosts: {ALLOWED_HOSTS}")
# # print(f"🔐 CORS Allow All Origins: {CORS_ALLOW_ALL_ORIGINS}")
# # print(f"👤 Auth User Model: {AUTH_USER_MODEL}")
# # print(f"🔑 JWT Token Blacklist Enabled: True")
# # print("="*70)
# # print("\n📁 STATIC FILES CONFIGURATION:")
# # print(f"   • STATIC_URL: {STATIC_URL}")
# # print(f"   • STATIC_ROOT: {STATIC_ROOT}")
# # print(f"   • MEDIA_URL: {MEDIA_URL}")
# # print(f"   • MEDIA_ROOT: {MEDIA_ROOT}")
# # print("\n✅ Authentication Classes:")
# # print("   • JWTAuthentication (Primary)")
# # print("   • SessionAuthentication (Fallback)")
# # print(f"\n🔄 JWT Token Lifetime:")
# # print(f"   • Access Token: {SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']}")
# # print(f"   • Refresh Token: {SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']}")
# # print("="*70)
# # print("🔧 PYTHONANYWHERE SETUP INSTRUCTIONS:")
# # print("="*70)
# # print("1. In PythonAnywhere Web Dashboard, add these Static File Mappings:")
# # print("   • URL: /static/ → Directory: /home/YOURUSERNAME/quickfix_backend/staticfiles")
# # print("   • URL: /media/ → Directory: /home/YOURUSERNAME/quickfix_backend/media")
# # print("\n2. Run: python manage.py collectstatic")
# # print("\n3. Click RELOAD button in PythonAnywhere Web tab")
# # print("\n4. Test static files: https://yourusername.pythonanywhere.com/static/admin/css/base.css")
# # print("="*70)
# ===============================================================================================================================
# ===============================================================================================================================
# quickfix_backend/settings.py
"""
Django settings for quickfix_backend project.
Complete with Email and SMS notifications
"""

from pathlib import Path
from datetime import timedelta
import os

# ==================== BASE PATHS ====================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== SECURITY SETTINGS ====================
SECRET_KEY = 'django-insecure-33y6f00ami&7(3!f^fv4h&mh#o-2*8i9klsw6t)6)u%gg4z_9)'
DEBUG = True
ALLOWED_HOSTS = ['*']

# ==================== APPLICATION DEFINITION ====================
INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'corsheaders',
    'django_filters',
    'rest_framework_simplejwt.token_blacklist',  # JWT token blacklist

    # Your custom apps
    'users',
    'registration',
    'mechanics',
]

# Custom user model
AUTH_USER_MODEL = 'users.CustomUser'

# ==================== MIDDLEWARE ====================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'quickfix_backend.urls'

# ==================== TEMPLATES ====================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'quickfix_backend.wsgi.application'

# ==================== DATABASE ====================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ==================== PASSWORD VALIDATION ====================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==================== INTERNATIONALIZATION ====================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==================== STATIC & MEDIA FILES ====================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== CORS CONFIGURATION ====================
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ==================== REST FRAMEWORK CONFIGURATION ====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ==================== JWT CONFIGURATION ====================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ==================== EMAIL CONFIGURATION ====================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'qfix910@gmail.com'
EMAIL_HOST_PASSWORD = 'sbntxflapmitoakx'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ==================== AFRICA'S TALKING SMS CONFIGURATION ====================
AFRICAS_TALKING_CONFIG = {
    'ENABLED': True,
    'USERNAME': 'sandbox',
    'API_KEY': 'atsk_e110831994fd9b074822cef08519329f43758dda59202cfc9adb66d6e1d45740b3717673',
    'SENDER_ID': 'QuickFix',
    'SANDBOX_SENDER_ID': 'AFRICASTKNG',
    'DEFAULT_COUNTRY_CODE': '255',
    'USE_PLUS_PREFIX': True,
    'MAX_SMS_LENGTH': 1600,
}

# ==================== COMPANY SETTINGS ====================
COMPANY_NAME = 'QuickFix Auto'
SUPPORT_EMAIL = 'support@quickfixauto.com'
DASHBOARD_URL = 'https://app.quickfixauto.com'
BASE_URL = 'https://api.quickfixauto.com'

# Create necessary directories
os.makedirs(BASE_DIR / 'logs', exist_ok=True)










