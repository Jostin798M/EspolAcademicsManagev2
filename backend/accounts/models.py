"""
Modelos del modulo ACCOUNTS.

Contiene la entidad Usuario, que representa a toda persona que interactua
con el sistema academico (super administrador, administrador de facultad,
profesor y estudiante).
"""
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class UsuarioManager(BaseUserManager):
    """Gestor del modelo Usuario: el identificador de acceso es el correo."""

    def create_user(self, correo, password=None, **extra_fields):
        if not correo:
            raise ValueError("El correo es obligatorio.")
        correo = self.normalize_email(correo)
        user = self.model(correo=correo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo, password=None, **extra_fields):
        extra_fields.setdefault('rol', Usuario.Rol.SUPERADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(correo, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Persona registrada en ESPOL Academics."""

    class Rol(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin Facultad'
        USER = 'USER', 'Usuario'

    class EstadoCivil(models.TextChoices):
        SOLTERO = 'soltero', 'Soltero/a'
        CASADO = 'casado', 'Casado/a'
        DIVORCIADO = 'divorciado', 'Divorciado/a'
        SEPARADO = 'separado', 'Separado/a'
        UNION_LIBRE = 'union libre', 'Union libre'

    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        INACTIVO = 'inactivo', 'Inactivo'

    id_usuario = models.BigAutoField(
        primary_key=True,
        db_column='id_usuario',
    )

    nombres = models.CharField(
        max_length=100,
        db_column='nombres',
        verbose_name='Nombres',
    )

    apellidos = models.CharField(
        max_length=100,
        db_column='apellidos',
        verbose_name='Apellidos',
    )

    identificacion = models.CharField(
        max_length=20,
        unique=True,
        db_column='identificacion',
        verbose_name='Identificacion',
    )

    telefono = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        db_column='telefono',
        verbose_name='Telefono convencional',
    )

    celular = models.CharField(
        max_length=15,
        db_column='celular',
        verbose_name='Celular',
    )

    correo = models.EmailField(
        unique=True,
        db_column='correo',
        verbose_name='Correo electronico',
    )

    direccion = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        db_column='direccion',
        verbose_name='Direccion',
    )

    estado_civil = models.CharField(
        max_length=20,
        choices=EstadoCivil.choices,
        default=EstadoCivil.SOLTERO,
        db_column='estado_civil',
        verbose_name='Estado civil',
    )

    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_column='estado',
        verbose_name='Estado de la cuenta',
    )

    facultad = models.ForeignKey(
        'cursos.Facultad',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='id_facultad',
        related_name='usuarios',
        verbose_name='Facultad a la que pertenece',
    )

    fecha_registro = models.DateField(
        auto_now_add=True,
        db_column='fecha_registro',
        verbose_name='Fecha de registro',
    )

    rol = models.CharField(
        max_length=15,
        choices=Rol.choices,
        default=Rol.USER,
        db_column='rol',
        verbose_name='Rol del sistema',
    )

    is_active = models.BooleanField(
        default=True,
        db_column='activo',
        verbose_name='Puede iniciar sesion',
    )

    is_staff = models.BooleanField(
        default=False,
        db_column='es_staff',
        verbose_name='Acceso al panel de administracion',
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombres', 'apellidos', 'identificacion', 'celular']

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.correo})"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def iniciales(self):
        return (self.nombres[0] + self.apellidos[0]).upper()
