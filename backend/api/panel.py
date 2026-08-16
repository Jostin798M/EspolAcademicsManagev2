"""
El panel propio de cada rol: /api/mi/...

Todo lo demas de la API responde a "dame los cursos" y devuelve lo que al
que pregunta le corresponda. Estas rutas responden a otra cosa: "dime que
tengo yo que hacer hoy". Son las que alimentan la pantalla de inicio de la
app movil y del sitio, y por eso cada rol recibe una estructura distinta:

    SUPERADMIN  -> el estado de todo el sistema
    ADMIN       -> el pulso de su facultad
    PROFESOR    -> sus cursos y lo que tiene por calificar
    ESTUDIANTE  -> sus cursos, lo que debe entregar y sus notas

La forma de la respuesta la anuncia el campo "tipo", para que la aplicacion
sepa que tarjetas dibujar sin adivinarlo por los campos que vengan.
"""
from django.db.models import Avg, Count, Q
from django.utils import timezone

from accounts.models import Usuario
from cursos.models import Curso, Inscripcion, Modulo, ProgresoModulo
from evaluaciones.models import Entrega, Quiz, Tarea
from reportes import servicios

from . import permisos
from .respuestas import ErrorApi, cuerpo_json, endpoint, ok, paginar, quien
from .serializadores import (
    curso_json,
    entrega_json,
    facultad_json,
    tarea_json,
    usuario_json,
)

#: Cuantas filas se devuelven en las listas cortas del panel. No es una
#: pagina: es un "lo mas urgente", y la pantalla de inicio no da para mas.
ASOMO = 5


def _numero(valor, decimales=2):
    return round(float(valor), decimales) if valor is not None else None


# ── Bloques reutilizables ────────────────────────────────────────────────────

def _proximas_tareas(cursos, usuario=None, limite=ASOMO):
    """
    Tareas con fecha limite por delante, de mas cercana a mas lejana.

    Si se pasa un usuario se marca ademas si ya entrego cada una, que es lo
    que convierte la lista en util para un estudiante.
    """
    ahora = timezone.now()

    consulta = Tarea.objects.filter(
        curso__in=cursos, fecha_limite__gte=ahora,
    ).select_related('curso').order_by('fecha_limite')[:limite]

    entregadas = set()

    if usuario is not None:
        entregadas = set(
            Entrega.objects.filter(
                usuario=usuario,
                tarea__in=[tarea.pk for tarea in consulta],
                estado=Entrega.Estado.ENTREGADO,
            ).values_list('tarea_id', flat=True)
        )

    filas = []

    for tarea in consulta:
        fila = tarea_json(tarea)
        fila['dias_restantes'] = (tarea.fecha_limite - ahora).days

        if usuario is not None:
            fila['entregada'] = tarea.pk in entregadas

        filas.append(fila)

    return filas


def _mis_cursos_resumidos(usuario, cursos):
    """Cada curso con los dos numeros que interesan en la pantalla de inicio."""
    filas = []

    for curso in cursos.select_related('facultad', 'profesor')[:20]:
        fila = curso_json(curso)

        fila['total_estudiantes'] = Inscripcion.objects.filter(
            curso=curso, rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
        ).count()
        fila['total_tareas'] = Tarea.objects.filter(curso=curso).count()

        filas.append(fila)

    return filas


# ── Un panel por rol ─────────────────────────────────────────────────────────

def _panel_superadmin(usuario, cursos):
    """El estado del sistema entero: personas, cursos y actividad."""
    por_rol = {}

    for opcion in Usuario.Rol:
        por_rol[opcion.value] = Usuario.objects.filter(rol=opcion.value).count()

    return {
        'tipo': 'superadmin',
        'titulo': 'Panel del sistema',
        'indicadores': servicios.resumen_general(cursos),
        'usuarios': {
            'total': Usuario.objects.count(),
            'activos': Usuario.objects.filter(estado=Usuario.Estado.ACTIVO).count(),
            'inactivos': Usuario.objects.filter(estado=Usuario.Estado.INACTIVO).count(),
            'por_rol': por_rol,
        },
        'por_facultad': servicios.estudiantes_por_facultad(),
        'cursos_por_estado': servicios.cursos_por_estado(cursos),
        'estado_entregas': servicios.estado_entregas(cursos),
        'ultimos_usuarios': [
            usuario_json(persona)
            for persona in Usuario.objects.select_related('facultad').order_by(
                '-fecha_registro', '-id_usuario',
            )[:ASOMO]
        ],
    }


