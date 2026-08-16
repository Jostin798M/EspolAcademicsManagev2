"""
Modulo de permisos de la API.

Responde a dos preguntas distintas, y conviene no mezclarlas:

    ¿QUE puede hacer? -> puede(usuario, recurso, accion)
    ¿SOBRE QUE datos? -> alcance_de(usuario, recurso, accion)

La primera es la matriz PERMISOS de mas abajo: para cada rol, que acciones
(ver, crear, editar, eliminar) tiene sobre cada recurso (cursos, tareas,
usuarios...). La segunda es el alcance: dos personas pueden tener el mismo
permiso "editar cursos" y aun asi no tocar los mismos cursos, porque el
administrador manda en su facultad y el profesor solo en los suyos.

Los cuatro roles efectivos no son los tres del modelo Usuario. En la base de
datos un profesor y un estudiante son los dos rol USER; lo que los distingue
es como estan inscritos en los cursos. rol_efectivo() hace esa traduccion, y
a partir de ahi todo el modulo razona con PROFESOR y ESTUDIANTE.

Este modulo no sabe de HTTP: devuelve datos y querysets. Quien decide que
responder es seguridad.py (si deja pasar) y views.py (que JSON envia).
"""
from django.db.models import Q

from accounts.models import Usuario
from cursos.models import Curso, Facultad, Inscripcion

# ── Roles efectivos ──────────────────────────────────────────────────────────

SUPERADMIN = 'SUPERADMIN'
ADMIN = 'ADMIN'
PROFESOR = 'PROFESOR'
ESTUDIANTE = 'ESTUDIANTE'

#: Quien no ha iniciado sesion, cuando el sitio esta en modo publico. No es
#: un rol de la base de datos -no hay ninguna cuenta con este rol-, pero se
#: modela como uno mas para que el visitante pase por la misma matriz que
#: todos los demas en vez de por un camino aparte lleno de excepciones.
VISITANTE = 'VISITANTE'

#: Los roles que puede tener una cuenta. VISITANTE queda fuera a proposito:
#: nadie inicia sesion como visitante.
ROLES = (SUPERADMIN, ADMIN, PROFESOR, ESTUDIANTE)

ETIQUETA_ROL = {
    SUPERADMIN: 'Super administrador',
    ADMIN: 'Administrador de facultad',
    PROFESOR: 'Profesor',
    ESTUDIANTE: 'Estudiante',
    VISITANTE: 'Visitante',
}

# ── Acciones ─────────────────────────────────────────────────────────────────

VER = 'ver'
CREAR = 'crear'
EDITAR = 'editar'
ELIMINAR = 'eliminar'

ACCIONES = (VER, CREAR, EDITAR, ELIMINAR)

# Metodo HTTP -> accion. Sirve para que una vista con varios metodos sepa
# que permiso pedir sin repetir la equivalencia en cada endpoint.
ACCION_DE_METODO = {
    'GET': VER,
    'HEAD': VER,
    'OPTIONS': VER,
    'POST': CREAR,
    'PUT': EDITAR,
    'PATCH': EDITAR,
    'DELETE': ELIMINAR,
}

# ── Alcances ─────────────────────────────────────────────────────────────────
# Sobre que subconjunto de datos vale un permiso.

TODO = 'todo'            # toda la base de datos
FACULTAD = 'facultad'    # lo que cuelga de su facultad
CURSOS = 'cursos'        # solo los cursos que dicta o cursa
PROPIO = 'propio'        # solo sus propios registros

ETIQUETA_ALCANCE = {
    TODO: 'Todos los registros del sistema',
    FACULTAD: 'Solo los de su facultad',
    CURSOS: 'Solo los de sus cursos',
    PROPIO: 'Solo los suyos',
}

# ── Recursos ─────────────────────────────────────────────────────────────────

FACULTADES = 'facultades'
CURSOS_R = 'cursos'
MODULOS = 'modulos'
MATERIALES = 'materiales'
TAREAS = 'tareas'
ENTREGAS = 'entregas'
QUIZZES = 'quizzes'
PREGUNTAS = 'preguntas'
INSCRIPCIONES = 'inscripciones'
USUARIOS = 'usuarios'
PROGRESO = 'progreso'
REPORTES = 'reportes'

RECURSOS = (
    FACULTADES, CURSOS_R, MODULOS, MATERIALES, TAREAS, ENTREGAS,
    QUIZZES, PREGUNTAS, INSCRIPCIONES, USUARIOS, PROGRESO, REPORTES,
)

