"""
Modulo de seguridad de la API.

Decide quien puede consultar cada recurso. Hay tres vias de acceso y basta
con cumplir una:

1. SESION  - haber iniciado sesion en el sitio (/admin/ o /panel/) con un
             usuario de rol SUPERADMIN. Es la via comoda desde el navegador:
             no hay que escribir ninguna clave.
2. TOKEN   - encabezado "Authorization: Bearer <token>". Es la via para
             otras aplicaciones: piden el token en /api/auth/login/ con el
             correo y la contrasena de un super administrador de esta base
             de datos, y con el consultan la API completa. El rol se vuelve
             a comprobar en CADA peticion, asi que si el usuario deja de ser
             super administrador el token deja de servir en ese mismo
             instante.
3. CLAVE   - encabezado X-API-Key con API_CLAVE. Es una clave unica del
             sitio, sin usuario detras; sirve para scripts propios.

Si API_CLAVE queda vacia en el .env, la via 3 simplemente no existe.

No devuelve respuestas HTTP: informa del resultado y quien llama decide.
Asi este modulo no depende de las vistas ni de respuestas.py.
"""
from django.conf import settings
from django.core.cache import cache

from .models import TokenApi

# Vias de acceso, para poder explicarlas en la respuesta del indice.
SESION = 'sesion'
TOKEN = 'token'
CLAVE = 'clave'
ABIERTO = 'abierto'

# Mensaje unico de "no autorizado". Se responde siempre el mismo texto para
# que la aplicacion que consume la API pueda mostrarselo tal cual a su
# usuario; el detalle tecnico va aparte, en "motivo" y "detalle".
NO_AUTORIZADO = 'No se ha autorizado que sea un super admin.'

# Motivos: codigos estables para que otra aplicacion decida que hacer
# (volver a pedir el login, renovar el token, avisar al usuario...).
SIN_CREDENCIALES = 'sin_credenciales'
TOKEN_INVALIDO = 'token_invalido'
TOKEN_CADUCADO = 'token_caducado'
TOKEN_REVOCADO = 'token_revocado'
NO_SUPERADMIN = 'no_superadmin'
CUENTA_INACTIVA = 'cuenta_inactiva'
CLAVE_INVALIDA = 'clave_invalida'


class Resultado:
    """Respuesta de una comprobacion de seguridad."""

    def __init__(self, permitido, via=None, mensaje='', codigo=401,
                 motivo=None, detalle='', usuario=None, token=None):
        self.permitido = permitido
        self.via = via
        self.mensaje = mensaje
        self.codigo = codigo
        self.motivo = motivo
        self.detalle = detalle
        self.usuario = usuario
        self.token = token

    def __bool__(self):
        return self.permitido


def _negar(motivo, detalle, codigo=401):
    """Denegacion: mensaje siempre igual, motivo y detalle especificos."""
    return Resultado(
        False,
        mensaje=NO_AUTORIZADO,
        codigo=codigo,
        motivo=motivo,
        detalle=detalle,
    )


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


def token_recibido(request):
    """
    Lee el token de "Authorization: Bearer <token>" o de X-API-Token.

    Se aceptan los dos encabezados porque algunos servidores compartidos
    filtran Authorization antes de que llegue a la aplicacion.
    """
    cabecera = (request.headers.get('Authorization') or '').strip()

    if cabecera:
        partes = cabecera.split(None, 1)

        if len(partes) == 2 and partes[0].lower() in ('bearer', 'token'):
            return partes[1].strip()

    return (request.headers.get('X-API-Token') or '').strip()


def cuenta_activa(usuario):
    """La cuenta permite iniciar sesion y no esta marcada como inactiva."""
    if not usuario or not usuario.is_active:
        return False

    estado = getattr(usuario, 'estado', 'activo')

    return str(estado).strip().lower() != 'inactivo'


def es_usuario_autorizado(usuario):
    """True si el usuario puede usar la API (rol y cuenta al dia)."""
    if not usuario or not getattr(usuario, 'is_authenticated', False):
        return False

    if not cuenta_activa(usuario):
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


def por_token(request):
    """
    Comprueba el token del encabezado.

    Devuelve None si no se envio ninguno (para poder seguir probando las
    otras vias) o un Resultado con el desenlace si si se envio.
    """
    plano = token_recibido(request)

    if not plano:
        return None

    token = TokenApi.objects.buscar(plano)

    if token is None:
        return _negar(
            TOKEN_INVALIDO,
            'El token no existe. Pide uno nuevo en /api/auth/login/.',
        )

    if token.revocado:
        return _negar(
            TOKEN_REVOCADO,
            'El token fue revocado. Pide uno nuevo en /api/auth/login/.',
        )

    if token.caducado:
        return _negar(
            TOKEN_CADUCADO,
            f'El token caduco el {token.expira.date().isoformat()}. '
            f'Pide uno nuevo en /api/auth/login/.',
        )

    if not cuenta_activa(token.usuario):
        return _negar(
            CUENTA_INACTIVA,
            'La cuenta duena del token esta inactiva.',
            403,
        )

    if not es_usuario_autorizado(token.usuario):
        return _negar(
            NO_SUPERADMIN,
            f'La cuenta {token.usuario.correo} ya no tiene un rol '
            f'autorizado ({", ".join(roles_permitidos())}) en esta base de datos.',
            403,
        )

    token.registrar_uso()

    return Resultado(True, TOKEN, usuario=token.usuario, token=token)


