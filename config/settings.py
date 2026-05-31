import os
from pathlib import Path
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'


def env_list(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only')
if not DEBUG and SECRET_KEY in {'', 'change-me', 'dev-only'}:
    raise ImproperlyConfigured('Set a real SECRET_KEY when DEBUG=false.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.tasks',
    'apps.reminders',
    'apps.telegram_bot',
    'apps.ai',
    'apps.integrations',
    'apps.briefing',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL', 'postgres://ceo:ceo@localhost:5432/ceo_copilot')
parsed = urlparse(DATABASE_URL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/'),
        'USER': parsed.username,
        'PASSWORD': parsed.password,
        'HOST': parsed.hostname,
        'PORT': parsed.port or 5432,
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'false').lower() == 'true'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'false').lower() == 'true'

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = 'Africa/Cairo'
CELERY_BEAT_SCHEDULE = {
    'send-due-reminders-every-minute': {
        'task': 'apps.reminders.tasks.send_due_reminders',
        'schedule': 60.0,
    },
    'send-daily-briefing': {
        'task': 'apps.briefing.tasks.send_daily_briefing',
        'schedule': 60.0,
    },
}

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_ALLOWED_CHAT_ID = os.getenv('TELEGRAM_ALLOWED_CHAT_ID', '')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
OLLAMA_TEMPERATURE = float(os.getenv('OLLAMA_TEMPERATURE', '0.5'))
GITLAB_BASE_URL = os.getenv('GITLAB_BASE_URL', 'https://gitlab.com')
GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', '')
BRIEFING_HOUR = int(os.getenv('BRIEFING_HOUR', '8'))
BRIEFING_MINUTE = int(os.getenv('BRIEFING_MINUTE', '30'))