ETIQUETA_RECURSO = {
    FACULTADES: 'Facultades',
    CURSOS_R: 'Cursos',
    MODULOS: 'Modulos',
    MATERIALES: 'Materiales de estudio',
    TAREAS: 'Tareas',
    ENTREGAS: 'Entregas de tareas',
    QUIZZES: 'Quizzes',
    PREGUNTAS: 'Preguntas de quiz',
    INSCRIPCIONES: 'Inscripciones',
    USUARIOS: 'Usuarios',
    PROGRESO: 'Progreso de modulos',
    REPORTES: 'Reportes e indicadores',
}


# ── La matriz ────────────────────────────────────────────────────────────────
# {rol: {recurso: {accion: alcance}}}. Si la accion no aparece, no se puede.
# Se lee como una tabla: cada fila es "este rol, sobre este recurso, puede
# estas acciones, y solo sobre estos datos".

PERMISOS = {
    SUPERADMIN: {
        recurso: {accion: TODO for accion in ACCIONES}
        for recurso in RECURSOS
    },

    ADMIN: {
        # Ve el catalogo entero de facultades, pero solo retoca la suya.
        FACULTADES:    {VER: TODO, EDITAR: FACULTAD},
        CURSOS_R:      {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD, ELIMINAR: FACULTAD},
        MODULOS:       {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD, ELIMINAR: FACULTAD},
        MATERIALES:    {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD, ELIMINAR: FACULTAD},
        TAREAS:        {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD, ELIMINAR: FACULTAD},
        ENTREGAS:      {VER: FACULTAD, EDITAR: FACULTAD},
        QUIZZES:       {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD, ELIMINAR: FACULTAD},
        PREGUNTAS:     {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD, ELIMINAR: FACULTAD},
        INSCRIPCIONES: {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD, ELIMINAR: FACULTAD},
        # Da de alta y corrige personas de su facultad; darlas de baja de
        # todo el sistema se lo deja al super administrador.
        USUARIOS:      {VER: FACULTAD, CREAR: FACULTAD, EDITAR: FACULTAD},
        PROGRESO:      {VER: FACULTAD},
        REPORTES:      {VER: FACULTAD},
    },

    PROFESOR: {
        FACULTADES:    {VER: TODO},
        # No crea ni borra cursos (eso es de la facultad), pero manda dentro
        # de los suyos: contenido, evaluaciones y notas.
        CURSOS_R:      {VER: CURSOS, EDITAR: CURSOS},
        MODULOS:       {VER: CURSOS, CREAR: CURSOS, EDITAR: CURSOS, ELIMINAR: CURSOS},
        MATERIALES:    {VER: CURSOS, CREAR: CURSOS, EDITAR: CURSOS, ELIMINAR: CURSOS},
        TAREAS:        {VER: CURSOS, CREAR: CURSOS, EDITAR: CURSOS, ELIMINAR: CURSOS},
        ENTREGAS:      {VER: CURSOS, EDITAR: CURSOS},
        QUIZZES:       {VER: CURSOS, CREAR: CURSOS, EDITAR: CURSOS, ELIMINAR: CURSOS},
        PREGUNTAS:     {VER: CURSOS, CREAR: CURSOS, EDITAR: CURSOS, ELIMINAR: CURSOS},
        INSCRIPCIONES: {VER: CURSOS, CREAR: CURSOS, ELIMINAR: CURSOS},
        # Ve la ficha de sus estudiantes; la unica que edita es la suya.
        USUARIOS:      {VER: CURSOS, EDITAR: PROPIO},
        PROGRESO:      {VER: CURSOS},
        REPORTES:      {VER: CURSOS},
    },

    ESTUDIANTE: {
        FACULTADES:    {VER: TODO},
        CURSOS_R:      {VER: CURSOS},
        MODULOS:       {VER: CURSOS},
        MATERIALES:    {VER: CURSOS},
        TAREAS:        {VER: CURSOS},
        # Entrega y corrige su entrega mientras no este calificada.
        ENTREGAS:      {VER: PROPIO, CREAR: PROPIO, EDITAR: PROPIO},
        QUIZZES:       {VER: CURSOS},
        PREGUNTAS:     {VER: CURSOS},
        INSCRIPCIONES: {VER: PROPIO},
        USUARIOS:      {VER: PROPIO, EDITAR: PROPIO},
        # Marca sus modulos como completados.
        PROGRESO:      {VER: PROPIO, EDITAR: PROPIO},
        REPORTES:      {VER: PROPIO},
    },

    # Solo cuando API_MODO='publica'. Ve el catalogo academico como una
    # vitrina y no puede tocar nada ni acercarse a un dato personal: no hay
    # ninguna entrada de USUARIOS, ENTREGAS ni INSCRIPCIONES en su fila.
    VISITANTE: {
        FACULTADES: {VER: TODO},
        CURSOS_R:   {VER: TODO},
        MODULOS:    {VER: TODO},
        MATERIALES: {VER: TODO},
        TAREAS:     {VER: TODO},
        QUIZZES:    {VER: TODO},
        PREGUNTAS:  {VER: TODO},
        REPORTES:   {VER: TODO},
    },
}