def _panel_admin(usuario, cursos):
    """El pulso de la facultad que administra."""
    facultades = permisos.facultades_de(usuario)

    inscritos = Inscripcion.objects.filter(curso__in=cursos)

    return {
        'tipo': 'admin',
        'titulo': 'Panel de facultad',
        'facultades': [facultad_json(facultad) for facultad in facultades],
        'indicadores': servicios.resumen_general(cursos),
        'personas': {
            'estudiantes': inscritos.filter(
                rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
            ).values('usuario').distinct().count(),
            'profesores': inscritos.filter(
                rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
            ).values('usuario').distinct().count(),
            'en_la_facultad': Usuario.objects.filter(facultad__in=facultades).count(),
        },
        'cursos_por_estado': servicios.cursos_por_estado(cursos),
        'estado_entregas': servicios.estado_entregas(cursos),
        'promedios_por_curso': servicios.promedio_por_curso(cursos),
        'mis_cursos': _mis_cursos_resumidos(usuario, cursos),
    }


def _panel_profesor(usuario, cursos):
    """Lo que un profesor necesita ver al abrir la app: que le falta hacer."""
    por_calificar = Entrega.objects.filter(
        tarea__curso__in=cursos,
        estado=Entrega.Estado.ENTREGADO,
        nota__isnull=True,
    ).select_related('tarea__curso', 'usuario').order_by('fecha')

    promedio = Entrega.objects.filter(
        tarea__curso__in=cursos,
    ).exclude(nota__isnull=True).aggregate(v=Avg('nota'))['v']

    return {
        'tipo': 'profesor',
        'titulo': 'Mis cursos',
        'indicadores': {
            'cursos': cursos.count(),
            'estudiantes': Inscripcion.objects.filter(
                curso__in=cursos,
                rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
            ).values('usuario').distinct().count(),
            'tareas': Tarea.objects.filter(curso__in=cursos).count(),
            'quizzes': Quiz.objects.filter(curso__in=cursos).count(),
            'por_calificar': por_calificar.count(),
            'promedio_general': _numero(promedio),
        },
        'mis_cursos': _mis_cursos_resumidos(usuario, cursos),
        'por_calificar': [
            entrega_json(entrega) for entrega in por_calificar[:ASOMO]
        ],
        'proximas_tareas': _proximas_tareas(cursos),
        'estado_entregas': servicios.estado_entregas(cursos),
    }


def _panel_estudiante(usuario, cursos):
    """Lo que un estudiante necesita: que debe entregar y como va."""
    mis_entregas = Entrega.objects.filter(usuario=usuario, tarea__curso__in=cursos)
    calificadas = mis_entregas.exclude(nota__isnull=True)

    modulos = Modulo.objects.filter(curso__in=cursos)
    total_modulos = modulos.count()

    completados = ProgresoModulo.objects.filter(
        usuario=usuario, modulo__in=modulos, completado=True,
    ).count()

    total_tareas = Tarea.objects.filter(curso__in=cursos).count()
    entregadas = mis_entregas.filter(estado=Entrega.Estado.ENTREGADO).count()

    promedio = calificadas.aggregate(v=Avg('nota'))['v']

    return {
        'tipo': 'estudiante',
        'titulo': 'Mi semestre',
        'indicadores': {
            'cursos': cursos.count(),
            'tareas': total_tareas,
            'entregadas': entregadas,
            'pendientes': max(0, total_tareas - entregadas),
            'promedio': _numero(promedio),
            'avance': round((completados / total_modulos) * 100, 1) if total_modulos else 0.0,
            'modulos_completados': completados,
            'modulos_totales': total_modulos,
        },
        'mis_cursos': _mis_cursos_resumidos(usuario, cursos),
        'proximas_tareas': _proximas_tareas(cursos, usuario),
        'ultimas_notas': [
            entrega_json(entrega, con_estudiante=False)
            for entrega in calificadas.select_related(
                'tarea__curso',
            ).order_by('-fecha')[:ASOMO]
        ],
    }