def modo():
    """'privada' (por defecto) o 'publica'."""
    return getattr(settings, 'API_MODO', 'privada').strip().lower()


def como_autorizarse(request=None):
    """Instrucciones que se adjuntan a toda respuesta de "no autorizado"."""
    ruta = request.build_absolute_uri('/api/auth/login/') if request else '/api/auth/login/'

    pasos = {
        'token': {
            'para': 'otras aplicaciones (es la via recomendada)',
            'paso_1': f'POST {ruta} con {{"correo": "...", "password": "..."}} '
                      f'de un usuario SUPERADMIN de esta base de datos',
            'paso_2': 'Envia el token recibido en cada peticion: '
                      'Authorization: Bearer <token>',
        },
        'sesion': {
            'para': 'mirar la API tu mismo desde el navegador',
            'como': 'Inicia sesion en /admin/ con un usuario SUPERADMIN y '
                    'abre la API en la misma ventana.',
        },
    }

    if getattr(settings, 'API_CLAVE', ''):
        pasos['clave'] = {
            'para': 'scripts propios, sin usuario detras',
            'como': 'Encabezado X-API-Key: <clave>  (o ?clave=<clave>)',
        }

    return pasos


def autorizar(request, privado=False):
    """
    Comprueba el acceso a un recurso.

    privado=True marca los recursos con datos personales (usuarios,
    estudiantes): esos nunca quedan abiertos, siempre exigen identificarse.

    Orden: sesion -> token -> clave. Si se envio un token se responde segun
    ese token, sin seguir probando: asi el error explica lo que pasa de
    verdad (caducado, revocado, ya no es super admin).
    """
    if por_sesion(request):
        return Resultado(True, SESION, usuario=request.user)

    resultado_token = por_token(request)
    if resultado_token is not None:
        return resultado_token

    if por_clave(request):
        return Resultado(True, CLAVE)

    # Sin credenciales validas.
    if privado or modo() == 'privada':
        if getattr(settings, 'API_CLAVE', '') and clave_recibida(request):
            return _negar(CLAVE_INVALIDA, 'La clave X-API-Key no coincide.')

        return _negar(
            SIN_CREDENCIALES,
            'No se recibio ninguna credencial valida (sesion, token o clave).',
        )

    # Modo publico: el catalogo academico se consulta sin identificarse.
    if getattr(settings, 'API_CLAVE', '') and clave_recibida(request):
        # Mando una clave, pero es incorrecta: es un error, no un anonimo.
        return _negar(CLAVE_INVALIDA, 'La clave X-API-Key no coincide.')

    return Resultado(True, ABIERTO)


# ── Freno a la fuerza bruta en el login ──────────────────────────────────────
# Se cuentan los intentos fallidos por IP y correo. La cuenta vive en la
# cache de Django (en memoria), asi que se olvida sola al reiniciar el sitio.

def ip_de(request):
    reenviada = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()

    return reenviada or request.META.get('REMOTE_ADDR') or ''


def _clave_intentos(request, correo):
    return f'api-login:{ip_de(request)}:{correo.lower()}'


def intentos_disponibles(request, correo):
    """Cuantos intentos de login le quedan a esta IP con este correo."""
    maximo = getattr(settings, 'API_LOGIN_INTENTOS', 10)

    return max(0, maximo - cache.get(_clave_intentos(request, correo), 0))


def anotar_intento_fallido(request, correo):
    clave = _clave_intentos(request, correo)
    minutos = getattr(settings, 'API_LOGIN_BLOQUEO_MIN', 5)

    cache.set(clave, cache.get(clave, 0) + 1, minutos * 60)


def olvidar_intentos(request, correo):
    cache.delete(_clave_intentos(request, correo))


def resumen(request):
    """Como esta configurada la seguridad ahora mismo (para el indice)."""
    autorizado = autorizar(request, privado=True)
    usuario = autorizado.usuario if autorizado else None

    return {
        'modo': modo(),
        'vias': {
            'token': {
                'activa': autorizado.via == TOKEN,
                'como': 'Authorization: Bearer <token>. El token se obtiene '
                        'en POST /api/auth/login/ con el correo y la '
                        'contrasena de un usuario SUPERADMIN.',
                'roles_permitidos': roles_permitidos(),
            },
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
            'usuario': usuario.correo if usuario else None,
            'motivo': autorizado.motivo,
            'mensaje': autorizado.mensaje or None,
        },
    }
