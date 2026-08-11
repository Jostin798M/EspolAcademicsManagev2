"""
Calculo de los indicadores academicos.

Se aisla la logica de negocio de las vistas para poder reutilizarla
tanto en el tablero HTML como en las exportaciones a CSV y PDF.
"""
from decimal import Decimal

from django.db.models import Avg, Count, F, Q, Sum

from accounts.models import Usuario
from cursos.models import Curso, Facultad, Inscripcion, Modulo, ProgresoModulo
from evaluaciones.models import Entrega, Quiz, RespuestaQuiz, Tarea


def _porcentaje(parte, total):
    return round((parte / total) * 100, 1) if total else 0.0


def resumen_general(cursos):
    """Indicadores principales que encabezan el tablero."""
    entregas = Entrega.objects.filter(tarea__curso__in=cursos)
    calificadas = entregas.exclude(nota__isnull=True)

    total_entregas = entregas.count()
    entregadas = entregas.filter(estado=Entrega.Estado.ENTREGADO).count()

    promedio = calificadas.aggregate(v=Avg('nota'))['v']

    return {
        'total_cursos': cursos.count(),
        'cursos_activos': cursos.filter(estado=Curso.Estado.ACTIVO).count(),
        'total_estudiantes': Inscripcion.objects.filter(
            curso__in=cursos,
            rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
        ).values('usuario').distinct().count(),
        'total_tareas': Tarea.objects.filter(curso__in=cursos).count(),
        'total_quizzes': Quiz.objects.filter(curso__in=cursos).count(),
        'tasa_entrega': _porcentaje(entregadas, total_entregas),
        'promedio_general': round(promedio, 2) if promedio is not None else None,
        'pendientes_calificar': entregas.filter(
            estado=Entrega.Estado.ENTREGADO,
            nota__isnull=True,
        ).count(),
    }


def estudiantes_por_facultad():
    """Cuantos estudiantes distintos hay inscritos en cada facultad."""
    filas = []

    for facultad in Facultad.objects.all().order_by('codigo'):
        total = Inscripcion.objects.filter(
            curso__facultad=facultad,
            rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
        ).values('usuario').distinct().count()

        filas.append({
            'etiqueta': facultad.codigo,
            'detalle': facultad.nombre,
            'valor': total,
            'cursos': Curso.objects.filter(facultad=facultad).count(),
        })

    return filas


def promedio_por_curso(cursos):
    """Nota promedio de las entregas calificadas de cada curso."""
    filas = []

    for curso in cursos.select_related('facultad').order_by('codigo'):
        agregado = Entrega.objects.filter(
            tarea__curso=curso,
        ).exclude(nota__isnull=True).aggregate(
            promedio=Avg('nota'),
            calificadas=Count('pk'),
        )

        promedio = agregado['promedio']

        filas.append({
            'etiqueta': curso.codigo,
            'detalle': curso.nombre,
            'facultad': curso.facultad.codigo,
            'valor': round(promedio, 2) if promedio is not None else 0,
            'calificadas': agregado['calificadas'],
            'sin_datos': promedio is None,
        })

    return filas


def estado_entregas(cursos):
    """Distribucion de las entregas por estado de calificacion."""
    entregas = Entrega.objects.filter(tarea__curso__in=cursos)

    entregadas = entregas.filter(estado=Entrega.Estado.ENTREGADO)

    return [
        {
            'etiqueta': 'Calificadas',
            'valor': entregadas.exclude(nota__isnull=True).count(),
        },
        {
            'etiqueta': 'Entregadas sin calificar',
            'valor': entregadas.filter(nota__isnull=True).count(),
        },
        {
            'etiqueta': 'Pendientes de entregar',
            'valor': entregas.filter(estado=Entrega.Estado.PENDIENTE).count(),
        },
    ]


def avance_estudiantes(cursos):
    """Porcentaje de modulos completados por cada estudiante inscrito."""
    filas = []

    inscripciones = Inscripcion.objects.filter(
        curso__in=cursos,
        rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
    ).select_related('usuario', 'curso').order_by('curso__codigo', 'usuario__apellidos')

    for inscripcion in inscripciones:
        modulos = Modulo.objects.filter(curso=inscripcion.curso)
        total = modulos.count()

        completados = ProgresoModulo.objects.filter(
            usuario=inscripcion.usuario,
            modulo__in=modulos,
            completado=True,
        ).count()

        nota = Entrega.objects.filter(
            tarea__curso=inscripcion.curso,
            usuario=inscripcion.usuario,
        ).exclude(nota__isnull=True).aggregate(v=Avg('nota'))['v']

        filas.append({
            'estudiante': inscripcion.usuario.nombre_completo,
            'correo': inscripcion.usuario.correo,
            'curso': inscripcion.curso.codigo,
            'modulos_completados': completados,
            'modulos_totales': total,
            'avance': _porcentaje(completados, total),
            'promedio': round(nota, 2) if nota is not None else None,
        })

    return filas


def cursos_por_estado(cursos):
    """Cursos activos frente a archivados."""
    return [
        {'etiqueta': 'Activos', 'valor': cursos.filter(estado=Curso.Estado.ACTIVO).count()},
        {'etiqueta': 'Archivados', 'valor': cursos.filter(estado=Curso.Estado.ARCHIVADO).count()},
    ]


def cursos_filtrados(facultad_id=None, estado=None):
    """Aplica los filtros del tablero sobre el conjunto de cursos."""
    cursos = Curso.objects.all()

    if facultad_id:
        cursos = cursos.filter(facultad_id=facultad_id)

    if estado:
        cursos = cursos.filter(estado=estado)

    return cursos


def construir_reporte(facultad_id=None, estado=None):
    """Arma todos los bloques del reporte en una sola estructura."""
    cursos = cursos_filtrados(facultad_id, estado)

    return {
        'resumen': resumen_general(cursos),
        'por_facultad': estudiantes_por_facultad(),
        'promedios': promedio_por_curso(cursos),
        'entregas': estado_entregas(cursos),
        'avance': avance_estudiantes(cursos),
        'estados_curso': cursos_por_estado(cursos),
    }
