"""
Modulo de seguridad de la API.

Decide quien puede consultar cada recurso. Hay dos vias de acceso y basta
con cumplir una:

1. SESION  - haber iniciado sesion en el sitio (/admin/ o /panel/) con un
             usuario de rol SUPERADMIN. Es la via comoda desde el navegador:
             no hay que escribir ninguna clave.
2. CLAVE   - enviar API_CLAVE en el encabezado X-API-Key. Es la via para
             programas externos (curl, otra aplicacion, un script), que no
             tienen sesion ni cookies.

Si API_CLAVE queda vacia en el .env, la via 2 simplemente no existe y solo
se entra con sesion de super administrador.

No devuelve respuestas HTTP: informa del resultado y quien llama decide.
Asi este modulo no depende de las vistas ni de respuestas.py.
"""
from django.conf import settings

# Vias de acceso, para poder explicarlas en la respuesta del indice.
SESION = 'sesion'
CLAVE = 'clave'
ABIERTO = 'abierto'


class Resultado:
    """Respuesta de una comprobacion de seguridad."""

    def __init__(self, permitido, via=None, mensaje='', codigo=401):
        self.permitido = permitido
        self.via = via
        self.mensaje = mensaje
        self.codigo = codigo

    def __bool__(self):
        return self.permitido


def roles_permitidos():
    """Roles que pueden consultar la API. Por defecto solo SUPERADMIN."""
    return [rol.upper() for rol in getattr(settings, 'API_ROLES', ['SUPERADMIN'])]


def clave_recibida(request):
    """Lee la clave del encabezado X-API-Key o del parametro ?clave=."""
    return (
        request.headers.get('X-API-Key')
        or request.GET.get('clave')
        or ''
    ).strip()


def es_usuario_autorizado(usuario):
    """True si el usuario de la sesion puede usar la API."""
    if not usuario or not usuario.is_authenticated:
        return False

    if not usuario.is_active:
        return False

    # Un superusuario de Django siempre entra, tenga el rol que tenga.
    if getattr(usuario, 'is_superuser', False):
        return True

    return getattr(usuario, 'rol', '') in roles_permitidos()


def por_sesion(request):
    """¿Viene de un navegador con sesion de super administrador?"""
    return es_usuario_autorizado(getattr(request, 'user', None))


def por_clave(request):
    """¿Trae la clave correcta? Falso si no hay clave configurada."""
    configurada = getattr(settings, 'API_CLAVE', '')

    return bool(configurada) and clave_recibida(request) == configurada


def modo():
    """'privada' (por defecto) o 'publica'."""
    return getattr(settings, 'API_MODO', 'privada').strip().lower()


def _mensaje_de_ayuda():
    """Explica las vias disponibles segun como este configurado el sitio."""
    opciones = ['inicia sesion en /admin/ con un usuario SUPERADMIN']

    if getattr(settings, 'API_CLAVE', ''):
        opciones.append('o envia el encabezado X-API-Key')

    return 'Acceso no autorizado: ' + ' '.join(opciones) + '.'


def autorizar(request, privado=False):
    """
    Comprueba el acceso a un recurso.

    privado=True marca los recursos con datos personales (usuarios,
    estudiantes): esos nunca quedan abiertos, siempre exigen sesion o clave.
    """
    if por_sesion(request):
        return Resultado(True, SESION)

    if por_clave(request):
        return Resultado(True, CLAVE)

    # Sin credenciales validas.
    if privado:
        return Resultado(False, None, _mensaje_de_ayuda(), 401)

    if modo() == 'privada':
        return Resultado(False, None, _mensaje_de_ayuda(), 401)

    # Modo publico: el catalogo academico se consulta sin identificarse.
    if getattr(settings, 'API_CLAVE', '') and clave_recibida(request):
        # Mando una clave, pero es incorrecta: es un error, no un anonimo.
        return Resultado(False, None, 'Clave de API invalida.', 401)

    return Resultado(True, ABIERTO)


def resumen(request):
    """Como esta configurada la seguridad ahora mismo (para el indice)."""
    usuario = getattr(request, 'user', None)
    autorizado = autorizar(request, privado=True)

    return {
        'modo': modo(),
        'vias': {
            'sesion': {
                'activa': por_sesion(request),
                'como': 'Inicia sesion en /admin/ con un usuario SUPERADMIN '
                        'y consulta la API en la misma ventana del navegador.',
                'roles_permitidos': roles_permitidos(),
            },
            'clave': {
                'configurada': bool(getattr(settings, 'API_CLAVE', '')),
                'activa': por_clave(request),
                'como': 'Encabezado X-API-Key: <clave>  (o ?clave=<clave>)',
            },
        },
        'acceso_actual': {
            'autorizado': bool(autorizado),
            'via': autorizado.via,
            'usuario': usuario.correo if es_usuario_autorizado(usuario) else None,
        },
    }
