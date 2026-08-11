"""
Vistas CRUD del modulo CURSOS.

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
    FacultadForm,
    CursoForm,
    FormulaComponenteForm,
    InscripcionForm,
    ModuloForm,
    MaterialForm,
    ProgresoModuloForm,
)
from .models import (
    Facultad,
    Curso,
    FormulaComponente,
    Inscripcion,
    Modulo,
    Material,
    ProgresoModulo,
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
# VISTAS CRUD DE FACULTADES
# ============================================================
class FacultadListView(LoginRequiredMixin, ListView):
    model = Facultad
    template_name = "cursos/facultad_list.html"
    context_object_name = "facultades"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Facultades",
    }

    def get_queryset(self):
        return (
            Facultad.objects
            .select_related(
                "admin",
            )
            .order_by("nombre")
        )


class FacultadCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Facultad
    form_class = FacultadForm
    template_name = "cursos/facultad_form.html"
    success_url = reverse_lazy("cursos:facultad_lista")

    mensaje_exito = "Facultad registrada correctamente."

    extra_context = {
        "titulo_pagina": "Registrar facultad",
        "texto_boton": "Guardar facultad",
    }


class FacultadDetailView(LoginRequiredMixin, DetailView):
    model = Facultad
    template_name = "cursos/facultad_detail.html"
    context_object_name = "facultad"

    extra_context = {
        "titulo_pagina": "Detalle de la facultad",
    }

    def get_queryset(self):
        return Facultad.objects.select_related(
                "admin",
        )


class FacultadUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Facultad
    form_class = FacultadForm
    template_name = "cursos/facultad_form.html"
    success_url = reverse_lazy("cursos:facultad_lista")

    mensaje_exito = "Facultad actualizada correctamente."

    extra_context = {
        "titulo_pagina": "Editar facultad",
        "texto_boton": "Actualizar facultad",
    }


class FacultadDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Facultad
    template_name = "cursos/facultad_confirm_delete.html"
    context_object_name = "facultad"
    success_url = reverse_lazy("cursos:facultad_lista")

    mensaje_exito = "Facultad eliminada correctamente."

    mensaje_protegido = (
        "No se puede eliminar la facultad porque tiene cursos "
        "relacionados."
    )

    extra_context = {
        "titulo_pagina": "Eliminar facultad",
    }


# ============================================================
# VISTAS CRUD DE CURSOS
# ============================================================
class CursoListView(LoginRequiredMixin, ListView):
    model = Curso
    template_name = "cursos/curso_list.html"
    context_object_name = "cursos"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Cursos",
    }

    def get_queryset(self):
        return (
            Curso.objects
            .select_related(
                "facultad",
                "profesor",
            )
            .order_by("-fecha_inicio", "codigo")
        )


class CursoCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Curso
    form_class = CursoForm
    template_name = "cursos/curso_form.html"
    success_url = reverse_lazy("cursos:curso_lista")

    mensaje_exito = "Curso registrado correctamente."

    extra_context = {
        "titulo_pagina": "Registrar curso",
        "texto_boton": "Guardar curso",
    }


class CursoDetailView(LoginRequiredMixin, DetailView):
    model = Curso
    template_name = "cursos/curso_detail.html"
    context_object_name = "curso"

    extra_context = {
        "titulo_pagina": "Detalle de el curso",
    }

    def get_queryset(self):
        return Curso.objects.select_related(
                "facultad",
                "profesor",
        )


class CursoUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Curso
    form_class = CursoForm
    template_name = "cursos/curso_form.html"
    success_url = reverse_lazy("cursos:curso_lista")

    mensaje_exito = "Curso actualizado correctamente."

    extra_context = {
        "titulo_pagina": "Editar curso",
        "texto_boton": "Actualizar curso",
    }


class CursoDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Curso
    template_name = "cursos/curso_confirm_delete.html"
    context_object_name = "curso"
    success_url = reverse_lazy("cursos:curso_lista")

    mensaje_exito = "Curso eliminado correctamente."

    mensaje_protegido = (
        "No se puede eliminar el curso porque tiene modulos, "
        "tareas, quizzes o inscripciones relacionadas."
    )

    extra_context = {
        "titulo_pagina": "Eliminar curso",
    }


# ============================================================
# VISTAS CRUD DE COMPONENTES DE LA FORMULA
# ============================================================
class FormulaComponenteListView(LoginRequiredMixin, ListView):
    model = FormulaComponente
    template_name = "cursos/formula_componente_list.html"
    context_object_name = "componentes"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Componentes de la formula",
    }

    def get_queryset(self):
        return (
            FormulaComponente.objects
            .select_related(
                "curso",
            )
            .order_by("curso", "orden")
        )


class FormulaComponenteCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = FormulaComponente
    form_class = FormulaComponenteForm
    template_name = "cursos/formula_componente_form.html"
    success_url = reverse_lazy("cursos:componente_lista")

    mensaje_exito = "Componente registrado correctamente."

    extra_context = {
        "titulo_pagina": "Registrar componente",
        "texto_boton": "Guardar componente",
    }


class FormulaComponenteDetailView(LoginRequiredMixin, DetailView):
    model = FormulaComponente
    template_name = "cursos/formula_componente_detail.html"
    context_object_name = "componente"

    extra_context = {
        "titulo_pagina": "Detalle de el componente",
    }

    def get_queryset(self):
        return FormulaComponente.objects.select_related(
                "curso",
        )


class FormulaComponenteUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = FormulaComponente
    form_class = FormulaComponenteForm
    template_name = "cursos/formula_componente_form.html"
    success_url = reverse_lazy("cursos:componente_lista")

    mensaje_exito = "Componente actualizado correctamente."

    extra_context = {
        "titulo_pagina": "Editar componente",
        "texto_boton": "Actualizar componente",
    }


class FormulaComponenteDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = FormulaComponente
    template_name = "cursos/formula_componente_confirm_delete.html"
    context_object_name = "componente"
    success_url = reverse_lazy("cursos:componente_lista")

    mensaje_exito = "Componente eliminado correctamente."

    mensaje_protegido = (
        "No se puede eliminar el componente porque esta "
        "relacionado con otros registros."
    )

    extra_context = {
        "titulo_pagina": "Eliminar componente",
    }


# ============================================================
# VISTAS CRUD DE INSCRIPCIONES
# ============================================================
class InscripcionListView(LoginRequiredMixin, ListView):
    model = Inscripcion
    template_name = "cursos/inscripcion_list.html"
    context_object_name = "inscripciones"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Inscripciones",
    }

    def get_queryset(self):
        return (
            Inscripcion.objects
            .select_related(
                "usuario",
                "curso",
            )
            .order_by("curso", "usuario")
        )


class InscripcionCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Inscripcion
    form_class = InscripcionForm
    template_name = "cursos/inscripcion_form.html"
    success_url = reverse_lazy("cursos:inscripcion_lista")

    mensaje_exito = "Inscripcion registrada correctamente."

    extra_context = {
        "titulo_pagina": "Registrar inscripcion",
        "texto_boton": "Guardar inscripcion",
    }


class InscripcionDetailView(LoginRequiredMixin, DetailView):
    model = Inscripcion
    template_name = "cursos/inscripcion_detail.html"
    context_object_name = "inscripcion"

    extra_context = {
        "titulo_pagina": "Detalle de la inscripcion",
    }

    def get_queryset(self):
        return Inscripcion.objects.select_related(
                "usuario",
                "curso",
        )


class InscripcionUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Inscripcion
    form_class = InscripcionForm
    template_name = "cursos/inscripcion_form.html"
    success_url = reverse_lazy("cursos:inscripcion_lista")

    mensaje_exito = "Inscripcion actualizada correctamente."

    extra_context = {
        "titulo_pagina": "Editar inscripcion",
        "texto_boton": "Actualizar inscripcion",
    }


class InscripcionDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Inscripcion
    template_name = "cursos/inscripcion_confirm_delete.html"
    context_object_name = "inscripcion"
    success_url = reverse_lazy("cursos:inscripcion_lista")

    mensaje_exito = "Inscripcion eliminada correctamente."

    mensaje_protegido = (
        "No se puede eliminar la inscripcion porque esta "
        "relacionada con otros registros."
    )

    extra_context = {
        "titulo_pagina": "Eliminar inscripcion",
    }


# ============================================================
# VISTAS CRUD DE MODULOS
# ============================================================
class ModuloListView(LoginRequiredMixin, ListView):
    model = Modulo
    template_name = "cursos/modulo_list.html"
    context_object_name = "modulos"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Modulos",
    }

    def get_queryset(self):
        return (
            Modulo.objects
            .select_related(
                "curso",
            )
            .order_by("curso", "orden")
        )


class ModuloCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Modulo
    form_class = ModuloForm
    template_name = "cursos/modulo_form.html"
    success_url = reverse_lazy("cursos:modulo_lista")

    mensaje_exito = "Modulo registrado correctamente."

    extra_context = {
        "titulo_pagina": "Registrar modulo",
        "texto_boton": "Guardar modulo",
    }


class ModuloDetailView(LoginRequiredMixin, DetailView):
    model = Modulo
    template_name = "cursos/modulo_detail.html"
    context_object_name = "modulo"

    extra_context = {
        "titulo_pagina": "Detalle de el modulo",
    }

    def get_queryset(self):
        return Modulo.objects.select_related(
                "curso",
        )


class ModuloUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Modulo
    form_class = ModuloForm
    template_name = "cursos/modulo_form.html"
    success_url = reverse_lazy("cursos:modulo_lista")

    mensaje_exito = "Modulo actualizado correctamente."

    extra_context = {
        "titulo_pagina": "Editar modulo",
        "texto_boton": "Actualizar modulo",
    }


class ModuloDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Modulo
    template_name = "cursos/modulo_confirm_delete.html"
    context_object_name = "modulo"
    success_url = reverse_lazy("cursos:modulo_lista")

    mensaje_exito = "Modulo eliminado correctamente."

    mensaje_protegido = (
        "No se puede eliminar el modulo porque tiene materiales "
        "o registros de progreso relacionados."
    )

    extra_context = {
        "titulo_pagina": "Eliminar modulo",
    }


# ============================================================
# VISTAS CRUD DE MATERIALES
# ============================================================
class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = "cursos/material_list.html"
    context_object_name = "materiales"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Materiales",
    }

    def get_queryset(self):
        return (
            Material.objects
            .select_related(
                "modulo",
                "modulo__curso",
            )
            .order_by("modulo", "titulo")
        )


class MaterialCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = Material
    form_class = MaterialForm
    template_name = "cursos/material_form.html"
    success_url = reverse_lazy("cursos:material_lista")

    mensaje_exito = "Material registrado correctamente."

    extra_context = {
        "titulo_pagina": "Registrar material",
        "texto_boton": "Guardar material",
    }


class MaterialDetailView(LoginRequiredMixin, DetailView):
    model = Material
    template_name = "cursos/material_detail.html"
    context_object_name = "material"

    extra_context = {
        "titulo_pagina": "Detalle de el material",
    }

    def get_queryset(self):
        return Material.objects.select_related(
                "modulo",
                "modulo__curso",
        )


class MaterialUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = Material
    form_class = MaterialForm
    template_name = "cursos/material_form.html"
    success_url = reverse_lazy("cursos:material_lista")

    mensaje_exito = "Material actualizado correctamente."

    extra_context = {
        "titulo_pagina": "Editar material",
        "texto_boton": "Actualizar material",
    }


class MaterialDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = Material
    template_name = "cursos/material_confirm_delete.html"
    context_object_name = "material"
    success_url = reverse_lazy("cursos:material_lista")

    mensaje_exito = "Material eliminado correctamente."

    mensaje_protegido = (
        "No se puede eliminar el material porque esta "
        "relacionado con otros registros."
    )

    extra_context = {
        "titulo_pagina": "Eliminar material",
    }


# ============================================================
# VISTAS CRUD DE PROGRESO DE MODULOS
# ============================================================
class ProgresoModuloListView(LoginRequiredMixin, ListView):
    model = ProgresoModulo
    template_name = "cursos/progreso_modulo_list.html"
    context_object_name = "progresos"
    paginate_by = 10

    extra_context = {
        "titulo_pagina": "Progreso de modulos",
    }

    def get_queryset(self):
        return (
            ProgresoModulo.objects
            .select_related(
                "usuario",
                "modulo",
            )
            .order_by("usuario", "modulo")
        )


class ProgresoModuloCreateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    CreateView,
):
    model = ProgresoModulo
    form_class = ProgresoModuloForm
    template_name = "cursos/progreso_modulo_form.html"
    success_url = reverse_lazy("cursos:progreso_lista")

    mensaje_exito = "Progreso registrado correctamente."

    extra_context = {
        "titulo_pagina": "Registrar progreso",
        "texto_boton": "Guardar progreso",
    }


class ProgresoModuloDetailView(LoginRequiredMixin, DetailView):
    model = ProgresoModulo
    template_name = "cursos/progreso_modulo_detail.html"
    context_object_name = "progreso"

    extra_context = {
        "titulo_pagina": "Detalle de el progreso",
    }

    def get_queryset(self):
        return ProgresoModulo.objects.select_related(
                "usuario",
                "modulo",
        )


class ProgresoModuloUpdateView(
    LoginRequiredMixin,
    MensajeFormularioMixin,
    UpdateView,
):
    model = ProgresoModulo
    form_class = ProgresoModuloForm
    template_name = "cursos/progreso_modulo_form.html"
    success_url = reverse_lazy("cursos:progreso_lista")

    mensaje_exito = "Progreso actualizado correctamente."

    extra_context = {
        "titulo_pagina": "Editar progreso",
        "texto_boton": "Actualizar progreso",
    }


class ProgresoModuloDeleteView(
    LoginRequiredMixin,
    EliminacionProtegidaMixin,
    DeleteView,
):
    model = ProgresoModulo
    template_name = "cursos/progreso_modulo_confirm_delete.html"
    context_object_name = "progreso"
    success_url = reverse_lazy("cursos:progreso_lista")

    mensaje_exito = "Progreso eliminado correctamente."

    mensaje_protegido = (
        "No se puede eliminar el progreso porque esta "
        "relacionado con otros registros."
    )

    extra_context = {
        "titulo_pagina": "Eliminar progreso",
    }
