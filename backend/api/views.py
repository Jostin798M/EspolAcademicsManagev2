"""
Vistas de la API publica (solo lectura).

Todas devuelven JSON con la forma:

    {"ok": true,  "datos": ...,  "paginacion": {...}}
    {"ok": false, "error": "...", "codigo": 404}

La autenticacion es por clave: encabezado X-API-Key o parametro ?clave=.
"""
from django.conf import settings
from django.contrib.auth import authenticate, login as abrir_sesion
from django.contrib.auth import logout as cerrar_sesion
from django.db import connection
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse

from accounts.models import Usuario
from cursos.models import Curso, Facultad, Inscripcion, Modulo
from evaluaciones.models import Quiz, Tarea
from reportes import servicios

from . import seguridad
from .models import TokenApi
from .respuestas import (
    ErrorApi,
    cuerpo_json,
    endpoint,
    error,
    esta_autenticado,
    no_autorizado,
    ok,
    paginar,
    texto,
)
from .serializadores import (
    curso_detalle_json,
    curso_json,
    facultad_json,
    inscripcion_json,
    modulo_json,
    quiz_json,
    tarea_json,
    usuario_json,
)

VERSION = '1.0'


def _url(request, nombre, **kwargs):
    return request.build_absolute_uri(reverse(f'api:{nombre}', kwargs=kwargs))


def _curso(codigo):
    """Busca un curso por su codigo (no por id) para URLs legibles."""
    return get_object_or_404(
        Curso.objects.select_related('facultad', 'profesor'),
        codigo__iexact=codigo,
    )


# ── Descubrimiento ───────────────────────────────────────────────────────────

@endpoint(abierto=True)
def indice(request):
    """
    Lista los recursos disponibles: es la portada de la API.

    No pide clave aunque este configurada. No devuelve ningun dato del
    sistema y es lo primero que abre quien la va a usar.
    """
    seguridad_actual = seguridad.resumen(request)
    seguridad_actual['ejemplos'] = {
        'otra_aplicacion': 'curl -X POST -H "Content-Type: application/json" '
                           '-d \'{"correo":"TU_CORREO","password":"TU_CLAVE"}\' '
                           + _url(request, 'auth_login'),
        'con_token': 'curl -H "Authorization: Bearer TU_TOKEN" '
                     + _url(request, 'cursos'),
        'navegador': 'Inicia sesion en '
                     + request.build_absolute_uri('/admin/')
                     + ' y abre '
                     + request.build_absolute_uri(reverse('api:cursos')),
        'curl': 'curl -H "X-API-Key: TU_CLAVE" '
                + request.build_absolute_uri(reverse('api:cursos')),
    }

    return ok({
        'nombre': 'API ESPOL Academics',
        'version': VERSION,
        'formato': 'JSON (UTF-8)',
        'metodos': ['GET'],
        'seguridad': seguridad_actual,
        'paginacion': {
            'parametros': ['pagina', 'tam'],
            'tam_por_defecto': settings.API_TAM_PAGINA,
            'tam_maximo': settings.API_TAM_PAGINA_MAX,
        },
        'recursos': {
            'estado': _url(request, 'estado'),
            'auth_login (POST)': _url(request, 'auth_login'),
            'auth_verificar': _url(request, 'auth_verificar'),
            'auth_logout (POST)': _url(request, 'auth_logout'),
            'facultades': _url(request, 'facultades'),
            'facultad_detalle': _url(request, 'facultad_detalle', codigo='FIEC'),
            'cursos': _url(request, 'cursos'),
            'curso_detalle': _url(request, 'curso_detalle', codigo='CODIGO'),
            'curso_modulos': _url(request, 'curso_modulos', codigo='CODIGO'),
            'curso_tareas': _url(request, 'curso_tareas', codigo='CODIGO'),
            'curso_quizzes': _url(request, 'curso_quizzes', codigo='CODIGO'),
            'quiz_detalle': _url(request, 'quiz_detalle', id_quiz=1),
            'reporte_resumen': _url(request, 'reporte_resumen'),
            'usuarios (privado)': _url(request, 'usuarios'),
            'curso_estudiantes (privado)': _url(
                request, 'curso_estudiantes', codigo='CODIGO',
            ),
        },
        'filtros': {
            'cursos': ['facultad', 'estado', 'buscar', 'profesor'],
            'usuarios': ['rol', 'estado', 'facultad', 'buscar'],
            'reporte_resumen': ['facultad', 'estado'],
        },
    })


