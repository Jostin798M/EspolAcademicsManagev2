"""
Pruebas del sistema de roles: quien puede que, y sobre que datos.

Se monta una facultad con dos cursos y cuatro personas -un super
administrador, un administrador de facultad, un profesor y un estudiante- y
se comprueba lo mismo desde los cuatro lados. Casi todas las pruebas tienen
la misma forma: la misma llamada, hecha por cuatro personas distintas, tiene
que dar cuatro resultados distintos.

Lo que mas importa comprobar aqui no es que el permitido pueda, sino que el
que no debe no pueda: un profesor no toca el curso del de al lado, y un
estudiante no ve mas ficha que la suya.
"""
import json
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from api import permisos
from cursos.models import Curso, Facultad, Inscripcion, Material, Modulo
from evaluaciones.models import Entrega, Quiz, Tarea


class BaseRoles(TestCase):
    """Un mundo pequeno pero completo: dos facultades y dos cursos."""

    @classmethod
    def setUpTestData(cls):
        cls.fiec = Facultad.objects.create(nombre='Electrica y Computacion', codigo='FIEC')
        cls.fimcp = Facultad.objects.create(nombre='Mecanica', codigo='FIMCP')

        def persona(correo, nombres, apellidos, cedula, rol=Usuario.Rol.USER,
                    facultad=None):
            return Usuario.objects.create_user(
                correo=correo,
                password='clave-de-prueba',
                nombres=nombres,
                apellidos=apellidos,
                identificacion=cedula,
                celular='0990000000',
                rol=rol,
                facultad=facultad,
            )

        cls.superadmin = persona(
            'jefe@espol.edu.ec', 'Sara', 'Jefa', '0900000001',
            Usuario.Rol.SUPERADMIN,
        )
        cls.admin = persona(
            'decano@espol.edu.ec', 'Luis', 'Decano', '0900000002',
            Usuario.Rol.ADMIN, cls.fiec,
        )
        cls.profesor = persona(
            'profe@espol.edu.ec', 'Ana', 'Torres', '0900000003',
            facultad=cls.fiec,
        )
        cls.otro_profesor = persona(
            'otro@espol.edu.ec', 'Beto', 'Mora', '0900000004',
            facultad=cls.fiec,
        )
        cls.estudiante = persona(
            'alumno@espol.edu.ec', 'Carla', 'Vera', '0900000005',
            facultad=cls.fiec,
        )
        cls.ajeno = persona(
            'ajeno@espol.edu.ec', 'Dora', 'Paz', '0900000006',
            facultad=cls.fimcp,
        )

        cls.fiec.admin = cls.admin
        cls.fiec.save()

        cls.inicio = date(2026, 5, 1)
        cls.fin = date(2026, 9, 30)

        cls.curso = Curso.objects.create(
            nombre='Programacion Web', codigo='WEB101',
            facultad=cls.fiec, profesor=cls.profesor,
            fecha_inicio=cls.inicio, fecha_fin=cls.fin,
        )
        cls.curso_ajeno = Curso.objects.create(
            nombre='Termodinamica', codigo='TER101',
            facultad=cls.fimcp, profesor=cls.otro_profesor,
            fecha_inicio=cls.inicio, fecha_fin=cls.fin,
        )

        Inscripcion.objects.create(
            usuario=cls.profesor, curso=cls.curso,
            rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
        )
        Inscripcion.objects.create(
            usuario=cls.estudiante, curso=cls.curso,
            rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
        )
        Inscripcion.objects.create(
            usuario=cls.otro_profesor, curso=cls.curso_ajeno,
            rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
        )

        cls.modulo = Modulo.objects.create(
            curso=cls.curso, titulo='Introduccion', orden=1,
        )
        cls.tarea = Tarea.objects.create(
            curso=cls.curso, titulo='Practica 1', descripcion='Primera practica.',
            puntaje_maximo=10,
            fecha_limite=timezone.now() + timedelta(days=7),
        )
        cls.quiz = Quiz.objects.create(
            curso=cls.curso, titulo='Quiz 1',
            fecha_limite=timezone.now() + timedelta(days=14),
        )

    def cuerpo(self, respuesta):
        return json.loads(respuesta.content)

    def como(self, usuario):
        """Entra como esa persona y devuelve el cliente listo."""
        self.client.force_login(usuario)
        return self.client

    def enviar(self, metodo, url, datos=None):
        return getattr(self.client, metodo)(
            url,
            data=json.dumps(datos or {}),
            content_type='application/json',
        )


