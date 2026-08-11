from django.urls import path
from django.views.generic import RedirectView

from .views import (
    EntregaCreateView,
    EntregaDeleteView,
    EntregaDetailView,
    EntregaListView,
    EntregaUpdateView,
    PreguntaCreateView,
    PreguntaDeleteView,
    PreguntaDetailView,
    PreguntaListView,
    PreguntaUpdateView,
    QuizCreateView,
    QuizDeleteView,
    QuizDetailView,
    QuizListView,
    QuizUpdateView,
    RespuestaQuizCreateView,
    RespuestaQuizDeleteView,
    RespuestaQuizDetailView,
    RespuestaQuizListView,
    RespuestaQuizUpdateView,
    TareaCreateView,
    TareaDeleteView,
    TareaDetailView,
    TareaListView,
    TareaUpdateView,
)

app_name = "evaluaciones"


urlpatterns = [
    # Pagina inicial de la aplicacion evaluaciones
    path(
        "",
        RedirectView.as_view(
            pattern_name="evaluaciones:tarea_lista",
            permanent=False,
        ),
        name="inicio",
    ),

    # ========================================================
    # URLs DE TAREAS
    # ========================================================

    path(
        "tareas/",
        TareaListView.as_view(),
        name="tarea_lista",
    ),

    path(
        "tareas/nuevo/",
        TareaCreateView.as_view(),
        name="tarea_crear",
    ),

    path(
        "tareas/<int:pk>/",
        TareaDetailView.as_view(),
        name="tarea_detalle",
    ),

    path(
        "tareas/<int:pk>/editar/",
        TareaUpdateView.as_view(),
        name="tarea_editar",
    ),

    path(
        "tareas/<int:pk>/eliminar/",
        TareaDeleteView.as_view(),
        name="tarea_eliminar",
    ),

    # ========================================================
    # URLs DE ENTREGAS
    # ========================================================

    path(
        "entregas/",
        EntregaListView.as_view(),
        name="entrega_lista",
    ),

    path(
        "entregas/nuevo/",
        EntregaCreateView.as_view(),
        name="entrega_crear",
    ),

    path(
        "entregas/<int:pk>/",
        EntregaDetailView.as_view(),
        name="entrega_detalle",
    ),

    path(
        "entregas/<int:pk>/editar/",
        EntregaUpdateView.as_view(),
        name="entrega_editar",
    ),

    path(
        "entregas/<int:pk>/eliminar/",
        EntregaDeleteView.as_view(),
        name="entrega_eliminar",
    ),

    # ========================================================
    # URLs DE QUIZZES
    # ========================================================

    path(
        "quizzes/",
        QuizListView.as_view(),
        name="quiz_lista",
    ),

    path(
        "quizzes/nuevo/",
        QuizCreateView.as_view(),
        name="quiz_crear",
    ),

    path(
        "quizzes/<int:pk>/",
        QuizDetailView.as_view(),
        name="quiz_detalle",
    ),

    path(
        "quizzes/<int:pk>/editar/",
        QuizUpdateView.as_view(),
        name="quiz_editar",
    ),

    path(
        "quizzes/<int:pk>/eliminar/",
        QuizDeleteView.as_view(),
        name="quiz_eliminar",
    ),

    # ========================================================
    # URLs DE PREGUNTAS
    # ========================================================

    path(
        "preguntas/",
        PreguntaListView.as_view(),
        name="pregunta_lista",
    ),

    path(
        "preguntas/nuevo/",
        PreguntaCreateView.as_view(),
        name="pregunta_crear",
    ),

    path(
        "preguntas/<int:pk>/",
        PreguntaDetailView.as_view(),
        name="pregunta_detalle",
    ),

    path(
        "preguntas/<int:pk>/editar/",
        PreguntaUpdateView.as_view(),
        name="pregunta_editar",
    ),

    path(
        "preguntas/<int:pk>/eliminar/",
        PreguntaDeleteView.as_view(),
        name="pregunta_eliminar",
    ),

    # ========================================================
    # URLs DE RESPUESTAS DE QUIZ
    # ========================================================

    path(
        "respuestas/",
        RespuestaQuizListView.as_view(),
        name="respuesta_lista",
    ),

    path(
        "respuestas/nuevo/",
        RespuestaQuizCreateView.as_view(),
        name="respuesta_crear",
    ),

    path(
        "respuestas/<int:pk>/",
        RespuestaQuizDetailView.as_view(),
        name="respuesta_detalle",
    ),

    path(
        "respuestas/<int:pk>/editar/",
        RespuestaQuizUpdateView.as_view(),
        name="respuesta_editar",
    ),

    path(
        "respuestas/<int:pk>/eliminar/",
        RespuestaQuizDeleteView.as_view(),
        name="respuesta_eliminar",
    ),

]
