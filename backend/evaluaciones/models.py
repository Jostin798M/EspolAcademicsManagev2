"""
Modelos del modulo EVALUACIONES.

Agrupa los instrumentos de evaluacion del sistema academico:
Tarea, Entrega, Quiz, Pregunta y RespuestaQuiz.
"""
from django.conf import settings
from django.db import models

from cursos.models import Curso


class Tarea(models.Model):
    """Trabajo asignado por el profesor dentro de un curso."""

    id_tarea = models.BigAutoField(
        primary_key=True,
        db_column='id_tarea',
    )

    curso = models.ForeignKey(
        Curso,
        on_delete=models.PROTECT,
        db_column='id_curso',
        related_name='tareas',
        verbose_name='Curso',
    )

    titulo = models.CharField(
        max_length=200,
        db_column='titulo',
        verbose_name='Titulo de la tarea',
    )

    descripcion = models.TextField(
        db_column='descripcion',
        verbose_name='Descripcion',
    )

    criterios = models.TextField(
        null=True,
        blank=True,
        db_column='criterios',
        verbose_name='Criterios de calificacion',
    )

    fecha_limite = models.DateTimeField(
        db_column='fecha_limite',
        verbose_name='Fecha limite de entrega',
    )

    puntaje_maximo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10,
        db_column='puntaje_maximo',
        verbose_name='Puntaje maximo',
    )

    class Meta:
        db_table = 'tarea'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['fecha_limite', 'titulo']

        constraints = [
            models.UniqueConstraint(
                fields=['curso', 'titulo'],
                name='uq_tarea_curso_titulo',
            ),
            models.CheckConstraint(
                condition=models.Q(puntaje_maximo__gte=0),
                name='ck_tarea_puntaje_no_negativo',
            ),
        ]

    def __str__(self):
        return f"{self.curso.codigo} - {self.titulo}"


class Entrega(models.Model):
    """Envio de un estudiante para una tarea, con su calificacion."""

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ENTREGADO = 'entregado', 'Entregado'

    id_entrega = models.BigAutoField(
        primary_key=True,
        db_column='id_entrega',
    )

    tarea = models.ForeignKey(
        Tarea,
        on_delete=models.PROTECT,
        db_column='id_tarea',
        related_name='entregas',
        verbose_name='Tarea',
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario',
        related_name='entregas',
        verbose_name='Estudiante',
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_column='estado',
        verbose_name='Estado de la entrega',
    )

    fecha = models.DateTimeField(
        null=True,
        blank=True,
        db_column='fecha',
        verbose_name='Fecha de entrega',
    )

    texto = models.TextField(
        null=True,
        blank=True,
        db_column='texto',
        verbose_name='Respuesta escrita',
    )

    archivo = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        db_column='archivo',
        verbose_name='Archivo entregado',
    )

    imagen = models.URLField(
        null=True,
        blank=True,
        db_column='imagen',
        verbose_name='Imagen entregada',
    )

    link = models.URLField(
        null=True,
        blank=True,
        db_column='link',
        verbose_name='Enlace entregado',
    )

    nota = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        db_column='nota',
        verbose_name='Nota obtenida',
    )

    comentario = models.TextField(
        null=True,
        blank=True,
        db_column='comentario',
        verbose_name='Comentario del profesor',
    )

    class Meta:
        db_table = 'entrega'
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'
        ordering = ['tarea', 'usuario']

        constraints = [
            models.UniqueConstraint(
                fields=['tarea', 'usuario'],
                name='uq_entrega_tarea_usuario',
            ),
            models.CheckConstraint(
                condition=models.Q(nota__isnull=True) | models.Q(nota__gte=0),
                name='ck_entrega_nota_no_negativa',
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.tarea.titulo} ({self.estado})"


class Quiz(models.Model):
    """Evaluacion en linea compuesta por preguntas."""

    id_quiz = models.BigAutoField(
        primary_key=True,
        db_column='id_quiz',
    )

    curso = models.ForeignKey(
        Curso,
        on_delete=models.PROTECT,
        db_column='id_curso',
        related_name='quizzes',
        verbose_name='Curso',
    )

    titulo = models.CharField(
        max_length=200,
        db_column='titulo',
        verbose_name='Titulo del quiz',
    )

    descripcion = models.TextField(
        null=True,
        blank=True,
        db_column='descripcion',
        verbose_name='Descripcion',
    )

    tiempo_limite_min = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_column='tiempo_limite_min',
        verbose_name='Tiempo limite en minutos',
    )

    fecha_limite = models.DateTimeField(
        db_column='fecha_limite',
        verbose_name='Fecha limite',
    )

    class Meta:
        db_table = 'quiz'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        ordering = ['fecha_limite', 'titulo']

        constraints = [
            models.UniqueConstraint(
                fields=['curso', 'titulo'],
                name='uq_quiz_curso_titulo',
            ),
        ]

    def __str__(self):
        return f"{self.curso.codigo} - {self.titulo}"


