from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = (
        "id_usuario",
        "correo",
        "nombres",
        "apellidos",
        "identificacion",
        "rol",
        "estado",
    )

    search_fields = (
        "correo",
        "nombres",
        "apellidos",
        "identificacion",
    )

    list_filter = (
        "rol",
        "estado",
        "estado_civil",
    )

    ordering = (
        "apellidos",
        "nombres",
    )

    fieldsets = (
        (None, {
            "fields": (
                "correo",
                "password",
            ),
        }),
        ("Datos personales", {
            "fields": (
                "nombres",
                "apellidos",
                "identificacion",
                "telefono",
                "celular",
                "direccion",
                "estado_civil",
                "facultad",
            ),
        }),
        ("Estado y rol", {
            "fields": (
                "rol",
                "estado",
                "is_active",
                "is_staff",
                "is_superuser",
            ),
        }),
        ("Permisos", {
            "fields": (
                "groups",
                "user_permissions",
            ),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "correo",
                "nombres",
                "apellidos",
                "identificacion",
                "celular",
                "rol",
                "password1",
                "password2",
            ),
        }),
    )
