"""Rutas de la API publica. Todas cuelgan de /api/."""
from django.urls import path, re_path

from . import views

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

    # Autenticacion de aplicaciones externas
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

    # Facultades
    path(
        "facultades/",
        views.facultades,
        name="facultades",
    ),

    path(
        "facultades/<str:codigo>/",
        views.facultad_detalle,
        name="facultad_detalle",
    ),

    # Cursos
    path(
        "cursos/",
        views.cursos,
        name="cursos",
    ),

    path(
        "cursos/<str:codigo>/",
        views.curso_detalle,
        name="curso_detalle",
    ),

    path(
        "cursos/<str:codigo>/modulos/",
        views.curso_modulos,
        name="curso_modulos",
    ),

    path(
        "cursos/<str:codigo>/tareas/",
        views.curso_tareas,
        name="curso_tareas",
    ),

    path(
        "cursos/<str:codigo>/quizzes/",
        views.curso_quizzes,
        name="curso_quizzes",
    ),

    path(
        "cursos/<str:codigo>/estudiantes/",
        views.curso_estudiantes,
        name="curso_estudiantes",
    ),

    # Evaluaciones
    path(
        "quizzes/<int:id_quiz>/",
        views.quiz_detalle,
        name="quiz_detalle",
    ),

    # Reportes
    path(
        "reportes/resumen/",
        views.reporte_resumen,
        name="reporte_resumen",
    ),

    # Usuarios (privado)
    path(
        "usuarios/",
        views.usuarios,
        name="usuarios",
    ),

    # Cualquier otra ruta bajo /api/ responde 404 en JSON, no en HTML
    re_path(
        r"^(?P<ruta>.*)$",
        views.no_encontrado,
        name="no_encontrado",
    ),
]