class Pregunta(models.Model):
    """Pregunta que forma parte de un quiz."""

    class Tipo(models.TextChoices):
        OPCION_MULTIPLE_UNA = 'opcion_multiple_una', 'Opcion multiple (1 respuesta)'
        OPCION_MULTIPLE_VARIAS = 'opcion_multiple_varias', 'Opcion multiple (varias respuestas)'
        VERDADERO_FALSO = 'verdadero_falso', 'Verdadero / Falso'
        COMPLETAR_ESPACIOS = 'completar_espacios', 'Completar espacios'
        RELACIONAR_COLUMNAS = 'relacionar_columnas', 'Relacionar columnas'
        ORDENAMIENTO = 'ordenamiento', 'Ordenamiento'
        RESPUESTA_NUMERICA = 'respuesta_numerica', 'Respuesta numerica'
        MENU_DESPLEGABLE = 'menu_desplegable', 'Menu desplegable'
        SELECCION_IMAGEN = 'seleccion_imagen', 'Seleccion en imagen'
        RESPUESTA_CORTA = 'respuesta_corta', 'Respuesta corta'
        ENSAYO = 'ensayo', 'Ensayo'
        SUBIDA_ARCHIVO = 'subida_archivo', 'Subida de archivo'
        RESPUESTA_IMAGEN = 'respuesta_imagen', 'Respuesta con imagen'
        EDITOR_CODIGO = 'editor_codigo', 'Editor de codigo'
        ESCALA_VALORACION = 'escala_valoracion', 'Escala de valoracion'

    AUTO_CORREGIBLES = {
        Tipo.OPCION_MULTIPLE_UNA,
        Tipo.OPCION_MULTIPLE_VARIAS,
        Tipo.VERDADERO_FALSO,
        Tipo.COMPLETAR_ESPACIOS,
        Tipo.RELACIONAR_COLUMNAS,
        Tipo.ORDENAMIENTO,
        Tipo.RESPUESTA_NUMERICA,
        Tipo.MENU_DESPLEGABLE,
        Tipo.SELECCION_IMAGEN,
    }

    id_pregunta = models.BigAutoField(
        primary_key=True,
        db_column='id_pregunta',
    )

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.PROTECT,
        db_column='id_quiz',
        related_name='preguntas',
        verbose_name='Quiz',
    )

    tipo = models.CharField(
        max_length=30,
        choices=Tipo.choices,
        default=Tipo.OPCION_MULTIPLE_UNA,
        db_column='tipo',
        verbose_name='Tipo de pregunta',
    )

    enunciado = models.TextField(
        db_column='enunciado',
        verbose_name='Enunciado',
    )

    puntaje = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        db_column='puntaje',
        verbose_name='Puntaje',
    )

    orden = models.PositiveSmallIntegerField(
        default=0,
        db_column='orden',
        verbose_name='Orden',
    )

    opciones = models.JSONField(
        default=list,
        blank=True,
        db_column='opciones',
        verbose_name='Opciones de respuesta',
    )

    respuesta_correcta = models.JSONField(
        null=True,
        blank=True,
        db_column='respuesta_correcta',
        verbose_name='Respuesta correcta',
    )

    class Meta:
        db_table = 'pregunta'
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'
        ordering = ['quiz', 'orden']

        constraints = [
            models.CheckConstraint(
                condition=models.Q(puntaje__gte=0),
                name='ck_pregunta_puntaje_no_negativo',
            ),
        ]

    @property
    def es_auto_corregible(self):
        return self.tipo in self.AUTO_CORREGIBLES

    def __str__(self):
        return f"P{self.orden}: {self.enunciado[:60]}"


class RespuestaQuiz(models.Model):
    """Intento resuelto de un estudiante sobre un quiz."""

    id_respuesta_quiz = models.BigAutoField(
        primary_key=True,
        db_column='id_respuesta_quiz',
    )

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.PROTECT,
        db_column='id_quiz',
        related_name='respuestas',
        verbose_name='Quiz',
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario',
        related_name='respuestas_quiz',
        verbose_name='Estudiante',
    )

    respuestas = models.JSONField(
        default=dict,
        blank=True,
        db_column='respuestas',
        verbose_name='Respuestas enviadas',
    )

    nota_automatica = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        db_column='nota_automatica',
        verbose_name='Nota automatica',
    )

    nota_manual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        db_column='nota_manual',
        verbose_name='Nota manual',
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
        db_column='fecha',
        verbose_name='Fecha de envio',
    )

    class Meta:
        db_table = 'respuesta_quiz'
        verbose_name = 'Respuesta de quiz'
        verbose_name_plural = 'Respuestas de quiz'
        ordering = ['quiz', 'usuario']

        constraints = [
            models.UniqueConstraint(
                fields=['quiz', 'usuario'],
                name='uq_respuesta_quiz_usuario',
            ),
            models.CheckConstraint(
                condition=models.Q(nota_automatica__gte=0),
                name='ck_respuesta_quiz_nota_auto_no_negativa',
            ),
            models.CheckConstraint(
                condition=models.Q(nota_manual__isnull=True) | models.Q(nota_manual__gte=0),
                name='ck_respuesta_quiz_nota_manual_no_negativa',
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.quiz.titulo}"