PANELES = {
    permisos.SUPERADMIN: _panel_superadmin,
    permisos.ADMIN: _panel_admin,
    permisos.PROFESOR: _panel_profesor,
    permisos.ESTUDIANTE: _panel_estudiante,
}


# ── Rutas ────────────────────────────────────────────────────────────────────

@endpoint(privado=True, recurso=permisos.REPORTES)
def mi_panel(request):
    """
    La pantalla de inicio que corresponde a quien pregunta.

    Es una sola direccion para los cuatro roles a proposito: la aplicacion
    llama siempre aqui al entrar y dibuja segun el campo "tipo" que reciba,
    sin tener que saber de antemano con quien esta hablando.
    """
    usuario = quien(request)
    rol = permisos.rol_efectivo(usuario)
    cursos = permisos.cursos_visibles(usuario)

    armar = PANELES.get(rol)

    if armar is None:
        raise ErrorApi(
            'No hay un panel definido para tu rol.',
            404,
            motivo='sin_panel',
        )

    datos = armar(usuario, cursos)
    datos['rol'] = rol
    datos['rol_etiqueta'] = permisos.ETIQUETA_ROL.get(rol, rol)
    datos['usuario'] = usuario_json(usuario) if not permisos.es_sitio(usuario) else None

    return ok(datos)


@endpoint(privado=True, recurso=permisos.USUARIOS)
def mis_permisos(request):
    """
    Lo que este usuario puede ver, crear, editar y eliminar de cada cosa.

    La app la consulta para dibujar su menu. Devuelve tambien los numeros de
    su alcance (cuantos cursos alcanza, cuantas facultades administra) para
    que la interfaz pueda explicarselo al usuario en lugar de limitarse a
    esconder botones sin decir por que.
    """
    usuario = quien(request)

    return ok({
        'permisos': permisos.resumen(usuario),
        'alcance': {
            'cursos': permisos.cursos_visibles(usuario).count(),
            'facultades': permisos.facultades_de(usuario).count()
                          if not permisos.es_sitio(usuario) else None,
        },
    })


@endpoint(privado=True, metodos=('GET', 'PATCH'), recurso=permisos.USUARIOS)
def mi_perfil(request):
    """
    La ficha del propio usuario. GET la lee, PATCH la corrige.

    Existe aparte de /api/usuarios/<id>/ porque la app no siempre sabe su
    propio id, y porque aqui no hace falta comprobar alcance: uno siempre
    se alcanza a si mismo.
    """
    from .escritura import editar_usuario

    usuario = quien(request)

    if permisos.es_sitio(usuario):
        raise ErrorApi(
            'La clave del sitio no corresponde a ninguna persona, asi que '
            'no tiene perfil.',
            404,
            motivo='sin_perfil',
        )

    if request.method == 'GET':
        datos = usuario_json(usuario)
        datos['rol_efectivo'] = permisos.rol_efectivo(usuario)
        datos['permisos'] = permisos.resumen(usuario)

        return ok(datos)

    # PATCH: se delega en la vista de siempre, que ya sabe que un usuario
    # solo puede tocar sus datos de contacto y su contrasena.
    return editar_usuario(request, usuario.pk)


