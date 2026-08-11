"""
Modelos del modulo CURSOS.

Agrupa la estructura academica del sistema:
Facultad, Curso, FormulaComponente, Inscripcion, Modulo, Material y
ProgresoModulo.
"""
from django.conf import settings
from django.db import models


class Facultad(models.Model):
    """Unidad academica de ESPOL a la que pertenecen los cursos."""

    id_facultad = models.BigAutoField(
        primary_key=True,
        db_column='id_facultad',
    )

    nombre = models.CharField(
        max_length=200,
        unique=True,
        db_column='nombre',
        verbose_name='Nombre de la facultad',
    )

    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_column='codigo',
        verbose_name='Codigo',
    )

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='id_admin',
        related_name='facultades_administradas',
        verbose_name='Administrador de la facultad',
    )

    class Meta:
        db_table = 'facultad'
        verbose_name = 'Facultad'
        verbose_name_plural = 'Facultades'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Curso(models.Model):
    """Curso dictado por un profesor dentro de una facultad."""

    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        ARCHIVADO = 'archivado', 'Archivado'

    id_curso = models.BigAutoField(
        primary_key=True,
        db_column='id_curso',
    )

    nombre = models.CharField(
        max_length=200,
        db_column='nombre',
        verbose_name='Nombre del curso',
    )

    codigo = models.CharField(
        max_length=20,
        unique=True,
        db_column='codigo',
        verbose_name='Codigo del curso',
    )

    descripcion = models.TextField(
        db_column='descripcion',
        verbose_name='Descripcion',
    )

    facultad = models.ForeignKey(
        Facultad,
        on_delete=models.PROTECT,
        db_column='id_facultad',
        related_name='cursos',
        verbose_name='Facultad',
    )

    profesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_profesor',
        related_name='cursos_como_profesor',
        verbose_name='Profesor responsable',
    )

    fecha_inicio = models.DateField(
        db_column='fecha_inicio',
        verbose_name='Fecha de inicio',
    )

    fecha_fin = models.DateField(
        db_column='fecha_fin',
        verbose_name='Fecha de finalizacion',
    )

    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_column='estado',
        verbose_name='Estado del curso',
    )

    class Meta:
        db_table = 'curso'
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['-fecha_inicio', 'codigo']

        constraints = [
            models.CheckConstraint(
                condition=models.Q(fecha_fin__gte=models.F('fecha_inicio')),
                name='ck_curso_fechas_coherentes',
            ),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def archivar_si_vencido(self):
        """Archiva el curso cuando su fecha de fin ya paso."""
        from django.utils import timezone

        if self.estado == self.Estado.ACTIVO and self.fecha_fin < timezone.localdate():
            self.estado = self.Estado.ARCHIVADO
            self.save(update_fields=['estado'])


class FormulaComponente(models.Model):
    """Componente porcentual de la formula de calificacion de un curso."""

    id_componente = models.BigAutoField(
        primary_key=True,
        db_column='id_componente',
    )

    curso = models.ForeignKey(
        Curso,
        on_delete=models.PROTECT,
        db_column='id_curso',
        related_name='formula',
        verbose_name='Curso',
    )

    componente = models.CharField(
        max_length=100,
        db_column='componente',
        verbose_name='Nombre del componente',
    )

    porcentaje = models.PositiveSmallIntegerField(
        db_column='porcentaje',
        verbose_name='Porcentaje',
    )

    orden = models.PositiveSmallIntegerField(
        default=0,
        db_column='orden',
        verbose_name='Orden',
    )

    class Meta:
        db_table = 'formula_componente'
        verbose_name = 'Componente de formula'
        verbose_name_plural = 'Componentes de formula'
        ordering = ['curso', 'orden']

        constraints = [
            models.UniqueConstraint(
                fields=['curso', 'componente'],
                name='uq_formula_curso_componente',
            ),
            models.CheckConstraint(
                condition=models.Q(porcentaje__gte=1) & models.Q(porcentaje__lte=100),
                name='ck_formula_porcentaje_valido',
            ),
        ]

    def __str__(self):
        return f"{self.curso.codigo} - {self.componente} ({self.porcentaje}%)"


class Inscripcion(models.Model):
    """Vinculo de un usuario con un curso, como profesor o estudiante."""

    class RolEnCurso(models.TextChoices):
        PROFESOR = 'PROFESOR', 'Profesor'
        ESTUDIANTE = 'ESTUDIANTE', 'Estudiante'

    id_inscripcion = models.BigAutoField(
        primary_key=True,
        db_column='id_inscripcion',
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario',
        related_name='inscripciones',
        verbose_name='Usuario',
    )

    curso = models.ForeignKey(
        Curso,
        on_delete=models.PROTECT,
        db_column='id_curso',
        related_name='inscripciones',
        verbose_name='Curso',
    )

    rol_en_curso = models.CharField(
        max_length=15,
        choices=RolEnCurso.choices,
        default=RolEnCurso.ESTUDIANTE,
        db_column='rol_en_curso',
        verbose_name='Rol en el curso',
    )

    fecha = models.DateField(
        auto_now_add=True,
        db_column='fecha',
        verbose_name='Fecha de inscripcion',
    )

    class Meta:
        db_table = 'inscripcion'
        verbose_name = 'Inscripcion'
        verbose_name_plural = 'Inscripciones'
        ordering = ['curso', 'usuario']

        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'curso'],
                name='uq_inscripcion_usuario_curso',
            ),
        ]

    def __str__(self):
        return f"{self.usuario} en {self.curso.codigo} ({self.rol_en_curso})"


