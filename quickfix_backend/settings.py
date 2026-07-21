from pathlib import Path
from datetime import timedelta
import os

# ==================== BASE PATHS ====================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== SECURITY SETTINGS ====================
SECRET_KEY = 'django-insecure-33y6f00ami&7(3!f^fv4h&mh#o-2*8i9klsw6t)6)u%gg4z_9)'
DEBUG = True
ALLOWED_HOSTS = ['*','localhost', '127.0.0.1', '.localhost']

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
    'rest_framework_simplejwt.token_blacklist',

    # Your custom apps
    'authe',
    'registration',
    'mechanics',
    'payments',
]

# Custom user model
AUTH_USER_MODEL = 'authe.User'

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

# ==================== CORS CONFIGURATION - REACT FRONTEND ====================
# React runs on port 3000, Django on port 8000
CORS_ALLOW_ALL_ORIGINS = False  # Don't allow all in production

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',  # Vite dev server (if used)
    'http://127.0.0.1:5173',
]

CORS_ALLOW_CREDENTIALS = True

# Additional CORS settings
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ==================== REST FRAMEWORK CONFIGURATION ====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Allow any for development
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# ==================== JWT CONFIGURATION ====================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# ==================== EMAIL CONFIGURATION ====================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'qfix910@gmail.com'
EMAIL_HOST_PASSWORD = 'sbntxflapmitoakx'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# For development, you can use console backend:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
DASHBOARD_URL = 'http://localhost:3000'  # React dev server
BASE_URL = 'http://127.0.0.1:8000'  # Django dev server
API_BASE_URL = 'http://127.0.0.1:8000/api'

# ==================== FRONTEND URLS ====================
FRONTEND_URLS = {
    'HOME': 'http://localhost:3000',
    'LOGIN': 'http://localhost:3000/login',
    'REGISTER': 'http://localhost:3000/signup',
    'VERIFY_OTP': 'http://localhost:3000/verify-otp',
    'DASHBOARD': 'http://localhost:3000/dashboard',
    'PROFILE': 'http://localhost:3000/profile',
    'BOOKINGS': 'http://localhost:3000/bookings',
    'GARAGES': 'http://localhost:3000/garages',
    'PAYMENTS': 'http://localhost:3000/payments',
}

# ==================== LOGGING CONFIGURATION ====================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ==================== CREATE LOGS DIRECTORY ====================
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# ==================== SESSION CONFIGURATION ====================
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF token

# ==================== CSRF TRUSTED ORIGINS ====================
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

# ==================== FILE UPLOAD SETTINGS ====================
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# ==================== API VERSION ====================
API_VERSION = 'v1'

# ==================== PRINT CONFIGURATION ON STARTUP ====================
print("\n" + "="*60)
print(" QUICKFIX BACKEND CONFIGURATION")
print("="*60)
print(f" Django Server: {BASE_URL}")
print(f" React Frontend: {DASHBOARD_URL}")
print(f" API Base URL: {API_BASE_URL}")
print(f" Email: {EMAIL_HOST_USER}")
print(f"Debug Mode: {DEBUG}")
print("="*60 + "\n")