# ── Que rol tiene de verdad ──────────────────────────────────────────────────

def rol_efectivo(usuario):
    """
    Traduce el rol de la base de datos al rol con el que trabaja la API.

    SUPERADMIN y ADMIN salen tal cual del campo rol. Un USER puede ser
    profesor o estudiante, y eso no esta en el campo: se mira si dicta algun
    curso (es su profesor titular o esta inscrito como PROFESOR). Si no
    dicta ninguno, entra como estudiante.

    Un superusuario de Django es siempre SUPERADMIN, tenga el rol que tenga:
    es quien administra la instalacion.
    """
    if usuario is None:
        return None

    # Las dos identidades sin persona detras se reconocen por su rol, sin
    # tocar la base de datos: no tienen inscripciones que consultar.
    if isinstance(usuario, Visitante):
        return VISITANTE

    if getattr(usuario, 'is_superuser', False):
        return SUPERADMIN

    rol = getattr(usuario, 'rol', '')

    if rol == Usuario.Rol.SUPERADMIN:
        return SUPERADMIN

    if rol == Usuario.Rol.ADMIN:
        return ADMIN

    dicta = (
        Curso.objects.filter(profesor=usuario).exists()
        or Inscripcion.objects.filter(
            usuario=usuario,
            rol_en_curso=Inscripcion.RolEnCurso.PROFESOR,
        ).exists()
    )

    return PROFESOR if dicta else ESTUDIANTE


def tabla_de(usuario):
    """La fila de PERMISOS que le toca a este usuario."""
    return PERMISOS.get(rol_efectivo(usuario), {})


def puede(usuario, recurso, accion):
    """¿Tiene este usuario permiso de accion sobre recurso?"""
    return alcance_de(usuario, recurso, accion) is not None


def alcance_de(usuario, recurso, accion):
    """
    Sobre que datos vale el permiso, o None si no lo tiene.

    Devolver None y devolver TODO son los dos extremos: sin permiso, o sin
    limite. Los intermedios (FACULTAD, CURSOS, PROPIO) los aplica despues
    filtrar_*() sobre el queryset.
    """
    return tabla_de(usuario).get(recurso, {}).get(accion)


def acciones_sobre(usuario, recurso):
    """Lista de acciones permitidas sobre un recurso, en orden fijo."""
    permitidas = tabla_de(usuario).get(recurso, {})

    return [accion for accion in ACCIONES if accion in permitidas]


# ── Que datos le tocan ───────────────────────────────────────────────────────

def facultades_de(usuario):
    """
    Facultades que administra: la suya y aquellas donde figura como admin.

    Son dos cosas distintas en el modelo (el campo facultad del usuario y el
    campo admin de la facultad) y en la practica coinciden, pero se aceptan
    las dos para que un administrador no se quede fuera por un dato suelto.
    """
    condicion = Q(admin=usuario)

    if getattr(usuario, 'facultad_id', None):
        condicion |= Q(pk=usuario.facultad_id)

    return Facultad.objects.filter(condicion)


def ids_facultades_de(usuario):
    return set(facultades_de(usuario).values_list('id_facultad', flat=True))


def cursos_visibles(usuario):
    """
    Queryset de los cursos que este usuario puede ver, ya recortado.

    Es la pieza central del alcance: casi todo lo demas (modulos, tareas,
    quizzes, inscripciones) cuelga de un curso, asi que se filtra
    preguntando si el curso esta aqui dentro.
    """
    rol = rol_efectivo(usuario)

    if rol == SUPERADMIN:
        return Curso.objects.all()

    if rol == ADMIN:
        return Curso.objects.filter(facultad__in=facultades_de(usuario))

    if rol == PROFESOR:
        return Curso.objects.filter(
            Q(profesor=usuario)
            | Q(inscripciones__usuario=usuario,
                inscripciones__rol_en_curso=Inscripcion.RolEnCurso.PROFESOR),
        ).distinct()

    if rol == ESTUDIANTE:
        return Curso.objects.filter(
            inscripciones__usuario=usuario,
            inscripciones__rol_en_curso=Inscripcion.RolEnCurso.ESTUDIANTE,
        ).distinct()

    return Curso.objects.none()


