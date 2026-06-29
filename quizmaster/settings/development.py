from .base import *

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Add any development-specific settings here
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
