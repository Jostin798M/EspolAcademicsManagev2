from django.urls import path
from django.views.generic import RedirectView

from .views import (
    CursoCreateView,
    CursoDeleteView,
    CursoDetailView,
    CursoListView,
    CursoUpdateView,
    FacultadCreateView,
    FacultadDeleteView,
    FacultadDetailView,
    FacultadListView,
    FacultadUpdateView,
    FormulaComponenteCreateView,
    FormulaComponenteDeleteView,
    FormulaComponenteDetailView,
    FormulaComponenteListView,
    FormulaComponenteUpdateView,
    InscripcionCreateView,
    InscripcionDeleteView,
    InscripcionDetailView,
    InscripcionListView,
    InscripcionUpdateView,
    MaterialCreateView,
    MaterialDeleteView,
    MaterialDetailView,
    MaterialListView,
    MaterialUpdateView,
    ModuloCreateView,
    ModuloDeleteView,
    ModuloDetailView,
    ModuloListView,
    ModuloUpdateView,
    ProgresoModuloCreateView,
    ProgresoModuloDeleteView,
    ProgresoModuloDetailView,
    ProgresoModuloListView,
    ProgresoModuloUpdateView,
)

app_name = "cursos"


urlpatterns = [
    # Pagina inicial de la aplicacion cursos
    path(
        "",
        RedirectView.as_view(
            pattern_name="cursos:facultad_lista",
            permanent=False,
        ),
        name="inicio",
    ),

    # ========================================================
    # URLs DE FACULTADES
    # ========================================================

    path(
        "facultades/",
        FacultadListView.as_view(),
        name="facultad_lista",
    ),

    path(
        "facultades/nuevo/",
        FacultadCreateView.as_view(),
        name="facultad_crear",
    ),

    path(
        "facultades/<int:pk>/",
        FacultadDetailView.as_view(),
        name="facultad_detalle",
    ),

    path(
        "facultades/<int:pk>/editar/",
        FacultadUpdateView.as_view(),
        name="facultad_editar",
    ),

    path(
        "facultades/<int:pk>/eliminar/",
        FacultadDeleteView.as_view(),
        name="facultad_eliminar",
    ),

    # ========================================================
    # URLs DE CURSOS
    # ========================================================

    path(
        "cursos/",
        CursoListView.as_view(),
        name="curso_lista",
    ),

    path(
        "cursos/nuevo/",
        CursoCreateView.as_view(),
        name="curso_crear",
    ),

    path(
        "cursos/<int:pk>/",
        CursoDetailView.as_view(),
        name="curso_detalle",
    ),

    path(
        "cursos/<int:pk>/editar/",
        CursoUpdateView.as_view(),
        name="curso_editar",
    ),

    path(
        "cursos/<int:pk>/eliminar/",
        CursoDeleteView.as_view(),
        name="curso_eliminar",
    ),

    # ========================================================
    # URLs DE COMPONENTES DE LA FORMULA
    # ========================================================

    path(
        "formula/",
        FormulaComponenteListView.as_view(),
        name="componente_lista",
    ),

    path(
        "formula/nuevo/",
        FormulaComponenteCreateView.as_view(),
        name="componente_crear",
    ),

    path(
        "formula/<int:pk>/",
        FormulaComponenteDetailView.as_view(),
        name="componente_detalle",
    ),

    path(
        "formula/<int:pk>/editar/",
        FormulaComponenteUpdateView.as_view(),
        name="componente_editar",
    ),

    path(
        "formula/<int:pk>/eliminar/",
        FormulaComponenteDeleteView.as_view(),
        name="componente_eliminar",
    ),

    # ========================================================
    # URLs DE INSCRIPCIONES
    # ========================================================

    path(
        "inscripciones/",
        InscripcionListView.as_view(),
        name="inscripcion_lista",
    ),

    path(
        "inscripciones/nuevo/",
        InscripcionCreateView.as_view(),
        name="inscripcion_crear",
    ),

    path(
        "inscripciones/<int:pk>/",
        InscripcionDetailView.as_view(),
        name="inscripcion_detalle",
    ),

    path(
        "inscripciones/<int:pk>/editar/",
        InscripcionUpdateView.as_view(),
        name="inscripcion_editar",
    ),

    path(
        "inscripciones/<int:pk>/eliminar/",
        InscripcionDeleteView.as_view(),
        name="inscripcion_eliminar",
    ),

    # ========================================================
    # URLs DE MODULOS
    # ========================================================

    path(
        "modulos/",
        ModuloListView.as_view(),
        name="modulo_lista",
    ),

    path(
        "modulos/nuevo/",
        ModuloCreateView.as_view(),
        name="modulo_crear",
    ),

    path(
        "modulos/<int:pk>/",
        ModuloDetailView.as_view(),
        name="modulo_detalle",
    ),

    path(
        "modulos/<int:pk>/editar/",
        ModuloUpdateView.as_view(),
        name="modulo_editar",
    ),

    path(
        "modulos/<int:pk>/eliminar/",
        ModuloDeleteView.as_view(),
        name="modulo_eliminar",
    ),

    # ========================================================
    # URLs DE MATERIALES
    # ========================================================

    path(
        "materiales/",
        MaterialListView.as_view(),
        name="material_lista",
    ),

    path(
        "materiales/nuevo/",
        MaterialCreateView.as_view(),
        name="material_crear",
    ),

    path(
        "materiales/<int:pk>/",
        MaterialDetailView.as_view(),
        name="material_detalle",
    ),

    path(
        "materiales/<int:pk>/editar/",
        MaterialUpdateView.as_view(),
        name="material_editar",
    ),

    path(
        "materiales/<int:pk>/eliminar/",
        MaterialDeleteView.as_view(),
        name="material_eliminar",
    ),

    # ========================================================
    # URLs DE PROGRESO DE MODULOS
    # ========================================================

    path(
        "progresos/",
        ProgresoModuloListView.as_view(),
        name="progreso_lista",
    ),

    path(
        "progresos/nuevo/",
        ProgresoModuloCreateView.as_view(),
        name="progreso_crear",
    ),

    path(
        "progresos/<int:pk>/",
        ProgresoModuloDetailView.as_view(),
        name="progreso_detalle",
    ),

    path(
        "progresos/<int:pk>/editar/",
        ProgresoModuloUpdateView.as_view(),
        name="progreso_editar",
    ),

    path(
        "progresos/<int:pk>/eliminar/",
        ProgresoModuloDeleteView.as_view(),
        name="progreso_eliminar",
    ),

]
