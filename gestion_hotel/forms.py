import re

from django import forms
from django.contrib.auth.hashers import make_password
from django.utils.html import format_html

from .models import Cliente
from .validators import (
    validar_documento_ecuador,
    validate_cedula_ruc,
    validate_letters_only,
    validate_password_strength,
    validate_phone,
)


class ClienteRegistroForm(forms.Form):
    tipo_documento = forms.ChoiceField(
        choices=[
            ('Cédula', 'Cédula'),
            ('RUC', 'RUC'),
            ('Pasaporte', 'Pasaporte'),
        ],
        label='Tipo de documento',
    )
    numero_documento = forms.CharField(
        max_length=20,
        label='Número de documento',
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Ej: 1712345678 / 1790012345001 / AB123456',
            }
        ),
    )
    nombres = forms.CharField(
        max_length=100,
        label='Nombres',
        validators=[validate_letters_only],
        widget=forms.TextInput(attrs={'placeholder': 'Ingresa tus nombres'}),
    )
    apellidos = forms.CharField(
        max_length=100,
        label='Apellidos',
        validators=[validate_letters_only],
        widget=forms.TextInput(attrs={'placeholder': 'Ingresa tus apellidos'}),
    )
    correo_electronico = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
    )
    telefono_celular = forms.CharField(
        max_length=20,
        label='Teléfono celular',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: 0998765432 o +593998765432'}),
    )
    pais_origen = forms.CharField(
        max_length=100,
        required=False,
        label='País de origen',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Ecuador'}),
    )
    ciudad = forms.CharField(
        max_length=100,
        required=False,
        label='Ciudad',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Quito'}),
    )

    def clean_pais_origen(self):
        pais = self.cleaned_data.get('pais_origen', '').strip()
        if pais:
            validate_letters_only(pais)
        return pais

    def clean_ciudad(self):
        ciudad = self.cleaned_data.get('ciudad', '').strip()
        if ciudad:
            validate_letters_only(ciudad)
        return ciudad
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'password-toggle',
                'autocomplete': 'new-password',
                'placeholder': 'Mínimo 8 caracteres',
            }
        ),
        min_length=8,
        label='Contraseña',
        help_text='Mínimo 8 caracteres con mayúscula, minúscula, número y carácter especial.',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'password-toggle',
                'autocomplete': 'new-password',
                'placeholder': 'Repite tu contraseña',
            }
        ),
        min_length=8,
        label='Confirmar contraseña',
    )

    def clean_numero_documento(self):
        numero_documento = self.cleaned_data['numero_documento'].strip()
        tipo_documento = self.cleaned_data.get('tipo_documento')

        if tipo_documento in {'Cédula', 'Cedula', 'cédula', 'cedula', 'RUC', 'ruc'}:
            numero_documento = re.sub(r"\D", "", numero_documento)
        elif tipo_documento in {'Pasaporte', 'pasaporte'}:
            numero_documento = re.sub(r"[^A-Za-z0-9]", "", numero_documento).upper()

        validate_cedula_ruc(numero_documento)

        if Cliente.objects.filter(numero_documento__iexact=numero_documento).exists():
            raise forms.ValidationError('El número de documento ya se encuentra registrado.')
        return numero_documento

    def clean_correo_electronico(self):
        correo_electronico = self.cleaned_data['correo_electronico'].strip().lower()
        if Cliente.objects.filter(correo_electronico__iexact=correo_electronico).exists():
            raise forms.ValidationError('El correo electrónico ya se encuentra registrado.')
        return correo_electronico

    def clean_telefono_celular(self):
        telefono_celular = self.cleaned_data['telefono_celular'].strip()
        validate_phone(telefono_celular)
        return telefono_celular

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if not password:
            raise forms.ValidationError('La contraseña es obligatoria.')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Las contraseñas no coinciden.')

        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password_strength(password)
        return password

    def save(self, commit=True):
        datos = self.cleaned_data
        direccion_parts = [
            datos.get('ciudad', '').strip(),
            datos.get('pais_origen', '').strip(),
        ]
        direccion = ', '.join([parte for parte in direccion_parts if parte]) or ''

        usuario = Cliente(
            tipo_documento=datos['tipo_documento'],
            numero_documento=datos['numero_documento'].strip(),
            nombres=datos['nombres'].strip(),
            apellidos=datos['apellidos'].strip(),
            correo_electronico=datos['correo_electronico'].strip().lower(),
            telefono_celular=datos['telefono_celular'].strip(),
            pais_origen=datos.get('pais_origen', '').strip(),
            ciudad=datos.get('ciudad', '').strip(),
            password=make_password(datos['password']),
            rol='cliente',
            activo=True,
            direccion=direccion,
        )
        if commit:
            usuario.save()
        return usuario


class PasswordToggleWidget(forms.PasswordInput):
    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        final_attrs.setdefault('class', '')
        final_attrs['class'] = f"{final_attrs['class']} password-toggle-input".strip()
        field_id = final_attrs.get('id', name)
        input_html = super().render(name, value, final_attrs, renderer)
        button_html = format_html(
            '<button type="button" class="password-toggle-btn" data-password-field-id="{}" aria-label="Mostrar contraseña" title="Mostrar contraseña">👁</button>',
            field_id,
        )
        return format_html('<div class="password-toggle-wrapper">{} {}</div>', input_html, button_html)

    @property
    def media(self):
        return forms.Media(
            css={'all': ['css/password-toggle.css']},
            js=['js/password-toggle.js'],
        )


class ClienteAdminForm(forms.ModelForm):
    password = forms.CharField(required=False, widget=PasswordToggleWidget(attrs={'autocomplete': 'new-password'}), label='Contraseña')

    class Meta:
        model = Cliente
        fields = ['numero_documento', 'nombres', 'apellidos', 'telefono_celular', 'correo_electronico', 'rol', 'activo', 'password']
        labels = {
            'numero_documento': 'Número de documento',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'telefono_celular': 'Teléfono celular',
            'correo_electronico': 'Correo electrónico',
            'rol': 'Rol',
            'activo': 'Activo',
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password_strength(password)
        return password

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        # Gestion_Hotel -> Cliente model must only contain clientes
        if rol and rol not in {'cliente'}:
            raise forms.ValidationError(
                'Los administradores y gerentes deben crearse en Autenticación y autorización, no en Clientes.'
            )
        return 'cliente'

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            usuario.password = make_password(password)
        if commit:
            usuario.save()
        return usuario


class ClienteLoginForm(forms.Form):
    correo_electronico = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'placeholder': 'correo@ejemplo.com',
                'autocomplete': 'username',
            }
        ),
        label='Correo electrónico',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'password-toggle',
                'autocomplete': 'current-password',
            }
        ),
        label='Contraseña',
    )
