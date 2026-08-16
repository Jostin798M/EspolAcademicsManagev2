"""
Conversion de los modelos de Django a diccionarios listos para JSON.

Cada funcion recibe una instancia y devuelve un dict con nombres de campo
iguales a los de la base de datos, para que el consumidor externo pueda
relacionarlos con el modelo entidad-relacion del proyecto.

Algunas aceptan un argumento que decide cuanto ensenar: quiz_json solo
incluye la respuesta correcta si quien pregunta puede editar el quiz, y
curso_detalle_json adjunta lo que ese usuario puede hacer dentro del curso.
La regla de quien puede que cosa no vive aqui -eso es permisos.py-; aqui
solo se obedece.
"""


def _fecha(valor):
    return valor.isoformat() if valor else None


def _numero(valor):
    """Convierte Decimal a float (JSON no maneja Decimal)."""
    return float(valor) if valor is not None else None


def facultad_json(facultad):
    datos = {
        'id_facultad': facultad.id_facultad,
        'codigo': facultad.codigo,
        'nombre': facultad.nombre,
    }

    # Solo aparece en los listados, donde el queryset lo calcula.
    if hasattr(facultad, 'total_cursos'):
        datos['total_cursos'] = facultad.total_cursos

    return datos


def usuario_json(usuario):
    """Datos personales: solo se exponen en endpoints privados."""
    return {
        'id_usuario': usuario.id_usuario,
        'nombres': usuario.nombres,
        'apellidos': usuario.apellidos,
        'nombre_completo': usuario.nombre_completo,
        'correo': usuario.correo,
        'rol': usuario.rol,
        'estado': usuario.estado,
        'facultad': usuario.facultad.codigo if usuario.facultad_id else None,
        'fecha_registro': _fecha(usuario.fecha_registro),
    }


def profesor_json(usuario):
    """Version publica de un usuario: sin correo ni datos de contacto."""
    return {
        'id_usuario': usuario.id_usuario,
        'nombre_completo': usuario.nombre_completo,
    }


def curso_json(curso):
    return {
        'id_curso': curso.id_curso,
        'codigo': curso.codigo,
        'nombre': curso.nombre,
        'descripcion': curso.descripcion,
        'estado': curso.estado,
        'fecha_inicio': _fecha(curso.fecha_inicio),
        'fecha_fin': _fecha(curso.fecha_fin),
        'facultad': facultad_json(curso.facultad),
        'profesor': profesor_json(curso.profesor),
    }


def componente_json(componente):
    return {
        'id_componente': componente.id_componente,
        'componente': componente.componente,
        'porcentaje': componente.porcentaje,
        'orden': componente.orden,
    }


def material_json(material):
    return {
        'id_material': material.id_material,
        'tipo': material.tipo,
        'titulo': material.titulo,
        'url': material.url,
    }


def modulo_json(modulo, con_materiales=True):
    datos = {
        'id_modulo': modulo.id_modulo,
        'titulo': modulo.titulo,
        'descripcion': modulo.descripcion,
        'orden': modulo.orden,
        'curso': modulo.curso.codigo,
    }

    if con_materiales:
        datos['materiales'] = [
            material_json(material) for material in modulo.materiales.all()
        ]

    return datos


def tarea_json(tarea):
    return {
        'id_tarea': tarea.id_tarea,
        'titulo': tarea.titulo,
        'descripcion': tarea.descripcion,
        'criterios': tarea.criterios,
        'fecha_limite': _fecha(tarea.fecha_limite),
        'puntaje_maximo': _numero(tarea.puntaje_maximo),
        'curso': tarea.curso.codigo,
    }


def quiz_json(quiz, con_preguntas=False, con_respuestas=False):
    datos = {
        'id_quiz': quiz.id_quiz,
        'titulo': quiz.titulo,
        'descripcion': quiz.descripcion,
        'tiempo_limite_min': quiz.tiempo_limite_min,
        'fecha_limite': _fecha(quiz.fecha_limite),
        'curso': quiz.curso.codigo,
    }

    if hasattr(quiz, 'total_preguntas'):
        datos['total_preguntas'] = quiz.total_preguntas

    if con_preguntas:
        datos['preguntas'] = [
            pregunta_json(pregunta, con_respuesta=con_respuestas)
            for pregunta in quiz.preguntas.all()
        ]

    return datos


