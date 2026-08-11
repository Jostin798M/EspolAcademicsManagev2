"""Formularios del modulo CURSOS."""
from django import forms

from .models import (
    Curso,
    Facultad,
    FormulaComponente,
    Inscripcion,
    Material,
    Modulo,
    ProgresoModulo,
)


class FacultadForm(forms.ModelForm):
    """Registro y edicion de facultades."""

    class Meta:
        model = Facultad

        fields = [
            "codigo",
            "nombre",
            "admin",
        ]

        labels = {
            "codigo": "Codigo de la facultad",
            "nombre": "Nombre de la facultad",
            "admin": "Administrador responsable",
        }

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: FIEC",
                    "maxlength": 10,
                    "autofocus": True,
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Facultad de Ingenieria en Electricidad y Computacion",
                    "maxlength": 200,
                }
            ),
            "admin": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

        error_messages = {
            "codigo": {
                "required": "Debe ingresar el codigo de la facultad.",
                "unique": "Ya existe una facultad con este codigo.",
                "max_length": "El codigo no puede superar los 10 caracteres.",
            },
            "nombre": {
                "required": "Debe ingresar el nombre de la facultad.",
                "unique": "Ya existe una facultad con este nombre.",
                "max_length": "El nombre no puede superar los 200 caracteres.",
            },
        }

    def clean_codigo(self):
        return self.cleaned_data.get("codigo", "").strip().upper()

    def clean_nombre(self):
        return self.cleaned_data.get("nombre", "").strip()


class CursoForm(forms.ModelForm):
    """Registro y edicion de cursos."""

    class Meta:
        model = Curso

        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "facultad",
            "profesor",
            "fecha_inicio",
            "fecha_fin",
            "estado",
        ]

        labels = {
            "codigo": "Codigo del curso",
            "nombre": "Nombre del curso",
            "descripcion": "Descripcion",
            "facultad": "Facultad",
            "profesor": "Profesor responsable",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de finalizacion",
            "estado": "Estado del curso",
        }

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: DAWM-2026A",
                    "maxlength": 20,
                    "autofocus": True,
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Desarrollo de Aplicaciones Web y Moviles",
                    "maxlength": 200,
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Contenido general del curso",
                    "rows": 3,
                }
            ),
            "facultad": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "profesor": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "fecha_inicio": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "fecha_fin": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "estado": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

        error_messages = {
            "codigo": {
                "required": "Debe ingresar el codigo del curso.",
                "unique": "Ya existe un curso con este codigo.",
                "max_length": "El codigo no puede superar los 20 caracteres.",
            },
            "nombre": {
                "required": "Debe ingresar el nombre del curso.",
                "max_length": "El nombre no puede superar los 200 caracteres.",
            },
            "descripcion": {
                "required": "Debe ingresar la descripcion del curso.",
            },
            "facultad": {
                "required": "Debe seleccionar la facultad del curso.",
            },
            "profesor": {
                "required": "Debe seleccionar el profesor responsable.",
            },
            "fecha_inicio": {
                "required": "Debe ingresar la fecha de inicio.",
                "invalid": "Ingrese una fecha de inicio valida.",
            },
            "fecha_fin": {
                "required": "Debe ingresar la fecha de finalizacion.",
                "invalid": "Ingrese una fecha de finalizacion valida.",
            },
        }

    def clean_codigo(self):
        return self.cleaned_data.get("codigo", "").strip().upper()

    def clean_nombre(self):
        return self.cleaned_data.get("nombre", "").strip()

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise forms.ValidationError(
                "La fecha de finalizacion no puede ser anterior a la fecha de inicio."
            )
        return cleaned_data


class FormulaComponenteForm(forms.ModelForm):
    """Registro y edicion de componentes de la formula de calificacion."""

    class Meta:
        model = FormulaComponente

        fields = [
            "curso",
            "componente",
            "porcentaje",
            "orden",
        ]

        labels = {
            "curso": "Curso",
            "componente": "Nombre del componente",
            "porcentaje": "Porcentaje",
            "orden": "Orden de presentacion",
        }

        widgets = {
            "curso": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "componente": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Tareas",
                    "maxlength": 100,
                }
            ),
            "porcentaje": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 100,
                }
            ),
            "orden": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
        }

        error_messages = {
            "curso": {
                "required": "Debe seleccionar el curso.",
            },
            "componente": {
                "required": "Debe ingresar el nombre del componente.",
                "max_length": "El nombre no puede superar los 100 caracteres.",
            },
            "porcentaje": {
                "required": "Debe ingresar el porcentaje del componente.",
                "invalid": "El porcentaje debe ser un numero entero.",
            },
        }

    def clean_componente(self):
        return self.cleaned_data.get("componente", "").strip()

    def clean_porcentaje(self):
        porcentaje = self.cleaned_data.get("porcentaje")

        if porcentaje is not None and not 1 <= porcentaje <= 100:
            raise forms.ValidationError(
                "El porcentaje debe estar entre 1 y 100."
            )
        return porcentaje

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get("curso")
        porcentaje = cleaned_data.get("porcentaje")

        if curso and porcentaje:
            otros = FormulaComponente.objects.filter(curso=curso)

            if self.instance.pk:
                otros = otros.exclude(pk=self.instance.pk)

            total = sum(c.porcentaje for c in otros) + porcentaje

            if total > 100:
                raise forms.ValidationError(
                    f"La suma de los componentes del curso seria {total}%. "
                    "El total no puede superar el 100%."
                )
        return cleaned_data


