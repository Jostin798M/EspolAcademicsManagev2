"""
Modulo de seguridad de la API.

Contesta dos preguntas seguidas, y en este orden:

    1. ¿QUIEN eres?  -> identificar(request)
    2. ¿PUEDES esto? -> autorizar(request, recurso, accion)

La primera es la autenticacion. Hay tres vias y basta con cumplir una:

1. SESION  - haber iniciado sesion en el sitio (/admin/, /panel/ o el propio
             index.html). Es la via comoda desde el navegador.
2. TOKEN   - encabezado "Authorization: Bearer <token>". Es la via de las
             otras aplicaciones (la app movil, por ejemplo): piden el token
             en /api/auth/login/ con su correo y contrasena.
3. CLAVE   - encabezado X-API-Key con API_CLAVE. Es una clave del sitio, sin
             usuario detras; sirve para scripts propios y no tiene limites.
             Si API_CLAVE queda vacia en el .env, esta via no existe.

La segunda pregunta es la autorizacion, y vive en permisos.py: cada endpoint
declara sobre que recurso trabaja y que accion hace, y aqui se comprueba
contra el rol efectivo de quien llama.

Lo importante: los permisos se recalculan en CADA peticion a partir del
usuario, nunca se leen del token. Si a alguien le cambian el rol o lo dan de
baja, su token deja de servir para lo que ya no le corresponde en ese mismo
instante, sin esperar a que caduque.

No devuelve respuestas HTTP: informa del resultado y quien llama decide. Asi
este modulo no depende de las vistas ni de respuestas.py.
"""
from django.conf import settings
from django.core.cache import cache

from . import permisos
from .models import TokenApi

# Vias de acceso, para poder explicarlas en la respuesta del indice.
SESION = 'sesion'
TOKEN = 'token'
CLAVE = 'clave'
ABIERTO = 'abierto'

# Mensajes. Se separan los dos fracasos porque no son lo mismo y la
# aplicacion que consume la API tiene que reaccionar distinto: ante el
# primero vuelve a pedir el login, ante el segundo esconde un boton.
NO_IDENTIFICADO = 'No se ha podido comprobar tu identidad.'
SIN_PERMISO_MSG = 'Tu rol no tiene permiso para hacer esto.'

# Se conserva el texto antiguo: lo siguen mostrando pantallas que solo
# hablaban de super administradores.
NO_AUTORIZADO = NO_IDENTIFICADO

# Motivos: codigos estables para que otra aplicacion decida que hacer
# (volver a pedir el login, renovar el token, avisar al usuario...).
SIN_CREDENCIALES = 'sin_credenciales'
TOKEN_INVALIDO = 'token_invalido'
TOKEN_CADUCADO = 'token_caducado'
TOKEN_REVOCADO = 'token_revocado'
CUENTA_INACTIVA = 'cuenta_inactiva'
CLAVE_INVALIDA = 'clave_invalida'
ROL_SIN_ACCESO = 'rol_sin_acceso'
SIN_PERMISO = 'sin_permiso'
FUERA_DE_ALCANCE = 'fuera_de_alcance'

# Motivo antiguo, cuando la API era solo para super administradores. Ya no
# se emite, pero se deja definido porque hay clientes que lo comprueban.
NO_SUPERADMIN = 'no_superadmin'

#: Motivos que significan "vuelve a iniciar sesion". Los demas son un "no
#: puedes", que no se arregla volviendo a entrar.
MOTIVOS_DE_SESION = (
    SIN_CREDENCIALES, TOKEN_INVALIDO, TOKEN_CADUCADO,
    TOKEN_REVOCADO, CUENTA_INACTIVA, ROL_SIN_ACCESO, NO_SUPERADMIN,
)


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

    @property
    def rol(self):
        """Rol efectivo de quien llama: SUPERADMIN, ADMIN, PROFESOR..."""
        return permisos.rol_efectivo(self.usuario) if self.usuario else None

    @property
    def persona(self):
        """El Usuario, o None si detras no hay nadie (clave del sitio)."""
        if (self.usuario is None
                or permisos.es_sitio(self.usuario)
                or permisos.es_visitante(self.usuario)):
            return None

        return self.usuario