class RolEfectivoTest(BaseRoles):
    """La traduccion del campo rol al rol con el que trabaja la API."""

    def test_el_campo_rol_manda_cuando_lo_dice(self):
        self.assertEqual(permisos.rol_efectivo(self.superadmin), permisos.SUPERADMIN)
        self.assertEqual(permisos.rol_efectivo(self.admin), permisos.ADMIN)

    def test_un_user_que_dicta_es_profesor(self):
        self.assertEqual(permisos.rol_efectivo(self.profesor), permisos.PROFESOR)

    def test_un_user_que_solo_cursa_es_estudiante(self):
        self.assertEqual(permisos.rol_efectivo(self.estudiante), permisos.ESTUDIANTE)

    def test_un_user_sin_cursos_entra_como_estudiante(self):
        """Sin inscripciones no hay nada que dictar: el defecto es cursar."""
        self.assertEqual(permisos.rol_efectivo(self.ajeno), permisos.ESTUDIANTE)


class AlcanceDeCursosTest(BaseRoles):
    """Cada rol ve una lista de cursos distinta en la misma direccion."""

    def test_el_superadmin_los_ve_todos(self):
        cuerpo = self.cuerpo(self.como(self.superadmin).get(reverse('api:cursos')))

        self.assertEqual(cuerpo['paginacion']['total'], 2)

    def test_el_admin_ve_solo_los_de_su_facultad(self):
        cuerpo = self.cuerpo(self.como(self.admin).get(reverse('api:cursos')))

        self.assertEqual(cuerpo['paginacion']['total'], 1)
        self.assertEqual(cuerpo['datos'][0]['codigo'], 'WEB101')

    def test_el_profesor_ve_solo_los_que_dicta(self):
        cuerpo = self.cuerpo(self.como(self.profesor).get(reverse('api:cursos')))

        self.assertEqual(cuerpo['paginacion']['total'], 1)
        self.assertEqual(cuerpo['datos'][0]['codigo'], 'WEB101')

    def test_el_estudiante_ve_solo_los_que_cursa(self):
        cuerpo = self.cuerpo(self.como(self.estudiante).get(reverse('api:cursos')))

        self.assertEqual(cuerpo['paginacion']['total'], 1)

    def test_un_curso_de_otra_facultad_responde_403_y_no_404(self):
        """
        Se distingue "no existe" de "no es tuyo" a proposito: el 404 diria
        que el curso no existe, y eso seria mentira.
        """
        url = reverse('api:curso_detalle', kwargs={'codigo': 'TER101'})
        respuesta = self.como(self.profesor).get(url)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'fuera_de_alcance')


class AlcanceDeUsuariosTest(BaseRoles):
    """El circulo de personas que alcanza a ver cada rol."""

    def test_el_superadmin_ve_el_directorio_entero(self):
        cuerpo = self.cuerpo(self.como(self.superadmin).get(reverse('api:usuarios')))

        self.assertEqual(cuerpo['paginacion']['total'], Usuario.objects.count())

    def test_el_admin_ve_a_los_de_su_facultad(self):
        cuerpo = self.cuerpo(self.como(self.admin).get(reverse('api:usuarios')))
        correos = {fila['correo'] for fila in cuerpo['datos']}

        self.assertIn(self.estudiante.correo, correos)
        self.assertNotIn(self.ajeno.correo, correos)

    def test_el_profesor_ve_a_sus_inscritos_y_a_si_mismo(self):
        cuerpo = self.cuerpo(self.como(self.profesor).get(reverse('api:usuarios')))
        correos = {fila['correo'] for fila in cuerpo['datos']}

        self.assertEqual(correos, {self.profesor.correo, self.estudiante.correo})

    def test_el_estudiante_solo_se_ve_a_si_mismo(self):
        cuerpo = self.cuerpo(self.como(self.estudiante).get(reverse('api:usuarios')))

        self.assertEqual(cuerpo['paginacion']['total'], 1)
        self.assertEqual(cuerpo['datos'][0]['correo'], self.estudiante.correo)

    def test_el_estudiante_no_abre_la_ficha_de_otro_por_su_id(self):
        """Lo que no sale en su listado tampoco se alcanza adivinando el id."""
        url = reverse('api:usuario_detalle', kwargs={'id_usuario': self.profesor.pk})

        self.assertEqual(self.como(self.estudiante).get(url).status_code, 404)


