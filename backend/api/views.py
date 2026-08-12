"""
Vistas de la API publica (solo lectura).

Todas devuelven JSON con la forma:

    {"ok": true,  "datos": ...,  "paginacion": {...}}
    {"ok": false, "error": "...", "codigo": 404}

La autenticacion es por clave: encabezado X-API-Key o parametro ?clave=.
"""
from django.conf import settings
from django.db import connection
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse

from accounts.models import Usuario
from cursos.models import Curso, Facultad, Inscripcion, Modulo
from evaluaciones.models import Quiz, Tarea
from reportes import servicios

from .respuestas import ErrorApi, endpoint, ok, paginar
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

@endpoint()
def indice(request):
    """Lista los recursos disponibles: es la portada de la API."""
    return ok({
        'nombre': 'API ESPOL Academics',
        'version': VERSION,
        'formato': 'JSON (UTF-8)',
        'metodos': ['GET'],
        'autenticacion': {
            'requerida': bool(settings.API_CLAVE),
            'como': 'Encabezado X-API-Key: <clave>  (o ?clave=<clave>)',
        },
        'paginacion': {
            'parametros': ['pagina', 'tam'],
            'tam_por_defecto': settings.API_TAM_PAGINA,
            'tam_maximo': settings.API_TAM_PAGINA_MAX,
        },
        'recursos': {
            'estado': _url(request, 'estado'),
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


@endpoint()
def estado(request):
    """Comprobacion de salud: sirve para monitorear el servicio."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        base_ok = True
    except Exception:
        base_ok = False

    return ok({
        'servicio': 'ESPOL Academics API',
        'version': VERSION,
        'base_de_datos': 'ok' if base_ok else 'sin conexion',
        'motor': connection.vendor,
        'totales': {
            'facultades': Facultad.objects.count(),
            'cursos': Curso.objects.count(),
            'modulos': Modulo.objects.count(),
            'tareas': Tarea.objects.count(),
            'quizzes': Quiz.objects.count(),
        } if base_ok else None,
    })


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


# ── Ruta no encontrada dentro de /api/ ───────────────────────────────────────

@endpoint()
def no_encontrado(request, ruta=''):
    raise ErrorApi(
        f'El recurso "/api/{ruta}" no existe. '
        f'Consulta {_url(request, "indice")} para ver los disponibles.',
        404,
    )
