"""Pruebas de la API publica (/api/)."""
import json
from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Usuario
from cursos.models import Curso, Facultad, Inscripcion, Modulo


class ApiBaseTest(TestCase):
    """Datos minimos compartidos por las pruebas."""

    @classmethod
    def setUpTestData(cls):
        cls.facultad = Facultad.objects.create(nombre='Facultad de Prueba', codigo='FIEC')

        cls.profesor = Usuario.objects.create_user(
            correo='profe@espol.edu.ec',
            password='clave-de-prueba',
            nombres='Ana',
            apellidos='Torres',
            identificacion='0900000001',
            celular='0990000001',
            facultad=cls.facultad,
        )

        cls.estudiante = Usuario.objects.create_user(
            correo='alumno@espol.edu.ec',
            password='clave-de-prueba',
            nombres='Luis',
            apellidos='Vera',
            identificacion='0900000002',
            celular='0990000002',
            facultad=cls.facultad,
        )

        cls.curso = Curso.objects.create(
            nombre='Programacion Web',
            codigo='WEB101',
            descripcion='Curso de prueba',
            facultad=cls.facultad,
            profesor=cls.profesor,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
        )

        Modulo.objects.create(curso=cls.curso, titulo='Introduccion', orden=1)

        Inscripcion.objects.create(
            usuario=cls.estudiante,
            curso=cls.curso,
            rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
        )

    def cuerpo(self, respuesta):
        return json.loads(respuesta.content)


