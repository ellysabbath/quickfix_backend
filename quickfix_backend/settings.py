"""
Django settings for quickfix_backend project.
JWT Version with Token Blacklist Support
"""

import os
from pathlib import Path
from datetime import timedelta

# ==================== BASE PATHS ====================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== SECURITY SETTINGS ====================
SECRET_KEY = 'django-insecure-33y6f00ami&7(3!f^fv4h&mh#o-2*8i9klsw6t)6)u%gg4z_9)'
DEBUG = True

# ALLOW ALL HOSTS FOR DEVELOPMENT
ALLOWED_HOSTS = ['*']

# ==================== CORS CONFIGURATION ====================
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins during development
CORS_ALLOW_CREDENTIALS = True

# Trusted origins
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8081',
    'http://127.0.0.1:8081',
    'http://192.168.137.1:8081',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'exp://192.168.137.1:8081',
]

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
]

# Custom user model
AUTH_USER_MODEL = 'users.CustomUser'

# ==================== MIDDLEWARE ====================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first
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
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'registration/templates',
        ],
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
        'OPTIONS': {'min_length': 6}
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
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== REST FRAMEWORK CONFIGURATION ====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT primary auth
        'rest_framework.authentication.SessionAuthentication',       # Fallback
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Default to authenticated
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# ==================== SIMPLE JWT CONFIGURATION ====================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    # Custom claims serializer
    'TOKEN_OBTAIN_SERIALIZER': 'users.serializers.CustomTokenObtainPairSerializer',
}

# ==================== EMAIL CONFIGURATION ====================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'mwananjelaelisha36@gmail.com'
EMAIL_HOST_PASSWORD = 'zpfoijsqdxofsren'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
EMAIL_TIMEOUT = 30

if DEBUG:
    EMAIL_SUBJECT_PREFIX = '[QuickFix Dev] '
else:
    EMAIL_SUBJECT_PREFIX = '[QuickFix] '

# ==================== SESSION & CSRF CONFIGURATION ====================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True

# CSRF settings
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_COOKIE_AGE = 31449600
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False

# ==================== LOGGING CONFIGURATION ====================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/debug.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'users': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'registration': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ==================== APP SPECIFIC SETTINGS ====================
# Registration settings
REGISTRATION_STAGES = {
    'PERSONAL_INFO': 1,
    'CONTACT_DETAILS': 2,
    'LOCATION': 3,
    'SECURITY': 4,
    'COMPLETE': 5,
}

# OTP settings
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 6

# Password reset settings
PASSWORD_RESET_TIMEOUT = 900  # 15 minutes

# App settings
APP_NAME = 'QuickFix Automotive'
APP_SUPPORT_EMAIL = 'support@quickfixauto.com'

# ==================== CREATE NECESSARY DIRECTORIES ====================
# Create directories if they don't exist
directories = [
    BASE_DIR / 'logs',
    BASE_DIR / 'media',
    BASE_DIR / 'media/profile_pictures',
]

for directory in directories:
    directory.mkdir(parents=True, exist_ok=True)

# ==================== PRINT CONFIGURATION STATUS ====================
print("\n" + "="*70)
print("✅ Django Settings Loaded Successfully!")
print("="*70)
print(f"📡 DEBUG Mode: {DEBUG}")
print(f"🌐 Allowed Hosts: {ALLOWED_HOSTS}")
print(f"🔐 CORS Allow All Origins: {CORS_ALLOW_ALL_ORIGINS}")
print(f"👤 Auth User Model: {AUTH_USER_MODEL}")
print(f"🔑 JWT Token Blacklist Enabled: True")
print(f"📧 Email Backend: {EMAIL_BACKEND}")
print("="*70)
print("\n✅ Authentication Classes:")
print("   • JWTAuthentication (Primary)")
print("   • SessionAuthentication (Fallback)")
print(f"\n🔄 JWT Token Lifetime:")
print(f"   • Access Token: {SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']}")
print(f"   • Refresh Token: {SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']}")
print(f"   • Token Rotation: {SIMPLE_JWT['ROTATE_REFRESH_TOKENS']}")
print(f"   • Blacklist After Rotation: {SIMPLE_JWT['BLACKLIST_AFTER_ROTATION']}")
print("\n" + "="*70)
print("⚠️  DEVELOPMENT SETTINGS - SECURE FOR PRODUCTION!")
print("="*70 + "\n")