class CrearCursoTest(BaseRoles):
    """Quien abre cursos y donde."""

    def datos_curso(self, codigo='NUE101', facultad='FIEC'):
        return {
            'nombre': 'Curso Nuevo',
            'codigo': codigo,
            'facultad': facultad,
            'profesor': self.profesor.correo,
            'fecha_inicio': '2026-05-01',
            'fecha_fin': '2026-09-30',
        }

    def test_el_superadmin_crea_en_cualquier_facultad(self):
        self.como(self.superadmin)
        respuesta = self.enviar('post', reverse('api:cursos'),
                                self.datos_curso(facultad='FIMCP'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self.cuerpo(respuesta)['creado'])

    def test_el_admin_crea_en_la_suya(self):
        self.como(self.admin)
        respuesta = self.enviar('post', reverse('api:cursos'), self.datos_curso())

        self.assertEqual(respuesta.status_code, 200)

    def test_el_admin_no_crea_en_la_facultad_de_al_lado(self):
        self.como(self.admin)
        respuesta = self.enviar('post', reverse('api:cursos'),
                                self.datos_curso(facultad='FIMCP'))

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'fuera_de_alcance')

    def test_el_profesor_no_crea_cursos(self):
        self.como(self.profesor)
        respuesta = self.enviar('post', reverse('api:cursos'), self.datos_curso())

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'sin_permiso')

    def test_el_estudiante_tampoco(self):
        self.como(self.estudiante)
        respuesta = self.enviar('post', reverse('api:cursos'), self.datos_curso())

        self.assertEqual(respuesta.status_code, 403)

    def test_un_codigo_repetido_avisa_en_lugar_de_reventar(self):
        self.como(self.superadmin)
        respuesta = self.enviar('post', reverse('api:cursos'),
                                self.datos_curso(codigo='WEB101'))

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'duplicado')

    def test_faltar_campos_los_enumera_todos_de_una_vez(self):
        self.como(self.superadmin)
        respuesta = self.enviar('post', reverse('api:cursos'), {'nombre': 'Solo esto'})
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            set(cuerpo['campos']),
            {'codigo', 'profesor', 'fecha_inicio', 'fecha_fin'},
        )

    def test_un_curso_no_puede_terminar_antes_de_empezar(self):
        self.como(self.superadmin)
        datos = self.datos_curso()
        datos['fecha_fin'] = '2026-01-01'

        respuesta = self.enviar('post', reverse('api:cursos'), datos)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.cuerpo(respuesta)['campo'], 'fecha_fin')


class EditarCursoTest(BaseRoles):
    """El profesor manda dentro de su curso, pero no sobre su marco."""

    def url(self, codigo='WEB101'):
        return reverse('api:curso_detalle', kwargs={'codigo': codigo})

    def test_el_profesor_cambia_la_descripcion_de_su_curso(self):
        self.como(self.profesor)
        respuesta = self.enviar('patch', self.url(), {'descripcion': 'Nueva'})

        self.assertEqual(respuesta.status_code, 200)
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.descripcion, 'Nueva')

    def test_el_profesor_no_se_cambia_el_codigo_ni_el_titular(self):
        self.como(self.profesor)
        respuesta = self.enviar('patch', self.url(), {'profesor': self.ajeno.correo})
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(cuerpo['motivo'], 'campo_no_permitido')
        self.assertEqual(cuerpo['campos'], ['profesor'])

    def test_el_admin_si_reasigna_el_curso(self):
        self.como(self.admin)
        respuesta = self.enviar('patch', self.url(), {'profesor': self.otro_profesor.correo})

        self.assertEqual(respuesta.status_code, 200)
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.profesor_id, self.otro_profesor.pk)

    def test_un_profesor_no_toca_el_curso_de_otro(self):
        self.como(self.profesor)
        respuesta = self.enviar('patch', self.url('TER101'), {'descripcion': 'Mia'})

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'fuera_de_alcance')

    def test_el_estudiante_no_edita_nada(self):
        self.como(self.estudiante)
        respuesta = self.enviar('patch', self.url(), {'descripcion': 'Mia'})

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'sin_permiso')


