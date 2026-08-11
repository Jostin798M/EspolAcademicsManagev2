"""Formularios del modulo ACCOUNTS."""
from django import forms

from .models import Usuario


class UsuarioForm(forms.ModelForm):
    """Registro y edicion de usuarios del sistema."""

    password = forms.CharField(
        label="Contrasena",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Minimo 6 caracteres",
                "autocomplete": "new-password",
            }
        ),
        help_text="Deje el campo vacio para conservar la contrasena actual.",
    )

    class Meta:
        model = Usuario

        fields = [
            "nombres",
            "apellidos",
            "identificacion",
            "telefono",
            "celular",
            "correo",
            "direccion",
            "estado_civil",
            "facultad",
            "rol",
            "estado",
        ]

        labels = {
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "identificacion": "Identificacion",
            "telefono": "Telefono convencional",
            "celular": "Celular",
            "correo": "Correo electronico",
            "direccion": "Direccion",
            "estado_civil": "Estado civil",
            "facultad": "Facultad a la que pertenece",
            "rol": "Rol del sistema",
            "estado": "Estado de la cuenta",
        }

        widgets = {
            "nombres": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Ana Lucia",
                    "maxlength": 100,
                    "autofocus": True,
                }
            ),
            "apellidos": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Paredes Suarez",
                    "maxlength": 100,
                }
            ),
            "identificacion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Cedula o pasaporte",
                    "maxlength": 20,
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "042123456",
                    "maxlength": 15,
                }
            ),
            "celular": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0991234567",
                    "maxlength": 15,
                }
            ),
            "correo": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "usuario@espol.edu.ec",
                }
            ),
            "direccion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ciudadela, calle y numero",
                    "maxlength": 200,
                }
            ),
            "estado_civil": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "facultad": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "rol": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "estado": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

        error_messages = {
            "nombres": {
                "required": "Debe ingresar los nombres del usuario.",
                "max_length": "Los nombres no pueden superar los 100 caracteres.",
            },
            "apellidos": {
                "required": "Debe ingresar los apellidos del usuario.",
                "max_length": "Los apellidos no pueden superar los 100 caracteres.",
            },
            "identificacion": {
                "required": "Debe ingresar la identificacion.",
                "unique": "Ya existe un usuario con esta identificacion.",
                "max_length": "La identificacion no puede superar los 20 caracteres.",
            },
            "celular": {
                "required": "Debe ingresar el numero de celular.",
                "max_length": "El celular no puede superar los 15 caracteres.",
            },
            "correo": {
                "required": "Debe ingresar el correo electronico.",
                "unique": "Ya existe un usuario con este correo.",
                "invalid": "Ingrese un correo electronico valido.",
            },
        }

    def clean_nombres(self):
        return self.cleaned_data.get("nombres", "").strip()

    def clean_apellidos(self):
        return self.cleaned_data.get("apellidos", "").strip()

    def clean_identificacion(self):
        identificacion = self.cleaned_data.get("identificacion", "").strip()

        if not identificacion.isdigit():
            raise forms.ValidationError(
                "La identificacion solo debe contener numeros."
            )
        return identificacion

    def clean_correo(self):
        return self.cleaned_data.get("correo", "").strip().lower()

    def clean_password(self):
        password = self.cleaned_data.get("password", "")

        if not password and self.instance.pk is None:
            raise forms.ValidationError(
                "Debe asignar una contrasena al crear el usuario."
            )

        if password and len(password) < 6:
            raise forms.ValidationError(
                "La contrasena debe tener al menos 6 caracteres."
            )
        return password

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get("password")

        if password:
            usuario.set_password(password)

        usuario.is_active = usuario.estado == Usuario.Estado.ACTIVO

        if commit:
            usuario.save()
            self.save_m2m()

        return usuario
