"""Pruebas de la API publica (/api/)."""
import json
from datetime import date, timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from api.models import TokenApi
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


@override_settings(API_CLAVE='', API_MODO='privada')
class ApiAutenticacionTest(ApiBaseTest):
    """
    Login de aplicaciones externas: /api/auth/login|verificar|logout.

    Es la via pensada para que OTRA aplicacion, con su propio sistema de
    login, use la API con la cuenta de super administrador de su usuario.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.superadmin = Usuario.objects.create_user(
            correo='jefe@espol.edu.ec',
            password='clave-de-prueba',
            nombres='Sofia',
            apellidos='Mora',
            identificacion='0900000010',
            celular='0990000010',
            rol=Usuario.Rol.SUPERADMIN,
        )

    def setUp(self):
        # Los intentos fallidos viven en la cache y no deben pasar de una
        # prueba a la siguiente.
        cache.clear()

    def login(self, correo='jefe@espol.edu.ec', password='clave-de-prueba', **extra):
        return self.client.post(
            reverse('api:auth_login'),
            data=json.dumps({'correo': correo, 'password': password, **extra}),
            content_type='application/json',
        )

    def token_valido(self):
        return self.cuerpo(self.login())['datos']['token']

    def con_token(self, url, token):
        return self.client.get(url, headers={'authorization': f'Bearer {token}'})

    # ── Login ────────────────────────────────────────────────────────────

    def test_login_de_superadmin_entrega_token(self):
        respuesta = self.login()
        datos = self.cuerpo(respuesta)['datos']

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(datos['autorizado'])
        self.assertEqual(datos['tipo'], 'Bearer')
        self.assertEqual(datos['usuario']['correo'], 'jefe@espol.edu.ec')
        self.assertTrue(datos['token'])

    def test_el_token_no_se_guarda_en_claro(self):
        plano = self.token_valido()

        self.assertFalse(TokenApi.objects.filter(huella=plano).exists())
        self.assertEqual(TokenApi.objects.get().prefijo, plano[:TokenApi.LARGO_PREFIJO])

    def test_usuario_sin_rol_superadmin_recibe_el_aviso(self):
        respuesta = self.login(correo='alumno@espol.edu.ec')
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(cuerpo['autorizado'])
        self.assertEqual(cuerpo['error'], 'No se ha autorizado que sea un super admin.')
        self.assertEqual(cuerpo['motivo'], 'no_superadmin')
        self.assertEqual(TokenApi.objects.count(), 0)

    def test_cuenta_inactiva_no_recibe_token(self):
        self.superadmin.estado = Usuario.Estado.INACTIVO
        self.superadmin.save(update_fields=['estado'])

        respuesta = self.login()

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'cuenta_inactiva')

    def test_contrasena_incorrecta_devuelve_401(self):
        respuesta = self.login(password='no-es-la-clave')
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(cuerpo['motivo'], 'credenciales_invalidas')
        self.assertEqual(cuerpo['intentos_restantes'], 9)

    def test_login_sin_credenciales_devuelve_400(self):
        respuesta = self.client.post(
            reverse('api:auth_login'), data='{}', content_type='application/json',
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'faltan_credenciales')

    def test_login_acepta_formulario_ademas_de_json(self):
        respuesta = self.client.post(reverse('api:auth_login'), {
            'correo': 'jefe@espol.edu.ec',
            'password': 'clave-de-prueba',
            'aplicacion': 'App de terceros',
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(TokenApi.objects.get().aplicacion, 'App de terceros')

    def test_login_por_get_no_esta_permitido(self):
        respuesta = self.client.get(reverse('api:auth_login'))

        self.assertEqual(respuesta.status_code, 405)

    def test_dias_fuera_de_rango_devuelve_400(self):
        respuesta = self.login(dias=99999)

        self.assertEqual(respuesta.status_code, 400)

    @override_settings(API_LOGIN_INTENTOS=3)
    def test_demasiados_intentos_bloquean_el_correo(self):
        for _ in range(3):
            self.login(password='mal')

        respuesta = self.login()

        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'demasiados_intentos')

    def test_un_login_correcto_borra_los_intentos_fallidos(self):
        self.login(password='mal')
        self.login()

        respuesta = self.login(password='mal')

        self.assertEqual(self.cuerpo(respuesta)['intentos_restantes'], 9)

    # ── Login del sitio (index.html): "sesion": true ─────────────────────

    def test_login_con_sesion_abre_la_cookie_de_django(self):
        cuerpo = self.cuerpo(self.login(sesion=True))

        self.assertTrue(cuerpo['datos']['autorizado'])
        self.assertTrue(cuerpo['datos']['sesion_django'])
        self.assertTrue(cuerpo['datos']['token'])

        # Sin mandar el token: entra por la cookie que acaba de abrirse.
        self.assertEqual(self.client.get(reverse('api:usuarios')).status_code, 200)

    def test_el_sitio_deja_entrar_a_quien_no_es_superadmin_pero_sin_api(self):
        respuesta = self.login(correo='alumno@espol.edu.ec', sesion=True)
        datos = self.cuerpo(respuesta)['datos']

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(datos['autorizado'])
        self.assertIsNone(datos['token'])
        self.assertEqual(datos['aviso'], 'No se ha autorizado que sea un super admin.')
        self.assertEqual(datos['usuario']['rol'], 'USER')

        # La cookie existe, pero la API sigue cerrada para ese rol.
        self.assertEqual(self.client.get(reverse('api:usuarios')).status_code, 401)

    def test_el_login_dice_con_que_rol_entra_un_usuario(self):
        alumno = self.cuerpo(self.login(correo='alumno@espol.edu.ec', sesion=True))

        self.assertEqual(alumno['datos']['rol_activo'], 'ESTUDIANTE')

        Inscripcion.objects.create(
            usuario=self.profesor,
            curso=self.curso,
            rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
        )
        docente = self.cuerpo(self.login(correo='profe@espol.edu.ec', sesion=True))

        self.assertEqual(docente['datos']['rol_activo'], 'PROFESOR')
        self.assertIsNone(self.cuerpo(self.login(sesion=True))['datos']['rol_activo'])

    def test_el_sitio_entra_sin_que_se_emita_ningun_token(self):
        datos = self.cuerpo(self.login(sesion=True, token=False))['datos']

        self.assertTrue(datos['autorizado'])
        self.assertIsNone(datos['token'])
        self.assertEqual(TokenApi.objects.count(), 0)

        # La cookie de sesion le abre la API igual.
        self.assertEqual(self.client.get(reverse('api:usuarios')).status_code, 200)

    def test_la_ficha_del_usuario_trae_lo_que_pinta_el_frontend(self):
        usuario = self.cuerpo(self.login(sesion=True))['datos']['usuario']

        self.assertEqual(usuario['id'], self.superadmin.id_usuario)
        self.assertEqual(usuario['iniciales'], 'SM')
        self.assertEqual(usuario['nombre_completo'], 'Sofia Mora')

    def test_una_cuenta_inactiva_no_entra_ni_al_sitio(self):
        self.estudiante.estado = Usuario.Estado.INACTIVO
        self.estudiante.save(update_fields=['estado'])

        respuesta = self.login(correo='alumno@espol.edu.ec', sesion=True)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'cuenta_inactiva')

    def test_sin_pedir_sesion_el_no_superadmin_sigue_recibiendo_403(self):
        respuesta = self.login(correo='alumno@espol.edu.ec')

        self.assertEqual(respuesta.status_code, 403)

    # ── Uso del token ────────────────────────────────────────────────────

    def test_el_token_abre_la_api_completa(self):
        token = self.token_valido()

        respuesta = self.con_token(reverse('api:usuarios'), token)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.cuerpo(respuesta)['paginacion']['total'], 3)

    def test_el_token_tambien_viaja_en_x_api_token(self):
        token = self.token_valido()

        respuesta = self.client.get(
            reverse('api:cursos'), headers={'x-api-token': token},
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_token_inventado_devuelve_401_con_el_aviso(self):
        respuesta = self.con_token(reverse('api:cursos'), 'no-es-un-token')
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(cuerpo['error'], 'No se ha autorizado que sea un super admin.')
        self.assertEqual(cuerpo['motivo'], 'token_invalido')
        self.assertIn('token', cuerpo['como_autorizarse'])

    def test_token_caducado_deja_de_servir(self):
        token = self.token_valido()
        TokenApi.objects.update(expira=timezone.now() - timedelta(days=1))

        respuesta = self.con_token(reverse('api:cursos'), token)

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'token_caducado')

    def test_si_el_usuario_deja_de_ser_superadmin_el_token_muere(self):
        token = self.token_valido()

        self.superadmin.rol = Usuario.Rol.USER
        self.superadmin.save(update_fields=['rol'])

        respuesta = self.con_token(reverse('api:usuarios'), token)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'no_superadmin')

    def test_el_token_anota_su_ultimo_uso(self):
        token = self.token_valido()

        self.con_token(reverse('api:cursos'), token)

        self.assertIsNotNone(TokenApi.objects.get().ultimo_uso)

    # ── Verificar ────────────────────────────────────────────────────────

    def test_verificar_sin_credenciales_avisa_que_no_es_superadmin(self):
        respuesta = self.client.get(reverse('api:auth_verificar'))
        cuerpo = self.cuerpo(respuesta)

        self.assertEqual(respuesta.status_code, 401)
        self.assertFalse(cuerpo['autorizado'])
        self.assertEqual(cuerpo['error'], 'No se ha autorizado que sea un super admin.')
        self.assertEqual(cuerpo['motivo'], 'sin_credenciales')

    @override_settings(API_MODO='publica')
    def test_verificar_no_se_ablanda_en_modo_publico(self):
        respuesta = self.client.get(reverse('api:auth_verificar'))

        self.assertEqual(respuesta.status_code, 401)
        self.assertFalse(self.cuerpo(respuesta)['autorizado'])

    def test_verificar_con_token_devuelve_al_superadmin(self):
        token = self.token_valido()

        cuerpo = self.cuerpo(self.con_token(reverse('api:auth_verificar'), token))

        self.assertTrue(cuerpo['datos']['autorizado'])
        self.assertEqual(cuerpo['datos']['via'], 'token')
        self.assertEqual(cuerpo['datos']['usuario']['correo'], 'jefe@espol.edu.ec')
        self.assertTrue(cuerpo['datos']['usuario']['es_superadmin'])

    def test_verificar_reconoce_la_sesion_del_navegador(self):
        self.client.force_login(self.superadmin)

        cuerpo = self.cuerpo(self.client.get(reverse('api:auth_verificar')))

        self.assertEqual(cuerpo['datos']['via'], 'sesion')

    def test_verificar_con_sesion_de_usuario_normal_no_autoriza(self):
        self.client.force_login(self.estudiante)

        respuesta = self.client.get(reverse('api:auth_verificar'))

        self.assertEqual(respuesta.status_code, 401)
        self.assertFalse(self.cuerpo(respuesta)['autorizado'])

    # ── Logout ───────────────────────────────────────────────────────────

    def test_logout_revoca_el_token(self):
        token = self.token_valido()

        respuesta = self.client.post(
            reverse('api:auth_logout'), headers={'authorization': f'Bearer {token}'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(TokenApi.objects.get().revocado)

        segunda = self.con_token(reverse('api:cursos'), token)
        self.assertEqual(segunda.status_code, 401)
        self.assertEqual(self.cuerpo(segunda)['motivo'], 'token_revocado')

    def test_logout_puede_revocar_todos_los_tokens_de_la_cuenta(self):
        primero = self.token_valido()
        self.token_valido()

        cuerpo = self.cuerpo(self.client.post(
            reverse('api:auth_logout'),
            data=json.dumps({'todos': True}),
            content_type='application/json',
            headers={'authorization': f'Bearer {primero}'},
        ))

        self.assertEqual(cuerpo['datos']['revocados'], 2)
        self.assertEqual(TokenApi.objects.filter(revocado=False).count(), 0)

    def test_logout_sin_nada_que_cerrar_avisa(self):
        respuesta = self.client.post(reverse('api:auth_logout'))

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.cuerpo(respuesta)['motivo'], 'sin_token')

    def test_logout_cierra_tambien_la_sesion_de_django(self):
        self.client.force_login(self.superadmin)

        cuerpo = self.cuerpo(self.client.post(reverse('api:auth_logout')))

        self.assertTrue(cuerpo['datos']['sesion_cerrada'])
        self.assertEqual(self.client.get(reverse('api:usuarios')).status_code, 401)

    # ── Descubrimiento ───────────────────────────────────────────────────

    def test_el_indice_publica_las_rutas_de_login(self):
        datos = self.cuerpo(self.client.get(reverse('api:indice')))['datos']

        self.assertIn('auth_login (POST)', datos['recursos'])
        self.assertIn('token', datos['seguridad']['vias'])

    def test_cors_permite_el_encabezado_de_autorizacion(self):
        respuesta = self.client.options(reverse('api:auth_login'))

        self.assertIn('POST', respuesta['Access-Control-Allow-Methods'])
        self.assertIn('Authorization', respuesta['Access-Control-Allow-Headers'])