class ContenidoDelCursoTest(BaseRoles):
    """Modulos, materiales, tareas y quizzes: el terreno del profesor."""

    def test_el_profesor_crea_un_modulo_en_su_curso(self):
        self.como(self.profesor)
        respuesta = self.enviar(
            'post',
            reverse('api:curso_modulos', kwargs={'codigo': 'WEB101'}),
            {'titulo': 'Modulo 2'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.curso.modulos.count(), 2)

    def test_el_orden_se_pone_solo_si_no_se_indica(self):
        self.como(self.profesor)
        respuesta = self.enviar(
            'post',
            reverse('api:curso_modulos', kwargs={'codigo': 'WEB101'}),
            {'titulo': 'Modulo 2'},
        )

        self.assertEqual(self.cuerpo(respuesta)['datos']['orden'], 2)

    def test_el_estudiante_no_crea_modulos(self):
        self.como(self.estudiante)
        respuesta = self.enviar(
            'post',
            reverse('api:curso_modulos', kwargs={'codigo': 'WEB101'}),
            {'titulo': 'Mio'},
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_el_profesor_cuelga_un_material_y_lo_borra(self):
        self.como(self.profesor)

        creacion = self.enviar(
            'post',
            reverse('api:modulo_materiales', kwargs={'id_modulo': self.modulo.pk}),
            {'titulo': 'Video 1', 'tipo': 'video', 'url': 'https://ejemplo.com/v'},
        )

        self.assertEqual(creacion.status_code, 200)
        id_material = self.cuerpo(creacion)['datos']['id_material']

        borrado = self.client.delete(
            reverse('api:material_detalle', kwargs={'id_material': id_material}),
        )

        self.assertEqual(borrado.status_code, 200)
        self.assertEqual(Material.objects.count(), 0)

    def test_una_url_sin_http_se_rechaza_con_el_nombre_del_campo(self):
        self.como(self.profesor)
        respuesta = self.enviar(
            'post',
            reverse('api:modulo_materiales', kwargs={'id_modulo': self.modulo.pk}),
            {'titulo': 'Malo', 'tipo': 'video', 'url': 'ejemplo.com'},
        )
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(cuerpo['campo'], 'url')

    def test_el_profesor_crea_una_tarea_con_fecha_limite(self):
        self.como(self.profesor)
        respuesta = self.enviar(
            'post',
            reverse('api:curso_tareas', kwargs={'codigo': 'WEB101'}),
            {'titulo': 'Practica 2', 'descripcion': 'La segunda.',
             'fecha_limite': '2026-12-01T23:59', 'puntaje_maximo': 20},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Tarea.objects.filter(curso=self.curso).count(), 2)

    def test_una_fecha_mal_escrita_se_explica(self):
        self.como(self.profesor)
        respuesta = self.enviar(
            'post',
            reverse('api:curso_tareas', kwargs={'codigo': 'WEB101'}),
            {'titulo': 'Practica 3', 'descripcion': 'Con la fecha al reves.',
             'fecha_limite': '01/12/2026'},
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.cuerpo(respuesta)['campo'], 'fecha_limite')


class RespuestasDelQuizTest(BaseRoles):
    """La respuesta correcta se ensena a quien corrige, no a quien rinde."""

    def setUp(self):
        self.pregunta = self.quiz.preguntas.create(
            tipo='verdadero_falso',
            enunciado='¿La API valida el rol en cada peticion?',
            puntaje=1,
            orden=1,
            opciones=['Verdadero', 'Falso'],
            respuesta_correcta='Verdadero',
        )

    def url(self):
        return reverse('api:quiz_detalle', kwargs={'id_quiz': self.quiz.pk})

    def test_el_profesor_ve_la_respuesta_correcta(self):
        datos = self.cuerpo(self.como(self.profesor).get(self.url()))['datos']

        self.assertIn('respuesta_correcta', datos['preguntas'][0])

    def test_el_estudiante_no_la_ve(self):
        datos = self.cuerpo(self.como(self.estudiante).get(self.url()))['datos']

        self.assertNotIn('respuesta_correcta', datos['preguntas'][0])
        self.assertEqual(datos['preguntas'][0]['enunciado'], self.pregunta.enunciado)


class EntregasYNotasTest(BaseRoles):
    """El estudiante entrega, el profesor califica, y ninguno hace lo del otro."""

    def test_el_estudiante_entrega_su_tarea(self):
        self.como(self.estudiante)
        respuesta = self.enviar(
            'post',
            reverse('api:tarea_entregas', kwargs={'id_tarea': self.tarea.pk}),
            {'texto': 'Ahi va mi practica.'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Entrega.objects.count(), 1)
        self.assertEqual(Entrega.objects.first().estado, Entrega.Estado.ENTREGADO)

    def test_volver_a_entregar_actualiza_en_vez_de_duplicar(self):
        self.como(self.estudiante)
        url = reverse('api:tarea_entregas', kwargs={'id_tarea': self.tarea.pk})

        self.enviar('post', url, {'texto': 'Primera'})
        self.enviar('post', url, {'texto': 'Corregida'})

        self.assertEqual(Entrega.objects.count(), 1)
        self.assertEqual(Entrega.objects.first().texto, 'Corregida')

    def test_quien_no_esta_inscrito_no_entrega(self):
        self.como(self.ajeno)
        respuesta = self.enviar(
            'post',
            reverse('api:tarea_entregas', kwargs={'id_tarea': self.tarea.pk}),
            {'texto': 'Yo tambien'},
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_el_profesor_califica(self):
        entrega = Entrega.objects.create(
            tarea=self.tarea, usuario=self.estudiante,
            estado=Entrega.Estado.ENTREGADO, texto='Hecha',
        )

        self.como(self.profesor)
        respuesta = self.enviar(
            'patch',
            reverse('api:entrega_detalle', kwargs={'id_entrega': entrega.pk}),
            {'nota': 9, 'comentario': 'Buen trabajo.'},
        )

        self.assertEqual(respuesta.status_code, 200)
        entrega.refresh_from_db()
        self.assertEqual(float(entrega.nota), 9.0)

    def test_la_nota_no_pasa_del_puntaje_maximo(self):
        entrega = Entrega.objects.create(
            tarea=self.tarea, usuario=self.estudiante,
            estado=Entrega.Estado.ENTREGADO,
        )

        self.como(self.profesor)
        respuesta = self.enviar(
            'patch',
            reverse('api:entrega_detalle', kwargs={'id_entrega': entrega.pk}),
            {'nota': 50},
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.cuerpo(respuesta)['campo'], 'nota')

    def test_el_estudiante_no_se_pone_nota_a_si_mismo(self):
        entrega = Entrega.objects.create(
            tarea=self.tarea, usuario=self.estudiante,
            estado=Entrega.Estado.ENTREGADO,
        )

        self.como(self.estudiante)
        respuesta = self.enviar(
            'patch',
            reverse('api:entrega_detalle', kwargs={'id_entrega': entrega.pk}),
            {'nota': 10},
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'campo_no_permitido')

    def test_una_entrega_calificada_ya_no_se_toca(self):
        Entrega.objects.create(
            tarea=self.tarea, usuario=self.estudiante,
            estado=Entrega.Estado.ENTREGADO, nota=8,
        )

        self.como(self.estudiante)
        respuesta = self.enviar(
            'post',
            reverse('api:tarea_entregas', kwargs={'id_tarea': self.tarea.pk}),
            {'texto': 'Segunda oportunidad'},
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'ya_calificada')

    def test_el_estudiante_solo_ve_su_entrega_en_la_lista(self):
        Entrega.objects.create(
            tarea=self.tarea, usuario=self.estudiante,
            estado=Entrega.Estado.ENTREGADO,
        )
        Entrega.objects.create(
            tarea=self.tarea, usuario=self.otro_profesor,
            estado=Entrega.Estado.ENTREGADO,
        )

        url = reverse('api:tarea_entregas', kwargs={'id_tarea': self.tarea.pk})

        del_profesor = self.cuerpo(self.como(self.profesor).get(url))
        self.client.logout()
        del_alumno = self.cuerpo(self.como(self.estudiante).get(url))

        self.assertEqual(del_profesor['paginacion']['total'], 2)
        self.assertEqual(del_alumno['paginacion']['total'], 1)


class FichaPropiaTest(BaseRoles):
    """Uno se edita a si mismo, pero no se asciende."""

    def test_el_estudiante_cambia_su_telefono(self):
        self.como(self.estudiante)
        respuesta = self.enviar('patch', reverse('api:mi_perfil'), {'celular': '0987654321'})

        self.assertEqual(respuesta.status_code, 200)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.celular, '0987654321')

    def test_el_estudiante_no_se_asciende_a_superadmin(self):
        self.como(self.estudiante)
        respuesta = self.enviar('patch', reverse('api:mi_perfil'), {'rol': 'SUPERADMIN'})
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(cuerpo['motivo'], 'campo_no_permitido')

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.rol, Usuario.Rol.USER)

    def test_el_admin_no_crea_super_administradores(self):
        self.como(self.admin)
        respuesta = self.enviar('post', reverse('api:usuarios'), {
            'nombres': 'Nuevo', 'apellidos': 'Jefe',
            'identificacion': '0911111111', 'celular': '0990000009',
            'correo': 'nuevojefe@espol.edu.ec', 'password': 'clave-larga-1',
            'rol': 'SUPERADMIN',
        })

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['campo'], 'rol')

    def test_el_admin_da_de_alta_en_su_facultad(self):
        self.como(self.admin)
        respuesta = self.enviar('post', reverse('api:usuarios'), {
            'nombres': 'Nueva', 'apellidos': 'Alumna',
            'identificacion': '0922222222', 'celular': '0990000010',
            'correo': 'nueva@espol.edu.ec', 'password': 'clave-larga-1',
        })

        self.assertEqual(respuesta.status_code, 200)
        creada = Usuario.objects.get(correo='nueva@espol.edu.ec')
        self.assertEqual(creada.facultad_id, self.fiec.pk)

    def test_nadie_se_elimina_a_si_mismo(self):
        self.como(self.superadmin)
        respuesta = self.client.delete(
            reverse('api:usuario_detalle', kwargs={'id_usuario': self.superadmin.pk}),
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'autodestruccion')


class PanelPorRolTest(BaseRoles):
    """La misma direccion, cuatro pantallas de inicio distintas."""

    def panel(self, usuario):
        return self.cuerpo(self.como(usuario).get(reverse('api:mi_panel')))['datos']

    def test_cada_rol_recibe_su_tipo_de_panel(self):
        self.assertEqual(self.panel(self.superadmin)['tipo'], 'superadmin')
        self.client.logout()
        self.assertEqual(self.panel(self.admin)['tipo'], 'admin')
        self.client.logout()
        self.assertEqual(self.panel(self.profesor)['tipo'], 'profesor')
        self.client.logout()
        self.assertEqual(self.panel(self.estudiante)['tipo'], 'estudiante')

    def test_el_panel_del_profesor_cuenta_lo_que_le_falta_calificar(self):
        Entrega.objects.create(
            tarea=self.tarea, usuario=self.estudiante,
            estado=Entrega.Estado.ENTREGADO,
        )

        datos = self.panel(self.profesor)

        self.assertEqual(datos['indicadores']['por_calificar'], 1)
        self.assertEqual(len(datos['por_calificar']), 1)

    def test_el_panel_del_estudiante_marca_lo_que_ya_entrego(self):
        datos = self.panel(self.estudiante)
        proximas = datos['proximas_tareas']

        self.assertEqual(len(proximas), 1)
        self.assertFalse(proximas[0]['entregada'])
        self.assertEqual(datos['indicadores']['pendientes'], 1)

    def test_el_panel_del_admin_solo_cuenta_su_facultad(self):
        datos = self.panel(self.admin)

        self.assertEqual(datos['indicadores']['total_cursos'], 1)

    def test_mis_permisos_describe_la_matriz_del_rol(self):
        cuerpo = self.cuerpo(self.como(self.profesor).get(reverse('api:mis_permisos')))
        recursos = cuerpo['datos']['permisos']['recursos']

        self.assertEqual(recursos['tareas']['crear'], 'cursos')
        self.assertIsNone(recursos['cursos']['eliminar'])
        self.assertEqual(cuerpo['datos']['alcance']['cursos'], 1)

    def test_mis_cursos_dice_que_se_puede_hacer_en_cada_uno(self):
        cuerpo = self.cuerpo(self.como(self.profesor).get(reverse('api:mis_cursos')))
        puedo = cuerpo['datos'][0]['puedo']

        self.assertIn('crear', puedo['tareas'])
        self.assertNotIn('eliminar', puedo.get('cursos', []))


class ProgresoTest(BaseRoles):
    """El estudiante marca sus modulos; el profesor no marca por el."""

    def url(self):
        return reverse('api:modulo_progreso', kwargs={'id_modulo': self.modulo.pk})

    def test_el_estudiante_marca_un_modulo_como_completado(self):
        self.como(self.estudiante)
        respuesta = self.enviar('post', self.url(), {})

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self.cuerpo(respuesta)['datos']['completado'])

    def test_puede_desmarcarlo(self):
        self.como(self.estudiante)
        self.enviar('post', self.url(), {})
        respuesta = self.enviar('post', self.url(), {'completado': False})

        self.assertFalse(self.cuerpo(respuesta)['datos']['completado'])

    def test_el_profesor_no_marca_progreso(self):
        """Ver el avance si; falsearlo no."""
        self.como(self.profesor)
        respuesta = self.enviar('post', self.url(), {})

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'sin_permiso')


