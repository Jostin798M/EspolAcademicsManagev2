"""Vistas generales del proyecto (panel de gestion academica)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

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


class PanelInicioView(LoginRequiredMixin, TemplateView):
    """Pagina de inicio del panel con el resumen de cada modulo."""

    template_name = "panel_inicio.html"

    extra_context = {
        "titulo_pagina": "Panel academico",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["modulos_sistema"] = [
            {
                "nombre": "Usuarios y cuentas",
                "icono": "bi-people",
                "descripcion": "Personas registradas en el sistema.",
                "registros": [
                    ("Usuarios", Usuario.objects.count(), "accounts:usuario_lista"),
                ],
            },
            {
                "nombre": "Cursos y contenidos",
                "icono": "bi-journal-bookmark",
                "descripcion": "Facultades, cursos, modulos y materiales.",
                "registros": [
                    ("Facultades", Facultad.objects.count(), "cursos:facultad_lista"),
                    ("Cursos", Curso.objects.count(), "cursos:curso_lista"),
                    ("Componentes de formula", FormulaComponente.objects.count(), "cursos:componente_lista"),
                    ("Inscripciones", Inscripcion.objects.count(), "cursos:inscripcion_lista"),
                    ("Modulos", Modulo.objects.count(), "cursos:modulo_lista"),
                    ("Materiales", Material.objects.count(), "cursos:material_lista"),
                    ("Progresos", ProgresoModulo.objects.count(), "cursos:progreso_lista"),
                ],
            },
            {
                "nombre": "Evaluaciones",
                "icono": "bi-clipboard-check",
                "descripcion": "Tareas, entregas, quizzes y respuestas.",
                "registros": [
                    ("Tareas", Tarea.objects.count(), "evaluaciones:tarea_lista"),
                    ("Entregas", Entrega.objects.count(), "evaluaciones:entrega_lista"),
                    ("Quizzes", Quiz.objects.count(), "evaluaciones:quiz_lista"),
                    ("Preguntas", Pregunta.objects.count(), "evaluaciones:pregunta_lista"),
                    ("Respuestas de quiz", RespuestaQuiz.objects.count(), "evaluaciones:respuesta_lista"),
                ],
            },
        ]
        return context
