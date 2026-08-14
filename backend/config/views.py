"""Vistas generales del proyecto (panel de gestion academica y sitio)."""
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.static import serve

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


# ── Paginas del sitio (frontend) con direcciones limpias ─────────────────────
# El sitio se navega con direcciones sin extension: /login,
# /superadmin/dashboard, /profesor/curso?id=3 ... En lugar de exponer los
# archivos .html sueltos, cada direccion sirve su archivo desde pages/.
#
# La carpeta del rol ADMIN se publica como "facultad" porque /admin/ ya es
# el panel de administracion de Django.

SECCIONES = {
    'superadmin': 'superadmin',
    'facultad': 'admin',
    'profesor': 'profesor',
    'estudiante': 'estudiante',
}

# Direccion limpia de cada carpeta real, para redirigir los .html antiguos.
CARPETAS = {carpeta: seccion for seccion, carpeta in SECCIONES.items()}


def login_sitio(request):
    """/login — la pantalla de entrada (index.html)."""
    return serve(request, 'index.html', document_root=settings.FRONTEND_DIR)


def pagina_sitio(request, seccion, pagina):
    """/<seccion>/<pagina> — cualquier pantalla del sitio."""
    carpeta = SECCIONES.get(seccion)

    if carpeta is None:
        raise Http404(f'La seccion "{seccion}" no existe.')

    relativa = f'pages/{carpeta}/{pagina}.html'

    if not (settings.FRONTEND_DIR / relativa).is_file():
        raise Http404(f'La pagina "/{seccion}/{pagina}" no existe.')

    return serve(request, relativa, document_root=settings.FRONTEND_DIR)


def pagina_antigua(request, carpeta, pagina):
    """Las direcciones .html de antes llevan a la direccion limpia."""
    seccion = CARPETAS.get(carpeta)

    if seccion is None:
        raise Http404(f'La carpeta "{carpeta}" no existe.')

    destino = f'/{seccion}/{pagina}'
    consulta = request.META.get('QUERY_STRING', '')

    return redirect(f'{destino}?{consulta}' if consulta else destino)