def ids_cursos_de(usuario):
    return set(cursos_visibles(usuario).values_list('id_curso', flat=True))


def alcanza_curso(usuario, curso, accion=VER):
    """
    ¿Puede este usuario hacer accion sobre ESTE curso concreto?

    Comprueba las dos mitades: que el rol tenga el permiso, y que el curso
    caiga dentro de su alcance.
    """
    alcance = alcance_de(usuario, CURSOS_R, accion)

    if alcance is None:
        return False

    if alcance == TODO:
        return True

    if alcance == FACULTAD:
        return curso.facultad_id in ids_facultades_de(usuario)

    return curso.id_curso in ids_cursos_de(usuario)


def puede_sobre_curso(usuario, recurso, accion, curso):
    """
    Igual que alcanza_curso pero para lo que cuelga de un curso.

    Un profesor puede EDITAR tareas (permiso) pero solo las de sus cursos
    (alcance); esta funcion junta las dos comprobaciones para modulos,
    materiales, tareas, quizzes y preguntas.
    """
    alcance = alcance_de(usuario, recurso, accion)

    if alcance is None:
        return False

    if alcance == TODO:
        return True

    if alcance == FACULTAD:
        return curso.facultad_id in ids_facultades_de(usuario)

    if alcance == CURSOS:
        return curso.id_curso in ids_cursos_de(usuario)

    # PROPIO sobre algo que cuelga de un curso: hace falta al menos estar en
    # el curso; quien llama afina despues si el registro es suyo.
    return curso.id_curso in ids_cursos_de(usuario)


# ── Filtros para los listados ────────────────────────────────────────────────

def filtrar_cursos(consulta, usuario):
    """Recorta un queryset de cursos al alcance del usuario."""
    if alcance_de(usuario, CURSOS_R, VER) == TODO:
        return consulta

    return consulta.filter(pk__in=ids_cursos_de(usuario))


def filtrar_por_curso(consulta, usuario, recurso, campo='curso'):
    """
    Recorta cualquier queryset que apunte a un curso (modulos, tareas...).

    campo es la ruta hasta el curso: 'curso' en Tarea, 'modulo__curso' en
    Material, etc.
    """
    if alcance_de(usuario, recurso, VER) == TODO:
        return consulta

    return consulta.filter(**{f'{campo}__in': ids_cursos_de(usuario)})


def filtrar_usuarios(consulta, usuario):
    """
    Recorta un listado de personas segun quien pregunta.

    Cada rol ve un circulo distinto: el super administrador a todos, el
    administrador a los de su facultad, el profesor a los inscritos en sus
    cursos (mas el mismo) y el estudiante unicamente su propia ficha.
    """
    alcance = alcance_de(usuario, USUARIOS, VER)

    if alcance == TODO:
        return consulta

    if alcance == FACULTAD:
        return consulta.filter(facultad__in=facultades_de(usuario))

    if alcance == CURSOS:
        return consulta.filter(
            Q(inscripciones__curso__in=ids_cursos_de(usuario))
            | Q(pk=usuario.pk),
        ).distinct()

    if alcance == PROPIO:
        return consulta.filter(pk=usuario.pk)

    return consulta.none()


def filtrar_inscripciones(consulta, usuario):
    """Recorta inscripciones: por facultad, por curso o solo las suyas."""
    alcance = alcance_de(usuario, INSCRIPCIONES, VER)

    if alcance == TODO:
        return consulta

    if alcance == FACULTAD:
        return consulta.filter(curso__facultad__in=facultades_de(usuario))

    if alcance == CURSOS:
        return consulta.filter(curso__in=ids_cursos_de(usuario))

    if alcance == PROPIO:
        return consulta.filter(usuario=usuario)

    return consulta.none()


def filtrar_entregas(consulta, usuario):
    """Recorta entregas: el estudiante solo ve las que mando el mismo."""
    alcance = alcance_de(usuario, ENTREGAS, VER)

    if alcance == TODO:
        return consulta

    if alcance == FACULTAD:
        return consulta.filter(tarea__curso__facultad__in=facultades_de(usuario))

    if alcance == CURSOS:
        return consulta.filter(tarea__curso__in=ids_cursos_de(usuario))

    if alcance == PROPIO:
        return consulta.filter(usuario=usuario)

    return consulta.none()


