"""Formularios del modulo EVALUACIONES."""
from django import forms

from .models import Entrega, Pregunta, Quiz, RespuestaQuiz, Tarea

# Formato aceptado por el control HTML datetime-local
FORMATOS_FECHA_HORA = [
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
]


class TareaForm(forms.ModelForm):
    """Registro y edicion de tareas."""

    class Meta:
        model = Tarea

        fields = [
            "curso",
            "titulo",
            "descripcion",
            "criterios",
            "fecha_limite",
            "puntaje_maximo",
        ]

        labels = {
            "curso": "Curso",
            "titulo": "Titulo de la tarea",
            "descripcion": "Descripcion",
            "criterios": "Criterios de calificacion",
            "fecha_limite": "Fecha limite de entrega",
            "puntaje_maximo": "Puntaje maximo",
        }

        widgets = {
            "curso": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "titulo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Pagina HTML estatica",
                    "maxlength": 200,
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Indicaciones de la tarea",
                    "rows": 3,
                }
            ),
            "criterios": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Aspectos que seran evaluados",
                    "rows": 3,
                }
            ),
            "fecha_limite": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "puntaje_maximo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
        }

        error_messages = {
            "curso": {
                "required": "Debe seleccionar el curso de la tarea.",
            },
            "titulo": {
                "required": "Debe ingresar el titulo de la tarea.",
                "max_length": "El titulo no puede superar los 200 caracteres.",
            },
            "descripcion": {
                "required": "Debe ingresar la descripcion de la tarea.",
            },
            "fecha_limite": {
                "required": "Debe ingresar la fecha limite de entrega.",
                "invalid": "Ingrese una fecha y hora validas.",
            },
            "puntaje_maximo": {
                "required": "Debe ingresar el puntaje maximo.",
                "invalid": "El puntaje debe ser un numero.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_limite"].input_formats = FORMATOS_FECHA_HORA

    def clean_titulo(self):
        return self.cleaned_data.get("titulo", "").strip()

    def clean_puntaje_maximo(self):
        puntaje = self.cleaned_data.get("puntaje_maximo")

        if puntaje is not None and puntaje < 0:
            raise forms.ValidationError(
                "El puntaje maximo no puede ser negativo."
            )
        return puntaje


class EntregaForm(forms.ModelForm):
    """Registro, edicion y calificacion de entregas."""

    class Meta:
        model = Entrega

        fields = [
            "tarea",
            "usuario",
            "estado",
            "fecha",
            "texto",
            "archivo",
            "imagen",
            "link",
            "nota",
            "comentario",
        ]

        labels = {
            "tarea": "Tarea",
            "usuario": "Estudiante",
            "estado": "Estado de la entrega",
            "fecha": "Fecha de entrega",
            "texto": "Respuesta escrita",
            "archivo": "Archivo entregado",
            "imagen": "Imagen entregada",
            "link": "Enlace entregado",
            "nota": "Nota obtenida",
            "comentario": "Comentario del profesor",
        }

        widgets = {
            "tarea": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "usuario": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "estado": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "fecha": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "texto": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Contenido enviado por el estudiante",
                    "rows": 3,
                }
            ),
            "archivo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: tarea1_ana.html",
                    "maxlength": 300,
                }
            ),
            "imagen": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://... (imagen)",
                }
            ),
            "link": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://...",
                }
            ),
            "nota": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "comentario": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Retroalimentacion para el estudiante",
                    "rows": 2,
                }
            ),
        }

        error_messages = {
            "tarea": {
                "required": "Debe seleccionar la tarea.",
            },
            "usuario": {
                "required": "Debe seleccionar el estudiante.",
            },
            "nota": {
                "invalid": "La nota debe ser un numero.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = FORMATOS_FECHA_HORA

    def clean_nota(self):
        nota = self.cleaned_data.get("nota")

        if nota is not None and nota < 0:
            raise forms.ValidationError("La nota no puede ser negativa.")
        return nota

    def clean(self):
        cleaned_data = super().clean()
        tarea = cleaned_data.get("tarea")
        usuario = cleaned_data.get("usuario")
        nota = cleaned_data.get("nota")

        if tarea and usuario:
            repetida = Entrega.objects.filter(tarea=tarea, usuario=usuario)

            if self.instance.pk:
                repetida = repetida.exclude(pk=self.instance.pk)

            if repetida.exists():
                raise forms.ValidationError(
                    "El estudiante ya tiene una entrega registrada para esta tarea."
                )

        if tarea and nota is not None and nota > tarea.puntaje_maximo:
            raise forms.ValidationError(
                f"La nota no puede superar el puntaje maximo de la tarea "
                f"({tarea.puntaje_maximo})."
            )
        return cleaned_data


class QuizForm(forms.ModelForm):
    """Registro y edicion de quizzes."""

    class Meta:
        model = Quiz

        fields = [
            "curso",
            "titulo",
            "descripcion",
            "tiempo_limite_min",
            "fecha_limite",
        ]

        labels = {
            "curso": "Curso",
            "titulo": "Titulo del quiz",
            "descripcion": "Descripcion",
            "tiempo_limite_min": "Tiempo limite en minutos",
            "fecha_limite": "Fecha limite",
        }

        widgets = {
            "curso": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "titulo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Quiz de HTML y CSS",
                    "maxlength": 200,
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Alcance de la evaluacion",
                    "rows": 3,
                }
            ),
            "tiempo_limite_min": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Ejemplo: 20",
                }
            ),
            "fecha_limite": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
        }

        error_messages = {
            "curso": {
                "required": "Debe seleccionar el curso del quiz.",
            },
            "titulo": {
                "required": "Debe ingresar el titulo del quiz.",
                "max_length": "El titulo no puede superar los 200 caracteres.",
            },
            "fecha_limite": {
                "required": "Debe ingresar la fecha limite del quiz.",
                "invalid": "Ingrese una fecha y hora validas.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_limite"].input_formats = FORMATOS_FECHA_HORA

    def clean_titulo(self):
        return self.cleaned_data.get("titulo", "").strip()

    def clean_tiempo_limite_min(self):
        tiempo = self.cleaned_data.get("tiempo_limite_min")

        if tiempo is not None and tiempo < 1:
            raise forms.ValidationError(
                "El tiempo limite debe ser de al menos 1 minuto."
            )
        return tiempo


class PreguntaForm(forms.ModelForm):
    """Registro y edicion de preguntas de un quiz."""

    class Meta:
        model = Pregunta

        fields = [
            "quiz",
            "orden",
            "tipo",
            "enunciado",
            "puntaje",
            "opciones",
            "respuesta_correcta",
        ]

        labels = {
            "quiz": "Quiz",
            "orden": "Orden de la pregunta",
            "tipo": "Tipo de pregunta",
            "enunciado": "Enunciado",
            "puntaje": "Puntaje",
            "opciones": "Opciones de respuesta (formato JSON)",
            "respuesta_correcta": "Respuesta correcta (formato JSON)",
        }

        widgets = {
            "quiz": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "orden": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "tipo": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "enunciado": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Texto de la pregunta",
                    "rows": 3,
                }
            ),
            "puntaje": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "opciones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": '["Opcion A", "Opcion B", "Opcion C"]',
                    "rows": 2,
                }
            ),
            "respuesta_correcta": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": '0   o   true   o   "justify-content"',
                    "rows": 2,
                }
            ),
        }

        error_messages = {
            "quiz": {
                "required": "Debe seleccionar el quiz.",
            },
            "tipo": {
                "required": "Debe seleccionar el tipo de pregunta.",
            },
            "enunciado": {
                "required": "Debe ingresar el enunciado de la pregunta.",
            },
            "puntaje": {
                "required": "Debe ingresar el puntaje de la pregunta.",
                "invalid": "El puntaje debe ser un numero.",
            },
            "opciones": {
                "invalid": "Las opciones deben escribirse en formato JSON valido.",
            },
            "respuesta_correcta": {
                "invalid": "La respuesta correcta debe escribirse en formato JSON valido.",
            },
        }

    def clean_enunciado(self):
        return self.cleaned_data.get("enunciado", "").strip()

    def clean_puntaje(self):
        puntaje = self.cleaned_data.get("puntaje")

        if puntaje is not None and puntaje < 0:
            raise forms.ValidationError("El puntaje no puede ser negativo.")
        return puntaje

    def clean_opciones(self):
        opciones = self.cleaned_data.get("opciones")

        if opciones in (None, ""):
            return []

        if not isinstance(opciones, list):
            raise forms.ValidationError(
                'Las opciones deben ser una lista JSON, por ejemplo: ["A", "B"].'
            )
        return opciones

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        opciones = cleaned_data.get("opciones")

        tipos_con_opciones = {
            Pregunta.Tipo.OPCION_MULTIPLE_UNA,
            Pregunta.Tipo.OPCION_MULTIPLE_VARIAS,
            Pregunta.Tipo.MENU_DESPLEGABLE,
        }

        if tipo in tipos_con_opciones and not opciones:
            raise forms.ValidationError(
                "Este tipo de pregunta requiere al menos una opcion de respuesta."
            )
        return cleaned_data


