"""
Contrato entre la API y las aplicaciones que la consumen.

Las pruebas de tests_permisos.py comprueban que la API decide bien. Estas
comprueban otra cosa distinta y igual de facil de romper: que la respuesta
trae los campos con los nombres que la app movil y la web leen.

Un renombrado inocente aqui -de "rol_efectivo" a "rol", por ejemplo- no
rompe ninguna prueba de permisos y sin embargo deja la app movil con la
pantalla en blanco. Por eso se listan los campos uno a uno, tal como los
lee cada pantalla, con el nombre de esa pantalla al lado.
"""
import json
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from cursos.models import Curso, Facultad, Inscripcion, Modulo
from evaluaciones.models import Entrega, Quiz, Tarea


class ContratoBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.facultad = Facultad.objects.create(nombre='Electrica', codigo='FIEC')

        def persona(correo, cedula, rol=Usuario.Rol.USER):
            return Usuario.objects.create_user(
                correo=correo, password='clave-de-prueba',
                nombres='Nom', apellidos='Ape', identificacion=cedula,
                celular='0990000000', rol=rol, facultad=cls.facultad,
            )

        cls.superadmin = persona('jefe@espol.edu.ec', '0900000001', Usuario.Rol.SUPERADMIN)
        cls.profesor = persona('profe@espol.edu.ec', '0900000003')
        cls.estudiante = persona('alumno@espol.edu.ec', '0900000005')

        cls.curso = Curso.objects.create(
            nombre='Programacion Web', codigo='WEB101',
            facultad=cls.facultad, profesor=cls.profesor,
            fecha_inicio=date(2026, 5, 1), fecha_fin=date(2026, 9, 30),
        )

        Inscripcion.objects.create(
            usuario=cls.profesor, curso=cls.curso,
            rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
        )
        Inscripcion.objects.create(
            usuario=cls.estudiante, curso=cls.curso,
            rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
        )

        cls.modulo = Modulo.objects.create(curso=cls.curso, titulo='Intro', orden=1)
        cls.tarea = Tarea.objects.create(
            curso=cls.curso, titulo='Practica 1', descripcion='Primera.',
            puntaje_maximo=10, fecha_limite=timezone.now() + timedelta(days=7),
        )
        Quiz.objects.create(
            curso=cls.curso, titulo='Quiz 1',
            fecha_limite=timezone.now() + timedelta(days=14),
        )
        cls.entrega = Entrega.objects.create(
            tarea=cls.tarea, usuario=cls.estudiante,
            estado=Entrega.Estado.ENTREGADO, texto='Hecha',
        )

    def datos(self, url):
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200, f'{url} respondio {respuesta.status_code}')
        return json.loads(respuesta.content)['datos']

    def tiene(self, diccionario, campos, donde):
        for campo in campos:
            self.assertIn(campo, diccionario, f'Falta "{campo}" en {donde}')


