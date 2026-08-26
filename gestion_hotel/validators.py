"""Validadores reutilizables para datos personales, documentos, telefono y seguridad de password."""

import re

from django.core.exceptions import ValidationError

NAME_PATTERN = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]+(?: [A-Za-zÁÉÍÓÚáéíóúÑñ]+)*$")
DIGIT_ONLY_PATTERN = re.compile(r"^\d+$")
ALPHA_NUMERIC_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


def validate_letters_only(value):
    """Acepta nombres con letras, espacios, tildes y enie, rechazando valores demasiado cortos."""

    if not value or not NAME_PATTERN.fullmatch(value.strip()):
        raise ValidationError("Solo se permiten letras, espacios, tildes y ñ.")
    if len(value.strip()) < 2:
        raise ValidationError("El nombre y apellido deben tener al menos 2 caracteres.")


def _validar_provincia(documento):
    if len(documento) < 2:
        return False
    provincia = int(documento[:2])
    return 1 <= provincia <= 24


def _calcular_digito_mod10(documento):
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for digit, coef in zip(documento[:-1], coeficientes):
        value = int(digit) * coef
        if value >= 10:
            value = value - 9
        total += value
    resto = total % 10
    return 0 if resto == 0 else 10 - resto


def _calcular_digito_mod11(documento, coeficientes):
    total = 0
    for digit, coef in zip(documento, coeficientes):
        total += int(digit) * coef
    residuo = total % 11
    if residuo == 0:
        return 0
    if residuo == 1:
        return 0
    return 11 - residuo


def validar_documento_ecuador(tipo_documento, value):
    """Normaliza y valida cedula, RUC o pasaporte; retorna un dict usado por formularios y vistas."""

    documento = (value or "").strip()
    tipo = (tipo_documento or "").strip()

    if not documento:
        return {
            "valido": False,
            "documento_limpio": "",
            "mensaje": "Ingrese un documento de identidad.",
        }

    if tipo == "Cédula":
        documento_limpio = re.sub(r"\D", "", documento)
        if len(documento_limpio) == 9:
            documento_limpio = "0" + documento_limpio
        if len(documento_limpio) != 10:
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "La cédula debe tener 10 dígitos.",
            }
        if not DIGIT_ONLY_PATTERN.fullmatch(documento_limpio):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "La cédula debe contener solo números.",
            }
        if not _validar_provincia(documento_limpio):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "La provincia del documento no es válida.",
            }
        if int(documento_limpio[2]) >= 6:
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "El tercer dígito de la cédula debe ser menor a 6.",
            }
        digito_verificador = _calcular_digito_mod10(documento_limpio)
        if digito_verificador != int(documento_limpio[-1]):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "La cédula no pasó la validación del dígito verificador.",
            }
        return {
            "valido": True,
            "documento_limpio": documento_limpio,
            "mensaje": "La cédula es válida.",
        }

    if tipo == "RUC":
        documento_limpio = re.sub(r"\D", "", documento)
        if len(documento_limpio) != 13:
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "El RUC debe tener exactamente 13 dígitos.",
            }
        if not DIGIT_ONLY_PATTERN.fullmatch(documento_limpio):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "El RUC debe contener solo números.",
            }
        if not documento_limpio.endswith("001"):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "El RUC debe terminar en 001.",
            }
        if not _validar_provincia(documento_limpio):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "La provincia del RUC no es válida.",
            }

        tercer_digito = int(documento_limpio[2])
        if tercer_digito in {0, 1, 2, 3, 4, 5}:
            cedula_parte = documento_limpio[:10]
            digito_verificador = _calcular_digito_mod10(cedula_parte)
            if digito_verificador != int(cedula_parte[-1]):
                return {
                    "valido": False,
                    "documento_limpio": documento_limpio,
                    "mensaje": "El RUC de persona natural no pasó la validación del dígito verificador.",
                }
        elif tercer_digito == 6:
            coeficientes = [3, 2, 7, 6, 5, 4, 3, 2]
            digito_verificador = _calcular_digito_mod11(documento_limpio[:8], coeficientes)
            if digito_verificador != int(documento_limpio[8]):
                return {
                    "valido": False,
                    "documento_limpio": documento_limpio,
                    "mensaje": "El RUC de sociedad pública no pasó la validación del dígito verificador.",
                }
        elif tercer_digito == 9:
            coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]
            digito_verificador = _calcular_digito_mod11(documento_limpio[:9], coeficientes)
            if digito_verificador != int(documento_limpio[9]):
                return {
                    "valido": False,
                    "documento_limpio": documento_limpio,
                    "mensaje": "El RUC de sociedad privada no pasó la validación del dígito verificador.",
                }
        else:
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "El tercer dígito del RUC no corresponde a un tipo válido.",
            }

        return {
            "valido": True,
            "documento_limpio": documento_limpio,
            "mensaje": "El RUC es válido.",
        }

    if tipo == "Pasaporte":
        documento_limpio = re.sub(r"\s+", "", documento)
        if not ALPHA_NUMERIC_PATTERN.fullmatch(documento_limpio):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "El pasaporte debe contener solo letras y números.",
            }
        if not (6 <= len(documento_limpio) <= 15):
            return {
                "valido": False,
                "documento_limpio": documento_limpio,
                "mensaje": "El pasaporte debe tener entre 6 y 15 caracteres.",
            }
        return {
            "valido": True,
            "documento_limpio": documento_limpio,
            "mensaje": "El pasaporte es válido.",
        }

    return {
        "valido": False,
        "documento_limpio": "",
        "mensaje": "Tipo de documento no soportado.",
    }


def validate_cedula_ruc(value):
    """Validador Django que acepta documentos ecuatorianos o pasaporte en un solo campo."""

    documento = validar_documento_ecuador("Cédula", value)
    if documento["valido"]:
        return

    documento_ruc = validar_documento_ecuador("RUC", value)
    if documento_ruc["valido"]:
        return

    documento_pasaporte = validar_documento_ecuador("Pasaporte", value)
    if documento_pasaporte["valido"]:
        return

    raise ValidationError(
        "Ingrese un documento de identidad ecuatoriano válido."
    )


def validate_phone(value):
    """Valida telefonos numericos nacionales o internacionales con longitud razonable."""

    value = (value or "").strip()
    if not re.fullmatch(r"\+?\d{10,15}", value):
        raise ValidationError("Ingrese un número de teléfono válido.")
    if not (10 <= len(value.replace('+', '')) <= 15):
        raise ValidationError("El teléfono debe tener entre 10 y 15 caracteres.")


def validate_password_strength(value):
    """Exige una contrasena minima para cuentas de clientes y usuarios gestionados."""

    value = value or ""
    weak_passwords = {
        '12345678',
        'password',
        'admin123',
        'qwerty123',
        '123456789',
        'abcdefg1',
    }
    if len(value) < 8:
        raise ValidationError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
        )
    if value.lower() in weak_passwords:
        raise ValidationError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
        )
    if not re.search(r"[A-Z]", value):
        raise ValidationError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
        )
    if not re.search(r"[a-z]", value):
        raise ValidationError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
        )
    if not re.search(r"\d", value):
        raise ValidationError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
        )
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValidationError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
        )


def validate_email_format(value):
    """Comprueba una estructura basica de correo antes de guardar o autenticar."""

    if not value or "@" not in value or "." not in value.split('@')[-1]:
        raise ValidationError("El correo electrónico debe tener un formato válido.")