class BorradoProtegidoTest(BaseRoles):
    """Lo que tiene cosas colgando avisa en lugar de reventar."""

    def test_un_curso_sin_trabajo_se_borra_con_su_andamiaje(self):
        """
        Modulos, tareas e inscripciones son parte del curso y se van con el.
        Exigir que se borren antes haria imposible eliminar un curso recien
        creado, porque el alta ya inscribe al profesor titular.
        """
        self.como(self.superadmin)
        respuesta = self.client.delete(
            reverse('api:curso_detalle', kwargs={'codigo': 'WEB101'}),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Curso.objects.filter(codigo='WEB101').exists())
        self.assertFalse(Modulo.objects.filter(pk=self.modulo.pk).exists())
        self.assertFalse(Inscripcion.objects.filter(curso_id=self.curso.pk).exists())

    def test_un_curso_con_entregas_no_se_borra(self):
        """Las notas de los estudiantes no se van por arrastre."""
        Entrega.objects.create(
            tarea=self.tarea, usuario=self.estudiante,
            estado=Entrega.Estado.ENTREGADO, nota=8,
        )

        self.como(self.superadmin)
        respuesta = self.client.delete(
            reverse('api:curso_detalle', kwargs={'codigo': 'WEB101'}),
        )
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(cuerpo['motivo'], 'tiene_trabajo')
        self.assertEqual(cuerpo['entregas'], 1)
        self.assertTrue(Curso.objects.filter(codigo='WEB101').exists())

    def test_tampoco_se_borra_si_alguien_marco_avance(self):
        from cursos.models import ProgresoModulo

        ProgresoModulo.objects.create(
            usuario=self.estudiante, modulo=self.modulo, completado=True,
        )

        self.como(self.superadmin)
        respuesta = self.client.delete(
            reverse('api:curso_detalle', kwargs={'codigo': 'WEB101'}),
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.cuerpo(respuesta)['avances'], 1)

    def test_el_admin_da_de_baja_a_alguien_de_un_curso(self):
        inscripcion = Inscripcion.objects.get(
            usuario=self.estudiante, curso=self.curso,
        )

        self.como(self.admin)
        respuesta = self.client.delete(
            reverse('api:inscripcion_detalle',
                    kwargs={'id_inscripcion': inscripcion.pk}),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Inscripcion.objects.filter(pk=inscripcion.pk).exists())


