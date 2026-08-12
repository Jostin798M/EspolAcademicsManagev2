from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from .views import PanelInicioView

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

    # Raiz -> index.html (login del frontend)
    re_path(r'^$', serve, {'document_root': FRONTEND, 'path': 'index.html'}),

    # Resto de archivos del frontend (css/, js/, pages/, imagenes)
    re_path(r'^(?P<path>.*)$', serve, {'document_root': FRONTEND}),
]
