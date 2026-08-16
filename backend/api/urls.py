"""
Rutas de la API. Todas cuelgan de /api/.

Una misma direccion sirve para leer y para escribir, que es como se espera
que funcione una API: GET /api/cursos/ lista y POST /api/cursos/ crea.
Django enruta por direccion y no por metodo, asi que ese reparto lo hace
segun_metodo(), y cada vista conserva su propio decorador con el permiso
que le corresponde.

Las rutas se agrupan por recurso, y dentro de cada grupo va primero la
coleccion y despues el elemento.
"""
from django.urls import path, re_path

from . import escritura, panel, views
from .respuestas import segun_metodo

app_name = "api"


urlpatterns = [
    path(
        "",
        views.indice,
        name="indice",
    ),

    path(
        "estado/",
        views.estado,
        name="estado",
    ),

    # ── Autenticacion ────────────────────────────────────────────────────────
    path(
        "auth/login/",
        views.auth_login,
        name="auth_login",
    ),

    path(
        "auth/verificar/",
        views.auth_verificar,
        name="auth_verificar",
    ),

    path(
        "auth/logout/",
        views.auth_logout,
        name="auth_logout",
    ),

    # ── Lo mio: el panel que corresponde a mi rol ────────────────────────────
    path(
        "mi/panel/",
        panel.mi_panel,
        name="mi_panel",
    ),

    path(
        "mi/permisos/",
        panel.mis_permisos,
        name="mis_permisos",
    ),

    path(
        "mi/perfil/",
        panel.mi_perfil,
        name="mi_perfil",
    ),

    path(
        "mi/cursos/",
        panel.mis_cursos,
        name="mis_cursos",
    ),

    path(
        "mi/tareas/",
        panel.mis_tareas,
        name="mis_tareas",
    ),

    # ── Facultades ───────────────────────────────────────────────────────────
    path(
        "facultades/",
        segun_metodo(
            GET=views.facultades,
            POST=escritura.crear_facultad,
        ),
        name="facultades",
    ),

    path(
        "facultades/<str:codigo>/",
        segun_metodo(
            GET=views.facultad_detalle,
            PATCH=escritura.editar_facultad,
            PUT=escritura.editar_facultad,
        ),
        name="facultad_detalle",
    ),

    # ── Cursos ───────────────────────────────────────────────────────────────
    path(
        "cursos/",
        segun_metodo(
            GET=views.cursos,
            POST=escritura.crear_curso,
        ),
        name="cursos",
    ),

    path(
        "cursos/<str:codigo>/",
        segun_metodo(
            GET=views.curso_detalle,
            PATCH=escritura.editar_curso,
            PUT=escritura.editar_curso,
            DELETE=escritura.eliminar_curso,
        ),
        name="curso_detalle",
    ),

    path(
        "cursos/<str:codigo>/modulos/",
        segun_metodo(
            GET=views.curso_modulos,
            POST=escritura.crear_modulo,
        ),
        name="curso_modulos",
    ),

    path(
        "cursos/<str:codigo>/tareas/",
        segun_metodo(
            GET=views.curso_tareas,
            POST=escritura.crear_tarea,
        ),
        name="curso_tareas",
    ),

    path(
        "cursos/<str:codigo>/quizzes/",
        segun_metodo(
            GET=views.curso_quizzes,
            POST=escritura.crear_quiz,
        ),
        name="curso_quizzes",
    ),

    path(
        "cursos/<str:codigo>/progreso/",
        panel.progreso_del_curso,
        name="curso_progreso",
    ),

    path(
        "cursos/<str:codigo>/estudiantes/",
        segun_metodo(
            GET=views.curso_estudiantes,
            POST=escritura.inscribir,
        ),
        name="curso_estudiantes",
    ),

    # ── Modulos y materiales ─────────────────────────────────────────────────
    path(
        "modulos/<int:id_modulo>/",
        segun_metodo(
            GET=views.modulo_detalle,
            PATCH=escritura.editar_modulo,
            PUT=escritura.editar_modulo,
            DELETE=escritura.eliminar_modulo,
        ),
        name="modulo_detalle",
    ),

    path(
        "modulos/<int:id_modulo>/materiales/",
        escritura.crear_material,
        name="modulo_materiales",
    ),

    path(
        "modulos/<int:id_modulo>/progreso/",
        escritura.marcar_modulo,
        name="modulo_progreso",
    ),

    path(
        "materiales/<int:id_material>/",
        segun_metodo(
            PATCH=escritura.editar_material,
            PUT=escritura.editar_material,
            DELETE=escritura.eliminar_material,
        ),
        name="material_detalle",
    ),

    # ── Tareas y entregas ────────────────────────────────────────────────────
    path(
        "tareas/<int:id_tarea>/",
        segun_metodo(
            GET=views.tarea_detalle,
            PATCH=escritura.editar_tarea,
            PUT=escritura.editar_tarea,
            DELETE=escritura.eliminar_tarea,
        ),
        name="tarea_detalle",
    ),

    path(
        "tareas/<int:id_tarea>/entregas/",
        segun_metodo(
            GET=panel.entregas_de_tarea,
            POST=escritura.entregar,
        ),
        name="tarea_entregas",
    ),

    path(
        "entregas/<int:id_entrega>/",
        segun_metodo(
            PATCH=escritura.calificar,
            PUT=escritura.calificar,
        ),
        name="entrega_detalle",
    ),

    # ── Quizzes y preguntas ──────────────────────────────────────────────────
    path(
        "quizzes/<int:id_quiz>/",
        segun_metodo(
            GET=views.quiz_detalle,
            PATCH=escritura.editar_quiz,
            PUT=escritura.editar_quiz,
            DELETE=escritura.eliminar_quiz,
        ),
        name="quiz_detalle",
    ),

    path(
        "quizzes/<int:id_quiz>/respuestas/",
        segun_metodo(
            GET=panel.respuestas_del_quiz,
            POST=escritura.responder_quiz,
        ),
        name="quiz_respuestas",
    ),

    path(
        "respuestas/<int:id_respuesta>/",
        escritura.calificar_quiz,
        name="respuesta_quiz_detalle",
    ),

    path(
        "quizzes/<int:id_quiz>/preguntas/",
        escritura.crear_pregunta,
        name="quiz_preguntas",
    ),

    path(
        "preguntas/<int:id_pregunta>/",
        segun_metodo(
            PATCH=escritura.editar_pregunta,
            PUT=escritura.editar_pregunta,
            DELETE=escritura.eliminar_pregunta,
        ),
        name="pregunta_detalle",
    ),

    # ── Inscripciones ────────────────────────────────────────────────────────
    path(
        "inscripciones/<int:id_inscripcion>/",
        escritura.eliminar_inscripcion,
        name="inscripcion_detalle",
    ),

    # ── Reportes ─────────────────────────────────────────────────────────────
    path(
        "reportes/resumen/",
        views.reporte_resumen,
        name="reporte_resumen",
    ),

    # ── Usuarios ─────────────────────────────────────────────────────────────
    path(
        "usuarios/",
        segun_metodo(
            GET=views.usuarios,
            POST=escritura.crear_usuario,
        ),
        name="usuarios",
    ),

    path(
        "usuarios/<int:id_usuario>/",
        segun_metodo(
            GET=views.usuario_detalle,
            PATCH=escritura.editar_usuario,
            PUT=escritura.editar_usuario,
            DELETE=escritura.eliminar_usuario,
        ),
        name="usuario_detalle",
    ),

    # Cualquier otra ruta bajo /api/ responde 404 en JSON, no en HTML
    re_path(
        r"^(?P<ruta>.*)$",
        views.no_encontrado,
        name="no_encontrado",
    ),
]
