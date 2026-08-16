"""
Validacion de los datos que llegan en un POST, PUT o PATCH.

La idea es escribir cada endpoint como una tabla de campos:

    CAMPOS_TAREA = {
        'titulo': cadena(200),
        'descripcion': parrafo(obligatorio=False),
        'fecha_limite': momento(),
        'puntaje_maximo': numero(minimo=0, maximo=100),
    }

y dejar que aplicar() haga el trabajo. Solo se tocan los campos que vinieron
en el cuerpo, asi que el mismo diccionario sirve para crear (donde ademas se
exigen los obligatorios con exigir()) y para editar con PATCH, donde la
aplicacion manda unicamente lo que cambio.

Cuando algo no cuadra se levanta ErrorApi, que el decorador de respuestas.py
convierte en el JSON de error de siempre, con el nombre del campo dentro
para que la app pueda senalar el recuadro correcto.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .respuestas import ErrorApi


def _fallo(campo, mensaje):
    raise ErrorApi(
        f'El campo "{campo}" {mensaje}',
        400,
        motivo='campo_invalido',
        campo=campo,
    )


# ── Conversores ──────────────────────────────────────────────────────────────
# Cada uno devuelve una funcion (valor, campo) -> valor limpio.

def cadena(maximo=None, obligatorio=True):
    """Texto de una linea. obligatorio=False acepta que llegue vacio."""
    def convertir(valor, campo):
        limpio = '' if valor is None else str(valor).strip()

        if not limpio and obligatorio:
            _fallo(campo, 'no puede quedar vacio.')

        if maximo and len(limpio) > maximo:
            _fallo(campo, f'no puede pasar de {maximo} caracteres.')

        return limpio
    return convertir


def parrafo(obligatorio=False):
    """Texto largo: no se recorta, solo se limpian los bordes."""
    def convertir(valor, campo):
        limpio = '' if valor is None else str(valor).strip()

        if not limpio and obligatorio:
            _fallo(campo, 'no puede quedar vacio.')

        return limpio
    return convertir


def enlace(obligatorio=True):
    """URL. Se comprueba solo que empiece por http:// o https://."""
    def convertir(valor, campo):
        limpio = '' if valor is None else str(valor).strip()

        if not limpio:
            if obligatorio:
                _fallo(campo, 'no puede quedar vacio.')
            return ''

        if not limpio.lower().startswith(('http://', 'https://')):
            _fallo(campo, 'debe ser una direccion que empiece por http:// o https://.')

        return limpio
    return convertir


def opcion(elecciones, obligatorio=True):
    """
    Uno de los valores de un choices del modelo.

    elecciones es la clase TextChoices; el mensaje de error enumera los
    validos, que es lo que hace falta para corregirlo sin abrir el codigo.
    """
    validos = [item.value for item in elecciones]

    def convertir(valor, campo):
        limpio = '' if valor is None else str(valor).strip().lower()

        if not limpio:
            if obligatorio:
                _fallo(campo, 'no puede quedar vacio.')
            return ''

        if limpio not in validos:
            _fallo(campo, f'debe ser uno de: {", ".join(validos)}.')

        return limpio
    return convertir


def opcion_mayus(elecciones, obligatorio=True):
    """Igual que opcion pero para los choices escritos en mayusculas."""
    validos = [item.value for item in elecciones]

    def convertir(valor, campo):
        limpio = '' if valor is None else str(valor).strip().upper()

        if not limpio:
            if obligatorio:
                _fallo(campo, 'no puede quedar vacio.')
            return ''

        if limpio not in validos:
            _fallo(campo, f'debe ser uno de: {", ".join(validos)}.')

        return limpio
    return convertir


def entero(minimo=None, maximo=None, nulo=False):
    def convertir(valor, campo):
        if valor in (None, ''):
            if nulo:
                return None
            _fallo(campo, 'no puede quedar vacio.')

        try:
            numero_ = int(valor)
        except (TypeError, ValueError):
            _fallo(campo, 'debe ser un numero entero.')

        if minimo is not None and numero_ < minimo:
            _fallo(campo, f'no puede ser menor que {minimo}.')

        if maximo is not None and numero_ > maximo:
            _fallo(campo, f'no puede ser mayor que {maximo}.')

        return numero_
    return convertir


def numero(minimo=None, maximo=None, nulo=False):
    """Decimal, para notas y puntajes."""
    def convertir(valor, campo):
        if valor in (None, ''):
            if nulo:
                return None
            _fallo(campo, 'no puede quedar vacio.')

        try:
            valor_ = Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError):
            _fallo(campo, 'debe ser un numero.')

        if minimo is not None and valor_ < Decimal(str(minimo)):
            _fallo(campo, f'no puede ser menor que {minimo}.')

        if maximo is not None and valor_ > Decimal(str(maximo)):
            _fallo(campo, f'no puede ser mayor que {maximo}.')

        return valor_
    return convertir