@endpoint(abierto=True)
def estado(request):
    """
    Comprobacion de salud: sirve para monitorear el servicio.

    Responde sin clave para que cualquier monitor pueda consultarlo, pero
    los totales solo se muestran a quien la envia.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        base_ok = True
    except Exception:
        base_ok = False

    datos = {
        'servicio': 'ESPOL Academics API',
        'version': VERSION,
        'base_de_datos': 'ok' if base_ok else 'sin conexion',
        'motor': connection.vendor,
    }

    if base_ok and esta_autenticado(request):
        datos['totales'] = {
            'facultades': Facultad.objects.count(),
            'cursos': Curso.objects.count(),
            'modulos': Modulo.objects.count(),
            'tareas': Tarea.objects.count(),
            'quizzes': Quiz.objects.count(),
        }

    return ok(datos)


# ── Facultades ───────────────────────────────────────────────────────────────

@endpoint()
def facultades(request):
    consulta = Facultad.objects.annotate(
        total_cursos=Count('cursos'),
    ).order_by('codigo')

    return paginar(consulta, request, facultad_json)


@endpoint()
def facultad_detalle(request, codigo):
    facultad = get_object_or_404(
        Facultad.objects.annotate(total_cursos=Count('cursos')),
        codigo__iexact=codigo,
    )

    datos = facultad_json(facultad)
    datos['cursos'] = [
        curso_json(curso)
        for curso in facultad.cursos.select_related('facultad', 'profesor')
    ]

    return ok(datos)


# ── Cursos ───────────────────────────────────────────────────────────────────

@endpoint()
def cursos(request):
    """Catalogo de cursos con filtros ?facultad= ?estado= ?buscar= ?profesor=."""
    consulta = Curso.objects.select_related('facultad', 'profesor')

    facultad = request.GET.get('facultad', '').strip()
    if facultad:
        consulta = consulta.filter(facultad__codigo__iexact=facultad)

    estado_curso = request.GET.get('estado', '').strip().lower()
    if estado_curso:
        validos = [opcion.value for opcion in Curso.Estado]
        if estado_curso not in validos:
            raise ErrorApi(
                f'Estado "{estado_curso}" no valido. Usa: {", ".join(validos)}.'
            )
        consulta = consulta.filter(estado=estado_curso)

    profesor = request.GET.get('profesor', '').strip()
    if profesor:
        if profesor.isdigit():
            consulta = consulta.filter(profesor__id_usuario=profesor)
        else:
            consulta = consulta.filter(profesor__correo__iexact=profesor)

    buscar = request.GET.get('buscar', '').strip()
    if buscar:
        consulta = consulta.filter(
            Q(nombre__icontains=buscar) | Q(codigo__icontains=buscar),
        )

    return paginar(consulta, request, curso_json)


@endpoint()
def curso_detalle(request, codigo):
    curso = get_object_or_404(
        Curso.objects.select_related('facultad', 'profesor').prefetch_related(
            'formula',
            'tareas',
            Prefetch('quizzes', queryset=Quiz.objects.annotate(
                total_preguntas=Count('preguntas'),
            )),
            Prefetch('modulos', queryset=Modulo.objects.prefetch_related(
                'materiales',
            ).select_related('curso')),
        ),
        codigo__iexact=codigo,
    )

    return ok(curso_detalle_json(curso))


@endpoint()
def curso_modulos(request, codigo):
    curso = _curso(codigo)

    consulta = curso.modulos.select_related('curso').prefetch_related('materiales')

    return paginar(consulta, request, modulo_json)


@endpoint()
def curso_tareas(request, codigo):
    curso = _curso(codigo)

    return paginar(curso.tareas.select_related('curso'), request, tarea_json)


@endpoint()
def curso_quizzes(request, codigo):
    curso = _curso(codigo)

    consulta = curso.quizzes.select_related('curso').annotate(
        total_preguntas=Count('preguntas'),
    )

    return paginar(consulta, request, quiz_json)


@endpoint()
def quiz_detalle(request, id_quiz):
    """Quiz con sus preguntas. No incluye las respuestas correctas."""
    quiz = get_object_or_404(
        Quiz.objects.select_related('curso').prefetch_related('preguntas').annotate(
            total_preguntas=Count('preguntas'),
        ),
        pk=id_quiz,
    )

    return ok(quiz_json(quiz, con_preguntas=True))


# ── Reportes ─────────────────────────────────────────────────────────────────

@endpoint()
def reporte_resumen(request):
    """Indicadores agregados del tablero (sin datos personales)."""
    facultad = request.GET.get('facultad', '').strip()
    estado_curso = request.GET.get('estado', '').strip().lower() or None

    id_facultad = None
    if facultad:
        id_facultad = get_object_or_404(
            Facultad, codigo__iexact=facultad,
        ).id_facultad

    seleccion = servicios.cursos_filtrados(id_facultad, estado_curso)

    return ok({
        'resumen': servicios.resumen_general(seleccion),
        'por_facultad': servicios.estudiantes_por_facultad(),
        'promedios_por_curso': servicios.promedio_por_curso(seleccion),
        'estado_entregas': servicios.estado_entregas(seleccion),
        'cursos_por_estado': servicios.cursos_por_estado(seleccion),
    })


# ── Recursos privados (datos personales) ─────────────────────────────────────

@endpoint(privado=True)
def usuarios(request):
    """Listado de usuarios. Exige clave: contiene datos personales."""
    consulta = Usuario.objects.select_related('facultad')

    rol = request.GET.get('rol', '').strip().upper()
    if rol:
        consulta = consulta.filter(rol=rol)

    estado_usuario = request.GET.get('estado', '').strip().lower()
    if estado_usuario:
        consulta = consulta.filter(estado=estado_usuario)

    facultad = request.GET.get('facultad', '').strip()
    if facultad:
        consulta = consulta.filter(facultad__codigo__iexact=facultad)

    buscar = request.GET.get('buscar', '').strip()
    if buscar:
        consulta = consulta.filter(
            Q(nombres__icontains=buscar)
            | Q(apellidos__icontains=buscar)
            | Q(correo__icontains=buscar),
        )

    return paginar(consulta, request, usuario_json)


@endpoint(privado=True)
def curso_estudiantes(request, codigo):
    """Estudiantes inscritos en un curso. Exige clave."""
    curso = _curso(codigo)

    consulta = Inscripcion.objects.filter(
        curso=curso,
        rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
    ).select_related('usuario', 'usuario__facultad', 'curso')

    return paginar(consulta, request, inscripcion_json)


# ── Autenticacion de aplicaciones externas ───────────────────────────────────
# Estas tres rutas son las que usa otra aplicacion con su propio login: pide
# un token con las credenciales de un super administrador de esta base de
# datos (login), comprueba en cualquier momento si sigue autorizada
# (verificar) y lo devuelve cuando su usuario cierra sesion (logout).

def _usuario_publico(usuario):
    """
    Ficha del usuario que se devuelve a quien inicia sesion.

    Lleva los mismos nombres de campo que usa el frontend (id, iniciales,
    nombre_completo) para que index.html pueda guardarla tal cual.
    """
    return {
        'id_usuario': usuario.id_usuario,
        'id': usuario.id_usuario,
        'nombres': usuario.nombres,
        'apellidos': usuario.apellidos,
        'nombre_completo': usuario.nombre_completo,
        'iniciales': usuario.iniciales,
        'correo': usuario.correo,
        'rol': usuario.rol,
        'estado': usuario.estado,
        'es_superadmin': seguridad.es_usuario_autorizado(usuario),
        'facultad': usuario.facultad.codigo if usuario.facultad_id else None,
    }


def _rol_activo(usuario):
    """
    Con que sombrero entra al sitio quien tiene rol USER.

    El frontend necesita saber si a un USER le toca el panel de profesor o
    el de estudiante; se decide por sus inscripciones, igual que antes lo
    hacia js/api.js con los datos locales.
    """
    if usuario.rol != Usuario.Rol.USER:
        return None

    es_profesor = Inscripcion.objects.filter(
        usuario=usuario,
        rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
    ).exists()

    return 'PROFESOR' if es_profesor else 'ESTUDIANTE'


def _quiere_sesion(datos):
    """El que llama pide ademas la cookie de sesion (lo hace index.html)."""
    return str(datos.get('sesion', '')).strip().lower() in ('1', 'true', 'si', 'yes')


def _quiere_token(datos):
    """
    Si hay que emitir token. Por defecto si.

    El sitio web manda "token": false: le basta la cookie de sesion, y asi
    no se guarda ningun token en el navegador ni se llena la tabla con uno
    por cada vez que alguien entra.
    """
    return str(datos.get('token', True)).strip().lower() not in ('0', 'false', 'no')


def _dias_solicitados(datos):
    """Duracion del token pedida por la aplicacion, dentro de los limites."""
    crudo = datos.get('dias')

    if crudo in (None, ''):
        return settings.API_TOKEN_DIAS

    try:
        dias = int(crudo)
    except (TypeError, ValueError):
        raise ErrorApi('El campo "dias" debe ser un numero entero.')

    if not 1 <= dias <= settings.API_TOKEN_DIAS_MAX:
        raise ErrorApi(
            f'El campo "dias" debe estar entre 1 y '
            f'{settings.API_TOKEN_DIAS_MAX}.'
        )

    return dias


@endpoint(abierto=True, metodos=('POST',))
def auth_login(request):
    """
    Entrega un token a una aplicacion externa.

    Es tambien el login del sitio: la pantalla de index.html llama aqui.

    Cuerpo (JSON o formulario):

        {"correo": "jefe@espol.edu.ec", "password": "...",
         "aplicacion": "Mi App", "dias": 30, "sesion": false, "token": true}

    Hay dos maneras de llamarlo, segun quien sea:

    · Otra aplicacion (sin "sesion"): recibe el token si la cuenta es
      SUPERADMIN en ESTA base de datos, y un 403 con el mensaje "No se ha
      autorizado que sea un super admin." si no lo es.

    · El sitio web ("sesion": true): entra cualquier usuario valido, porque
      es el login de la aplicacion. Se abre la cookie de sesion de Django
      (la misma de /admin/ y /panel/) y, si ademas es super administrador,
      la respuesta trae el token de la API. Si no lo es, entra igual a su
      panel pero con "autorizado": false y el aviso.

    El texto del token se muestra UNA sola vez: guardalo al recibirlo.
    """
    datos = cuerpo_json(request)
    correo = texto(datos, 'correo', 'email', 'usuario').lower()
    contrasena = texto(datos, 'password', 'contrasena', 'clave_acceso')

    if not correo or not contrasena:
        raise ErrorApi(
            'Faltan credenciales: envia "correo" y "password" en el cuerpo.',
            400,
            motivo='faltan_credenciales',
        )

    if seguridad.intentos_disponibles(request, correo) <= 0:
        raise ErrorApi(
            'Demasiados intentos fallidos con este correo. '
            f'Espera {settings.API_LOGIN_BLOQUEO_MIN} minutos.',
            429,
            motivo='demasiados_intentos',
        )

    usuario = authenticate(request, correo=correo, password=contrasena)

    if usuario is None:
        seguridad.anotar_intento_fallido(request, correo)

        return error(
            'Correo o contrasena incorrectos.',
            401,
            autorizado=False,
            motivo='credenciales_invalidas',
            intentos_restantes=seguridad.intentos_disponibles(request, correo),
        )

    seguridad.olvidar_intentos(request, correo)
    quiere_sesion = _quiere_sesion(datos)

    if not seguridad.cuenta_activa(usuario):
        # Una cuenta inactiva no entra a ningun sitio, ni al sitio web.
        return error(
            seguridad.NO_AUTORIZADO,
            403,
            autorizado=False,
            motivo=seguridad.CUENTA_INACTIVA,
            detalle=f'La cuenta {usuario.correo} esta inactiva.',
            usuario=_usuario_publico(usuario),
        )

    autorizado = seguridad.es_usuario_autorizado(usuario)

    if not autorizado and not quiere_sesion:
        # Una aplicacion externa pidiendo token con una cuenta que no es de
        # super admin: no hay nada que entregarle.
        return error(
            seguridad.NO_AUTORIZADO,
            403,
            autorizado=False,
            motivo=seguridad.NO_SUPERADMIN,
            detalle=f'La cuenta {usuario.correo} tiene rol {usuario.rol}; '
                    f'la API solo la usan los roles '
                    f'{", ".join(seguridad.roles_permitidos())}.',
            usuario=_usuario_publico(usuario),
        )

    if quiere_sesion:
        # Login del sitio (index.html): deja la cookie de sesion, la misma
        # que reconocen /admin/, /panel/ y la propia API. Con un solo login
        # el super administrador queda dentro de todo.
        abrir_sesion(request, usuario)

    respuesta = {
        'autorizado': autorizado,
        'usuario': _usuario_publico(usuario),
        'rol_activo': _rol_activo(usuario),
        'sesion_django': quiere_sesion,
        'acceso': 'completo' if autorizado else 'sin_api',
        'token': None,
    }

    if not autorizado:
        # Entra al sitio con su rol, pero la API no se le abre.
        respuesta['aviso'] = seguridad.NO_AUTORIZADO
        respuesta['motivo'] = seguridad.NO_SUPERADMIN
        respuesta['detalle'] = (
            f'La cuenta {usuario.correo} tiene rol {usuario.rol}; '
            f'la API solo la usan los roles '
            f'{", ".join(seguridad.roles_permitidos())}.'
        )

        return ok(respuesta)

    if not _quiere_token(datos):
        # Login del sitio: la cookie ya basta, no se emite ningun token.
        respuesta['como_usarlo'] = {
            'sesion': 'Ya puedes consultar la API en esta misma ventana; '
                      'la cookie de sesion viaja sola.',
            'indice': _url(request, 'indice'),
        }

        return ok(respuesta)

    token, plano = TokenApi.objects.crear(
        usuario,
        aplicacion=texto(datos, 'aplicacion', 'app', 'cliente'),
        dias=_dias_solicitados(datos),
        ip=seguridad.ip_de(request) or None,
    )

    respuesta.update({
        'token': plano,
        'tipo': 'Bearer',
        'expira': token.expira.isoformat() if token.expira else None,
        'creado': token.creado.isoformat(),
        'como_usarlo': {
            'encabezado': 'Authorization: Bearer ' + plano,
            'alternativa': 'X-API-Token: ' + plano,
            'verificar': _url(request, 'auth_verificar'),
            'indice': _url(request, 'indice'),
            'aviso': 'El token no se vuelve a mostrar. Guardalo en el '
                     'servidor de tu aplicacion, nunca en el navegador.',
        },
    })

    return ok(respuesta)


@endpoint(abierto=True)
def auth_verificar(request):
    """
    Dice si quien pregunta esta identificado como super administrador.

    Es la ruta que consulta otra aplicacion para saber si su usuario tiene
    acceso. Responde 200 con los datos del super administrador, o 401/403
    con "No se ha autorizado que sea un super admin." y el motivo exacto.
    En los dos casos el cuerpo trae el campo "autorizado".
    """
    # privado=True: aunque el catalogo este en modo publico, aqui se
    # pregunta por el super administrador, no por el acceso anonimo.
    acceso = seguridad.autorizar(request, privado=True)

    if not acceso:
        return no_autorizado(request, acceso)

    datos = {
        'autorizado': True,
        'via': acceso.via,
        'mensaje': 'Sesion de super administrador confirmada.',
        'usuario': _usuario_publico(acceso.usuario) if acceso.usuario else None,
        'roles_permitidos': seguridad.roles_permitidos(),
        'acceso': 'completo',
    }

    if acceso.token:
        datos['token'] = {
            'prefijo': acceso.token.prefijo,
            'aplicacion': acceso.token.aplicacion or None,
            'creado': acceso.token.creado.isoformat(),
            'expira': acceso.token.expira.isoformat() if acceso.token.expira else None,
        }

    return ok(datos)


@endpoint(abierto=True, metodos=('POST',))
def auth_logout(request):
    """
    Cierra la sesion: revoca el token y/o cierra la cookie de Django.

    Es el reverso de /api/auth/login/, y sirve para los dos casos:

    · Con "Authorization: Bearer <token>" revoca ese token. Con
      {"todos": true} revoca todos los de esa cuenta, util cuando se
      sospecha que uno se filtro.
    · Desde el sitio web cierra ademas la sesion de Django, de modo que un
      solo boton de "Salir" deja fuera del sitio, de /admin/ y de la API.
    """
    acceso = request.acceso
    datos = cuerpo_json(request)
    todos = str(datos.get('todos', '')).strip().lower() in ('1', 'true', 'si', 'yes')

    revocados = 0
    token = acceso.token if acceso else None

    if token:
        if todos:
            revocados = TokenApi.objects.filter(
                usuario=token.usuario, revocado=False,
            ).update(revocado=True)
        else:
            token.revocar()
            revocados = 1

    tenia_sesion = getattr(request.user, 'is_authenticated', False)

    if tenia_sesion:
        cerrar_sesion(request)

    if not token and not tenia_sesion:
        raise ErrorApi(
            'No hay nada que cerrar: no se recibio ningun token ni hay '
            'sesion iniciada.',
            400,
            motivo='sin_token',
        )

    return ok({
        'revocados': revocados,
        'sesion_cerrada': tenia_sesion,
        'mensaje': 'Sesion cerrada. Vuelve a /api/auth/login/ para entrar.',
    })


# ── Ruta no encontrada dentro de /api/ ───────────────────────────────────────

@endpoint()
def no_encontrado(request, ruta=''):
    raise ErrorApi(
        f'El recurso "/api/{ruta}" no existe. '
        f'Consulta {_url(request, "indice")} para ver los disponibles.',
        404,
    )