class InscripcionForm(forms.ModelForm):
    """Registro y edicion de inscripciones."""

    class Meta:
        model = Inscripcion

        fields = [
            "usuario",
            "curso",
            "rol_en_curso",
        ]

        labels = {
            "usuario": "Usuario",
            "curso": "Curso",
            "rol_en_curso": "Rol en el curso",
        }

        widgets = {
            "usuario": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "curso": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "rol_en_curso": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

        error_messages = {
            "usuario": {
                "required": "Debe seleccionar el usuario a inscribir.",
            },
            "curso": {
                "required": "Debe seleccionar el curso.",
            },
            "rol_en_curso": {
                "required": "Debe indicar el rol dentro del curso.",
            },
        }

    def clean(self):
        cleaned_data = super().clean()
        usuario = cleaned_data.get("usuario")
        curso = cleaned_data.get("curso")

        if usuario and curso:
            existente = Inscripcion.objects.filter(usuario=usuario, curso=curso)

            if self.instance.pk:
                existente = existente.exclude(pk=self.instance.pk)

            if existente.exists():
                raise forms.ValidationError(
                    "El usuario ya se encuentra inscrito en este curso."
                )
        return cleaned_data


class ModuloForm(forms.ModelForm):
    """Registro y edicion de modulos del curso."""

    class Meta:
        model = Modulo

        fields = [
            "curso",
            "orden",
            "titulo",
            "descripcion",
        ]

        labels = {
            "curso": "Curso",
            "orden": "Orden del modulo",
            "titulo": "Titulo del modulo",
            "descripcion": "Descripcion",
        }

        widgets = {
            "curso": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "orden": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "titulo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Introduccion al Desarrollo Web",
                    "maxlength": 200,
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Contenido que cubre el modulo",
                    "rows": 3,
                }
            ),
        }

        error_messages = {
            "curso": {
                "required": "Debe seleccionar el curso del modulo.",
            },
            "orden": {
                "required": "Debe ingresar el orden del modulo.",
                "invalid": "El orden debe ser un numero entero.",
            },
            "titulo": {
                "required": "Debe ingresar el titulo del modulo.",
                "max_length": "El titulo no puede superar los 200 caracteres.",
            },
        }

    def clean_titulo(self):
        return self.cleaned_data.get("titulo", "").strip()

    def clean_orden(self):
        orden = self.cleaned_data.get("orden")

        if orden is not None and orden < 1:
            raise forms.ValidationError(
                "El orden del modulo debe ser mayor o igual a 1."
            )
        return orden

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get("curso")
        orden = cleaned_data.get("orden")

        if curso and orden:
            repetido = Modulo.objects.filter(curso=curso, orden=orden)

            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)

            if repetido.exists():
                raise forms.ValidationError(
                    "Ya existe un modulo con ese orden en el curso seleccionado."
                )
        return cleaned_data


class MaterialForm(forms.ModelForm):
    """Registro y edicion de materiales de estudio."""

    class Meta:
        model = Material

        fields = [
            "modulo",
            "tipo",
            "titulo",
            "url",
        ]

        labels = {
            "modulo": "Modulo",
            "tipo": "Tipo de material",
            "titulo": "Titulo del material",
            "url": "Enlace del recurso",
        }

        widgets = {
            "modulo": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "tipo": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "titulo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Guia de referencia HTML5",
                    "maxlength": 200,
                }
            ),
            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://...",
                }
            ),
        }

        error_messages = {
            "modulo": {
                "required": "Debe seleccionar el modulo.",
            },
            "tipo": {
                "required": "Debe seleccionar el tipo de material.",
            },
            "titulo": {
                "required": "Debe ingresar el titulo del material.",
                "max_length": "El titulo no puede superar los 200 caracteres.",
            },
            "url": {
                "required": "Debe ingresar el enlace del recurso.",
                "invalid": "Ingrese una direccion web valida.",
            },
        }

    def clean_titulo(self):
        return self.cleaned_data.get("titulo", "").strip()


class ProgresoModuloForm(forms.ModelForm):
    """Registro y edicion del avance de un estudiante en un modulo."""

    class Meta:
        model = ProgresoModulo

        fields = [
            "usuario",
            "modulo",
            "completado",
        ]

        labels = {
            "usuario": "Estudiante",
            "modulo": "Modulo",
            "completado": "Modulo completado",
        }

        widgets = {
            "usuario": forms.Select(
                attrs={
                    "class": "form-select",
                    "autofocus": True,
                }
            ),
            "modulo": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "completado": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        error_messages = {
            "usuario": {
                "required": "Debe seleccionar el estudiante.",
            },
            "modulo": {
                "required": "Debe seleccionar el modulo.",
            },
        }

    def clean(self):
        cleaned_data = super().clean()
        usuario = cleaned_data.get("usuario")
        modulo = cleaned_data.get("modulo")

        if usuario and modulo:
            repetido = ProgresoModulo.objects.filter(usuario=usuario, modulo=modulo)

            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)

            if repetido.exists():
                raise forms.ValidationError(
                    "Ya existe un registro de progreso para este estudiante y modulo."
                )
        return cleaned_data
