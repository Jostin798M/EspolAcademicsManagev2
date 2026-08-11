from django.urls import path
from django.views.generic import RedirectView

from .views import (
    UsuarioCreateView,
    UsuarioDeleteView,
    UsuarioDetailView,
    UsuarioListView,
    UsuarioUpdateView,
)

app_name = "accounts"


urlpatterns = [
    # Pagina inicial de la aplicacion accounts
    path(
        "",
        RedirectView.as_view(
            pattern_name="accounts:usuario_lista",
            permanent=False,
        ),
        name="inicio",
    ),

    # ========================================================
    # URLs DE USUARIOS
    # ========================================================

    path(
        "usuarios/",
        UsuarioListView.as_view(),
        name="usuario_lista",
    ),

    path(
        "usuarios/nuevo/",
        UsuarioCreateView.as_view(),
        name="usuario_crear",
    ),

    path(
        "usuarios/<int:pk>/",
        UsuarioDetailView.as_view(),
        name="usuario_detalle",
    ),

    path(
        "usuarios/<int:pk>/editar/",
        UsuarioUpdateView.as_view(),
        name="usuario_editar",
    ),

    path(
        "usuarios/<int:pk>/eliminar/",
        UsuarioDeleteView.as_view(),
        name="usuario_eliminar",
    ),
]