# ── Retrato de los permisos, para el token y para las apps ───────────────────

def resumen(usuario):
    """
    Los permisos del usuario en JSON, tal como los recibe la aplicacion.

    Es lo que viaja en la respuesta del login y en /api/mi/permisos/: la app
    movil y la web lo leen para decidir que botones dibujar. No es la
    autoridad -el servidor vuelve a comprobar todo en cada peticion-, es el
    mapa que evita ensenar un boton que va a terminar en un 403.
    """
    rol = rol_efectivo(usuario)
    tabla = PERMISOS.get(rol, {})

    recursos = {}

    for recurso in RECURSOS:
        permitidas = tabla.get(recurso, {})

        recursos[recurso] = {
            'etiqueta': ETIQUETA_RECURSO[recurso],
            'ver': permitidas.get(VER),
            'crear': permitidas.get(CREAR),
            'editar': permitidas.get(EDITAR),
            'eliminar': permitidas.get(ELIMINAR),
            'acciones': [accion for accion in ACCIONES if accion in permitidas],
        }

    return {
        'rol': rol,
        'rol_etiqueta': ETIQUETA_ROL.get(rol, rol),
        'alcances': ETIQUETA_ALCANCE,
        'recursos': recursos,
    }


def resumen_corto(usuario):
    """
    Version compacta que se guarda dentro del token: {recurso: [acciones]}.

    En la fila del token no hacen falta las etiquetas ni los alcances, solo
    que se pueda auditar despues con que permisos se emitio.
    """
    tabla = PERMISOS.get(rol_efectivo(usuario), {})

    return {
        recurso: [accion for accion in ACCIONES if accion in tabla.get(recurso, {})]
        for recurso in RECURSOS
        if tabla.get(recurso)
    }


#: Recursos que cuelgan de un curso: son los que tienen sentido preguntar
#: "¿que puedo hacer aqui dentro?".
RECURSOS_DE_CURSO = (
    CURSOS_R, MODULOS, MATERIALES, TAREAS, ENTREGAS,
    QUIZZES, PREGUNTAS, INSCRIPCIONES,
)


def acciones_en_curso(usuario, curso):
    """
    Que puede hacer este usuario DENTRO de este curso: {recurso: [acciones]}.

    Es resumen() aterrizado en un curso concreto. La diferencia importa: un
    profesor "puede crear tareas" en general, pero en el curso que esta
    mirando quiza no, porque no es suyo. La app movil pinta los botones de
    la pantalla del curso con esto, y asi no ofrece nada que vaya a acabar
    en un 403.
    """
    permitido = {}

    for recurso in RECURSOS_DE_CURSO:
        acciones = [
            accion for accion in ACCIONES
            if puede_sobre_curso(usuario, recurso, accion, curso)
        ]

        if acciones:
            permitido[recurso] = acciones

    return permitido


# ── El sitio llamandose a si mismo ───────────────────────────────────────────

class SitioWeb:
    """
    Identidad de quien entra con la clave del sitio (X-API-Key).

    No hay una persona detras: es un script propio, ejecutado por el dueno
    del servidor. Se comporta como un super administrador y por eso responde
    a las mismas preguntas que un Usuario (is_superuser, rol), pero no tiene
    ficha ni facultad, y por eso nunca se le devuelve como "usuario" en las
    respuestas: se le devuelve None.
    """

    is_superuser = True
    is_authenticated = True
    is_active = True
    rol = SUPERADMIN
    estado = 'activo'
    pk = None
    facultad_id = None

    def __str__(self):
        return 'clave del sitio'


#: Instancia unica: no hace falta mas de una.
SITIO = SitioWeb()


def es_sitio(quien):
    """True si es la clave del sitio y no una persona registrada."""
    return isinstance(quien, SitioWeb)


class Visitante:
    """
    Quien mira la API sin haber iniciado sesion, en modo publico.

    Tampoco hay una persona detras, pero al reves que la clave del sitio:
    este no puede nada mas que mirar el catalogo. Se le da forma de usuario
    para que atraviese la misma matriz de permisos que los demas.
    """

    is_superuser = False
    is_authenticated = False
    is_active = True
    rol = VISITANTE
    estado = 'activo'
    pk = None
    facultad_id = None

    def __str__(self):
        return 'visitante'


#: Instancia unica del visitante anonimo.
VISITA = Visitante()


def es_visitante(quien):
    """True si nadie ha iniciado sesion y el sitio esta en modo publico."""
    return isinstance(quien, Visitante)