class TokenConRolTest(BaseRoles):
    """El token queda sellado con el rol que tenia su dueno."""

    def login(self, correo):
        return self.cuerpo(self.client.post(
            reverse('api:auth_login'),
            data=json.dumps({'correo': correo, 'password': 'clave-de-prueba'}),
            content_type='application/json',
        ))['datos']

    def test_cada_rol_recibe_su_token_sellado(self):
        for correo, esperado in (
            ('jefe@espol.edu.ec', 'SUPERADMIN'),
            ('decano@espol.edu.ec', 'ADMIN'),
            ('profe@espol.edu.ec', 'PROFESOR'),
            ('alumno@espol.edu.ec', 'ESTUDIANTE'),
        ):
            with self.subTest(correo=correo):
                datos = self.login(correo)

                self.assertEqual(datos['rol'], esperado)
                self.assertEqual(datos['rol_del_token'], esperado)
                self.assertEqual(datos['permisos']['rol'], esperado)

    def test_el_token_guarda_los_permisos_con_los_que_nacio(self):
        from api.models import TokenApi

        self.login('profe@espol.edu.ec')
        token = TokenApi.objects.get(usuario=self.profesor)

        self.assertEqual(token.rol, 'PROFESOR')
        self.assertIn('crear', token.permisos['tareas'])
        self.assertNotIn('eliminar', token.permisos['cursos'])

    def test_verificar_avisa_si_el_rol_cambio_desde_la_emision(self):
        datos = self.login('alumno@espol.edu.ec')

        Inscripcion.objects.create(
            usuario=self.estudiante, curso=self.curso_ajeno,
            rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
        )

        respuesta = self.client.get(
            reverse('api:auth_verificar'),
            HTTP_AUTHORIZATION=f'Bearer {datos["token"]}',
        )
        cuerpo = self.cuerpo(respuesta)['datos']

        self.assertEqual(cuerpo['rol'], 'PROFESOR')
        self.assertEqual(cuerpo['token']['rol_al_emitir'], 'ESTUDIANTE')
        self.assertTrue(cuerpo['token']['rol_cambio'])


