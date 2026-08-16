"""
Vistas que crean, editan y eliminan.

Aqui esta la parte de la API que cambia datos, y por eso cada vista repite
siempre la misma comprobacion en tres pasos:

    1. ¿Tu rol puede hacer esto?    -> lo hace el decorador (recurso=...)
    2. ¿Sobre ESTE registro?        -> permisos.puede_sobre_curso(...)
    3. ¿Los datos son validos?      -> validacion.aplicar(...)

El paso 2 es el que no puede automatizarse: hasta que no se busca el objeto
no se sabe de que curso o de que facultad es. Cada vista lo hace explicito
en su primera linea, de modo que se lea de un vistazo a quien pertenece lo
que se esta tocando.

Un detalle del modelo que se nota mucho aqui: casi todas las relaciones son
on_delete=PROTECT. Eso significa que borrar un curso con inscripciones no
falla en silencio, sino que revienta con ProtectedError. En vez de dejar
salir un error 500, _borrar() lo traduce a un 409 que explica que hay que
quitar primero.
"""
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404

from accounts.models import Usuario
from cursos.models import (
    Curso,
    Facultad,
    FormulaComponente,
    Inscripcion,
    Material,
    Modulo,
    ProgresoModulo,
)
from evaluaciones.models import Entrega, Pregunta, Quiz, RespuestaQuiz, Tarea

from . import permisos, validacion as v
from .respuestas import (
    ErrorApi,
    cuerpo_json,
    endpoint,
    exigir_alcance,
    ok,
    quien,
)
from .serializadores import (
    curso_json,
    facultad_json,
    entrega_json,
    inscripcion_json,
    material_json,
    modulo_json,
    pregunta_json,
    progreso_json,
    quiz_json,
    respuesta_quiz_json,
    tarea_json,
    usuario_json,
)


# ── Utilidades comunes ───────────────────────────────────────────────────────

def _creado(datos, mensaje):
    """Respuesta de un alta. Va con 'creado': true para no confundirla."""
    return ok(datos, creado=True, mensaje=mensaje)


def _borrar(objeto, etiqueta):
    """
    Elimina un registro y traduce ProtectedError a un mensaje util.

    El modelo protege las relaciones a proposito: no se borra un curso al
    que hay gente inscrita. Cuando pasa, lo que necesita saber quien llama
    no es "error interno" sino que tiene que deshacer antes.
    """
    try:
        with transaction.atomic():
            objeto.delete()
    except ProtectedError as bloqueo:
        cuantos = len(bloqueo.protected_objects)

        raise ErrorApi(
            f'No se puede eliminar {etiqueta}: hay {cuantos} registro(s) '
            f'que dependen de el. Quitalos primero.',
            409,
            motivo='tiene_dependencias',
            dependencias=cuantos,
        )

    return ok({'eliminado': True}, mensaje=f'Se elimino {etiqueta}.')


def _curso_de(request, codigo, recurso, accion):
    """Busca el curso y exige que este dentro del alcance para esa accion."""
    curso = get_object_or_404(
        Curso.objects.select_related('facultad', 'profesor'),
        codigo__iexact=codigo,
    )

    exigir_alcance(
        request,
        permisos.puede_sobre_curso(quien(request), recurso, accion, curso),
        recurso,
        detalle=f'El curso {curso.codigo} no esta entre los que puedes '
                f'{accion} con tu rol.',
    )

    return curso


def _exigir_curso(request, curso, recurso, accion):
    """Igual que _curso_de pero cuando el curso ya se tiene a mano."""
    exigir_alcance(
        request,
        permisos.puede_sobre_curso(quien(request), recurso, accion, curso),
        recurso,
        detalle=f'Ese registro pertenece al curso {curso.codigo}, que no '
                f'esta entre los tuyos.',
    )


def _comprobar_fechas(curso):
    """Un curso no puede terminar antes de empezar."""
    if curso.fecha_fin < curso.fecha_inicio:
        raise ErrorApi(
            'La fecha de fin no puede ser anterior a la de inicio.',
            400,
            motivo='campo_invalido',
            campo='fecha_fin',
        )


def _facultad_por_codigo(codigo, campo='facultad'):
    facultad = Facultad.objects.filter(codigo__iexact=str(codigo).strip()).first()

    if facultad is None:
        raise ErrorApi(
            f'No existe ninguna facultad con codigo "{codigo}".',
            400,
            motivo='campo_invalido',
            campo=campo,
        )

    return facultad


def _usuario_por_referencia(referencia, campo='usuario'):
    """Busca una persona por su id o por su correo, lo que llegue."""
    crudo = str(referencia).strip()

    persona = (
        Usuario.objects.filter(pk=crudo).first() if crudo.isdigit()
        else Usuario.objects.filter(correo__iexact=crudo).first()
    )

    if persona is None:
        raise ErrorApi(
            f'No existe ningun usuario "{referencia}".',
            400,
            motivo='campo_invalido',
            campo=campo,
        )

    return persona


# ══ CURSOS ═══════════════════════════════════════════════════════════════════

CAMPOS_CURSO = {
    'nombre': v.cadena(150),
    'codigo': v.cadena(20),
    'descripcion': v.parrafo(),
    # El modelo las exige (no admiten NULL), asi que aqui tampoco se
    # aceptan vacias: mas vale un 400 claro que un 500 de la base de datos.
    'fecha_inicio': v.dia(),
    'fecha_fin': v.dia(),
    'estado': v.opcion(Curso.Estado),
}

