from django.urls import path

from .views import ExportarCSVView, ExportarPDFView, TableroView

app_name = "reportes"


urlpatterns = [
    path(
        "",
        TableroView.as_view(),
        name="tablero",
    ),

    path(
        "exportar/csv/",
        ExportarCSVView.as_view(),
        name="exportar_csv",
    ),

    path(
        "exportar/pdf/",
        ExportarPDFView.as_view(),
        name="exportar_pdf",
    ),
]