@endpoint(privado=True, recurso=permisos.CURSOS_R)
def mis_cursos(request):
    """
    Los cursos de este usuario, con lo que puede hacer en cada uno.

    Es /api/cursos/ mas el bloque "puedo", que la app usa para decidir si
    ensena el boton de editar dentro de cada tarjeta.
    """
    usuario = quien(request)

    consulta = permisos.cursos_visibles(usuario).select_related(
        'facultad', 'profesor',
    ).annotate(
        total_estudiantes=Count(
            'inscripciones',
            filter=Q(inscripciones__rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE),
            distinct=True,
        ),
        total_tareas=Count('tareas', distinct=True),
    )

    # Con que sombrero esta este usuario en cada curso. No se puede deducir
    # del rol general: la misma persona puede dictar uno y cursar otro, y el
    # sitio necesita saberlo curso por curso para ensenar la pantalla que
    # toca.
    mi_rol = dict(
        Inscripcion.objects.filter(
            usuario=usuario, curso__in=consulta,
        ).values_list('curso_id', 'rol_en_curso')
    ) if not permisos.es_sitio(usuario) else {}

    def como_json(curso):
        datos = curso_json(curso)
        datos['total_estudiantes'] = curso.total_estudiantes
        datos['total_tareas'] = curso.total_tareas
        datos['puedo'] = permisos.acciones_en_curso(usuario, curso)
        datos['mi_rol'] = mi_rol.get(curso.id_curso)

        # El profesor titular manda en su curso aunque nadie lo haya
        # inscrito: la inscripcion es una comodidad, el campo profesor es
        # el que decide.
        if datos['mi_rol'] is None and curso.profesor_id == getattr(usuario, 'pk', None):
            datos['mi_rol'] = Inscripcion.RolEnCurso.PROFESOR

        return datos

    return paginar(consulta, request, como_json)


@endpoint(privado=True, recurso=permisos.TAREAS)
def mis_tareas(request):
    """
    Las tareas que le tocan, entendiendo "tocar" segun el rol.

    Para un estudiante son las de sus cursos, marcadas con si ya entrego y
    que nota saco. Para un profesor son las que puso, con cuantas entregas
    lleva recibidas y cuantas le faltan por calificar. La misma direccion,
    dos lecturas distintas del mismo dato.
    """
    usuario = quien(request)
    rol = permisos.rol_efectivo(usuario)
    cursos = permisos.cursos_visibles(usuario)

    consulta = Tarea.objects.filter(curso__in=cursos).select_related(
        'curso',
    ).order_by('fecha_limite', 'titulo')

    codigo = request.GET.get('curso', '').strip()
    if codigo:
        consulta = consulta.filter(curso__codigo__iexact=codigo)

    if rol == permisos.ESTUDIANTE:
        mias = {
            entrega.tarea_id: entrega
            for entrega in Entrega.objects.filter(usuario=usuario, tarea__in=consulta)
        }

        def como_json(tarea):
            datos = tarea_json(tarea)
            entrega = mias.get(tarea.pk)

            datos['entregada'] = bool(entrega) and entrega.estado == Entrega.Estado.ENTREGADO
            datos['nota'] = _numero(entrega.nota) if entrega else None
            datos['id_entrega'] = entrega.id_entrega if entrega else None

            return datos
    else:
        consulta = consulta.annotate(
            recibidas=Count(
                'entregas',
                filter=Q(entregas__estado=Entrega.Estado.ENTREGADO),
                distinct=True,
            ),
            sin_calificar=Count(
                'entregas',
                filter=Q(entregas__estado=Entrega.Estado.ENTREGADO,
                         entregas__nota__isnull=True),
                distinct=True,
            ),
        )

        def como_json(tarea):
            datos = tarea_json(tarea)
            datos['recibidas'] = tarea.recibidas
            datos['sin_calificar'] = tarea.sin_calificar

            return datos

    return paginar(consulta, request, como_json)


@endpoint(privado=True, recurso=permisos.ENTREGAS)
def entregas_de_tarea(request, id_tarea):
    """
    Las entregas de una tarea.

    El profesor recibe la lista completa para calificarla; el estudiante,
    solo la suya, porque filtrar_entregas ya lo recorta a lo propio.
    """
    from django.shortcuts import get_object_or_404

    from .respuestas import exigir_alcance

    tarea = get_object_or_404(
        Tarea.objects.select_related('curso', 'curso__facultad'), pk=id_tarea,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        tarea.curso_id in permisos.ids_cursos_de(usuario)
        or permisos.alcance_de(usuario, permisos.ENTREGAS, permisos.VER) == permisos.TODO,
        permisos.ENTREGAS,
        detalle=f'La tarea "{tarea.titulo}" es del curso {tarea.curso.codigo}, '
                f'que no esta entre los tuyos.',
    )

    consulta = permisos.filtrar_entregas(
        Entrega.objects.filter(tarea=tarea).select_related(
            'tarea__curso', 'usuario',
        ).order_by('usuario__apellidos'),
        usuario,
    )

    ve_a_todos = permisos.alcance_de(
        usuario, permisos.ENTREGAS, permisos.VER,
    ) != permisos.PROPIO

    return paginar(
        consulta, request,
        lambda entrega: entrega_json(entrega, con_estudiante=ve_a_todos),
    )


