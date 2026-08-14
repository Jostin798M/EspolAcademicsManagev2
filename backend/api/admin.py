"""
Administracion de los tokens de la API.

Desde /admin/ un super administrador ve que aplicaciones tienen acceso y
puede revocarles el token. Los tokens no se crean aqui: se piden en
/api/auth/login/, porque el texto solo existe en el momento de generarlo.
"""
from django.contrib import admin

from .models import TokenApi


@admin.register(TokenApi)
class TokenApiAdmin(admin.ModelAdmin):
    list_display = (
        'prefijo',
        'usuario',
        'aplicacion',
        'creado',
        'expira',
        'ultimo_uso',
        'revocado',
    )
    list_filter = ('revocado', 'creado')
    search_fields = ('prefijo', 'aplicacion', 'usuario__correo')
    ordering = ('-creado',)
    date_hierarchy = 'creado'
    readonly_fields = (
        'usuario',
        'aplicacion',
        'prefijo',
        'huella',
        'creado',
        'expira',
        'ultimo_uso',
        'ip_origen',
    )
    actions = ('revocar_tokens',)

    def has_add_permission(self, request):
        return False

    @admin.action(description='Revocar los tokens seleccionados')
    def revocar_tokens(self, request, queryset):
        revocados = queryset.filter(revocado=False).update(revocado=True)
        self.message_user(request, f'{revocados} token(s) revocado(s).')
