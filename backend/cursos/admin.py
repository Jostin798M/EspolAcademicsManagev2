from django.contrib import admin

from .models import (
    Curso,
    Facultad,
    FormulaComponente,
    Inscripcion,
    Material,
    Modulo,
    ProgresoModulo,
)


@admin.register(Facultad)
class FacultadAdmin(admin.ModelAdmin):
    list_display = (
        "id_facultad",
        "codigo",
        "nombre",
        "admin",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = (
        "admin",
    )

    ordering = (
        "nombre",
    )

    list_select_related = (
        "admin",
    )


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = (
        "id_curso",
        "codigo",
        "nombre",
        "facultad",
        "profesor",
        "fecha_inicio",
        "fecha_fin",
        "estado",
    )

    search_fields = (
        "codigo",
        "nombre",
        "descripcion",
    )

    list_filter = (
        "facultad",
        "estado",
    )

    ordering = (
        "codigo",
    )

    list_select_related = (
        "facultad",
        "profesor",
    )

    date_hierarchy = "fecha_inicio"


@admin.register(FormulaComponente)
class FormulaComponenteAdmin(admin.ModelAdmin):
    list_display = (
        "id_componente",
        "curso",
        "componente",
        "porcentaje",
        "orden",
    )

    search_fields = (
        "componente",
        "curso__codigo",
    )

    list_filter = (
        "curso",
    )

    ordering = (
        "curso",
        "orden",
    )

    list_select_related = (
        "curso",
    )


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = (
        "id_inscripcion",
        "usuario",
        "curso",
        "rol_en_curso",
        "fecha",
    )

    search_fields = (
        "usuario__nombres",
        "usuario__apellidos",
        "curso__codigo",
    )

    list_filter = (
        "rol_en_curso",
        "curso",
    )

    ordering = (
        "curso",
        "usuario",
    )

    list_select_related = (
        "usuario",
        "curso",
    )


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = (
        "id_modulo",
        "curso",
        "orden",
        "titulo",
    )

    search_fields = (
        "titulo",
        "curso__codigo",
    )

    list_filter = (
        "curso",
    )

    ordering = (
        "curso",
        "orden",
    )

    list_select_related = (
        "curso",
    )


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "id_material",
        "titulo",
        "modulo",
        "tipo",
        "url",
    )

    search_fields = (
        "titulo",
        "modulo__titulo",
    )

    list_filter = (
        "tipo",
        "modulo",
    )

    ordering = (
        "titulo",
    )

    list_select_related = (
        "modulo",
    )


@admin.register(ProgresoModulo)
class ProgresoModuloAdmin(admin.ModelAdmin):
    list_display = (
        "id_progreso",
        "usuario",
        "modulo",
        "completado",
        "fecha",
    )

    search_fields = (
        "usuario__nombres",
        "usuario__apellidos",
        "modulo__titulo",
    )

    list_filter = (
        "completado",
        "modulo",
    )

    ordering = (
        "usuario",
        "modulo",
    )

    list_select_related = (
        "usuario",
        "modulo",
    )
