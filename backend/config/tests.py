"""Pruebas de las direcciones del sitio (URLs limpias, sin .html)."""
from django.test import TestCase


class DireccionesDelSitioTest(TestCase):
    """El sitio se navega sin extensiones: /login, /superadmin/dashboard…"""

    def test_la_raiz_lleva_a_login(self):
        respuesta = self.client.get('/')

        self.assertRedirects(respuesta, '/login', fetch_redirect_response=False)

    def test_el_index_html_antiguo_lleva_a_login(self):
        respuesta = self.client.get('/index.html')

        self.assertRedirects(respuesta, '/login', fetch_redirect_response=False)

    def test_login_sirve_la_pantalla_de_entrada(self):
        respuesta = self.client.get('/login')

        self.assertEqual(respuesta.status_code, 200)
        cuerpo = b''.join(respuesta.streaming_content)
        self.assertIn(b'id="login-form"', cuerpo)

    def test_cada_seccion_sirve_su_pagina(self):
        for direccion in (
            '/superadmin/dashboard',
            '/superadmin/usuarios',
            '/facultad/dashboard',
            '/profesor/mis-cursos',
            '/estudiante/mis-cursos',
        ):
            with self.subTest(direccion=direccion):
                self.assertEqual(self.client.get(direccion).status_code, 200)

    def test_una_pagina_inexistente_da_404(self):
        self.assertEqual(self.client.get('/superadmin/inventada').status_code, 404)

    def test_una_seccion_inexistente_da_404(self):
        self.assertEqual(self.client.get('/inventada/dashboard').status_code, 404)

    def test_la_carpeta_admin_se_publica_como_facultad(self):
        # /admin/ es el panel de Django, asi que el rol ADMIN vive en
        # /facultad/…: /admin/dashboard lo atiende Django (manda a su login),
        # nunca sirve la pagina del frontend.
        respuesta = self.client.get('/admin/dashboard')

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta['Location'].startswith('/admin/login/'))

    def test_las_direcciones_html_antiguas_redirigen(self):
        respuesta = self.client.get('/pages/superadmin/dashboard.html')

        self.assertRedirects(
            respuesta, '/superadmin/dashboard', fetch_redirect_response=False,
        )

    def test_la_redireccion_conserva_los_parametros(self):
        respuesta = self.client.get('/pages/profesor/curso.html?id=3')

        self.assertRedirects(
            respuesta, '/profesor/curso?id=3', fetch_redirect_response=False,
        )

    def test_los_recursos_siguen_sirviendose(self):
        for recurso in ('/css/main.css', '/js/api.js'):
            with self.subTest(recurso=recurso):
                self.assertEqual(self.client.get(recurso).status_code, 200)

    def test_el_panel_y_la_api_no_se_confunden_con_una_pagina(self):
        # /panel/ pide sesion (302 al login de Django) y /api/ responde JSON.
        self.assertEqual(self.client.get('/panel/').status_code, 302)
        self.assertEqual(self.client.get('/api/').status_code, 200)
