"""
Vistas CRUD del modulo ACCOUNTS.

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

from .forms import UsuarioForm
from .models import Usuario


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
# VISTAS CRUD DE USUARIO
# ============================================================
class UsuarioListView(LoginRequiredMixin, ListView):
    model = Usuario
    template_name = "accounts/usuario_list.html"
    context_object_name = "usuarios"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Usuarios",
    }

    def get_queryset(self):
        return Usuario.objects.order_by("apellidos", "nombres")


class UsuarioCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Usuario
    form_class = UsuarioForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuario_lista")

    mensaje_exito = "Usuario registrado correctamente."

    extra_context = {
        "titulo_pagina": "Registrar usuario",
        "texto_boton": "Guardar usuario",
    }


class UsuarioDetailView(LoginRequiredMixin, DetailView):
    model = Usuario
    template_name = "accounts/usuario_detail.html"
    context_object_name = "usuario_registro"

    extra_context = {
        "titulo_pagina": "Detalle del usuario",
    }


class UsuarioUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Usuario
    form_class = UsuarioForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuario_lista")

    mensaje_exito = "Usuario actualizado correctamente."

    extra_context = {
        "titulo_pagina": "Editar usuario",
        "texto_boton": "Actualizar usuario",
    }


class UsuarioDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Usuario
    template_name = "accounts/usuario_confirm_delete.html"
    context_object_name = "usuario_registro"
    success_url = reverse_lazy("accounts:usuario_lista")

    mensaje_exito = "Usuario eliminado correctamente."

    mensaje_protegido = (
        "No se puede eliminar el usuario porque tiene "
        "cursos, inscripciones o entregas relacionadas."
    )

    extra_context = {
        "titulo_pagina": "Eliminar usuario",
    }