class ContratoDelLogin(ContratoBase):
    """Lo que la app guarda nada mas entrar (src/contexto/Sesion.js)."""

    def login(self, correo):
        respuesta = self.client.post(
            reverse('api:auth_login'),
            data=json.dumps({'correo': correo, 'password': 'clave-de-prueba'}),
            content_type='application/json',
        )
        self.assertEqual(respuesta.status_code, 200)
        return json.loads(respuesta.content)['datos']

    def test_el_login_trae_lo_que_la_app_guarda(self):
        datos = self.login('alumno@espol.edu.ec')

        self.tiene(datos, ['token', 'usuario', 'rol', 'permisos', 'panel',
                           'autorizado', 'rol_del_token'], 'la respuesta del login')

    def test_la_ficha_del_usuario_trae_lo_que_pinta_la_app(self):
        usuario = self.login('alumno@espol.edu.ec')['usuario']

        self.tiene(usuario, ['id_usuario', 'id', 'nombres', 'apellidos',
                             'nombre_completo', 'iniciales', 'correo', 'rol',
                             'rol_efectivo', 'rol_etiqueta', 'estado',
                             'es_superadmin', 'facultad'],
                   'usuario del login (Cuenta.js, Panel.js)')

    def test_los_permisos_tienen_la_forma_que_lee_puede(self):
        """useSesion().puede() lee permisos.recursos[recurso][accion]."""
        permisos = self.login('profe@espol.edu.ec')['permisos']

        self.tiene(permisos, ['rol', 'rol_etiqueta', 'alcances', 'recursos'],
                   'bloque de permisos')

        for recurso in ('cursos', 'tareas', 'entregas', 'usuarios',
                        'modulos', 'materiales', 'inscripciones', 'quizzes'):
            self.tiene(permisos['recursos'], [recurso], 'permisos.recursos')
            self.tiene(permisos['recursos'][recurso],
                       ['etiqueta', 'ver', 'crear', 'editar', 'eliminar', 'acciones'],
                       f'permisos.recursos.{recurso}')

    def test_verificar_devuelve_lo_mismo_que_el_login(self):
        """Al arrancar, la app rehidrata la sesion desde aqui."""
        self.client.force_login(self.profesor)
        datos = self.datos(reverse('api:auth_verificar'))

        self.tiene(datos, ['autorizado', 'via', 'usuario', 'rol', 'permisos'],
                   'auth/verificar')


class ContratoDelPanel(ContratoBase):
    """Los campos que lee cada bloque de src/pantallas/Panel.js."""

    def panel(self, usuario):
        self.client.force_login(usuario)
        return self.datos(reverse('api:mi_panel'))

    def test_panel_de_estudiante(self):
        datos = self.panel(self.estudiante)

        self.assertEqual(datos['tipo'], 'estudiante')
        self.tiene(datos, ['titulo', 'rol', 'rol_etiqueta', 'indicadores',
                           'mis_cursos', 'proximas_tareas', 'ultimas_notas'],
                   'panel de estudiante')
        self.tiene(datos['indicadores'],
                   ['cursos', 'tareas', 'entregadas', 'pendientes', 'promedio',
                    'avance', 'modulos_completados', 'modulos_totales'],
                   'indicadores del estudiante')
        self.tiene(datos['proximas_tareas'][0],
                   ['id_tarea', 'titulo', 'curso', 'fecha_limite',
                    'dias_restantes', 'entregada'],
                   'proximas_tareas del estudiante')

    def test_panel_de_profesor(self):
        datos = self.panel(self.profesor)

        self.assertEqual(datos['tipo'], 'profesor')
        self.tiene(datos, ['indicadores', 'mis_cursos', 'por_calificar',
                           'proximas_tareas', 'estado_entregas'],
                   'panel de profesor')
        self.tiene(datos['indicadores'],
                   ['cursos', 'estudiantes', 'tareas', 'quizzes',
                    'por_calificar', 'promedio_general'],
                   'indicadores del profesor')
        self.tiene(datos['por_calificar'][0],
                   ['id_entrega', 'estudiante', 'tarea', 'tarea_titulo', 'curso'],
                   'por_calificar del profesor')

    def test_panel_de_superadmin(self):
        datos = self.panel(self.superadmin)

        self.assertEqual(datos['tipo'], 'superadmin')
        self.tiene(datos, ['indicadores', 'usuarios', 'por_facultad',
                           'cursos_por_estado', 'estado_entregas',
                           'ultimos_usuarios'],
                   'panel de superadmin')
        self.tiene(datos['usuarios'], ['total', 'activos', 'inactivos', 'por_rol'],
                   'usuarios del panel de superadmin')

    def test_las_tarjetas_de_curso_del_panel(self):
        datos = self.panel(self.profesor)

        self.tiene(datos['mis_cursos'][0],
                   ['id_curso', 'codigo', 'nombre', 'estado',
                    'total_estudiantes', 'total_tareas'],
                   'mis_cursos del panel')