@override_settings(API_CLAVE='', API_MODO='publica')
class ApiPublicaTest(ApiBaseTest):
    """Modo publico y sin clave: el catalogo queda abierto a cualquiera."""

    def test_indice_lista_los_recursos(self):
        respuesta = self.client.get(reverse('api:indice'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('cursos', self.cuerpo(respuesta)['datos']['recursos'])

    def test_estado_reporta_la_base_de_datos(self):
        cuerpo = self.cuerpo(self.client.get(reverse('api:estado')))

        self.assertTrue(cuerpo['ok'])
        self.assertEqual(cuerpo['datos']['base_de_datos'], 'ok')

    def test_listado_de_cursos_pagina(self):
        cuerpo = self.cuerpo(self.client.get(reverse('api:cursos')))

        self.assertEqual(cuerpo['paginacion']['total'], 1)
        self.assertEqual(cuerpo['datos'][0]['codigo'], 'WEB101')

    def test_filtro_por_facultad(self):
        cuerpo = self.cuerpo(
            self.client.get(reverse('api:cursos'), {'facultad': 'fiec'}),
        )

        self.assertEqual(len(cuerpo['datos']), 1)

    def test_filtro_con_estado_invalido_devuelve_400(self):
        respuesta = self.client.get(reverse('api:cursos'), {'estado': 'inventado'})

        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(self.cuerpo(respuesta)['ok'])

    def test_detalle_de_curso_incluye_modulos(self):
        url = reverse('api:curso_detalle', kwargs={'codigo': 'web101'})
        cuerpo = self.cuerpo(self.client.get(url))

        self.assertEqual(cuerpo['datos']['nombre'], 'Programacion Web')
        self.assertEqual(len(cuerpo['datos']['modulos']), 1)

    def test_curso_inexistente_devuelve_404_en_json(self):
        url = reverse('api:curso_detalle', kwargs={'codigo': 'NOEXISTE'})
        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta['Content-Type'], 'application/json')

    def test_ruta_desconocida_devuelve_404_en_json(self):
        respuesta = self.client.get('/api/loquesea/')

        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(self.cuerpo(respuesta)['ok'])

    def test_metodo_post_no_permitido(self):
        respuesta = self.client.post(reverse('api:cursos'))

        self.assertEqual(respuesta.status_code, 405)

    def test_cabecera_cors_presente(self):
        respuesta = self.client.get(reverse('api:cursos'))

        self.assertEqual(respuesta['Access-Control-Allow-Origin'], '*')

    def test_recurso_privado_sin_identificarse_devuelve_401(self):
        respuesta = self.client.get(reverse('api:usuarios'))

        self.assertEqual(respuesta.status_code, 401)

    def test_reporte_resumen_entrega_indicadores(self):
        cuerpo = self.cuerpo(self.client.get(reverse('api:reporte_resumen')))

        self.assertEqual(cuerpo['datos']['resumen']['total_cursos'], 1)


@override_settings(API_CLAVE='clave-secreta-de-prueba')
class ApiConClaveTest(ApiBaseTest):
    """Con clave configurada: todos los recursos la exigen."""

    def test_sin_clave_devuelve_401(self):
        respuesta = self.client.get(reverse('api:cursos'))

        self.assertEqual(respuesta.status_code, 401)

    def test_el_indice_no_pide_clave(self):
        respuesta = self.client.get(reverse('api:indice'))

        self.assertEqual(respuesta.status_code, 200)
        seguridad = self.cuerpo(respuesta)['datos']['seguridad']
        self.assertFalse(seguridad['acceso_actual']['autorizado'])
        self.assertTrue(seguridad['vias']['clave']['configurada'])

    def test_el_estado_no_pide_clave_pero_oculta_los_totales(self):
        cuerpo = self.cuerpo(self.client.get(reverse('api:estado')))

        self.assertTrue(cuerpo['ok'])
        self.assertNotIn('totales', cuerpo['datos'])

    def test_el_estado_muestra_los_totales_con_clave(self):
        cuerpo = self.cuerpo(self.client.get(
            reverse('api:estado'), headers={'x-api-key': 'clave-secreta-de-prueba'},
        ))

        self.assertEqual(cuerpo['datos']['totales']['cursos'], 1)

    def test_clave_incorrecta_devuelve_401(self):
        respuesta = self.client.get(
            reverse('api:cursos'), headers={'x-api-key': 'otra'},
        )

        self.assertEqual(respuesta.status_code, 401)

    def test_clave_en_encabezado_funciona(self):
        respuesta = self.client.get(
            reverse('api:cursos'), headers={'x-api-key': 'clave-secreta-de-prueba'},
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_clave_en_parametro_funciona(self):
        respuesta = self.client.get(
            reverse('api:cursos'), {'clave': 'clave-secreta-de-prueba'},
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_usuarios_con_clave_devuelve_datos(self):
        respuesta = self.client.get(
            reverse('api:usuarios'), headers={'x-api-key': 'clave-secreta-de-prueba'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.cuerpo(respuesta)['paginacion']['total'], 2)

    def test_estudiantes_del_curso_con_clave(self):
        url = reverse('api:curso_estudiantes', kwargs={'codigo': 'WEB101'})
        cuerpo = self.cuerpo(
            self.client.get(url, headers={'x-api-key': 'clave-secreta-de-prueba'}),
        )

        self.assertEqual(cuerpo['datos'][0]['usuario']['correo'], 'alumno@espol.edu.ec')


@override_settings(API_CLAVE='')
class ApiSesionTest(ApiBaseTest):
    """Acceso con la sesion del sitio, sin ninguna clave configurada."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.superadmin = Usuario.objects.create_user(
            correo='jefe@espol.edu.ec',
            password='clave-de-prueba',
            nombres='Sofia',
            apellidos='Mora',
            identificacion='0900000003',
            celular='0990000003',
            rol=Usuario.Rol.SUPERADMIN,
        )

    def test_superadmin_entra_a_los_recursos_privados(self):
        self.client.force_login(self.superadmin)

        respuesta = self.client.get(reverse('api:usuarios'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.cuerpo(respuesta)['paginacion']['total'], 3)

    def test_usuario_normal_no_entra(self):
        self.client.force_login(self.estudiante)

        respuesta = self.client.get(reverse('api:usuarios'))

        self.assertEqual(respuesta.status_code, 401)

    def test_superadmin_inactivo_no_entra(self):
        self.superadmin.is_active = False
        self.superadmin.save(update_fields=['is_active'])
        self.client.force_login(self.superadmin)

        respuesta = self.client.get(reverse('api:usuarios'))

        self.assertEqual(respuesta.status_code, 401)

    def test_el_indice_informa_de_la_via_usada(self):
        self.client.force_login(self.superadmin)

        datos = self.cuerpo(self.client.get(reverse('api:indice')))['datos']

        self.assertEqual(datos['seguridad']['acceso_actual']['via'], 'sesion')
        self.assertEqual(
            datos['seguridad']['acceso_actual']['usuario'], 'jefe@espol.edu.ec',
        )

    def test_sin_sesion_el_catalogo_exige_identificarse(self):
        respuesta = self.client.get(reverse('api:cursos'))

        self.assertEqual(respuesta.status_code, 401)

    @override_settings(API_MODO='publica')
    def test_en_modo_publico_el_catalogo_queda_abierto(self):
        respuesta = self.client.get(reverse('api:cursos'))

        self.assertEqual(respuesta.status_code, 200)


@override_settings(API_CLAVE='', API_MODO='privada')
class ApiModoPrivadaTest(ApiBaseTest):
    """Con API_MODO=privada no se consulta nada sin identificarse."""

    def test_el_catalogo_exige_identificarse(self):
        respuesta = self.client.get(reverse('api:cursos'))

        self.assertEqual(respuesta.status_code, 401)

    def test_el_indice_sigue_abierto(self):
        respuesta = self.client.get(reverse('api:indice'))

        self.assertEqual(respuesta.status_code, 200)

    def test_el_superusuario_de_django_entra(self):
        jefe = Usuario.objects.create_superuser(
            correo='root@espol.edu.ec',
            password='clave-de-prueba',
            nombres='Root',
            apellidos='Django',
            identificacion='0900000004',
            celular='0990000004',
        )
        self.client.force_login(jefe)

        respuesta = self.client.get(reverse('api:cursos'))

        self.assertEqual(respuesta.status_code, 200)