def _negar(motivo, detalle, codigo=401, mensaje=None):
    """Denegacion: mensaje para el usuario, motivo y detalle para la app."""
    return Resultado(
        False,
        mensaje=mensaje or NO_IDENTIFICADO,
        codigo=codigo,
        motivo=motivo,
        detalle=detalle,
    )


def roles_permitidos():
    """
    Roles que pueden entrar a la API.

    Por defecto los cuatro: la API dejo de ser exclusiva del super
    administrador y ahora cada rol entra al trozo que le corresponde. Se
    puede recortar desde el .env con API_ROLES si algun dia hiciera falta
    cerrarle la puerta a un rol entero.
    """
    configurados = getattr(settings, 'API_ROLES', None) or permisos.ROLES

    return [rol.upper() for rol in configurados]


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
    """
    True si el usuario puede usar la API.

    Ya no pregunta si es super administrador: pregunta si su cuenta esta al
    dia y si su rol efectivo esta entre los que pueden entrar. Los permisos
    concretos se deciden despues, recurso por recurso.
    """
    if not usuario or not getattr(usuario, 'is_authenticated', False):
        return False

    if not cuenta_activa(usuario):
        return False

    if getattr(usuario, 'is_superuser', False):
        return True

    return permisos.rol_efectivo(usuario) in roles_permitidos()


def por_sesion(request):
    """¿Viene de un navegador con la sesion del sitio iniciada?"""
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
            ROL_SIN_ACCESO,
            f'La cuenta {token.usuario.correo} no tiene un rol con acceso '
            f'a la API ({", ".join(roles_permitidos())}).',
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
                      f'de cualquier cuenta activa de esta base de datos',
            'paso_2': 'Envia el token recibido en cada peticion: '
                      'Authorization: Bearer <token>',
            'paso_3': 'La respuesta del login trae tu rol y tus permisos: '
                      'usalos para saber que puedes ver y modificar.',
        },
        'sesion': {
            'para': 'mirar la API tu mismo desde el navegador',
            'como': 'Inicia sesion en el sitio o en /admin/ y abre la API en '
                    'la misma ventana.',
        },
    }

    if getattr(settings, 'API_CLAVE', ''):
        pasos['clave'] = {
            'para': 'scripts propios, sin usuario detras',
            'como': 'Encabezado X-API-Key: <clave>  (o ?clave=<clave>)',
        }

    return pasos


# ── Identificacion ───────────────────────────────────────────────────────────

def identificar(request):
    """
    Averigua quien llama, sin mirar todavia que quiere hacer.

    Orden: sesion -> token -> clave. Si se envio un token se responde segun
    ese token, sin seguir probando: asi el error explica lo que pasa de
    verdad (caducado, revocado, cuenta inactiva).
    """
    if por_sesion(request):
        return Resultado(True, SESION, usuario=request.user)

    resultado_token = por_token(request)
    if resultado_token is not None:
        return resultado_token

    if por_clave(request):
        # Sin persona detras: el sitio ejecutando un script propio.
        return Resultado(True, CLAVE, usuario=permisos.SITIO)

    if getattr(settings, 'API_CLAVE', '') and clave_recibida(request):
        # Mando una clave, pero es incorrecta: es un error, no un anonimo.
        return _negar(CLAVE_INVALIDA, 'La clave X-API-Key no coincide.')

    return _negar(
        SIN_CREDENCIALES,
        'No se recibio ninguna credencial valida (sesion, token o clave). '
        'Inicia sesion en /api/auth/login/.',
    )


# ── Autorizacion ─────────────────────────────────────────────────────────────