class RespuestaQuizForm(forms.ModelForm):
    """Registro y edicion de los intentos resueltos de un quiz."""

    class Meta:
        model = RespuestaQuiz

        fields = [
            "quiz",
            "usuario",
            "respuestas",
            "nota_automatica",
            "nota_manual",
        ]

        labels = {
            "quiz": "Quiz",
            "usuario": "Estudiante",
            "respuestas": "Respuestas enviadas (formato JSON)",
            "nota_automatica": "Nota automatica",
            "nota_manual": "Nota manual",
        }

        widgets = {
            "quiz": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "usuario": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "respuestas": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": '{"1": 0, "2": "Verdadero"}',
                    "rows": 3,
                }
            ),
            "nota_automatica": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "nota_manual": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
        }

        error_messages = {
            "quiz": {
                "required": "Debe seleccionar el quiz.",
            },
            "usuario": {
                "required": "Debe seleccionar el estudiante.",
            },
            "respuestas": {
                "invalid": "Las respuestas deben escribirse en formato JSON valido.",
            },
        }

    def clean_nota_automatica(self):
        nota = self.cleaned_data.get("nota_automatica")

        if nota is not None and nota < 0:
            raise forms.ValidationError(
                "La nota automatica no puede ser negativa."
            )
        return nota

    def clean_nota_manual(self):
        nota = self.cleaned_data.get("nota_manual")

        if nota is not None and nota < 0:
            raise forms.ValidationError(
                "La nota manual no puede ser negativa."
            )
        return nota

    def clean(self):
        cleaned_data = super().clean()
        quiz = cleaned_data.get("quiz")
        usuario = cleaned_data.get("usuario")

        if quiz and usuario:
            repetida = RespuestaQuiz.objects.filter(quiz=quiz, usuario=usuario)

            if self.instance.pk:
                repetida = repetida.exclude(pk=self.instance.pk)

            if repetida.exists():
                raise forms.ValidationError(
                    "El estudiante ya registro una respuesta para este quiz."
                )
        return cleaned_data