def pregunta_json(pregunta, con_respuesta=False):
    """
    Una pregunta del quiz.

    respuesta_correcta solo viaja cuando con_respuesta es True, y eso solo
    ocurre para quien puede editar el quiz: el profesor que lo arma la
    necesita, el estudiante que lo va a rendir no.
    """
    datos = {
        'id_pregunta': pregunta.id_pregunta,
        'tipo': pregunta.tipo,
        'enunciado': pregunta.enunciado,
        'puntaje': _numero(pregunta.puntaje),
        'orden': pregunta.orden,
        'opciones': pregunta.opciones,
        'quiz': pregunta.quiz_id,
    }

    if con_respuesta:
        datos['respuesta_correcta'] = pregunta.respuesta_correcta

    return datos


def curso_detalle_json(curso, puedo=None):
    """
    Curso con su formula, modulos, tareas y quizzes.

    puedo es {recurso: [acciones]} calculado por
    permisos.acciones_en_curso(): lo que quien pregunta puede hacer dentro
    de ESTE curso. La app lo usa para decidir que botones dibuja en la
    pantalla del curso.
    """
    datos = curso_json(curso)

    datos['formula'] = [
        componente_json(componente) for componente in curso.formula.all()
    ]
    datos['modulos'] = [
        modulo_json(modulo) for modulo in curso.modulos.all()
    ]
    datos['tareas'] = [tarea_json(tarea) for tarea in curso.tareas.all()]
    datos['quizzes'] = [quiz_json(quiz) for quiz in curso.quizzes.all()]

    if puedo is not None:
        datos['puedo'] = puedo

    return datos


def inscripcion_json(inscripcion):
    """Inscripcion con los datos del estudiante (endpoint privado)."""
    return {
        'id_inscripcion': inscripcion.id_inscripcion,
        'rol_en_curso': inscripcion.rol_en_curso,
        'fecha': _fecha(inscripcion.fecha),
        'curso': inscripcion.curso.codigo,
        'usuario': usuario_json(inscripcion.usuario),
    }


def entrega_json(entrega, con_estudiante=True):
    """
    Una entrega de tarea.

    con_estudiante=False lo usa el estudiante al mirar las suyas: ahi el
    nombre sobra, y asi la misma funcion sirve para el profesor que revisa
    la lista completa.
    """
    datos = {
        'id_entrega': entrega.id_entrega,
        'tarea': entrega.tarea_id,
        'tarea_titulo': entrega.tarea.titulo,
        'curso': entrega.tarea.curso.codigo,
        'estado': entrega.estado,
        'fecha': _fecha(entrega.fecha),
        'texto': entrega.texto,
        'archivo': entrega.archivo,
        'imagen': entrega.imagen,
        'link': entrega.link,
        'nota': _numero(entrega.nota),
        'puntaje_maximo': _numero(entrega.tarea.puntaje_maximo),
        'comentario': entrega.comentario,
        'calificada': entrega.nota is not None,
    }

    if con_estudiante:
        datos['usuario'] = entrega.usuario_id
        datos['estudiante'] = entrega.usuario.nombre_completo

    return datos


def progreso_json(progreso):
    """Marca de un modulo completado por un estudiante."""
    return {
        'id_progreso': progreso.id_progreso,
        'modulo': progreso.modulo_id,
        'modulo_titulo': progreso.modulo.titulo,
        'curso': progreso.modulo.curso.codigo,
        'usuario': progreso.usuario_id,
        'completado': progreso.completado,
        'fecha': _fecha(progreso.fecha),
    }


def respuesta_quiz_json(respuesta):
    """Intento de un estudiante en un quiz, con la nota que saco."""
    return {
        'id_respuesta_quiz': respuesta.id_respuesta_quiz,
        'quiz': respuesta.quiz_id,
        'quiz_titulo': respuesta.quiz.titulo,
        'curso': respuesta.quiz.curso.codigo,
        'usuario': respuesta.usuario_id,
        'estudiante': respuesta.usuario.nombre_completo,
        'nota_automatica': _numero(respuesta.nota_automatica),
        'nota_manual': _numero(respuesta.nota_manual),
        'fecha': _fecha(respuesta.fecha),
    }
