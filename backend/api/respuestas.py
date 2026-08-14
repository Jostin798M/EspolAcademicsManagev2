"""
Utilidades comunes de la API: respuestas JSON, errores, clave y paginacion.

Se implementa con Django puro (JsonResponse) para no anadir dependencias
al servidor, que tiene una cuota de disco pequena.
"""
import functools
import json

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from . import seguridad


class ErrorApi(Exception):
    """Error controlado que se devuelve al cliente en formato JSON."""

    def __init__(self, mensaje, codigo=400, **extra):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.extra = extra


def ok(datos, **extra):
    """Respuesta correcta: {"ok": true, "datos": ...}."""
    cuerpo = {'ok': True, 'datos': datos}
    cuerpo.update(extra)
    return JsonResponse(cuerpo, json_dumps_params={'ensure_ascii': False})


def error(mensaje, codigo=400, **extra):
    """
    Respuesta de error: {"ok": false, "error": "..."}.

    Los campos extra (motivo, detalle, autorizado...) los usa la aplicacion
    que consume la API para decidir que hacer sin leer el texto del mensaje.
    """
    cuerpo = {'ok': False, 'error': mensaje, 'codigo': codigo}
    cuerpo.update(extra)

    return JsonResponse(
        cuerpo,
        status=codigo,
        json_dumps_params={'ensure_ascii': False},
    )


def no_autorizado(request, acceso):
    """Traduce un Resultado denegado de seguridad.py a respuesta JSON."""
    return error(
        acceso.mensaje,
        acceso.codigo,
        autorizado=False,
        motivo=acceso.motivo,
        detalle=acceso.detalle,
        como_autorizarse=seguridad.como_autorizarse(request),
    )


def cuerpo_json(request):
    """
    Lee el cuerpo de un POST, venga en JSON o en un formulario.

    Asi funciona igual desde fetch() con Content-Type: application/json que
    desde un formulario HTML o desde curl -d.
    """
    tipo = (request.content_type or '').split(';')[0].strip().lower()

    if tipo == 'application/json':
        if not request.body:
            return {}

        try:
            datos = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise ErrorApi('El cuerpo de la peticion no es JSON valido.')

        if not isinstance(datos, dict):
            raise ErrorApi('El cuerpo de la peticion debe ser un objeto JSON.')

        return datos

    return request.POST.dict()


def texto(datos, *nombres, por_defecto=''):
    """Primer valor no vacio de entre varios nombres posibles del campo."""
    for nombre in nombres:
        valor = datos.get(nombre)

        if valor is not None and str(valor).strip():
            return str(valor).strip()

    return por_defecto


def esta_autenticado(request):
    """True si quien consulta se identifico (sesion, token o clave)."""
    acceso = getattr(request, 'acceso', None)

    if acceso is not None:
        return bool(acceso) and acceso.via != seguridad.ABIERTO

    return seguridad.por_sesion(request) or seguridad.por_clave(request)


def endpoint(privado=False, abierto=False, metodos=('GET',)):
    """
    Decorador de las vistas de la API.

    Acepta los metodos indicados, comprueba el acceso y convierte cualquier
    error (incluido un 404) en una respuesta JSON coherente. Cuando el
    acceso se concede, deja el resultado en request.acceso para que la
    vista sepa quien pregunta.

    abierto=True omite la comprobacion: se usa en los recursos que no
    devuelven datos del sistema (el indice, la salud del servicio y el
    login), para que cualquiera pueda descubrir la API desde el navegador.

    metodos=('POST',) habilita el envio de datos; esas rutas quedan exentas
    de CSRF porque no se autentican con la cookie de sesion, sino con el
    cuerpo (login) o con el encabezado del token.
    """
    permitidos = tuple(metodos) + ('HEAD', 'OPTIONS')

    def decorador(vista):
        @functools.wraps(vista)
        def envoltura(request, *args, **kwargs):
            if request.method not in permitidos:
                return error(
                    f'Metodo {request.method} no permitido. '
                    f'Usa {" o ".join(metodos)}.',
                    405,
                )

            try:
                acceso = seguridad.autorizar(request, privado)
                request.acceso = acceso

                if not abierto and not acceso:
                    return no_autorizado(request, acceso)

                return vista(request, *args, **kwargs)
            except ErrorApi as exc:
                return error(exc.mensaje, exc.codigo, **exc.extra)
            except Http404 as exc:
                return error(str(exc) or 'Recurso no encontrado.', 404)

        if 'POST' in metodos:
            return csrf_exempt(envoltura)

        return envoltura
    return decorador


def entero(request, nombre, por_defecto, minimo=1, maximo=None):
    """Lee un parametro numerico de la URL con limites."""
    crudo = request.GET.get(nombre)

    if crudo in (None, ''):
        return por_defecto

    try:
        valor = int(crudo)
    except ValueError:
        raise ErrorApi(f'El parametro "{nombre}" debe ser un numero entero.')

    if valor < minimo:
        raise ErrorApi(f'El parametro "{nombre}" no puede ser menor que {minimo}.')

    if maximo is not None and valor > maximo:
        raise ErrorApi(f'El parametro "{nombre}" no puede ser mayor que {maximo}.')

    return valor


def paginar(queryset, request, serializador):
    """
    Pagina un queryset con ?pagina= y ?tam= y arma la respuesta estandar.

    Devuelve los objetos ya serializados junto al bloque "paginacion".
    """
    tam = entero(
        request, 'tam',
        settings.API_TAM_PAGINA,
        minimo=1,
        maximo=settings.API_TAM_PAGINA_MAX,
    )
    numero = entero(request, 'pagina', 1)

    paginador = Paginator(queryset, tam)

    try:
        pagina = paginador.page(numero)
    except EmptyPage:
        raise ErrorApi(
            f'La pagina {numero} no existe (hay {paginador.num_pages}).', 404,
        )

    return ok(
        [serializador(objeto) for objeto in pagina.object_list],
        paginacion={
            'pagina': pagina.number,
            'paginas': paginador.num_pages,
            'tam': tam,
            'total': paginador.count,
            'siguiente': pagina.next_page_number() if pagina.has_next() else None,
            'anterior': pagina.previous_page_number() if pagina.has_previous() else None,
        },
    )
