"""
Vistas CRUD del modulo EVALUACIONES.

Se utilizan vistas genericas basadas en clases: ListView, DetailView,
CreateView, UpdateView y DeleteView.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import (
    TareaForm,
    EntregaForm,
    QuizForm,
    PreguntaForm,
    RespuestaQuizForm,
)
from .models import (
    Tarea,
    Entrega,
    Quiz,
    Pregunta,
    RespuestaQuiz,
)


class MensajeFormularioMixin:
    """Agrega un mensaje despues de registrar o actualizar un objeto."""

    mensaje_exito = ""

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.mensaje_exito:
            messages.success(
                self.request,
                self.mensaje_exito,
            )
        return response


class EliminacionProtegidaMixin:
    """
    Controla la eliminacion de objetos relacionados mediante
    claves foraneas configuradas con models.PROTECT.
    """

    mensaje_exito = ""
    mensaje_protegido = ""

    def form_valid(self, form):
        try:
            response = super().form_valid(form)

        except ProtectedError:
            messages.error(
                self.request,
                self.mensaje_protegido,
            )
            return redirect(self.get_success_url())

        if self.mensaje_exito:
            messages.success(
                self.request,
                self.mensaje_exito,
            )

        return response


# ============================================================
# VISTAS CRUD DE TAREAS
# ============================================================
class TareaListView(LoginRequiredMixin, ListView):
    model = Tarea
    template_name = "evaluaciones/tarea_list.html"
    context_object_name = "tareas"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Tareas",
    }

    def get_queryset(self):
        return (
            Tarea.objects
            .select_related(
                "curso",
            )
            .order_by("fecha_limite", "titulo")
        )


class TareaCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Tarea
    form_class = TareaForm
    template_name = "evaluaciones/tarea_form.html"
    success_url = reverse_lazy("evaluaciones:tarea_lista")

    mensaje_exito = "Tarea registrada correctamente."

    extra_context = {
        "titulo_pagina": "Registrar tarea",
        "texto_boton": "Guardar tarea",
    }


class TareaDetailView(LoginRequiredMixin, DetailView):
    model = Tarea
    template_name = "evaluaciones/tarea_detail.html"
    context_object_name = "tarea"

    extra_context = {
        "titulo_pagina": "Detalle de la tarea",
    }

    def get_queryset(self):
        return Tarea.objects.select_related(
                "curso",
        )


class TareaUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Tarea
    form_class = TareaForm
    template_name = "evaluaciones/tarea_form.html"
    success_url = reverse_lazy("evaluaciones:tarea_lista")

    mensaje_exito = "Tarea actualizada correctamente."

    extra_context = {
        "titulo_pagina": "Editar tarea",
        "texto_boton": "Actualizar tarea",
    }


class TareaDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Tarea
    template_name = "evaluaciones/tarea_confirm_delete.html"
    context_object_name = "tarea"
    success_url = reverse_lazy("evaluaciones:tarea_lista")

    mensaje_exito = "Tarea eliminada correctamente."

    mensaje_protegido = (
        "No se puede eliminar la tarea porque tiene entregas "
        "registradas."
    )

    extra_context = {
        "titulo_pagina": "Eliminar tarea",
    }


# ============================================================
# VISTAS CRUD DE ENTREGAS
# ============================================================
class EntregaListView(LoginRequiredMixin, ListView):
    model = Entrega
    template_name = "evaluaciones/entrega_list.html"
    context_object_name = "entregas"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Entregas",
    }

    def get_queryset(self):
        return (
            Entrega.objects
            .select_related(
                "tarea",
                "usuario",
            )
            .order_by("tarea", "usuario")
        )


class EntregaCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Entrega
    form_class = EntregaForm
    template_name = "evaluaciones/entrega_form.html"
    success_url = reverse_lazy("evaluaciones:entrega_lista")

    mensaje_exito = "Entrega registrada correctamente."

    extra_context = {
        "titulo_pagina": "Registrar entrega",
        "texto_boton": "Guardar entrega",
    }


class EntregaDetailView(LoginRequiredMixin, DetailView):
    model = Entrega
    template_name = "evaluaciones/entrega_detail.html"
    context_object_name = "entrega"

    extra_context = {
        "titulo_pagina": "Detalle de la entrega",
    }

    def get_queryset(self):
        return Entrega.objects.select_related(
                "tarea",
                "usuario",
        )


class EntregaUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Entrega
    form_class = EntregaForm
    template_name = "evaluaciones/entrega_form.html"
    success_url = reverse_lazy("evaluaciones:entrega_lista")

    mensaje_exito = "Entrega actualizada correctamente."

    extra_context = {
        "titulo_pagina": "Editar entrega",
        "texto_boton": "Actualizar entrega",
    }


class EntregaDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Entrega
    template_name = "evaluaciones/entrega_confirm_delete.html"
    context_object_name = "entrega"
    success_url = reverse_lazy("evaluaciones:entrega_lista")

    mensaje_exito = "Entrega eliminada correctamente."

    mensaje_protegido = (
        "No se puede eliminar la entrega porque esta "
        "relacionada con otros registros."
    )

    extra_context = {
        "titulo_pagina": "Eliminar entrega",
    }


# ============================================================
# VISTAS CRUD DE QUIZZES
# ============================================================
class QuizListView(LoginRequiredMixin, ListView):
    model = Quiz
    template_name = "evaluaciones/quiz_list.html"
    context_object_name = "quizzes"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Quizzes",
    }

    def get_queryset(self):
        return (
            Quiz.objects
            .select_related(
                "curso",
            )
            .order_by("fecha_limite", "titulo")
        )


class QuizCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Quiz
    form_class = QuizForm
    template_name = "evaluaciones/quiz_form.html"
    success_url = reverse_lazy("evaluaciones:quiz_lista")

    mensaje_exito = "Quiz registrado correctamente."

    extra_context = {
        "titulo_pagina": "Registrar quiz",
        "texto_boton": "Guardar quiz",
    }


class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = "evaluaciones/quiz_detail.html"
    context_object_name = "quiz"

    extra_context = {
        "titulo_pagina": "Detalle de el quiz",
    }

    def get_queryset(self):
        return Quiz.objects.select_related(
                "curso",
        )


class QuizUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Quiz
    form_class = QuizForm
    template_name = "evaluaciones/quiz_form.html"
    success_url = reverse_lazy("evaluaciones:quiz_lista")

    mensaje_exito = "Quiz actualizado correctamente."

    extra_context = {
        "titulo_pagina": "Editar quiz",
        "texto_boton": "Actualizar quiz",
    }


class QuizDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Quiz
    template_name = "evaluaciones/quiz_confirm_delete.html"
    context_object_name = "quiz"
    success_url = reverse_lazy("evaluaciones:quiz_lista")

    mensaje_exito = "Quiz eliminado correctamente."

    mensaje_protegido = (
        "No se puede eliminar el quiz porque tiene preguntas o "
        "respuestas registradas."
    )

    extra_context = {
        "titulo_pagina": "Eliminar quiz",
    }


# ============================================================
# VISTAS CRUD DE PREGUNTAS
# ============================================================
class PreguntaListView(LoginRequiredMixin, ListView):
    model = Pregunta
    template_name = "evaluaciones/pregunta_list.html"
    context_object_name = "preguntas"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Preguntas",
    }

    def get_queryset(self):
        return (
            Pregunta.objects
            .select_related(
                "quiz",
                "quiz__curso",
            )
            .order_by("quiz", "orden")
        )


class PreguntaCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Pregunta
    form_class = PreguntaForm
    template_name = "evaluaciones/pregunta_form.html"
    success_url = reverse_lazy("evaluaciones:pregunta_lista")

    mensaje_exito = "Pregunta registrada correctamente."

    extra_context = {
        "titulo_pagina": "Registrar pregunta",
        "texto_boton": "Guardar pregunta",
    }


class PreguntaDetailView(LoginRequiredMixin, DetailView):
    model = Pregunta
    template_name = "evaluaciones/pregunta_detail.html"
    context_object_name = "pregunta"

    extra_context = {
        "titulo_pagina": "Detalle de la pregunta",
    }

    def get_queryset(self):
        return Pregunta.objects.select_related(
                "quiz",
                "quiz__curso",
        )


class PreguntaUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Pregunta
    form_class = PreguntaForm
    template_name = "evaluaciones/pregunta_form.html"
    success_url = reverse_lazy("evaluaciones:pregunta_lista")

    mensaje_exito = "Pregunta actualizada correctamente."

    extra_context = {
        "titulo_pagina": "Editar pregunta",
        "texto_boton": "Actualizar pregunta",
    }


class PreguntaDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Pregunta
    template_name = "evaluaciones/pregunta_confirm_delete.html"
    context_object_name = "pregunta"
    success_url = reverse_lazy("evaluaciones:pregunta_lista")

    mensaje_exito = "Pregunta eliminada correctamente."

    mensaje_protegido = (
        "No se puede eliminar la pregunta porque esta "
        "relacionada con otros registros."
    )

    extra_context = {
        "titulo_pagina": "Eliminar pregunta",
    }


# ============================================================
# VISTAS CRUD DE RESPUESTAS DE QUIZ
# ============================================================
class RespuestaQuizListView(LoginRequiredMixin, ListView):
    model = RespuestaQuiz
    template_name = "evaluaciones/respuesta_quiz_list.html"
    context_object_name = "respuestas"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Respuestas de quiz",
    }

    def get_queryset(self):
        return (
            RespuestaQuiz.objects
            .select_related(
                "quiz",
                "usuario",
            )
            .order_by("quiz", "usuario")
        )


class RespuestaQuizCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = RespuestaQuiz
    form_class = RespuestaQuizForm
    template_name = "evaluaciones/respuesta_quiz_form.html"
    success_url = reverse_lazy("evaluaciones:respuesta_lista")

    mensaje_exito = "Respuesta registrada correctamente."

    extra_context = {
        "titulo_pagina": "Registrar respuesta",
        "texto_boton": "Guardar respuesta",
    }


class RespuestaQuizDetailView(LoginRequiredMixin, DetailView):
    model = RespuestaQuiz
    template_name = "evaluaciones/respuesta_quiz_detail.html"
    context_object_name = "respuesta"

    extra_context = {
        "titulo_pagina": "Detalle de la respuesta",
    }

    def get_queryset(self):
        return RespuestaQuiz.objects.select_related(
                "quiz",
                "usuario",
        )


class RespuestaQuizUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = RespuestaQuiz
    form_class = RespuestaQuizForm
    template_name = "evaluaciones/respuesta_quiz_form.html"
    success_url = reverse_lazy("evaluaciones:respuesta_lista")

    mensaje_exito = "Respuesta actualizada correctamente."

    extra_context = {
        "titulo_pagina": "Editar respuesta",
        "texto_boton": "Actualizar respuesta",
    }


class RespuestaQuizDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = RespuestaQuiz
    template_name = "evaluaciones/respuesta_quiz_confirm_delete.html"
    context_object_name = "respuesta"
    success_url = reverse_lazy("evaluaciones:respuesta_lista")

    mensaje_exito = "Respuesta eliminada correctamente."

    mensaje_protegido = (
        "No se puede eliminar la respuesta porque esta "
        "relacionada con otros registros."
    )

    extra_context = {
        "titulo_pagina": "Eliminar respuesta",
    }