#: Lo unico que un profesor retoca de su propio curso. El codigo, la
#: facultad y el profesor titular son decisiones de la facultad, no suyas.
CAMPOS_CURSO_PROFESOR = ('nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 'estado')


@endpoint(metodos=('POST',), recurso=permisos.CURSOS_R, privado=True)
def crear_curso(request):
    """
    Abre un curso nuevo.

    Lo hacen el super administrador y el administrador de facultad; un
    profesor no crea cursos, se los asignan. El administrador solo puede
    crearlos dentro de las facultades que administra, y si no dice cual, se
    toma la suya.
    """
    datos = cuerpo_json(request)
    usuario = quien(request)

    v.exigir(datos, 'nombre', 'codigo', 'profesor', 'fecha_inicio', 'fecha_fin')

    facultad = (
        _facultad_por_codigo(datos['facultad']) if datos.get('facultad')
        else getattr(usuario, 'facultad', None)
    )

    if facultad is None:
        raise ErrorApi(
            'Indica la facultad del curso en el campo "facultad" (su codigo).',
            400,
            motivo='faltan_campos',
            campos=['facultad'],
        )

    alcance = permisos.alcance_de(usuario, permisos.CURSOS_R, permisos.CREAR)

    if alcance == permisos.FACULTAD:
        exigir_alcance(
            request,
            facultad.id_facultad in permisos.ids_facultades_de(usuario),
            permisos.CURSOS_R,
            detalle=f'Solo puedes crear cursos en tu facultad, no en '
                    f'{facultad.codigo}.',
        )

    profesor = _usuario_por_referencia(datos['profesor'], 'profesor')

    codigo = str(datos['codigo']).strip().upper()

    if Curso.objects.filter(codigo__iexact=codigo).exists():
        raise ErrorApi(
            f'Ya existe un curso con codigo "{codigo}".',
            409,
            motivo='duplicado',
            campo='codigo',
        )

    curso = v.aplicar(Curso(), datos, CAMPOS_CURSO)
    curso.codigo = codigo
    curso.facultad = facultad
    curso.profesor = profesor
    _comprobar_fechas(curso)
    curso.save()

    # El profesor titular queda tambien inscrito: asi aparece en sus cursos
    # sin depender de una segunda llamada que alguien puede olvidar.
    Inscripcion.objects.get_or_create(
        usuario=profesor,
        curso=curso,
        defaults={'rol_en_curso': Inscripcion.RolEnCurso.PROFESOR},
    )

    return _creado(curso_json(curso), f'Curso {curso.codigo} creado.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.CURSOS_R, privado=True)
def editar_curso(request, codigo):
    """
    Cambia los datos de un curso.

    El administrador puede tocarlo todo, incluido a quien se lo asigna. El
    profesor solo el contenido informativo del suyo: ni el codigo, ni la
    facultad, ni el titular.
    """
    curso = _curso_de(request, codigo, permisos.CURSOS_R, permisos.EDITAR)
    datos = cuerpo_json(request)
    usuario = quien(request)

    manda_en_la_facultad = permisos.alcance_de(
        usuario, permisos.CURSOS_R, permisos.EDITAR,
    ) in (permisos.TODO, permisos.FACULTAD)

    if not manda_en_la_facultad:
        v.solo_estos(
            datos, CAMPOS_CURSO_PROFESOR,
            contexto=' de un curso que dictas',
        )

    if manda_en_la_facultad and datos.get('facultad'):
        nueva = _facultad_por_codigo(datos['facultad'])

        exigir_alcance(
            request,
            permisos.alcance_de(usuario, permisos.CURSOS_R, permisos.EDITAR) == permisos.TODO
            or nueva.id_facultad in permisos.ids_facultades_de(usuario),
            permisos.CURSOS_R,
            detalle=f'No puedes mover un curso a la facultad {nueva.codigo}.',
        )

        curso.facultad = nueva

    if manda_en_la_facultad and datos.get('profesor'):
        curso.profesor = _usuario_por_referencia(datos['profesor'], 'profesor')

        Inscripcion.objects.get_or_create(
            usuario=curso.profesor,
            curso=curso,
            defaults={'rol_en_curso': Inscripcion.RolEnCurso.PROFESOR},
        )

    if datos.get('codigo') and manda_en_la_facultad:
        nuevo_codigo = str(datos['codigo']).strip().upper()

        if Curso.objects.filter(codigo__iexact=nuevo_codigo).exclude(pk=curso.pk).exists():
            raise ErrorApi(
                f'Ya existe otro curso con codigo "{nuevo_codigo}".',
                409,
                motivo='duplicado',
                campo='codigo',
            )

        datos['codigo'] = nuevo_codigo

    v.aplicar(curso, datos, CAMPOS_CURSO)
    _comprobar_fechas(curso)
    curso.save()

    return ok(curso_json(curso), mensaje=f'Curso {curso.codigo} actualizado.')


@endpoint(metodos=('DELETE',), recurso=permisos.CURSOS_R, privado=True)
def eliminar_curso(request, codigo):
    """
    Elimina un curso con todo su andamiaje.

    Hay que separar dos cosas que el modelo protege por igual pero que no
    valen lo mismo:

    · El ANDAMIAJE del curso -sus modulos, materiales, tareas, quizzes,
      preguntas, la formula y las inscripciones- es parte del curso. No
      tiene sentido pedir que se borre a mano antes: si se elimina el
      curso, eso se va con el. De hecho el propio alta inscribe al profesor
      titular, asi que exigirlo haria imposible borrar un curso recien
      creado.

    · El TRABAJO de los estudiantes -entregas, quizzes rendidos y avance en
      los modulos- no. Eso son notas y esfuerzo de personas, y borrarlo por
      arrastre seria una perdida silenciosa. Si hay algo de eso, se rechaza
      con 409 y se dice cuanto hay.
    """
    curso = _curso_de(request, codigo, permisos.CURSOS_R, permisos.ELIMINAR)

    entregas = Entrega.objects.filter(tarea__curso=curso).count()
    rendidos = RespuestaQuiz.objects.filter(quiz__curso=curso).count()
    avances = ProgresoModulo.objects.filter(modulo__curso=curso).count()

    if entregas or rendidos or avances:
        raise ErrorApi(
            f'No se puede eliminar el curso {curso.codigo}: ya tiene trabajo '
            f'de estudiantes ({entregas} entrega(s), {rendidos} quiz(zes) '
            f'rendido(s), {avances} modulo(s) marcado(s)). Archivalo en vez '
            f'de borrarlo.',
            409,
            motivo='tiene_trabajo',
            entregas=entregas,
            quizzes_rendidos=rendidos,
            avances=avances,
        )

    etiqueta = f'el curso {curso.codigo}'

    with transaction.atomic():
        Pregunta.objects.filter(quiz__curso=curso).delete()
        Quiz.objects.filter(curso=curso).delete()
        Tarea.objects.filter(curso=curso).delete()
        Material.objects.filter(modulo__curso=curso).delete()
        Modulo.objects.filter(curso=curso).delete()
        FormulaComponente.objects.filter(curso=curso).delete()
        Inscripcion.objects.filter(curso=curso).delete()
        curso.delete()

    return ok({'eliminado': True}, mensaje=f'Se elimino {etiqueta}.')


# ══ MODULOS ══════════════════════════════════════════════════════════════════

CAMPOS_MODULO = {
    'titulo': v.cadena(150),
    'descripcion': v.parrafo(),
    'orden': v.entero(minimo=1, maximo=999),
}


@endpoint(metodos=('POST',), recurso=permisos.MODULOS, privado=True)
def crear_modulo(request, codigo):
    """Anade un modulo al curso. Si no se indica orden, va al final."""
    curso = _curso_de(request, codigo, permisos.MODULOS, permisos.CREAR)
    datos = cuerpo_json(request)

    v.exigir(datos, 'titulo')

    modulo = v.aplicar(Modulo(curso=curso), datos, CAMPOS_MODULO)

    if not datos.get('orden'):
        modulo.orden = curso.modulos.count() + 1

    modulo.save()

    return _creado(modulo_json(modulo), f'Modulo "{modulo.titulo}" creado.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.MODULOS, privado=True)
def editar_modulo(request, id_modulo):
    modulo = get_object_or_404(
        Modulo.objects.select_related('curso', 'curso__facultad'), pk=id_modulo,
    )
    _exigir_curso(request, modulo.curso, permisos.MODULOS, permisos.EDITAR)

    v.aplicar(modulo, cuerpo_json(request), CAMPOS_MODULO)
    modulo.save()

    return ok(modulo_json(modulo), mensaje='Modulo actualizado.')


@endpoint(metodos=('DELETE',), recurso=permisos.MODULOS, privado=True)
def eliminar_modulo(request, id_modulo):
    modulo = get_object_or_404(
        Modulo.objects.select_related('curso', 'curso__facultad'), pk=id_modulo,
    )
    _exigir_curso(request, modulo.curso, permisos.MODULOS, permisos.ELIMINAR)

    return _borrar(modulo, f'el modulo "{modulo.titulo}"')


# ══ MATERIALES ═══════════════════════════════════════════════════════════════

CAMPOS_MATERIAL = {
    'titulo': v.cadena(200),
    'tipo': v.opcion(Material.Tipo),
    'url': v.enlace(),
}


@endpoint(metodos=('POST',), recurso=permisos.MATERIALES, privado=True)
def crear_material(request, id_modulo):
    """Cuelga un video, un PDF o un enlace de un modulo."""
    modulo = get_object_or_404(
        Modulo.objects.select_related('curso', 'curso__facultad'), pk=id_modulo,
    )
    _exigir_curso(request, modulo.curso, permisos.MATERIALES, permisos.CREAR)

    datos = cuerpo_json(request)
    v.exigir(datos, 'titulo', 'url')

    material = v.aplicar(Material(modulo=modulo), datos, CAMPOS_MATERIAL)
    material.save()

    return _creado(material_json(material), f'Material "{material.titulo}" creado.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.MATERIALES, privado=True)
def editar_material(request, id_material):
    material = get_object_or_404(
        Material.objects.select_related('modulo__curso__facultad'), pk=id_material,
    )
    _exigir_curso(request, material.modulo.curso, permisos.MATERIALES, permisos.EDITAR)

    v.aplicar(material, cuerpo_json(request), CAMPOS_MATERIAL)
    material.save()

    return ok(material_json(material), mensaje='Material actualizado.')


@endpoint(metodos=('DELETE',), recurso=permisos.MATERIALES, privado=True)
def eliminar_material(request, id_material):
    material = get_object_or_404(
        Material.objects.select_related('modulo__curso__facultad'), pk=id_material,
    )
    _exigir_curso(request, material.modulo.curso, permisos.MATERIALES, permisos.ELIMINAR)

    return _borrar(material, f'el material "{material.titulo}"')


# ══ TAREAS ═══════════════════════════════════════════════════════════════════

# descripcion y fecha_limite no admiten NULL en el modelo, asi que se
# exigen al crear en lugar de dejar que falle la base de datos.
CAMPOS_TAREA = {
    'titulo': v.cadena(200),
    'descripcion': v.parrafo(obligatorio=True),
    'criterios': v.parrafo(),
    'fecha_limite': v.momento(),
    'puntaje_maximo': v.numero(minimo=0, maximo=1000),
}


@endpoint(metodos=('POST',), recurso=permisos.TAREAS, privado=True)
def crear_tarea(request, codigo):
    """Pone una tarea nueva en el curso, con su fecha de entrega."""
    curso = _curso_de(request, codigo, permisos.TAREAS, permisos.CREAR)
    datos = cuerpo_json(request)

    v.exigir(datos, 'titulo', 'descripcion', 'fecha_limite')

    tarea = v.aplicar(Tarea(curso=curso), datos, CAMPOS_TAREA)
    tarea.save()

    return _creado(tarea_json(tarea), f'Tarea "{tarea.titulo}" creada.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.TAREAS, privado=True)
def editar_tarea(request, id_tarea):
    tarea = get_object_or_404(
        Tarea.objects.select_related('curso', 'curso__facultad'), pk=id_tarea,
    )
    _exigir_curso(request, tarea.curso, permisos.TAREAS, permisos.EDITAR)

    v.aplicar(tarea, cuerpo_json(request), CAMPOS_TAREA)
    tarea.save()

    return ok(tarea_json(tarea), mensaje='Tarea actualizada.')


@endpoint(metodos=('DELETE',), recurso=permisos.TAREAS, privado=True)
def eliminar_tarea(request, id_tarea):
    tarea = get_object_or_404(
        Tarea.objects.select_related('curso', 'curso__facultad'), pk=id_tarea,
    )
    _exigir_curso(request, tarea.curso, permisos.TAREAS, permisos.ELIMINAR)

    return _borrar(tarea, f'la tarea "{tarea.titulo}"')


# ══ QUIZZES Y PREGUNTAS ══════════════════════════════════════════════════════

CAMPOS_QUIZ = {
    'titulo': v.cadena(200),
    'descripcion': v.parrafo(),
    'tiempo_limite_min': v.entero(minimo=1, maximo=600, nulo=True),
    'fecha_limite': v.momento(),
}

CAMPOS_PREGUNTA = {
    'tipo': v.opcion(Pregunta.Tipo),
    'enunciado': v.parrafo(obligatorio=True),
    'puntaje': v.numero(minimo=0, maximo=1000),
    'orden': v.entero(minimo=1, maximo=999),
    'opciones': v.lista(),
    'respuesta_correcta': v.libre(),
}


@endpoint(metodos=('POST',), recurso=permisos.QUIZZES, privado=True)
def crear_quiz(request, codigo):
    """Crea un quiz vacio; las preguntas se anaden despues, una a una."""
    curso = _curso_de(request, codigo, permisos.QUIZZES, permisos.CREAR)
    datos = cuerpo_json(request)

    v.exigir(datos, 'titulo', 'fecha_limite')

    quiz = v.aplicar(Quiz(curso=curso), datos, CAMPOS_QUIZ)
    quiz.save()

    return _creado(quiz_json(quiz), f'Quiz "{quiz.titulo}" creado.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.QUIZZES, privado=True)
def editar_quiz(request, id_quiz):
    quiz = get_object_or_404(
        Quiz.objects.select_related('curso', 'curso__facultad'), pk=id_quiz,
    )
    _exigir_curso(request, quiz.curso, permisos.QUIZZES, permisos.EDITAR)

    v.aplicar(quiz, cuerpo_json(request), CAMPOS_QUIZ)
    quiz.save()

    return ok(quiz_json(quiz), mensaje='Quiz actualizado.')


@endpoint(metodos=('DELETE',), recurso=permisos.QUIZZES, privado=True)
def eliminar_quiz(request, id_quiz):
    quiz = get_object_or_404(
        Quiz.objects.select_related('curso', 'curso__facultad'), pk=id_quiz,
    )
    _exigir_curso(request, quiz.curso, permisos.QUIZZES, permisos.ELIMINAR)

    return _borrar(quiz, f'el quiz "{quiz.titulo}"')


@endpoint(metodos=('POST',), recurso=permisos.PREGUNTAS, privado=True)
def crear_pregunta(request, id_quiz):
    """Anade una pregunta a un quiz. Sin orden, va al final."""
    quiz = get_object_or_404(
        Quiz.objects.select_related('curso', 'curso__facultad'), pk=id_quiz,
    )
    _exigir_curso(request, quiz.curso, permisos.PREGUNTAS, permisos.CREAR)

    datos = cuerpo_json(request)
    v.exigir(datos, 'enunciado')

    pregunta = v.aplicar(Pregunta(quiz=quiz), datos, CAMPOS_PREGUNTA)

    if not datos.get('orden'):
        pregunta.orden = quiz.preguntas.count() + 1

    pregunta.save()

    return _creado(
        pregunta_json(pregunta, con_respuesta=True),
        'Pregunta creada.',
    )


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.PREGUNTAS, privado=True)
def editar_pregunta(request, id_pregunta):
    pregunta = get_object_or_404(
        Pregunta.objects.select_related('quiz__curso__facultad'), pk=id_pregunta,
    )
    _exigir_curso(request, pregunta.quiz.curso, permisos.PREGUNTAS, permisos.EDITAR)

    v.aplicar(pregunta, cuerpo_json(request), CAMPOS_PREGUNTA)
    pregunta.save()

    return ok(
        pregunta_json(pregunta, con_respuesta=True),
        mensaje='Pregunta actualizada.',
    )


@endpoint(metodos=('DELETE',), recurso=permisos.PREGUNTAS, privado=True)
def eliminar_pregunta(request, id_pregunta):
    pregunta = get_object_or_404(
        Pregunta.objects.select_related('quiz__curso__facultad'), pk=id_pregunta,
    )
    _exigir_curso(request, pregunta.quiz.curso, permisos.PREGUNTAS, permisos.ELIMINAR)

    return _borrar(pregunta, 'la pregunta')


# ══ INSCRIPCIONES ════════════════════════════════════════════════════════════

@endpoint(metodos=('POST',), recurso=permisos.INSCRIPCIONES, privado=True)
def inscribir(request, codigo):
    """
    Matricula a alguien en un curso, como estudiante o como profesor.

    Cuerpo: {"usuario": "correo@espol.edu.ec", "rol_en_curso": "ESTUDIANTE"}
    """
    curso = _curso_de(request, codigo, permisos.INSCRIPCIONES, permisos.CREAR)
    datos = cuerpo_json(request)

    v.exigir(datos, 'usuario')

    persona = _usuario_por_referencia(datos['usuario'])
    rol_en_curso = v.opcion_mayus(Inscripcion.RolEnCurso)(
        datos.get('rol_en_curso') or Inscripcion.RolEnCurso.ESTUDIANTE,
        'rol_en_curso',
    )

    inscripcion, nueva = Inscripcion.objects.get_or_create(
        usuario=persona,
        curso=curso,
        defaults={'rol_en_curso': rol_en_curso},
    )

    if not nueva:
        raise ErrorApi(
            f'{persona.nombre_completo} ya esta inscrito en {curso.codigo} '
            f'como {inscripcion.rol_en_curso}.',
            409,
            motivo='duplicado',
        )

    return _creado(
        inscripcion_json(inscripcion),
        f'{persona.nombre_completo} inscrito en {curso.codigo}.',
    )


@endpoint(metodos=('DELETE',), recurso=permisos.INSCRIPCIONES, privado=True)
def eliminar_inscripcion(request, id_inscripcion):
    """Da de baja a alguien de un curso."""
    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related('curso__facultad', 'usuario'),
        pk=id_inscripcion,
    )
    _exigir_curso(request, inscripcion.curso, permisos.INSCRIPCIONES, permisos.ELIMINAR)

    etiqueta = (
        f'la inscripcion de {inscripcion.usuario.nombre_completo} en '
        f'{inscripcion.curso.codigo}'
    )

    return _borrar(inscripcion, etiqueta)


# ══ USUARIOS ═════════════════════════════════════════════════════════════════

CAMPOS_USUARIO = {
    'nombres': v.cadena(100),
    'apellidos': v.cadena(100),
    'identificacion': v.cadena(20),
    'telefono': v.cadena(15, obligatorio=False),
    'celular': v.cadena(15),
    'correo': v.cadena(150),
    'direccion': v.cadena(200, obligatorio=False),
    'estado_civil': v.opcion(Usuario.EstadoCivil),
    'estado': v.opcion(Usuario.Estado),
    'rol': v.opcion_mayus(Usuario.Rol),
}

#: Lo que cualquiera puede cambiar de su propia ficha. Ni el rol, ni el
#: estado de la cuenta, ni la facultad: eso lo decide quien administra.
CAMPOS_PROPIOS = ('nombres', 'apellidos', 'telefono', 'celular', 'direccion',
                  'estado_civil', 'password')


@endpoint(metodos=('POST',), recurso=permisos.USUARIOS, privado=True)
def crear_usuario(request):
    """
    Da de alta a una persona.

    Un administrador de facultad solo puede crearla dentro de su facultad y
    nunca con rol SUPERADMIN: no se reparte a si mismo mas poder del que
    tiene.
    """
    datos = cuerpo_json(request)
    usuario = quien(request)

    v.exigir(datos, 'nombres', 'apellidos', 'identificacion', 'celular',
             'correo', 'password')

    correo = str(datos['correo']).strip().lower()

    if Usuario.objects.filter(correo__iexact=correo).exists():
        raise ErrorApi(
            f'Ya hay una cuenta con el correo "{correo}".',
            409,
            motivo='duplicado',
            campo='correo',
        )

    if Usuario.objects.filter(identificacion=str(datos['identificacion']).strip()).exists():
        raise ErrorApi(
            'Ya hay una cuenta con esa identificacion.',
            409,
            motivo='duplicado',
            campo='identificacion',
        )

    alcance = permisos.alcance_de(usuario, permisos.USUARIOS, permisos.CREAR)
    rol_pedido = v.opcion_mayus(Usuario.Rol)(
        datos.get('rol') or Usuario.Rol.USER, 'rol',
    )

    facultad = (
        _facultad_por_codigo(datos['facultad']) if datos.get('facultad')
        else getattr(usuario, 'facultad', None)
    )

    if alcance == permisos.FACULTAD:
        if rol_pedido == Usuario.Rol.SUPERADMIN:
            raise ErrorApi(
                'No puedes crear cuentas de super administrador.',
                403,
                motivo='sin_permiso',
                campo='rol',
            )

        exigir_alcance(
            request,
            facultad is not None
            and facultad.id_facultad in permisos.ids_facultades_de(usuario),
            permisos.USUARIOS,
            detalle='Solo puedes dar de alta personas en tu propia facultad.',
        )

    nuevo = v.aplicar(Usuario(), datos, CAMPOS_USUARIO)
    nuevo.correo = correo
    nuevo.rol = rol_pedido
    nuevo.facultad = facultad
    nuevo.set_password(str(datos['password']))
    nuevo.save()

    return _creado(usuario_json(nuevo), f'Cuenta creada para {correo}.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.USUARIOS, privado=True)
def editar_usuario(request, id_usuario):
    """
    Corrige la ficha de una persona.

    Hay dos situaciones muy distintas bajo la misma direccion:

    · Editas TU ficha: cambias tus datos de contacto y tu contrasena, nada
      mas. Un estudiante no se asciende a administrador editandose.
    · Editas la de OTRO: hace falta el permiso con alcance sobre esa
      persona, y ahi si se puede cambiar su rol, su estado y su facultad.
    """
    objetivo = get_object_or_404(
        Usuario.objects.select_related('facultad'), pk=id_usuario,
    )
    datos = cuerpo_json(request)
    usuario = quien(request)

    es_uno_mismo = getattr(usuario, 'pk', None) == objetivo.pk
    alcance = permisos.alcance_de(usuario, permisos.USUARIOS, permisos.EDITAR)

    if alcance == permisos.PROPIO or (es_uno_mismo and alcance is None):
        exigir_alcance(
            request,
            es_uno_mismo,
            permisos.USUARIOS,
            detalle='Con tu rol solo puedes editar tu propia ficha.',
        )
        v.solo_estos(datos, CAMPOS_PROPIOS, contexto=' de tu propia ficha')

    elif alcance == permisos.FACULTAD:
        exigir_alcance(
            request,
            objetivo.facultad_id in permisos.ids_facultades_de(usuario),
            permisos.USUARIOS,
            detalle=f'{objetivo.nombre_completo} no pertenece a tu facultad.',
        )

        if str(datos.get('rol', '')).strip().upper() == Usuario.Rol.SUPERADMIN:
            raise ErrorApi(
                'No puedes ascender a nadie a super administrador.',
                403,
                motivo='sin_permiso',
                campo='rol',
            )

    elif alcance == permisos.CURSOS and not es_uno_mismo:
        exigir_alcance(
            request, False, permisos.USUARIOS,
            detalle='Puedes ver a tus estudiantes, pero no editar su ficha.',
        )

    if datos.get('correo'):
        correo = str(datos['correo']).strip().lower()

        if Usuario.objects.filter(correo__iexact=correo).exclude(pk=objetivo.pk).exists():
            raise ErrorApi(
                f'Ya hay otra cuenta con el correo "{correo}".',
                409,
                motivo='duplicado',
                campo='correo',
            )

        datos['correo'] = correo

    if datos.get('facultad') and alcance in (permisos.TODO, permisos.FACULTAD):
        objetivo.facultad = _facultad_por_codigo(datos['facultad'])

    v.aplicar(objetivo, datos, CAMPOS_USUARIO)

    if datos.get('password'):
        objetivo.set_password(str(datos['password']))

    objetivo.save()

    return ok(usuario_json(objetivo), mensaje='Ficha actualizada.')


@endpoint(metodos=('DELETE',), recurso=permisos.USUARIOS, privado=True)
def eliminar_usuario(request, id_usuario):
    """Da de baja una cuenta. Solo el super administrador llega aqui."""
    objetivo = get_object_or_404(Usuario, pk=id_usuario)
    usuario = quien(request)

    if getattr(usuario, 'pk', None) == objetivo.pk:
        raise ErrorApi(
            'No puedes eliminar tu propia cuenta.',
            409,
            motivo='autodestruccion',
        )

    return _borrar(objetivo, f'la cuenta de {objetivo.nombre_completo}')


# ══ ENTREGAS ═════════════════════════════════════════════════════════════════

CAMPOS_ENTREGA = {
    'texto': v.parrafo(),
    'archivo': v.cadena(255, obligatorio=False),
    'imagen': v.enlace(obligatorio=False),
    'link': v.enlace(obligatorio=False),
}

CAMPOS_CALIFICACION = {
    'nota': v.numero(minimo=0, maximo=1000, nulo=True),
    'comentario': v.parrafo(),
}


@endpoint(metodos=('POST',), recurso=permisos.ENTREGAS, privado=True)
def entregar(request, id_tarea):
    """
    El estudiante manda su entrega de una tarea.

    Si ya habia entregado, se actualiza la que tenia en lugar de crear una
    segunda: en el modelo la pareja (tarea, estudiante) es unica, y ademas
    es lo que espera quien vuelve a subir un archivo corregido.
    """
    tarea = get_object_or_404(
        Tarea.objects.select_related('curso', 'curso__facultad'), pk=id_tarea,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        tarea.curso_id in permisos.ids_cursos_de(usuario),
        permisos.ENTREGAS,
        detalle=f'No estas inscrito en {tarea.curso.codigo}, asi que no '
                f'puedes entregar esta tarea.',
    )

    entrega, nueva = Entrega.objects.get_or_create(
        tarea=tarea,
        usuario=usuario,
        defaults={'estado': Entrega.Estado.PENDIENTE},
    )

    if entrega.nota is not None:
        raise ErrorApi(
            'Esta entrega ya esta calificada y no se puede cambiar.',
            409,
            motivo='ya_calificada',
        )

    v.aplicar(entrega, cuerpo_json(request), CAMPOS_ENTREGA)
    entrega.estado = Entrega.Estado.ENTREGADO
    entrega.save()

    datos = entrega_json(entrega, con_estudiante=False)

    if nueva:
        return _creado(datos, f'Entrega registrada para "{tarea.titulo}".')

    return ok(datos, mensaje='Entrega actualizada.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.ENTREGAS, privado=True)
def calificar(request, id_entrega):
    """
    Pone nota y comentario a una entrega.

    La misma direccion sirve para dos cosas segun quien llame: el profesor
    califica, y el estudiante corrige su propio envio mientras no tenga
    nota. Se decide por el alcance, no por un campo del cuerpo.
    """
    entrega = get_object_or_404(
        Entrega.objects.select_related('tarea__curso__facultad', 'usuario'),
        pk=id_entrega,
    )
    usuario = quien(request)
    alcance = permisos.alcance_de(usuario, permisos.ENTREGAS, permisos.EDITAR)

    if alcance == permisos.PROPIO:
        exigir_alcance(
            request,
            entrega.usuario_id == getattr(usuario, 'pk', None),
            permisos.ENTREGAS,
            detalle='Solo puedes modificar tus propias entregas.',
        )

        if entrega.nota is not None:
            raise ErrorApi(
                'Tu entrega ya fue calificada y no se puede cambiar.',
                409,
                motivo='ya_calificada',
            )

        v.solo_estos(cuerpo_json(request), CAMPOS_ENTREGA.keys(),
                     contexto=' de tu entrega')
        v.aplicar(entrega, cuerpo_json(request), CAMPOS_ENTREGA)
        entrega.estado = Entrega.Estado.ENTREGADO
        entrega.save()

        return ok(
            entrega_json(entrega, con_estudiante=False),
            mensaje='Entrega actualizada.',
        )

    _exigir_curso(request, entrega.tarea.curso, permisos.ENTREGAS, permisos.EDITAR)

    datos = cuerpo_json(request)

    if datos.get('nota') is not None:
        tope = entrega.tarea.puntaje_maximo

        nota = v.numero(minimo=0, maximo=tope)(datos['nota'], 'nota')

        if nota > tope:
            raise ErrorApi(
                f'La nota no puede pasar del puntaje maximo de la tarea ({tope}).',
                400,
                motivo='campo_invalido',
                campo='nota',
            )

    v.aplicar(entrega, datos, CAMPOS_CALIFICACION)
    entrega.save()

    return ok(
        entrega_json(entrega),
        mensaje=f'Entrega de {entrega.usuario.nombre_completo} calificada.',
    )


# ══ PROGRESO DE MODULOS ══════════════════════════════════════════════════════

@endpoint(metodos=('POST', 'PATCH'), recurso=permisos.PROGRESO,
          accion=permisos.EDITAR, privado=True)
def marcar_modulo(request, id_modulo):
    """
    El estudiante marca (o desmarca) un modulo como completado.

    Cuerpo opcional: {"completado": true}. Sin cuerpo se da por completado,
    que es lo que quiere el 99% de las veces quien pulsa el boton.
    """
    modulo = get_object_or_404(
        Modulo.objects.select_related('curso', 'curso__facultad'), pk=id_modulo,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        modulo.curso_id in permisos.ids_cursos_de(usuario),
        permisos.PROGRESO,
        detalle=f'No estas inscrito en {modulo.curso.codigo}.',
    )

    datos = cuerpo_json(request)
    completado = (
        v.si_o_no()(datos['completado'], 'completado')
        if 'completado' in datos else True
    )

    progreso, _ = ProgresoModulo.objects.get_or_create(
        usuario=usuario, modulo=modulo,
    )
    progreso.completado = completado
    progreso.save()

    return ok(
        progreso_json(progreso),
        mensaje='Modulo completado.' if completado else 'Modulo marcado como pendiente.',
    )


# ══ FACULTADES ═══════════════════════════════════════════════════════════════

CAMPOS_FACULTAD = {
    'nombre': v.cadena(100),
    'codigo': v.cadena(10),
}


@endpoint(metodos=('POST',), recurso=permisos.FACULTADES, privado=True)
def crear_facultad(request):
    """Abre una facultad nueva. Solo el super administrador llega aqui."""
    datos = cuerpo_json(request)

    v.exigir(datos, 'nombre', 'codigo')

    codigo = str(datos['codigo']).strip().upper()

    if Facultad.objects.filter(codigo__iexact=codigo).exists():
        raise ErrorApi(
            f'Ya existe una facultad con codigo "{codigo}".',
            409,
            motivo='duplicado',
            campo='codigo',
        )

    facultad = v.aplicar(Facultad(), datos, CAMPOS_FACULTAD)
    facultad.codigo = codigo

    if datos.get('admin'):
        facultad.admin = _usuario_por_referencia(datos['admin'], 'admin')

    facultad.save()

    return _creado(facultad_json(facultad), f'Facultad {facultad.codigo} creada.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.FACULTADES, privado=True)
def editar_facultad(request, codigo):
    """
    Corrige una facultad.

    El super administrador puede con cualquiera; el administrador, solo con
    la suya, y por eso se comprueba el alcance antes de tocar nada.
    """
    facultad = get_object_or_404(Facultad, codigo__iexact=codigo)
    usuario = quien(request)

    if permisos.alcance_de(usuario, permisos.FACULTADES, permisos.EDITAR) != permisos.TODO:
        exigir_alcance(
            request,
            facultad.id_facultad in permisos.ids_facultades_de(usuario),
            permisos.FACULTADES,
            detalle=f'{facultad.codigo} no es tu facultad.',
        )

    datos = cuerpo_json(request)

    if datos.get('codigo'):
        nuevo = str(datos['codigo']).strip().upper()

        if Facultad.objects.filter(codigo__iexact=nuevo).exclude(pk=facultad.pk).exists():
            raise ErrorApi(
                f'Ya existe otra facultad con codigo "{nuevo}".',
                409,
                motivo='duplicado',
                campo='codigo',
            )

        datos['codigo'] = nuevo

    if 'admin' in datos:
        facultad.admin = (
            _usuario_por_referencia(datos['admin'], 'admin') if datos['admin'] else None
        )

    v.aplicar(facultad, datos, CAMPOS_FACULTAD)
    facultad.save()

    return ok(facultad_json(facultad), mensaje=f'Facultad {facultad.codigo} actualizada.')


# ══ QUIZZES RENDIDOS ═════════════════════════════════════════════════════════
# Un intento de quiz es, para el sistema de permisos, lo mismo que una
# entrega de tarea: algo que manda el estudiante y califica el profesor. Por
# eso comparte el recurso ENTREGAS en lugar de inventarse uno propio.


def _calificar_automatico(quiz, respuestas):
    """
    Suma el puntaje de las preguntas que se corrigen solas.

    Las que no (ensayo, subida de archivo, respuesta corta...) quedan fuera
    de esta cuenta: esas las pone el profesor a mano en nota_manual, y por
    eso la nota automatica de un quiz con ensayos nunca es la nota final.
    """
    puntaje = 0

    for pregunta in quiz.preguntas.all():
        if not pregunta.es_auto_corregible:
            continue

        enviada = respuestas.get(str(pregunta.id_pregunta))

        if enviada is None:
            enviada = respuestas.get(pregunta.id_pregunta)

        if enviada is None:
            continue

        correcta = pregunta.respuesta_correcta

        if _coincide(pregunta.tipo, enviada, correcta):
            puntaje += float(pregunta.puntaje or 0)

    return puntaje


def _coincide(tipo, enviada, correcta):
    """Compara la respuesta del estudiante con la correcta, segun el tipo."""
    if tipo == Pregunta.Tipo.VERDADERO_FALSO:
        if isinstance(enviada, str):
            enviada = enviada.strip().lower() in ('verdadero', 'true', 'si', '1')

        return bool(enviada) == bool(correcta)

    if tipo in (Pregunta.Tipo.OPCION_MULTIPLE_VARIAS,
                Pregunta.Tipo.ORDENAMIENTO,
                Pregunta.Tipo.RELACIONAR_COLUMNAS):
        # En estas el orden puede no importar, pero el conjunto si.
        if isinstance(enviada, list) and isinstance(correcta, list):
            if tipo == Pregunta.Tipo.ORDENAMIENTO:
                return enviada == correcta

            return sorted(map(str, enviada)) == sorted(map(str, correcta))

        return enviada == correcta

    if tipo == Pregunta.Tipo.RESPUESTA_NUMERICA:
        try:
            return float(enviada) == float(correcta)
        except (TypeError, ValueError):
            return False

    if isinstance(enviada, str) and isinstance(correcta, str):
        return enviada.strip().lower() == correcta.strip().lower()

    return enviada == correcta


@endpoint(metodos=('POST',), recurso=permisos.ENTREGAS, privado=True)
def responder_quiz(request, id_quiz):
    """
    El estudiante rinde un quiz.

    Cuerpo: {"respuestas": {"<id_pregunta>": <respuesta>, ...}}

    Se guarda el intento y se calcula al vuelo la nota de las preguntas
    auto-corregibles. Igual que con las tareas, si el intento ya tiene nota
    manual no se puede volver a rendir.
    """
    quiz = get_object_or_404(
        Quiz.objects.select_related('curso', 'curso__facultad').prefetch_related('preguntas'),
        pk=id_quiz,
    )
    usuario = quien(request)

    exigir_alcance(
        request,
        quiz.curso_id in permisos.ids_cursos_de(usuario),
        permisos.ENTREGAS,
        detalle=f'No estas inscrito en {quiz.curso.codigo}.',
    )

    datos = cuerpo_json(request)
    respuestas = datos.get('respuestas')

    if not isinstance(respuestas, dict):
        raise ErrorApi(
            'Envia el campo "respuestas" como un objeto '
            '{"<id_pregunta>": <respuesta>}.',
            400,
            motivo='campo_invalido',
            campo='respuestas',
        )

    intento, nuevo = RespuestaQuiz.objects.get_or_create(
        quiz=quiz, usuario=usuario, defaults={'respuestas': {}},
    )

    if intento.nota_manual is not None:
        raise ErrorApi(
            'Este quiz ya fue calificado por el profesor.',
            409,
            motivo='ya_calificada',
        )

    intento.respuestas = respuestas
    intento.nota_automatica = _calificar_automatico(quiz, respuestas)
    intento.save()

    resultado = respuesta_quiz_json(intento)

    if nuevo:
        return _creado(resultado, f'Quiz "{quiz.titulo}" enviado.')

    return ok(resultado, mensaje='Respuestas actualizadas.')


@endpoint(metodos=('PATCH', 'PUT'), recurso=permisos.ENTREGAS, privado=True)
def calificar_quiz(request, id_respuesta):
    """
    El profesor pone la nota manual de un quiz rendido.

    Un estudiante tiene permiso de EDITAR entregas -lo necesita para
    corregir la suya antes de que la califiquen-, y su alcance PROPIO le
    deja entrar aqui si el intento es suyo. Pero nota_manual no es un campo
    de la entrega, es la calificacion: se le cierra la puerta antes de mirar
    nada mas. Sin esta comprobacion, un estudiante se pondria su propia nota
    con una sola peticion.
    """
    intento = get_object_or_404(
        RespuestaQuiz.objects.select_related('quiz__curso__facultad', 'usuario'),
        pk=id_respuesta,
    )
    usuario = quien(request)

    if permisos.alcance_de(usuario, permisos.ENTREGAS, permisos.EDITAR) == permisos.PROPIO:
        exigir_alcance(
            request, False, permisos.ENTREGAS,
            detalle='La nota de un quiz la pone el profesor del curso.',
        )

    _exigir_curso(request, intento.quiz.curso, permisos.ENTREGAS, permisos.EDITAR)

    datos = cuerpo_json(request)

    v.aplicar(intento, datos, {'nota_manual': v.numero(minimo=0, maximo=1000, nulo=True)})
    intento.save()

    return ok(
        respuesta_quiz_json(intento),
        mensaje=f'Quiz de {intento.usuario.nombre_completo} calificado.',
    )
