"""
Configuracion del proyecto ESPOL Academics (v2).

Los valores que cambian entre el equipo local y el servidor de produccion
(AlwaysData) se leen desde variables de entorno o desde backend/.env.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Raiz del proyecto (un nivel arriba de backend/): css/, js/, pages/, index.html
FRONTEND_DIR = BASE_DIR.parent


def cargar_env(ruta):
    """Carga un archivo .env sencillo (CLAVE=valor) dentro de os.environ."""
    if not ruta.exists():
        return

    for linea in ruta.read_text().splitlines():
        linea = linea.strip()

        if not linea or linea.startswith('#') or '=' not in linea:
            continue

        clave, valor = linea.split('=', 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


cargar_env(BASE_DIR / '.env')


def env_bool(nombre, por_defecto=False):
    return os.environ.get(nombre, str(por_defecto)).strip().lower() in (
        '1', 'true', 'yes', 'on',
    )


def env_list(nombre, por_defecto=''):
    valor = os.environ.get(nombre, por_defecto)
    return [item.strip() for item in valor.split(',') if item.strip()]


SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-cambia-esta-clave-en-produccion-espol-academics-v2',
)

DEBUG = env_bool('DJANGO_DEBUG', True)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'config',
    'api',
    'accounts',
    'cursos',
    'evaluaciones',
    'reportes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'api.middleware.CorsApiMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            FRONTEND_DIR,
        ],
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

WSGI_APPLICATION = 'config.wsgi.application'

# ── BASE DE DATOS ─────────────────────────────────────────────
# DB_ENGINE = sqlite (por defecto) | mysql | postgresql
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').strip().lower()

if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', ''),
            'USER': os.environ.get('DB_USER', ''),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'mysql.alwaysdata.com'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
elif DB_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', ''),
            'USER': os.environ.get('DB_USER', ''),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'postgresql.alwaysdata.com'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'accounts.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

# ── ARCHIVOS ESTATICOS ────────────────────────────────────────
# css/, js/ y pages/ del frontend se sirven desde config/urls.py.
# /static/ contiene los recursos del panel de administracion de Django.
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/panel/'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '0'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0

# ── API PUBLICA (/api/) ───────────────────────────────────────
# Se entra de tres formas y basta con una (ver api/seguridad.py):
#   1. sesion iniciada en el sitio con un usuario SUPERADMIN;
#   2. token pedido en POST /api/auth/login/ con las credenciales de un
#      usuario SUPERADMIN (es la via de las otras aplicaciones);
#   3. clave del sitio en el encabezado X-API-Key.
#
# API_MODO controla el catalogo academico (facultades, cursos, modulos,
# tareas, quizzes, reportes):
#   privada -> exige sesion de superadmin o clave (por defecto)
#   publica -> cualquiera puede consultarlo sin identificarse
# Los datos personales (usuarios, estudiantes) exigen siempre una de las
# dos vias, aunque el modo sea publico.
API_MODO = os.environ.get('API_MODO', 'privada').strip().lower()

# Roles que pueden usar la API con su sesion. Un superusuario de Django
# entra siempre, tenga el rol que tenga.
API_ROLES = env_list('API_ROLES', 'SUPERADMIN')

# Clave para programas externos (curl, otra aplicacion). Es opcional:
# si queda vacia, solo se entra con sesion de super administrador.
API_CLAVE = os.environ.get('API_CLAVE', '').strip()

# Tokens que se entregan a otras aplicaciones en /api/auth/login/.
# API_TOKEN_DIAS = duracion por defecto (0 = no caduca).
# API_TOKEN_DIAS_MAX = lo maximo que puede pedir la aplicacion en "dias".
API_TOKEN_DIAS = int(os.environ.get('API_TOKEN_DIAS', '30'))
API_TOKEN_DIAS_MAX = int(os.environ.get('API_TOKEN_DIAS_MAX', '365'))

# Freno a la fuerza bruta en /api/auth/login/: intentos fallidos permitidos
# por IP y correo, y minutos que dura el bloqueo.
API_LOGIN_INTENTOS = int(os.environ.get('API_LOGIN_INTENTOS', '10'))
API_LOGIN_BLOQUEO_MIN = int(os.environ.get('API_LOGIN_BLOQUEO_MIN', '5'))

# Dominios autorizados a consultar la API desde un navegador.
# '*' = cualquiera. Ejemplo: API_ORIGENES=https://misitio.com,https://otro.com
API_ORIGENES = env_list('API_ORIGENES', '*')

# Paginacion de los listados (?pagina= y ?tam=)
API_TAM_PAGINA = int(os.environ.get('API_TAM_PAGINA', '25'))
API_TAM_PAGINA_MAX = int(os.environ.get('API_TAM_PAGINA_MAX', '100'))

# Config academica global
PORCENTAJE_MINIMO_APROBACION = 60
