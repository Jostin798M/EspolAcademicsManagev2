"""
Vistas de consulta de la API y autenticacion.

Todas devuelven JSON con la forma:

    {"ok": true,  "datos": ...,  "paginacion": {...}}
    {"ok": false, "error": "...", "codigo": 404}

Cada vista declara en su decorador sobre que recurso trabaja; el decorador
comprueba que el rol tenga el permiso y la vista recorta los datos al
alcance de quien pregunta (su facultad, sus cursos o los suyos). Dos
personas pueden pedir /api/cursos/ y recibir listas distintas: eso no es un
error, es el alcance haciendo su trabajo.

Las vistas que crean, editan y eliminan viven en escritura.py, y las del
panel propio de cada rol en panel.py.
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

from . import permisos, seguridad
from .models import TokenApi
from .respuestas import (
    ErrorApi,
    cuerpo_json,
    endpoint,
    error,
    esta_autenticado,
    exigir_alcance,
    no_autorizado,
    ok,
    paginar,
    quien,
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


def curso_al_alcance(request, codigo, recurso=permisos.CURSOS_R,
                     accion=permisos.VER):
    """
    Busca el curso y comprueba que quede dentro del alcance de quien pide.

    Es el paso que el decorador no puede dar: el permiso ya esta concedido
    ("este rol puede ver tareas"), pero hasta que no se encuentra el curso
    no se sabe si es uno de los suyos. Responde 404 si no existe y 403 si
    existe pero no le corresponde.
    """
    curso = _curso(codigo)
    usuario = quien(request)

    exigir_alcance(
        request,
        permisos.puede_sobre_curso(usuario, recurso, accion, curso),
        recurso,
        detalle=f'El curso {curso.codigo} no esta entre los que puedes '
                f'{accion} con tu rol.',
    )

    return curso


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
        'metodos': ['GET', 'POST', 'PATCH', 'PUT', 'DELETE'],
        'como_funciona': {
            'quien_entra': 'Cualquier cuenta activa, con el rol que tenga.',
            'que_puede': 'Depende de su rol. Consulta tus permisos en '
                         + _url(request, 'mis_permisos'),
            'donde_empezar': 'Entra en /api/auth/login/ y abre despues '
                             + _url(request, 'mi_panel'),
            'roles': {
                'SUPERADMIN': 'Todo el sistema.',
                'ADMIN': 'Su facultad: cursos, personas y reportes.',
                'PROFESOR': 'Los cursos que dicta: contenido, tareas, notas.',
                'ESTUDIANTE': 'Los cursos que cursa, sus entregas y su ficha.',
            },
        },
        'seguridad': seguridad_actual,
        'paginacion': {
            'parametros': ['pagina', 'tam'],
            'tam_por_defecto': settings.API_TAM_PAGINA,
            'tam_maximo': settings.API_TAM_PAGINA_MAX,
        },
        'recursos': {
            'estado': _url(request, 'estado'),

            'auth_login': _url(request, 'auth_login'),
            'auth_verificar': _url(request, 'auth_verificar'),
            'auth_logout': _url(request, 'auth_logout'),

            'mi_panel': _url(request, 'mi_panel'),
            'mis_permisos': _url(request, 'mis_permisos'),
            'mi_perfil': _url(request, 'mi_perfil'),
            'mis_cursos': _url(request, 'mis_cursos'),
            'mis_tareas': _url(request, 'mis_tareas'),

            'facultades': _url(request, 'facultades'),
            'facultad_detalle': _url(request, 'facultad_detalle', codigo='FIEC'),
            'curso_progreso': _url(request, 'curso_progreso', codigo='CODIGO'),
            'quiz_respuestas': _url(request, 'quiz_respuestas', id_quiz=1),
            'respuesta_quiz_detalle': _url(request, 'respuesta_quiz_detalle', id_respuesta=1),

            'cursos': _url(request, 'cursos'),
            'curso_detalle': _url(request, 'curso_detalle', codigo='CODIGO'),
            'curso_modulos': _url(request, 'curso_modulos', codigo='CODIGO'),
            'curso_tareas': _url(request, 'curso_tareas', codigo='CODIGO'),
            'curso_quizzes': _url(request, 'curso_quizzes', codigo='CODIGO'),
            'curso_estudiantes': _url(request, 'curso_estudiantes', codigo='CODIGO'),

            'modulo_detalle': _url(request, 'modulo_detalle', id_modulo=1),
            'modulo_materiales': _url(request, 'modulo_materiales', id_modulo=1),
            'modulo_progreso': _url(request, 'modulo_progreso', id_modulo=1),
            'material_detalle': _url(request, 'material_detalle', id_material=1),

            'tarea_detalle': _url(request, 'tarea_detalle', id_tarea=1),
            'tarea_entregas': _url(request, 'tarea_entregas', id_tarea=1),
            'entrega_detalle': _url(request, 'entrega_detalle', id_entrega=1),

            'quiz_detalle': _url(request, 'quiz_detalle', id_quiz=1),
            'quiz_preguntas': _url(request, 'quiz_preguntas', id_quiz=1),
            'pregunta_detalle': _url(request, 'pregunta_detalle', id_pregunta=1),

            'inscripcion_detalle': _url(request, 'inscripcion_detalle', id_inscripcion=1),

            'reporte_resumen': _url(request, 'reporte_resumen'),

            'usuarios': _url(request, 'usuarios'),
            'usuario_detalle': _url(request, 'usuario_detalle', id_usuario=1),
        },

        # Que metodos acepta cada recurso. Va aparte de las direcciones para
        # que quien ya leia "recursos" siga encontrando ahi la URL limpia.
        'metodos_por_recurso': {
            'auth_login': ['POST'],
            'facultades': ['GET', 'POST'],
            'facultad_detalle': ['GET', 'PATCH', 'PUT'],
            'quiz_respuestas': ['GET', 'POST'],
            'respuesta_quiz_detalle': ['PATCH'],
            'auth_logout': ['POST'],
            'mi_perfil': ['GET', 'PATCH'],
            'cursos': ['GET', 'POST'],
            'curso_detalle': ['GET', 'PATCH', 'PUT', 'DELETE'],
            'curso_modulos': ['GET', 'POST'],
            'curso_tareas': ['GET', 'POST'],
            'curso_quizzes': ['GET', 'POST'],
            'curso_estudiantes': ['GET', 'POST'],
            'modulo_detalle': ['GET', 'PATCH', 'PUT', 'DELETE'],
            'modulo_materiales': ['POST'],
            'modulo_progreso': ['POST', 'PATCH'],
            'material_detalle': ['PATCH', 'PUT', 'DELETE'],
            'tarea_detalle': ['GET', 'PATCH', 'PUT', 'DELETE'],
            'tarea_entregas': ['GET', 'POST'],
            'entrega_detalle': ['PATCH', 'PUT'],
            'quiz_detalle': ['GET', 'PATCH', 'PUT', 'DELETE'],
            'quiz_preguntas': ['POST'],
            'pregunta_detalle': ['PATCH', 'PUT', 'DELETE'],
            'inscripcion_detalle': ['DELETE'],
            'usuarios': ['GET', 'POST'],
            'usuario_detalle': ['GET', 'PATCH', 'PUT', 'DELETE'],
        },

        'filtros': {
            'cursos': ['facultad', 'estado', 'buscar', 'profesor'],
            'usuarios': ['rol', 'estado', 'facultad', 'buscar'],
            'mis_tareas': ['curso'],
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

@endpoint(recurso=permisos.FACULTADES)
def facultades(request):
    """El catalogo de facultades lo ven todos los roles: no es dato personal."""
    consulta = Facultad.objects.annotate(
        total_cursos=Count('cursos'),
    ).order_by('codigo')

    return paginar(consulta, request, facultad_json)


@endpoint(recurso=permisos.FACULTADES)
def facultad_detalle(request, codigo):
    """La facultad la ve cualquiera; sus cursos, solo los que le tocan."""
    facultad = get_object_or_404(
        Facultad.objects.annotate(total_cursos=Count('cursos')),
        codigo__iexact=codigo,
    )

    visibles = permisos.filtrar_cursos(
        facultad.cursos.select_related('facultad', 'profesor'),
        quien(request),
    )

    datos = facultad_json(facultad)
    datos['cursos'] = [curso_json(curso) for curso in visibles]
    datos['mis_cursos'] = len(datos['cursos'])

    return ok(datos)


# ── Cursos ───────────────────────────────────────────────────────────────────

@endpoint(recurso=permisos.CURSOS_R)
def cursos(request):
    """
    Cursos con filtros ?facultad= ?estado= ?buscar= ?profesor=.

    La lista sale ya recortada: el super administrador ve todos, el
    administrador los de su facultad, el profesor los que dicta y el
    estudiante los que cursa.
    """
    consulta = permisos.filtrar_cursos(
        Curso.objects.select_related('facultad', 'profesor'),
        quien(request),
    )

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


@endpoint(recurso=permisos.CURSOS_R)
def curso_detalle(request, codigo):
    curso_al_alcance(request, codigo)

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

    return ok(curso_detalle_json(
        curso,
        puedo=permisos.acciones_en_curso(quien(request), curso),
    ))


@endpoint(recurso=permisos.MODULOS)
def curso_modulos(request, codigo):
    curso = curso_al_alcance(request, codigo, permisos.MODULOS)

    consulta = curso.modulos.select_related('curso').prefetch_related('materiales')

    return paginar(consulta, request, modulo_json)


@endpoint(recurso=permisos.TAREAS)
def curso_tareas(request, codigo):
    curso = curso_al_alcance(request, codigo, permisos.TAREAS)

    return paginar(curso.tareas.select_related('curso'), request, tarea_json)


@endpoint(recurso=permisos.QUIZZES)
def curso_quizzes(request, codigo):
    curso = curso_al_alcance(request, codigo, permisos.QUIZZES)

    consulta = curso.quizzes.select_related('curso').annotate(
        total_preguntas=Count('preguntas'),
    )

    return paginar(consulta, request, quiz_json)


@endpoint(recurso=permisos.MODULOS)
def modulo_detalle(request, id_modulo):
    """
    Un modulo con sus materiales, por su id.

    Existe porque una pantalla puede abrir un modulo directamente, sin
    haber cargado antes el curso entero.
    """
    modulo = get_object_or_404(
        Modulo.objects.select_related('curso', 'curso__facultad').prefetch_related(
            'materiales',
        ),
        pk=id_modulo,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        permisos.puede_sobre_curso(usuario, permisos.MODULOS, permisos.VER, modulo.curso),
        permisos.MODULOS,
        detalle=f'El modulo es del curso {modulo.curso.codigo}, que no es tuyo.',
    )

    return ok(modulo_json(modulo))


@endpoint(recurso=permisos.TAREAS)
def tarea_detalle(request, id_tarea):
    """
    Una tarea suelta, por su id.

    La ficha de una tarea se abre por enlace directo, sin haber pasado por
    el curso, y por eso hace falta esta ruta ademas de la lista que cuelga
    del curso.
    """
    tarea = get_object_or_404(
        Tarea.objects.select_related('curso', 'curso__facultad'), pk=id_tarea,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        permisos.puede_sobre_curso(usuario, permisos.TAREAS, permisos.VER, tarea.curso),
        permisos.TAREAS,
        detalle=f'La tarea es del curso {tarea.curso.codigo}, que no es tuyo.',
    )

    datos = tarea_json(tarea)
    datos['puedo'] = [
        accion for accion in permisos.ACCIONES
        if permisos.puede_sobre_curso(usuario, permisos.TAREAS, accion, tarea.curso)
    ]

    return ok(datos)


@endpoint(recurso=permisos.QUIZZES)
def quiz_detalle(request, id_quiz):
    """
    Quiz con sus preguntas.

    La respuesta correcta solo viaja para quien puede editar el quiz: el
    profesor la necesita para revisarlo, el estudiante no debe verla.
    """
    quiz = get_object_or_404(
        Quiz.objects.select_related('curso', 'curso__facultad').prefetch_related(
            'preguntas',
        ).annotate(total_preguntas=Count('preguntas')),
        pk=id_quiz,
    )

    usuario = quien(request)

    exigir_alcance(
        request,
        permisos.puede_sobre_curso(usuario, permisos.QUIZZES, permisos.VER, quiz.curso),
        permisos.QUIZZES,
        detalle=f'El quiz {quiz.id_quiz} es del curso {quiz.curso.codigo}, '
                f'que no esta entre los tuyos.',
    )

    con_respuestas = permisos.puede_sobre_curso(
        usuario, permisos.PREGUNTAS, permisos.EDITAR, quiz.curso,
    )

    return ok(quiz_json(quiz, con_preguntas=True, con_respuestas=con_respuestas))


# ── Reportes ─────────────────────────────────────────────────────────────────

@endpoint(recurso=permisos.REPORTES)
def reporte_resumen(request):
    """
    Indicadores agregados del tablero (sin datos personales).

    Los numeros salen solo de los cursos que el usuario alcanza: el decano
    ve los de su facultad y el profesor los de sus cursos, de modo que el
    mismo endpoint sirve de tablero a cada rol sin ensenar de mas.
    """
    facultad = request.GET.get('facultad', '').strip()
    estado_curso = request.GET.get('estado', '').strip().lower() or None

    id_facultad = None
    if facultad:
        id_facultad = get_object_or_404(
            Facultad, codigo__iexact=facultad,
        ).id_facultad

    seleccion = permisos.filtrar_cursos(
        servicios.cursos_filtrados(id_facultad, estado_curso),
        quien(request),
    )

    return ok({
        'resumen': servicios.resumen_general(seleccion),
        'por_facultad': servicios.estudiantes_por_facultad(),
        'promedios_por_curso': servicios.promedio_por_curso(seleccion),
        'estado_entregas': servicios.estado_entregas(seleccion),
        'cursos_por_estado': servicios.cursos_por_estado(seleccion),
        'alcance': permisos.alcance_de(
            quien(request), permisos.REPORTES, permisos.VER,
        ),
        'cursos_incluidos': seleccion.count(),
    })


# ── Recursos privados (datos personales) ─────────────────────────────────────

@endpoint(privado=True, recurso=permisos.USUARIOS)
def usuarios(request):
    """
    Listado de personas, recortado a quien tiene derecho a ver cada rol.

    El super administrador ve el directorio entero; el administrador, su
    facultad; el profesor, los inscritos en sus cursos; y el estudiante,
    unicamente su propia ficha.
    """
    consulta = permisos.filtrar_usuarios(
        Usuario.objects.select_related('facultad'),
        quien(request),
    )

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


@endpoint(privado=True, recurso=permisos.INSCRIPCIONES)
def curso_estudiantes(request, codigo):
    """Estudiantes inscritos en un curso, si el curso es de los suyos."""
    curso = curso_al_alcance(request, codigo, permisos.INSCRIPCIONES)

    consulta = Inscripcion.objects.filter(curso=curso).select_related(
        'usuario', 'usuario__facultad', 'curso',
    )

    # Por defecto solo los estudiantes, que es lo que pide el nombre de la
    # ruta. Con ?rol=PROFESOR o ?rol=todos se obtienen los demas.
    rol_pedido = request.GET.get('rol', '').strip().upper() or 'ESTUDIANTE'

    if rol_pedido != 'TODOS':
        validos = [opcion.value for opcion in Inscripcion.RolEnCurso]

        if rol_pedido not in validos:
            raise ErrorApi(
                f'Rol "{rol_pedido}" no valido. Usa: {", ".join(validos)} o todos.',
            )

        consulta = consulta.filter(rol_en_curso=rol_pedido)

    return paginar(consulta, request, inscripcion_json)


# ── Autenticacion de aplicaciones externas ───────────────────────────────────
# Estas tres rutas son las que usa otra aplicacion con su propio login: pide
# un token con sus credenciales (login), comprueba en cualquier momento si
# sigue sirviendo (verificar) y lo devuelve cuando cierra sesion (logout).
#
# Entra cualquier cuenta activa, no solo la del super administrador. Lo que
# cambia de una a otra no es si recibe token, sino que trae dentro: el rol
# efectivo y la lista de lo que ese rol puede ver, crear, editar y eliminar.

def _usuario_publico(usuario):
    """
    Ficha del usuario que se devuelve a quien inicia sesion.

    Lleva los mismos nombres de campo que usa el frontend (id, iniciales,
    nombre_completo) para que index.html pueda guardarla tal cual, y ademas
    el rol efectivo, que es con el que trabajan la app movil y la web.
    """
    rol = permisos.rol_efectivo(usuario)

    return {
        'id_usuario': usuario.id_usuario,
        'id': usuario.id_usuario,
        'nombres': usuario.nombres,
        'apellidos': usuario.apellidos,
        'nombre_completo': usuario.nombre_completo,
        'iniciales': usuario.iniciales,
        'correo': usuario.correo,
        'rol': usuario.rol,
        'rol_efectivo': rol,
        'rol_etiqueta': permisos.ETIQUETA_ROL.get(rol, rol),
        'estado': usuario.estado,
        'es_superadmin': rol == permisos.SUPERADMIN,
        'facultad': usuario.facultad.codigo if usuario.facultad_id else None,
        'facultad_nombre': usuario.facultad.nombre if usuario.facultad_id else None,
    }


def _rol_activo(usuario):
    """
    Con que sombrero entra al sitio quien tiene rol USER.

    El frontend distingue el panel de profesor del de estudiante, y esa
    diferencia no esta en el campo rol sino en las inscripciones. Lo decide
    permisos.rol_efectivo(); aqui solo se devuelve None para los roles que
    ya vienen escritos en la ficha, que es lo que el frontend espera.
    """
    if usuario.rol != Usuario.Rol.USER:
        return None

    return permisos.rol_efectivo(usuario)


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
    Entrega un token a quien inicia sesion, sea cual sea su rol.

    Es tambien el login del sitio: la pantalla de index.html llama aqui.

    Cuerpo (JSON o formulario):

        {"correo": "ana@espol.edu.ec", "password": "...",
         "aplicacion": "Mi App", "dias": 30, "sesion": false, "token": true}

    Entra cualquier cuenta activa. Lo que distingue a un super
    administrador de un estudiante no es si recibe token, sino que viene
    dentro de la respuesta:

        rol       -> SUPERADMIN, ADMIN, PROFESOR o ESTUDIANTE
        permisos  -> que puede ver, crear, editar y eliminar de cada cosa
        panel     -> la pantalla de inicio que le corresponde

    La aplicacion que llama usa "permisos" para dibujar su interfaz (que
    pestanas ensena, que botones habilita). No es una autorizacion: el
    servidor vuelve a comprobarlo todo en cada peticion.

    Con "sesion": true se abre ademas la cookie de sesion de Django, la
    misma de /admin/ y /panel/, para que un solo login sirva para el sitio
    entero. Es lo que hace index.html.

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
    rol = permisos.rol_efectivo(usuario)

    if not autorizado:
        # El rol quedo fuera de API_ROLES: el administrador del sitio le
        # cerro la puerta a ese rol entero.
        return error(
            seguridad.NO_IDENTIFICADO,
            403,
            autorizado=False,
            motivo=seguridad.ROL_SIN_ACCESO,
            detalle=f'La cuenta {usuario.correo} entra como {rol}, y ese rol '
                    f'no esta habilitado en este sitio '
                    f'({", ".join(seguridad.roles_permitidos())}).',
            usuario=_usuario_publico(usuario),
        )

    if quiere_sesion:
        # Login del sitio (index.html): deja la cookie de sesion, la misma
        # que reconocen /admin/, /panel/ y la propia API. Con un solo login
        # el usuario queda dentro de todo lo que su rol le permite.
        abrir_sesion(request, usuario)

    respuesta = {
        'autorizado': True,
        'usuario': _usuario_publico(usuario),
        'rol': rol,
        'rol_activo': _rol_activo(usuario),
        'permisos': permisos.resumen(usuario),
        'panel': _url(request, 'mi_panel'),
        'sesion_django': quiere_sesion,
        'acceso': 'completo',
        'token': None,
    }

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
        'rol_del_token': token.rol,
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
    Dice si el token sigue sirviendo, de quien es y que permite hoy.

    Es lo primero que llama la app movil al arrancar. Devuelve los permisos
    recalculados en este momento, no los que tenia el token al nacer: si al
    profesor le quitaron un curso o al usuario lo ascendieron a
    administrador, la app se entera aqui y redibuja su menu.
    """
    # privado=True: aunque el catalogo este en modo publico, aqui se
    # pregunta por una identidad concreta, no por el acceso anonimo.
    acceso = seguridad.autorizar(request, privado=True)

    if not acceso:
        return no_autorizado(request, acceso)

    persona = acceso.persona

    datos = {
        'autorizado': True,
        'via': acceso.via,
        'mensaje': f'Sesion confirmada como {acceso.rol}.' if persona
                   else 'Acceso confirmado con la clave del sitio.',
        'usuario': _usuario_publico(persona) if persona else None,
        'rol': acceso.rol,
        'permisos': permisos.resumen(acceso.usuario),
        'panel': _url(request, 'mi_panel'),
        'roles_permitidos': seguridad.roles_permitidos(),
        'acceso': 'completo',
    }

    if acceso.token:
        datos['token'] = {
            'prefijo': acceso.token.prefijo,
            'aplicacion': acceso.token.aplicacion or None,
            'creado': acceso.token.creado.isoformat(),
            'expira': acceso.token.expira.isoformat() if acceso.token.expira else None,
            'rol_al_emitir': acceso.token.rol or None,
            'rol_cambio': bool(acceso.token.rol) and acceso.token.rol != acceso.rol,
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


@endpoint(privado=True, recurso=permisos.USUARIOS)
def usuario_detalle(request, id_usuario):
    """
    La ficha de una persona, si esta dentro del circulo de quien pregunta.

    Se reutiliza el mismo filtro del listado en lugar de escribir otra
    comprobacion: si la persona no aparece en el listado que le corresponde,
    tampoco puede abrirla por su id.
    """
    persona = get_object_or_404(
        permisos.filtrar_usuarios(
            Usuario.objects.select_related('facultad'), quien(request),
        ),
        pk=id_usuario,
    )

    datos = usuario_json(persona)
    datos['rol_efectivo'] = permisos.rol_efectivo(persona)

    inscripciones = Inscripcion.objects.filter(
        usuario=persona,
        curso__in=permisos.cursos_visibles(quien(request)),
    ).select_related('curso')

    datos['cursos'] = [
        {
            'codigo': inscripcion.curso.codigo,
            'nombre': inscripcion.curso.nombre,
            'rol_en_curso': inscripcion.rol_en_curso,
        }
        for inscripcion in inscripciones
    ]

    return ok(datos)