class Modulo(models.Model):
    """Unidad de contenido dentro de un curso."""

    id_modulo = models.BigAutoField(
        primary_key=True,
        db_column='id_modulo',
    )

    curso = models.ForeignKey(
        Curso,
        on_delete=models.PROTECT,
        db_column='id_curso',
        related_name='modulos',
        verbose_name='Curso',
    )

    titulo = models.CharField(
        max_length=200,
        db_column='titulo',
        verbose_name='Titulo del modulo',
    )

    descripcion = models.TextField(
        null=True,
        blank=True,
        db_column='descripcion',
        verbose_name='Descripcion',
    )

    orden = models.PositiveSmallIntegerField(
        default=1,
        db_column='orden',
        verbose_name='Orden',
    )

    class Meta:
        db_table = 'modulo'
        verbose_name = 'Modulo'
        verbose_name_plural = 'Modulos'
        ordering = ['curso', 'orden']

        constraints = [
            models.UniqueConstraint(
                fields=['curso', 'orden'],
                name='uq_modulo_curso_orden',
            ),
            models.CheckConstraint(
                condition=models.Q(orden__gte=1),
                name='ck_modulo_orden_positivo',
            ),
        ]

    def __str__(self):
        return f"{self.curso.codigo} - {self.orden}. {self.titulo}"


class Material(models.Model):
    """Recurso de estudio asociado a un modulo."""

    class Tipo(models.TextChoices):
        VIDEO = 'video', 'Video'
        PDF = 'pdf', 'PDF'
        ENLACE = 'enlace', 'Enlace externo'

    id_material = models.BigAutoField(
        primary_key=True,
        db_column='id_material',
    )

    modulo = models.ForeignKey(
        Modulo,
        on_delete=models.PROTECT,
        db_column='id_modulo',
        related_name='materiales',
        verbose_name='Modulo',
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.VIDEO,
        db_column='tipo',
        verbose_name='Tipo de material',
    )

    titulo = models.CharField(
        max_length=200,
        db_column='titulo',
        verbose_name='Titulo del material',
    )

    url = models.URLField(
        db_column='url',
        verbose_name='Enlace del recurso',
    )

    class Meta:
        db_table = 'material'
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        ordering = ['modulo', 'titulo']

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"


class ProgresoModulo(models.Model):
    """Avance de un estudiante sobre un modulo del curso."""

    id_progreso = models.BigAutoField(
        primary_key=True,
        db_column='id_progreso',
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario',
        related_name='progresos',
        verbose_name='Usuario',
    )

    modulo = models.ForeignKey(
        Modulo,
        on_delete=models.PROTECT,
        db_column='id_modulo',
        related_name='progresos',
        verbose_name='Modulo',
    )

    completado = models.BooleanField(
        default=False,
        db_column='completado',
        verbose_name='Modulo completado',
    )

    fecha = models.DateField(
        auto_now=True,
        db_column='fecha',
        verbose_name='Ultima actualizacion',
    )

    class Meta:
        db_table = 'progreso_modulo'
        verbose_name = 'Progreso de modulo'
        verbose_name_plural = 'Progresos de modulo'
        ordering = ['usuario', 'modulo']

        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'modulo'],
                name='uq_progreso_usuario_modulo',
            ),
        ]

    def __str__(self):
        estado = 'completado' if self.completado else 'pendiente'
        return f"{self.usuario} - {self.modulo.titulo} ({estado})"