@endpoint(privado=True, recurso=permisos.PROGRESO)
def progreso_del_curso(request, codigo):
    """
    Que modulos lleva completados cada quien en un curso.

    El estudiante recibe su propia fila; el profesor y el administrador, la
    de todos los inscritos. Es lo que alimenta la barra de avance del sitio
    y la pantalla de progreso de la app.
    """
    from django.shortcuts import get_object_or_404

    from cursos.models import Curso
    from .respuestas import exigir_alcance

    curso = get_object_or_404(
        Curso.objects.select_related('facultad'), codigo__iexact=codigo,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        permisos.puede_sobre_curso(usuario, permisos.PROGRESO, permisos.VER, curso),
        permisos.PROGRESO,
        detalle=f'El curso {curso.codigo} no esta entre los tuyos.',
    )

    modulos = list(Modulo.objects.filter(curso=curso).order_by('orden'))
    total = len(modulos)

    # Quien ve solo lo suyo recibe una unica fila: la propia.
    if permisos.alcance_de(usuario, permisos.PROGRESO, permisos.VER) == permisos.PROPIO:
        personas = [usuario]
    else:
        personas = [
            inscripcion.usuario
            for inscripcion in Inscripcion.objects.filter(
                curso=curso,
                rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
            ).select_related('usuario').order_by('usuario__apellidos')
        ]

    completados = {}

    for marca in ProgresoModulo.objects.filter(
        modulo__curso=curso, completado=True,
    ).values_list('usuario_id', 'modulo_id'):
        completados.setdefault(marca[0], set()).add(marca[1])

    filas = []

    for persona in personas:
        suyos = completados.get(persona.pk, set())

        filas.append({
            'usuario': persona.pk,
            'estudiante': persona.nombre_completo,
            'correo': persona.correo,
            'completados': len(suyos),
            'total': total,
            'avance': round((len(suyos) / total) * 100, 1) if total else 0.0,
            'modulos': [
                {
                    'id_modulo': modulo.id_modulo,
                    'titulo': modulo.titulo,
                    'orden': modulo.orden,
                    'completado': modulo.id_modulo in suyos,
                }
                for modulo in modulos
            ],
        })

    return ok({
        'curso': curso.codigo,
        'total_modulos': total,
        'filas': filas,
    })


@endpoint(privado=True, recurso=permisos.ENTREGAS)
def respuestas_del_quiz(request, id_quiz):
    """
    Los intentos de un quiz.

    Como en las entregas de tarea, el estudiante ve el suyo y el profesor
    los de todos: el recorte lo hace el alcance, no un parametro.
    """
    from django.shortcuts import get_object_or_404

    from evaluaciones.models import RespuestaQuiz
    from .respuestas import exigir_alcance
    from .serializadores import respuesta_quiz_json

    quiz = get_object_or_404(
        Quiz.objects.select_related('curso', 'curso__facultad'), pk=id_quiz,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        permisos.puede_sobre_curso(usuario, permisos.ENTREGAS, permisos.VER, quiz.curso)
        or quiz.curso_id in permisos.ids_cursos_de(usuario),
        permisos.ENTREGAS,
        detalle=f'El quiz es del curso {quiz.curso.codigo}, que no es tuyo.',
    )

    consulta = RespuestaQuiz.objects.filter(quiz=quiz).select_related(
        'quiz__curso', 'usuario',
    ).order_by('usuario__apellidos')

    if permisos.alcance_de(usuario, permisos.ENTREGAS, permisos.VER) == permisos.PROPIO:
        consulta = consulta.filter(usuario=usuario)

    return paginar(consulta, request, respuesta_quiz_json)
