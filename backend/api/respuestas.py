"""
Utilidades comunes de la API: respuestas JSON, errores, clave y paginacion.

Se implementa con Django puro (JsonResponse) para no anadir dependencias
al servidor, que tiene una cuota de disco pequena.
"""
import functools

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from django.http import Http404, JsonResponse

from . import seguridad


class ErrorApi(Exception):
    """Error controlado que se devuelve al cliente en formato JSON."""

    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def ok(datos, **extra):
    """Respuesta correcta: {"ok": true, "datos": ...}."""
    cuerpo = {'ok': True, 'datos': datos}
    cuerpo.update(extra)
    return JsonResponse(cuerpo, json_dumps_params={'ensure_ascii': False})


def error(mensaje, codigo=400):
    """Respuesta de error: {"ok": false, "error": "..."}."""
    return JsonResponse(
        {'ok': False, 'error': mensaje, 'codigo': codigo},
        status=codigo,
        json_dumps_params={'ensure_ascii': False},
    )


def esta_autenticado(request):
    """True si quien consulta se identifico (sesion de superadmin o clave)."""
    return seguridad.por_sesion(request) or seguridad.por_clave(request)


def endpoint(privado=False, abierto=False):
    """
    Decorador de las vistas de la API.

    Acepta solo GET, valida la clave y convierte cualquier error
    (incluido un 404) en una respuesta JSON coherente.

    abierto=True omite la clave: se usa en los recursos que no devuelven
    datos del sistema (el indice y la comprobacion de salud), para que
    cualquiera pueda descubrir la API desde el navegador.
    """
    def decorador(vista):
        @functools.wraps(vista)
        def envoltura(request, *args, **kwargs):
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                return error(f'Metodo {request.method} no permitido. Usa GET.', 405)

            try:
                if not abierto:
                    acceso = seguridad.autorizar(request, privado)

                    if not acceso:
                        return error(acceso.mensaje, acceso.codigo)

                return vista(request, *args, **kwargs)
            except ErrorApi as exc:
                return error(exc.mensaje, exc.codigo)
            except Http404 as exc:
                return error(str(exc) or 'Recurso no encontrado.', 404)

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
