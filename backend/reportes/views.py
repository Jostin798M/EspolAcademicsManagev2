"""
Vistas del modulo REPORTES.

Presenta el tablero de indicadores academicos y permite exportar el
resultado a CSV y a PDF respetando los filtros seleccionados.
"""
import csv
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from cursos.models import Curso, Facultad

from .servicios import construir_reporte


class FiltrosReporteMixin:
    """Lee los filtros de la barra superior del tablero."""

    def leer_filtros(self):
        facultad_id = self.request.GET.get('facultad') or None
        estado = self.request.GET.get('estado') or None

        if estado not in dict(Curso.Estado.choices):
            estado = None

        return facultad_id, estado


class TableroView(LoginRequiredMixin, FiltrosReporteMixin, TemplateView):
    """Tablero con los indicadores y los graficos."""

    template_name = "reportes/tablero.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facultad_id, estado = self.leer_filtros()

        reporte = construir_reporte(facultad_id, estado)

        context.update(reporte)
        context.update({
            'titulo_pagina': 'Reportes academicos',
            'facultades': Facultad.objects.all().order_by('codigo'),
            'estados_disponibles': Curso.Estado.choices,
            'facultad_seleccionada': facultad_id,
            'estado_seleccionado': estado,
            'generado': timezone.localtime(),
        })

        # Series listas para Chart.js.
        # Se entrega el diccionario tal cual: el filtro json_script del
        # template es el que lo serializa (si se serializara aqui, el
        # template lo codificaria por segunda vez).
        context['datos_graficos'] = {
            'facultades': {
                'etiquetas': [f['etiqueta'] for f in reporte['por_facultad']],
                'valores': [f['valor'] for f in reporte['por_facultad']],
            },
            'promedios': {
                'etiquetas': [p['etiqueta'] for p in reporte['promedios']],
                'valores': [float(p['valor']) for p in reporte['promedios']],
            },
            'entregas': {
                'etiquetas': [e['etiqueta'] for e in reporte['entregas']],
                'valores': [e['valor'] for e in reporte['entregas']],
            },
            'estados_curso': {
                'etiquetas': [e['etiqueta'] for e in reporte['estados_curso']],
                'valores': [e['valor'] for e in reporte['estados_curso']],
            },
        }

        return context


class ExportarCSVView(LoginRequiredMixin, FiltrosReporteMixin, View):
    """Descarga el reporte completo en formato CSV."""

    def get(self, request, *args, **kwargs):
        facultad_id, estado = self.leer_filtros()
        reporte = construir_reporte(facultad_id, estado)

        marca = datetime.now().strftime('%Y%m%d_%H%M')
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="reporte_academico_{marca}.csv"'
        )
        response.write('﻿')  # BOM para que Excel respete los acentos

        escritor = csv.writer(response, delimiter=';')

        escritor.writerow(['REPORTE ACADEMICO - ESPOL ACADEMICS'])
        escritor.writerow(['Generado', timezone.localtime().strftime('%d/%m/%Y %H:%M')])
        escritor.writerow([])

        resumen = reporte['resumen']
        escritor.writerow(['RESUMEN GENERAL'])
        escritor.writerow(['Indicador', 'Valor'])
        escritor.writerow(['Cursos registrados', resumen['total_cursos']])
        escritor.writerow(['Cursos activos', resumen['cursos_activos']])
        escritor.writerow(['Estudiantes inscritos', resumen['total_estudiantes']])
        escritor.writerow(['Tareas creadas', resumen['total_tareas']])
        escritor.writerow(['Quizzes creados', resumen['total_quizzes']])
        escritor.writerow(['Tasa de entrega (%)', resumen['tasa_entrega']])
        escritor.writerow(['Promedio general', resumen['promedio_general'] or 'Sin datos'])
        escritor.writerow(['Entregas por calificar', resumen['pendientes_calificar']])
        escritor.writerow([])

        escritor.writerow(['ESTUDIANTES POR FACULTAD'])
        escritor.writerow(['Codigo', 'Facultad', 'Cursos', 'Estudiantes'])
        for fila in reporte['por_facultad']:
            escritor.writerow([fila['etiqueta'], fila['detalle'], fila['cursos'], fila['valor']])
        escritor.writerow([])

        escritor.writerow(['PROMEDIO POR CURSO'])
        escritor.writerow(['Codigo', 'Curso', 'Facultad', 'Entregas calificadas', 'Promedio'])
        for fila in reporte['promedios']:
            escritor.writerow([
                fila['etiqueta'], fila['detalle'], fila['facultad'],
                fila['calificadas'],
                'Sin datos' if fila['sin_datos'] else fila['valor'],
            ])
        escritor.writerow([])

        escritor.writerow(['AVANCE POR ESTUDIANTE'])
        escritor.writerow([
            'Estudiante', 'Correo', 'Curso',
            'Modulos completados', 'Modulos totales', 'Avance (%)', 'Promedio',
        ])
        for fila in reporte['avance']:
            escritor.writerow([
                fila['estudiante'], fila['correo'], fila['curso'],
                fila['modulos_completados'], fila['modulos_totales'],
                fila['avance'], fila['promedio'] if fila['promedio'] is not None else 'Sin nota',
            ])

        return response


class ExportarPDFView(LoginRequiredMixin, FiltrosReporteMixin, TemplateView):
    """
    Version imprimible del reporte.

    Se abre en el navegador con el dialogo de impresion, lo que permite
    guardarlo como PDF sin depender de librerias externas en el servidor.
    """

    template_name = "reportes/reporte_pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facultad_id, estado = self.leer_filtros()

        context.update(construir_reporte(facultad_id, estado))
        context.update({
            'generado': timezone.localtime(),
            'facultad': Facultad.objects.filter(pk=facultad_id).first() if facultad_id else None,
            'estado_seleccionado': estado,
        })
        return context