def _negar_permiso(usuario, recurso, accion):
    """El usuario es quien dice ser, pero su rol no llega a tanto."""
    rol = permisos.rol_efectivo(usuario)
    etiqueta = permisos.ETIQUETA_RECURSO.get(recurso, recurso)
    puede_ahora = permisos.acciones_sobre(usuario, recurso)

    detalle = (
        f'Tu rol es {permisos.ETIQUETA_ROL.get(rol, rol)} y sobre '
        f'"{etiqueta}" '
    )
    detalle += (
        f'solo puedes: {", ".join(puede_ahora)}.' if puede_ahora
        else 'no tienes ningun permiso.'
    )

    return Resultado(
        False,
        mensaje=SIN_PERMISO_MSG,
        codigo=403,
        motivo=SIN_PERMISO,
        detalle=detalle,
        usuario=usuario,
    )


def negar_alcance(usuario, recurso, detalle=''):
    """
    El rol si tiene el permiso, pero ese registro no es suyo.

    La usan las vistas cuando ya han buscado el objeto concreto: un profesor
    puede editar tareas, pero no las de un curso que no dicta.
    """
    rol = permisos.rol_efectivo(usuario)
    etiqueta = permisos.ETIQUETA_RECURSO.get(recurso, recurso)

    return Resultado(
        False,
        mensaje='Ese registro esta fuera de tu alcance.',
        codigo=403,
        motivo=FUERA_DE_ALCANCE,
        detalle=detalle or (
            f'Como {permisos.ETIQUETA_ROL.get(rol, rol)} solo trabajas con '
            f'"{etiqueta}" de tu propio ambito.'
        ),
        usuario=usuario,
    )


def autorizar(request, privado=False, recurso=None, accion=permisos.VER):
    """
    Comprueba el acceso a un recurso: primero quien eres, luego que puedes.

    privado=True marca los recursos con datos personales: esos nunca quedan
    abiertos, siempre exigen identificarse aunque la API este en modo
    publico.

    recurso y accion son los de permisos.py. Si se pasan, ademas de
    identificar al usuario se comprueba que su rol tenga ese permiso; el
    alcance (que ese registro concreto sea suyo) lo afina cada vista, porque
    hace falta haber buscado el objeto para saberlo.
    """
    resultado = identificar(request)

    if not resultado:
        # En modo publico, quien no se identifica no es un intruso: es un
        # visitante, y como tal tiene su propia fila en la matriz. Se le da
        # esa identidad y se sigue por el camino de siempre, de modo que sus
        # limites se comprueban igual que los de todos los demas.
        puede_visitar = (
            resultado.motivo == SIN_CREDENCIALES
            and not privado
            and accion == permisos.VER
            and modo() == 'publica'
        )

        if not puede_visitar:
            return resultado

        resultado = Resultado(True, ABIERTO, usuario=permisos.VISITA)

    if recurso and not permisos.puede(resultado.usuario, recurso, accion):
        return _negar_permiso(resultado.usuario, recurso, accion)

    return resultado


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
    acceso = identificar(request)
    persona = acceso.persona

    return {
        'modo': modo(),
        'vias': {
            'token': {
                'activa': acceso.via == TOKEN,
                'como': 'Authorization: Bearer <token>. El token se obtiene '
                        'en POST /api/auth/login/ con el correo y la '
                        'contrasena de cualquier cuenta activa.',
                'roles_permitidos': roles_permitidos(),
            },
            'sesion': {
                'activa': por_sesion(request),
                'como': 'Inicia sesion en el sitio o en /admin/ y consulta '
                        'la API en la misma ventana del navegador.',
                'roles_permitidos': roles_permitidos(),
            },
            'clave': {
                'configurada': bool(getattr(settings, 'API_CLAVE', '')),
                'activa': por_clave(request),
                'como': 'Encabezado X-API-Key: <clave>  (o ?clave=<clave>)',
            },
        },
        'acceso_actual': {
            'autorizado': bool(acceso),
            'via': acceso.via,
            'usuario': persona.correo if persona else None,
            'rol': acceso.rol,
            'motivo': acceso.motivo,
            'mensaje': acceso.mensaje or None,
        },
        'permisos': permisos.resumen(acceso.usuario) if acceso and acceso.usuario else None,
    }
