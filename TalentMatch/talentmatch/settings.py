"""
Django settings for talentmatch_ai project.

UPDATED FOR RAILWAY + S3 DEPLOYMENT
"""
from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_URL = os.getenv("API_BASE", "http://localhost:3000")

# ============================================
# STEP 1 CHANGE: Add SECRET_KEY with fallback
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-PLEASE-CHANGE-IN-PRODUCTION")

# ============================================
# STEP 2 CHANGE: Make DEBUG configurable
# ============================================
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'widget_tweaks',
    'django_filters',
    'channels',
    
    # ============================================
    # STEP 3 CHANGE: Add 'storages' for S3
    # ============================================
    
    'jobs.apps.JobsConfig',
    #new app
    # External apps
    'accounts',
    'cv_manager',
    'interview',
    'ranking',
    'resumedata',
    'notifications',
    'user_profile',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    
    # ============================================
    # STEP 4 CHANGE: Add WhiteNoise for static files
    # ============================================
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]



ROOT_URLCONF = 'talentmatch.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================
# STEP 5 CHANGE: Add Railway domain to CSRF
# ============================================
CSRF_TRUSTED_ORIGINS = [
    "https://tallent-match-ai.vercel.app",
    "https://*.railway.app",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

WSGI_APPLICATION = 'talentmatch.wsgi.application'

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQLDATABASE"),
        "USER": os.getenv("MYSQLUSER"),
        "PASSWORD": os.getenv("MYSQLPASSWORD"),
        "HOST": os.getenv("MYSQLHOST"),
        "PORT": os.getenv("MYSQLPORT"),
    }
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# # ============================================
# # STEP 6 CHANGE: Add WhiteNoise storage
# # ============================================
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# # ============================================
# # STEP 7 CHANGE: AWS S3 Configuration for Media Files
# # ============================================
# USE_S3 = os.getenv('USE_S3', 'False') == 'True'

# if USE_S3:
#     # AWS S3 Settings
#     AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
#     AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
#     AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
#     AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
#     AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
#     # S3 File Settings
#     AWS_S3_FILE_OVERWRITE = False
#     AWS_DEFAULT_ACL = 'public-read'
#     AWS_S3_OBJECT_PARAMETERS = {
#         'CacheControl': 'max-age=86400',
#     }
    
#     # Use S3 for media files
#     DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
#     MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
# else:
    # Local development - use filesystem
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'resume_parser.log',
        },
    },
    'loggers': {
        'cv_manager.services.parser': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# API Keys (remove duplicate SECRET_KEY if exists below)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

ML_MODELS_DIR = os.path.join(BASE_DIR, "resumedata/models")
RESUME_RANKER_MODEL_PATH = os.path.join(ML_MODELS_DIR, "resume_ranker_model.pkl")
EMBEDDING_MODEL_PATH = os.path.join(ML_MODELS_DIR, "embedding_model.pkl")

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# Notification settings
NOTIFICATION_SETTINGS = {
    'DEFAULT_EXPIRY_DAYS': 30,
    'BATCH_SIZE': 50,
    'ENABLE_EMAIL_NOTIFICATIONS': True,
    'ENABLE_PUSH_NOTIFICATIONS': False,
}

ASGI_APPLICATION = 'talentmatch.asgi.application'

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.getenv("email")       # <-- your Gmail address
# EMAIL_HOST_PASSWORD = os.getenv("password")   # <-- Gmail App Password (NOT your real password)
# DEFAULT_FROM_EMAIL = 'TalentMatch AI <{0}>'.format(os.getenv("email"))
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
# Cache — required for OTP storage
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
    }
}