class FacultadesTest(BaseRoles):
    """Las facultades las abre el super administrador; el decano retoca la suya."""

    def test_el_superadmin_crea_una_facultad(self):
        self.como(self.superadmin)
        respuesta = self.enviar('post', reverse('api:facultades'), {
            'nombre': 'Ciencias de la Vida', 'codigo': 'FCV',
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(Facultad.objects.filter(codigo='FCV').exists())

    def test_el_admin_no_crea_facultades(self):
        self.como(self.admin)
        respuesta = self.enviar('post', reverse('api:facultades'), {
            'nombre': 'Otra', 'codigo': 'OTR',
        })

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'sin_permiso')

    def test_el_admin_edita_la_suya_pero_no_la_de_al_lado(self):
        self.como(self.admin)

        propia = self.enviar(
            'patch',
            reverse('api:facultad_detalle', kwargs={'codigo': 'FIEC'}),
            {'nombre': 'Electrica y Computacion (FIEC)'},
        )
        ajena = self.enviar(
            'patch',
            reverse('api:facultad_detalle', kwargs={'codigo': 'FIMCP'}),
            {'nombre': 'Mia tambien'},
        )

        self.assertEqual(propia.status_code, 200)
        self.assertEqual(ajena.status_code, 403)
        self.assertEqual(self.cuerpo(ajena)['motivo'], 'fuera_de_alcance')


class ProgresoDelCursoTest(BaseRoles):
    """El avance por modulos: cada rol ve el suyo o el de todos."""

    def url(self, codigo='WEB101'):
        return reverse('api:curso_progreso', kwargs={'codigo': codigo})

    def test_el_profesor_ve_el_avance_de_todos_sus_estudiantes(self):
        datos = self.cuerpo(self.como(self.profesor).get(self.url()))['datos']

        self.assertEqual(datos['curso'], 'WEB101')
        self.assertEqual(len(datos['filas']), 1)
        self.assertEqual(datos['filas'][0]['estudiante'], self.estudiante.nombre_completo)

    def test_el_estudiante_solo_ve_su_propia_fila(self):
        datos = self.cuerpo(self.como(self.estudiante).get(self.url()))['datos']

        self.assertEqual(len(datos['filas']), 1)
        self.assertEqual(datos['filas'][0]['usuario'], self.estudiante.pk)

    def test_el_avance_sube_al_marcar_un_modulo(self):
        self.como(self.estudiante)
        self.enviar('post', reverse('api:modulo_progreso',
                                    kwargs={'id_modulo': self.modulo.pk}), {})

        datos = self.cuerpo(self.client.get(self.url()))['datos']

        self.assertEqual(datos['filas'][0]['completados'], 1)
        self.assertEqual(datos['filas'][0]['avance'], 100.0)


class QuizRendidoTest(BaseRoles):
    """Rendir un quiz, corregirlo solo y ponerle nota a mano."""

    def setUp(self):
        self.pregunta = self.quiz.preguntas.create(
            tipo='verdadero_falso', enunciado='¿2 + 2 = 4?', puntaje=5, orden=1,
            opciones=['Verdadero', 'Falso'], respuesta_correcta=True,
        )
        self.abierta = self.quiz.preguntas.create(
            tipo='ensayo', enunciado='Explica por que.', puntaje=5, orden=2,
            opciones=[], respuesta_correcta=None,
        )

    def url(self):
        return reverse('api:quiz_respuestas', kwargs={'id_quiz': self.quiz.pk})

    def test_el_estudiante_rinde_y_se_corrige_lo_automatico(self):
        self.como(self.estudiante)
        respuesta = self.enviar('post', self.url(), {
            'respuestas': {
                str(self.pregunta.id_pregunta): 'Verdadero',
                str(self.abierta.id_pregunta): 'Porque si.',
            },
        })
        datos = self.cuerpo(respuesta)['datos']

        self.assertEqual(respuesta.status_code, 200)
        # Solo puntua la de verdadero/falso; el ensayo lo califica el profesor.
        self.assertEqual(datos['nota_automatica'], 5.0)
        self.assertIsNone(datos['nota_manual'])

    def test_una_respuesta_equivocada_no_suma(self):
        self.como(self.estudiante)
        datos = self.cuerpo(self.enviar('post', self.url(), {
            'respuestas': {str(self.pregunta.id_pregunta): 'Falso'},
        }))['datos']

        self.assertEqual(datos['nota_automatica'], 0.0)

    def test_quien_no_esta_inscrito_no_rinde(self):
        self.como(self.ajeno)
        respuesta = self.enviar('post', self.url(), {'respuestas': {}})

        self.assertEqual(respuesta.status_code, 403)

    def test_el_profesor_pone_la_nota_manual(self):
        self.como(self.estudiante)
        intento = self.cuerpo(self.enviar('post', self.url(), {
            'respuestas': {str(self.pregunta.id_pregunta): 'Verdadero'},
        }))['datos']

        self.client.logout()
        self.como(self.profesor)
        respuesta = self.enviar(
            'patch',
            reverse('api:respuesta_quiz_detalle',
                    kwargs={'id_respuesta': intento['id_respuesta_quiz']}),
            {'nota_manual': 9},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.cuerpo(respuesta)['datos']['nota_manual'], 9.0)

    def test_el_estudiante_no_se_pone_su_propia_nota(self):
        self.como(self.estudiante)
        intento = self.cuerpo(self.enviar('post', self.url(), {'respuestas': {}}))['datos']

        respuesta = self.enviar(
            'patch',
            reverse('api:respuesta_quiz_detalle',
                    kwargs={'id_respuesta': intento['id_respuesta_quiz']}),
            {'nota_manual': 10},
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_el_estudiante_solo_ve_su_intento(self):
        self.como(self.estudiante)
        self.enviar('post', self.url(), {'respuestas': {}})

        suyos = self.cuerpo(self.client.get(self.url()))
        self.client.logout()
        del_profesor = self.cuerpo(self.como(self.profesor).get(self.url()))

        self.assertEqual(suyos['paginacion']['total'], 1)
        self.assertEqual(del_profesor['paginacion']['total'], 1)