class ContratoDeLasPantallas(ContratoBase):
    """Los campos que leen las demas pantallas de la app."""

    def test_mis_cursos_trae_el_bloque_puedo(self):
        """Cursos.js decide con esto si pinta la insignia de editable."""
        self.client.force_login(self.profesor)
        datos = self.datos(reverse('api:mis_cursos'))

        curso = datos[0]
        self.tiene(curso, ['id_curso', 'codigo', 'nombre', 'estado', 'facultad',
                           'profesor', 'total_estudiantes', 'total_tareas', 'puedo'],
                   'mi/cursos')
        self.assertIsInstance(curso['puedo'].get('tareas'), list)

    def test_el_detalle_del_curso_trae_puedo_y_su_contenido(self):
        """CursoDetalle.js dibuja sus botones leyendo curso.puedo."""
        self.client.force_login(self.profesor)
        datos = self.datos(reverse('api:curso_detalle', kwargs={'codigo': 'WEB101'}))

        self.tiene(datos, ['codigo', 'nombre', 'descripcion', 'estado',
                           'fecha_inicio', 'fecha_fin', 'facultad', 'profesor',
                           'formula', 'modulos', 'tareas', 'quizzes', 'puedo'],
                   'detalle del curso')
        self.tiene(datos['modulos'][0], ['id_modulo', 'titulo', 'orden', 'materiales'],
                   'modulos del curso')
        self.tiene(datos['tareas'][0], ['id_tarea', 'titulo', 'puntaje_maximo',
                                        'fecha_limite'],
                   'tareas del curso')

    def test_mis_tareas_para_un_estudiante(self):
        self.client.force_login(self.estudiante)
        datos = self.datos(reverse('api:mis_tareas'))

        self.tiene(datos[0], ['id_tarea', 'titulo', 'curso', 'fecha_limite',
                              'puntaje_maximo', 'entregada', 'nota', 'id_entrega'],
                   'mi/tareas de un estudiante (Tareas.js)')

    def test_mis_tareas_para_un_profesor(self):
        self.client.force_login(self.profesor)
        datos = self.datos(reverse('api:mis_tareas'))

        self.tiene(datos[0], ['id_tarea', 'titulo', 'curso', 'recibidas',
                              'sin_calificar'],
                   'mi/tareas de un profesor (Tareas.js)')

    def test_las_entregas_que_lee_la_pantalla_de_tarea(self):
        self.client.force_login(self.profesor)
        datos = self.datos(
            reverse('api:tarea_entregas', kwargs={'id_tarea': self.tarea.pk}),
        )

        self.tiene(datos[0], ['id_entrega', 'tarea_titulo', 'curso', 'estado',
                              'fecha', 'texto', 'link', 'nota', 'puntaje_maximo',
                              'comentario', 'calificada', 'estudiante'],
                   'entregas de una tarea (TareaDetalle.js)')

    def test_el_estudiante_ve_su_entrega_sin_el_nombre(self):
        self.client.force_login(self.estudiante)
        datos = self.datos(
            reverse('api:tarea_entregas', kwargs={'id_tarea': self.tarea.pk}),
        )

        self.assertEqual(len(datos), 1)
        self.assertNotIn('estudiante', datos[0])
        self.tiene(datos[0], ['calificada', 'nota', 'puntaje_maximo'],
                   'mi entrega (TareaDetalle.js)')

    def test_la_lista_de_personas(self):
        self.client.force_login(self.superadmin)
        datos = self.datos(reverse('api:usuarios'))

        self.tiene(datos[0], ['id_usuario', 'nombre_completo', 'correo', 'rol',
                              'estado', 'facultad'],
                   'usuarios (Usuarios.js)')

    def test_mis_permisos_trae_el_alcance_en_numeros(self):
        self.client.force_login(self.profesor)
        datos = self.datos(reverse('api:mis_permisos'))

        self.tiene(datos, ['permisos', 'alcance'], 'mi/permisos')
        self.tiene(datos['alcance'], ['cursos', 'facultades'], 'mi/permisos.alcance')

    def test_las_facultades_que_llenan_los_filtros(self):
        self.client.force_login(self.profesor)
        datos = self.datos(reverse('api:facultades'))

        self.tiene(datos[0], ['id_facultad', 'codigo', 'nombre'],
                   'facultades (Cursos.js, CursoForm.js)')
