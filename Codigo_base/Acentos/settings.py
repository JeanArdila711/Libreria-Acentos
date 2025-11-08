import os
from pathlib import Path
from dotenv import load_dotenv

# ===============================================
# 🔧 CONFIGURACIÓN BÁSICA
# ===============================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables desde el archivo openAI.env
load_dotenv(os.path.join(BASE_DIR, "openAI.env"))

SECRET_KEY = 'django-insecure-reemplaza-esto-por-una-clave-real'
DEBUG = True
ALLOWED_HOSTS = ['3.81.229.122', 'localhost', '127.0.0.1']

# ===============================================
# 📦 APLICACIONES
# ===============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps del proyecto
    'accounts',
    'books',
    'news',
]

# ===============================================
# ⚙️ MIDDLEWARE
# ===============================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Acentos.urls'

# ===============================================
# 🎨 TEMPLATES
# ===============================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'books.context_processors.cart_counter',
                'books.context_processors.common_context',
                'books.context_processors.back_button_context',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Acentos.wsgi.application'

# ===============================================
# 🗄️ BASE DE DATOS (SQLite)
# ===============================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ===============================================
# 🔐 VALIDACIÓN DE CONTRASEÑAS
# ===============================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===============================================
# 🌎 INTERNACIONALIZACIÓN
# ===============================================
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ===============================================
# 🗂️ ARCHIVOS ESTÁTICOS Y MEDIA
# ===============================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===============================================
# 🤖 CLAVE OPENAI
# ===============================================
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# ===============================================
# ⚙️ SESIONES Y ARCHIVOS ESTÁTICOS
# ===============================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Redirección después del login y logout
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