def dia(nulo=False):
    """Fecha en formato AAAA-MM-DD."""
    def convertir(valor, campo):
        if valor in (None, ''):
            if nulo:
                return None
            _fallo(campo, 'no puede quedar vacio.')

        if isinstance(valor, date) and not isinstance(valor, datetime):
            return valor

        try:
            return date.fromisoformat(str(valor).strip()[:10])
        except ValueError:
            _fallo(campo, 'debe tener el formato AAAA-MM-DD.')
    return convertir


def momento(nulo=False):
    """
    Fecha y hora en formato ISO (AAAA-MM-DDTHH:MM).

    Si llega sin zona horaria se le pone la del sitio (America/Guayaquil),
    que es lo que espera quien escribe "2026-09-01T23:59" pensando en la
    hora de aqui.
    """
    def convertir(valor, campo):
        if valor in (None, ''):
            if nulo:
                return None
            _fallo(campo, 'no puede quedar vacio.')

        if isinstance(valor, datetime):
            fecha_hora = valor
        else:
            crudo = str(valor).strip().replace('Z', '+00:00')

            try:
                fecha_hora = datetime.fromisoformat(crudo)
            except ValueError:
                _fallo(campo, 'debe tener el formato AAAA-MM-DDTHH:MM.')

        if timezone.is_naive(fecha_hora):
            fecha_hora = timezone.make_aware(fecha_hora)

        return fecha_hora
    return convertir


def si_o_no():
    """Booleano tolerante: acepta true/false, 1/0, si/no."""
    def convertir(valor, campo):
        if isinstance(valor, bool):
            return valor

        limpio = str(valor).strip().lower()

        if limpio in ('1', 'true', 'si', 'yes', 'on'):
            return True

        if limpio in ('0', 'false', 'no', 'off', ''):
            return False

        _fallo(campo, 'debe ser verdadero o falso.')
    return convertir


def lista(obligatoria=False):
    """
    Lista JSON (las opciones de una pregunta, por ejemplo).

    Una lista vacia se guarda como [], nunca como NULL: el modelo la declara
    con default=list y no admite nulos, asi que devolver None aqui haria
    saltar la base de datos en vez de guardar "sin opciones".
    """
    def convertir(valor, campo):
        if valor in (None, ''):
            if obligatoria:
                _fallo(campo, 'no puede quedar vacio.')
            return []

        if not isinstance(valor, list):
            _fallo(campo, 'debe ser una lista.')

        return valor
    return convertir


def libre():
    """Cualquier valor JSON: se guarda tal cual (respuestas de un quiz)."""
    def convertir(valor, campo):
        return valor
    return convertir


# ── Aplicacion ───────────────────────────────────────────────────────────────

def exigir(datos, *campos):
    """
    Comprueba que el cuerpo traiga estos campos. Se usa al crear.

    Los enumera todos de una vez en lugar de parar en el primero: quien
    llama corrige su peticion en un solo viaje.
    """
    faltan = [
        campo for campo in campos
        if campo not in datos or datos[campo] in (None, '')
    ]

    if faltan:
        raise ErrorApi(
            f'Faltan campos obligatorios: {", ".join(faltan)}.',
            400,
            motivo='faltan_campos',
            campos=faltan,
        )


def aplicar(objeto, datos, mapa):
    """
    Copia al objeto los campos del cuerpo que aparecen en el mapa.

    Los que no vengan se quedan como estaban: por eso un PATCH puede mandar
    solo el campo que cambio. Devuelve el objeto sin guardarlo, para que
    quien llama pueda anadir lo suyo antes del save().
    """
    for campo, convertir in mapa.items():
        if campo in datos:
            setattr(objeto, campo, convertir(datos[campo], campo))

    return objeto


def solo_estos(datos, permitidos, contexto=''):
    """
    Rechaza los campos que este rol no tiene derecho a tocar.

    Un estudiante puede editar su telefono, no su rol; en vez de ignorar el
    campo en silencio (y dejarlo creyendo que lo cambio), se le dice que no
    puede. El silencio en una API es la peor respuesta posible.
    """
    intrusos = [campo for campo in datos if campo not in permitidos]

    if intrusos:
        raise ErrorApi(
            f'No puedes modificar estos campos{contexto}: '
            f'{", ".join(sorted(intrusos))}. '
            f'Los que si puedes son: {", ".join(sorted(permitidos))}.',
            403,
            motivo='campo_no_permitido',
            campos=sorted(intrusos),
        )
