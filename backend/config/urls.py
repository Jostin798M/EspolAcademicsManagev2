from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from .views import PanelInicioView, login_sitio, pagina_antigua, pagina_sitio

FRONTEND = settings.FRONTEND_DIR

urlpatterns = [
    path('admin/', admin.site.urls),

    # Panel CRUD con vistas genericas de Django (Taller 3)
    path('panel/', PanelInicioView.as_view(), name='panel_inicio'),
    path('accounts/', include('accounts.urls')),
    path('cursos/', include('cursos.urls')),
    path('evaluaciones/', include('evaluaciones.urls')),
    path('reportes/', include('reportes.urls')),

    # API publica de consulta externa (JSON)
    path('api/', include('api.urls')),

    # ── Sitio web, con direcciones limpias (sin .html) ──────────────────────
    # La raiz y el antiguo index.html llevan a /login.
    re_path(r'^$', RedirectView.as_view(url='/login', permanent=False)),
    re_path(r'^index\.html$', RedirectView.as_view(url='/login', permanent=False)),

    path('login', login_sitio, name='login_sitio'),
    re_path(r'^login/$', RedirectView.as_view(url='/login', permanent=False)),

    # Las direcciones .html de antes redirigen a la limpia equivalente,
    # para que ningun enlace guardado se quede colgado.
    re_path(
        r'^pages/(?P<carpeta>[\w-]+)/(?P<pagina>[\w-]+)\.html$',
        pagina_antigua,
    ),

    # /superadmin/dashboard, /profesor/curso, /estudiante/quiz ...
    path('<slug:seccion>/<slug:pagina>', pagina_sitio, name='pagina_sitio'),

    # Recursos del frontend (css/, js/, imagenes)
    re_path(r'^(?P<path>.*)$', serve, {'document_root': FRONTEND}),
]
