from dotenv import load_dotenv
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = [
    'ttumy.vn',
    'www.ttumy.vn',
    'api.ttumy.vn',
    'app.ttumy.vn',
]

# ALLOWED_HOSTS = ['*']   # DEV


# =========================
# STATIC & MEDIA CONFIG
# =========================

TTUMY_STATIC_ROOT = '/home/aitumyon6802/domains/ttumy.vn/public_html/assets'
TTUMY_MEDIA_ROOT  = '/home/aitumyon6802/domains/ttumy.vn/public_html/media'

# -------- api.ttumy.vn (API) --------
API_STATIC_ROOT = '/home/aitumyon6802/domains/api.ttumy.vn/public_html/static'
API_MEDIA_ROOT  = '/home/aitumyon6802/domains/api.ttumy.vn/public_html/media'

# -------- app.ttumy.vn (SPA / file tĩnh) --------
APP_STATIC_ROOT = '/home/aitumyon6802/domains/app.ttumy.vn/public_html/static'
APP_MEDIA_ROOT  = '/home/aitumyon6802/domains/app.ttumy.vn/public_html/media'

# Dùng tĩnh cho subdomain hiện tại
import socket
current_host = socket.gethostname()  # tạm, bạn có thể set bằng ENV hoặc subdomain

if 'api.ttumy.vn' in current_host:
    STATIC_ROOT = API_STATIC_ROOT
    MEDIA_ROOT = API_MEDIA_ROOT
elif 'app.ttumy.vn' in current_host:
    STATIC_ROOT = APP_STATIC_ROOT
    MEDIA_ROOT = APP_MEDIA_ROOT
else:
    STATIC_ROOT = TTUMY_STATIC_ROOT
    MEDIA_ROOT = TTUMY_MEDIA_ROOT

# STATIC_URL = '/static/'
# MEDIA_URL = '/media/'

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# =========================
# CSRF / CORS (Flutter API)
# =========================
CSRF_TRUSTED_ORIGINS = [
    "https://api.ttumy.vn",
    "https://ttumy.vn",
    "https://app.ttumy.vn",
]

# Nếu Flutter gọi API, CORS headers
CORS_ALLOWED_ORIGINS = [
    "https://app.ttumy.vn",
    "https://ttumy.vn",
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "channels",
    "support",
    "webshell",
    "dashboard",
    "admin_portal",
    "appconfig",

    # Third-party
    "rest_framework",
    "corsheaders",
    'core',
    'knowledge_base',
    'django_ckeditor_5',

    # Local apps
    "documents",
    "users",
    "drive_integration",
    "ai_assistant",
    "accounting",
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',   # CORS cho Flutter
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "core.middleware.session_validation.SessionValidationMiddleware",
]

ROOT_URLCONF = 'aitumy_backend.urls'

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold", "italic", "underline",
            "|",
            "link",
            "bulletedList", "numberedList",
            "|",
            "blockQuote",
            "|",
            "imageUpload",   # 👈 thêm dòng này
            "|",
            "undo", "redo",
        ],
        "image": {
            "toolbar": [
                "imageTextAlternative",
                "imageStyle:full",
                "imageStyle:side",
            ],
        },
        "height": "400px",
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [],
        "DIRS": [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.template.context_processors.debug",
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'aitumy_backend.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST", "localhost"),
        'PORT': os.getenv("DB_PORT", "3306"),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        "OPTIONS": {"min_length": 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =========================
# TIMEZONE / LANGUAGE
# =========================
LANGUAGE_CODE = 'vi-vn'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# =========================
# LOGGING (cơ bản)
# =========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =======================================
#  DRF CONFIG
# =======================================

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

# =======================================
#  CORS CONFIG (cho phép Flutter gọi API)
# =======================================

scope = [
  "https://www.googleapis.com/auth/drive.file",
  "https://www.googleapis.com/auth/userinfo.email",
  "https://www.googleapis.com/auth/userinfo.profile",
]


# =========================
# GOOGLE DRIVE OAUTH
# =========================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = "postmessage"

GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

GOOGLE_OAUTH_ACCESS_TYPE = "offline"
GOOGLE_OAUTH_PROMPT = "consent"

AUTH_USER_MODEL = "users.User"

# =====================================================
# EXPORT PDF – TEMP FILE CLEANUP CONFIG
# =====================================================

# media/exports
EXPORT_MEDIA_DIR = BASE_DIR / "media" / "exports"

# File sống tối đa 30 phút
EXPORT_FILE_TTL_SECONDS = 30 * 60

# Không xóa file mới tạo trong 60s gần nhất
EXPORT_EXCLUDE_RECENT_SECONDS = 60

# Cleanup chạy tối đa mỗi 5 phút (khi gọi từ API)
EXPORT_CLEANUP_INTERVAL_SECONDS = 5 * 60


ASGI_APPLICATION = "project.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

USE_OPENAI_EMBEDDING = False
OPENAI_API_KEY = None
DEFAULT_ACCOUNTING_REGIME_BY_TYPE = {
    "INDIVIDUAL": "152/2025/TT-BTC",
    "HKD": "152/2025/TT-BTC",
    "ENTERPRISE": "99/2025/TT-BTC",
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# ================================
# EMAIL CONFIG (DEV MODE)
# ================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "TTUMY <contact@ttumy.vn>"