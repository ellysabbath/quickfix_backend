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
    # 'users',
    'registration',
    'mechanics',
    'authe',
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


