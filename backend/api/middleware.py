"""
Middleware CORS minimo para /api/.

Permite que paginas web de otros dominios (o herramientas como Postman)
consulten la API desde el navegador. Solo afecta a las rutas /api/.
"""
from django.conf import settings
from django.http import HttpResponse

PREFIJO = '/api/'


class CorsApiMiddleware:
    """Anade las cabeceras CORS y responde a las peticiones preflight."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        es_api = request.path.startswith(PREFIJO) or request.path == PREFIJO.rstrip('/')

        if es_api and request.method == 'OPTIONS':
            respuesta = HttpResponse(status=204)
        else:
            respuesta = self.get_response(request)

        if es_api:
            self._agregar_cabeceras(request, respuesta)

        return respuesta

    def _agregar_cabeceras(self, request, respuesta):
        origenes = getattr(settings, 'API_ORIGENES', ['*'])
        origen = request.headers.get('Origin', '')

        if '*' in origenes:
            # Con '*' el navegador NO envia cookies, asi que una pagina de otro
            # dominio nunca puede leer datos usando la sesion de quien la visita.
            respuesta['Access-Control-Allow-Origin'] = '*'
        elif origen in origenes:
            respuesta['Access-Control-Allow-Origin'] = origen
            respuesta['Vary'] = 'Origin'
            # Solo con dominios concretos se permiten cookies: asi la sesion de
            # super administrador sirve tambien desde otra aplicacion tuya.
            respuesta['Access-Control-Allow-Credentials'] = 'true'
        else:
            return

        respuesta['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        respuesta['Access-Control-Allow-Headers'] = 'X-API-Key, Content-Type'
        respuesta['Access-Control-Max-Age'] = '86400'
