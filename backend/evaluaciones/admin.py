from django.contrib import admin

from .models import Entrega, Pregunta, Quiz, RespuestaQuiz, Tarea


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = (
        "id_tarea",
        "titulo",
        "curso",
        "fecha_limite",
        "puntaje_maximo",
    )

    search_fields = (
        "titulo",
        "descripcion",
        "curso__codigo",
    )

    list_filter = (
        "curso",
    )

    ordering = (
        "fecha_limite",
    )

    list_select_related = (
        "curso",
    )


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = (
        "id_entrega",
        "tarea",
        "usuario",
        "estado",
        "fecha",
        "nota",
    )

    search_fields = (
        "tarea__titulo",
        "usuario__nombres",
        "usuario__apellidos",
    )

    list_filter = (
        "estado",
        "tarea",
    )

    ordering = (
        "tarea",
        "usuario",
    )

    list_select_related = (
        "tarea",
        "usuario",
    )


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "id_quiz",
        "titulo",
        "curso",
        "tiempo_limite_min",
        "fecha_limite",
    )

    search_fields = (
        "titulo",
        "descripcion",
        "curso__codigo",
    )

    list_filter = (
        "curso",
    )

    ordering = (
        "fecha_limite",
    )

    list_select_related = (
        "curso",
    )


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = (
        "id_pregunta",
        "quiz",
        "orden",
        "tipo",
        "puntaje",
    )

    search_fields = (
        "enunciado",
        "quiz__titulo",
    )

    list_filter = (
        "tipo",
        "quiz",
    )

    ordering = (
        "quiz",
        "orden",
    )

    list_select_related = (
        "quiz",
    )


@admin.register(RespuestaQuiz)
class RespuestaQuizAdmin(admin.ModelAdmin):
    list_display = (
        "id_respuesta_quiz",
        "quiz",
        "usuario",
        "nota_automatica",
        "nota_manual",
        "fecha",
    )

    search_fields = (
        "quiz__titulo",
        "usuario__nombres",
        "usuario__apellidos",
    )

    list_filter = (
        "quiz",
    )

    ordering = (
        "quiz",
        "usuario",
    )

    list_select_related = (
        "quiz",
        "usuario",
    )
