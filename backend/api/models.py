"""
Modelos del modulo API.

El unico modelo propio es TokenApi: la credencial que se entrega a una
aplicacion externa cuando alguien inicia sesion en /api/auth/login/ con una
cuenta de super administrador de esta base de datos.

En la tabla NO se guarda el token, sino su huella SHA-256. Si alguien lee la
base de datos no puede reconstruirlo; el texto del token solo se ve una vez,
en la respuesta del login.

Cada token queda sellado con el rol y los permisos que tenia su dueno al
emitirlo (campos rol y permisos). Ese sello NO es lo que autoriza -en cada
peticion se vuelven a calcular los permisos reales del usuario, para que un
cambio de rol tenga efecto al instante-, sino el registro de con que
credencial se entrego: sirve para auditar y para que la aplicacion sepa, al
recibirlo, que puede dibujar en su pantalla.

El resto de la API expone en JSON los modelos de accounts, cursos y
evaluaciones (ver serializadores.py).
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

# Cada cuanto se refresca "ultimo_uso": evita un UPDATE por peticion.
MINUTOS_ENTRE_REGISTROS_DE_USO = 5


def huella_de(token):
    """Huella SHA-256 del token en texto. Es lo unico que se almacena."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class TokenApiManager(models.Manager):
    """Crear y buscar tokens sin que el texto plano toque la base de datos."""

    def crear(self, usuario, aplicacion='', dias=None, ip=None):
        """
        Genera un token nuevo para un usuario.

        Devuelve la pareja (objeto, texto_plano). El texto plano no se puede
        recuperar despues: se entrega una sola vez a quien inicio sesion.
        """
        from . import permisos

        plano = secrets.token_urlsafe(36)

        if dias is None:
            dias = getattr(settings, 'API_TOKEN_DIAS', 30)

        expira = timezone.now() + timedelta(days=dias) if dias else None

        token = self.create(
            usuario=usuario,
            aplicacion=(aplicacion or '')[:100],
            prefijo=plano[:TokenApi.LARGO_PREFIJO],
            huella=huella_de(plano),
            expira=expira,
            ip_origen=ip,
            rol=permisos.rol_efectivo(usuario) or '',
            permisos=permisos.resumen_corto(usuario),
        )

        return token, plano

    def buscar(self, plano):
        """
        Busca un token por su texto. Devuelve None si no existe ninguno.

        Devuelve tambien los revocados y los caducados: quien llama decide
        que responder, para poder explicar el motivo exacto.
        """
        if not plano:
            return None

        return self.select_related('usuario', 'usuario__facultad').filter(
            huella=huella_de(plano),
        ).first()


class TokenApi(models.Model):
    """Credencial de acceso a la API para una aplicacion externa."""

    LARGO_PREFIJO = 12

    id_token = models.BigAutoField(
        primary_key=True,
        db_column='id_token',
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='id_usuario',
        related_name='tokens_api',
        verbose_name='Dueno del token',
    )

    aplicacion = models.CharField(
        max_length=100,
        blank=True,
        db_column='aplicacion',
        verbose_name='Aplicacion que lo solicito',
    )

    rol = models.CharField(
        max_length=15,
        blank=True,
        db_column='rol',
        verbose_name='Rol con el que se emitio',
        help_text='SUPERADMIN, ADMIN, PROFESOR o ESTUDIANTE en el momento '
                  'de la emision. El rol vigente se recalcula en cada '
                  'peticion; este campo es el registro de como nacio.',
    )

    permisos = models.JSONField(
        default=dict,
        blank=True,
        db_column='permisos',
        verbose_name='Permisos con los que se emitio',
        help_text='{recurso: [acciones]} tal como estaban al crearlo.',
    )

    prefijo = models.CharField(
        max_length=LARGO_PREFIJO,
        db_column='prefijo',
        verbose_name='Inicio del token',
        help_text='Primeros caracteres, para reconocerlo en este listado.',
    )

    huella = models.CharField(
        max_length=64,
        unique=True,
        db_column='huella',
        verbose_name='Huella SHA-256',
    )

    creado = models.DateTimeField(
        auto_now_add=True,
        db_column='creado',
        verbose_name='Fecha de creacion',
    )

    expira = models.DateTimeField(
        null=True,
        blank=True,
        db_column='expira',
        verbose_name='Caduca el',
        help_text='Vacio = no caduca.',
    )

    ultimo_uso = models.DateTimeField(
        null=True,
        blank=True,
        db_column='ultimo_uso',
        verbose_name='Ultimo uso',
    )

    revocado = models.BooleanField(
        default=False,
        db_column='revocado',
        verbose_name='Revocado',
    )

    ip_origen = models.GenericIPAddressField(
        null=True,
        blank=True,
        db_column='ip_origen',
        verbose_name='IP desde la que se pidio',
    )

    objects = TokenApiManager()

    class Meta:
        db_table = 'token_api'
        verbose_name = 'Token de API'
        verbose_name_plural = 'Tokens de API'
        ordering = ['-creado']

    def __str__(self):
        return f"{self.prefijo}... ({self.usuario.correo} · {self.rol or '?'})"

    @property
    def caducado(self):
        return self.expira is not None and self.expira <= timezone.now()

    @property
    def vigente(self):
        return not self.revocado and not self.caducado

    def revocar(self):
        if not self.revocado:
            self.revocado = True
            self.save(update_fields=['revocado'])

    def registrar_uso(self):
        """Anota el ultimo uso, como mucho una vez cada pocos minutos."""
        ahora = timezone.now()
        margen = timedelta(minutes=MINUTOS_ENTRE_REGISTROS_DE_USO)

        if self.ultimo_uso and ahora - self.ultimo_uso < margen:
            return

        self.ultimo_uso = ahora
        self.save(update_fields=['ultimo_uso'])
