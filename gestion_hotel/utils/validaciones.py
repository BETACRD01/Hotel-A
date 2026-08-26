"""Funciones de normalizacion y validacion usadas antes de crear clientes desde vistas."""

import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

def limpiar_numeros(valor):
    """Devuelve solo digitos para cedulas, RUC y telefonos."""

    return re.sub(r"\D", "", valor or "")

def limpiar_pasaporte(valor):
    """Normaliza pasaportes dejando letras y numeros en mayusculas."""

    return re.sub(r"[^A-Za-z0-9]", "", valor or "").upper()

def limpiar_correo(valor):
    """Normaliza correos para comparaciones insensibles a mayusculas y espacios."""

    return (valor or "").strip().lower()

def normalizar_tipo_documento(tipo_documento):
    """Unifica variantes escritas del tipo de documento recibido desde formularios."""

    tipo = (tipo_documento or "").strip().lower()
    tipo = tipo.replace("é", "e")
    return tipo

def validar_provincia(numero):
    """Valida que los dos primeros digitos correspondan a una provincia ecuatoriana."""

    if len(numero) < 2:
        return False

    provincia = int(numero[:2])
    return 1 <= provincia <= 24

def modulo_10(cedula):
    """Calcula y compara el digito verificador de cedula por modulo 10."""

    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0

    for i in range(9):
        valor = int(cedula[i]) * coeficientes[i]

        if valor >= 10:
            valor -= 9

        suma += valor

    digito = 10 - (suma % 10)

    if digito == 10:
        digito = 0

    return digito == int(cedula[9])

def modulo_11(numero, coeficientes, posicion_verificador):
    """Calcula y compara digito verificador para RUC publico o privado por modulo 11."""

    suma = 0

    for i, coeficiente in enumerate(coeficientes):
        suma += int(numero[i]) * coeficiente

    residuo = suma % 11
    digito = 11 - residuo

    if digito == 11:
        digito = 0

    if digito == 10:
        return False

    return digito == int(numero[posicion_verificador])

def validar_cedula(numero_documento):
    """Valida formato, provincia y digito verificador de una cedula ecuatoriana."""

    numero = limpiar_numeros(numero_documento)

    if len(numero) == 9:
        numero = "0" + numero

    if len(numero) != 10:
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "La cédula debe tener 10 dígitos."
        }

    if numero == numero[0] * len(numero):
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "La cédula ingresada no es válida."
        }

    if not validar_provincia(numero):
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "El código de provincia de la cédula no es válido."
        }

    if int(numero[2]) >= 6:
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "El tercer dígito de la cédula no es válido."
        }

    if not modulo_10(numero):
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "El dígito verificador de la cédula no es válido."
        }

    return {
        "valido": True,
        "documento": numero,
        "mensaje": "Cédula válida."
    }

def validar_ruc(numero_documento):
    """Valida RUC ecuatoriano de persona natural, institucion publica o sociedad privada."""

    numero = limpiar_numeros(numero_documento)

    if len(numero) != 13:
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "El RUC debe tener exactamente 13 dígitos."
        }

    if not numero.endswith("001"):
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "El RUC debe terminar en 001."
        }

    if not validar_provincia(numero):
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "El código de provincia del RUC no es válido."
        }

    tercer_digito = int(numero[2])

    if 0 <= tercer_digito <= 5:
        cedula_base = numero[:10]
        resultado = validar_cedula(cedula_base)

        if not resultado["valido"]:
            return {
                "valido": False,
                "documento": numero,
                "mensaje": "El RUC de persona natural no es válido."
            }

    elif tercer_digito == 6:
        coeficientes = [3, 2, 7, 6, 5, 4, 3, 2]

        if not modulo_11(numero, coeficientes, 8):
            return {
                "valido": False,
                "documento": numero,
                "mensaje": "El RUC de institución pública no es válido."
            }

    elif tercer_digito == 9:
        coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]

        if not modulo_11(numero, coeficientes, 9):
            return {
                "valido": False,
                "documento": numero,
                "mensaje": "El RUC de sociedad privada no es válido."
            }

    else:
        return {
            "valido": False,
            "documento": numero,
            "mensaje": "El tercer dígito del RUC no es válido."
        }

    return {
        "valido": True,
        "documento": numero,
        "mensaje": "RUC válido."
    }

def validar_pasaporte(numero_documento):
    """Valida estructura alfanumerica basica de pasaporte."""

    documento = limpiar_pasaporte(numero_documento)

    if len(documento) < 6 or len(documento) > 15:
        return {
            "valido": False,
            "documento": documento,
            "mensaje": "El pasaporte debe tener entre 6 y 15 caracteres."
        }

    return {
        "valido": True,
        "documento": documento,
        "mensaje": "Pasaporte válido."
    }

def validar_documento_cliente(tipo_documento, numero_documento):
    """Valida y normaliza el documento antes de continuar con el registro de cliente."""

    tipo = normalizar_tipo_documento(tipo_documento)

    if tipo == "cedula":
        return validar_cedula(numero_documento)

    if tipo == "ruc":
        return validar_ruc(numero_documento)

    if tipo == "pasaporte":
        return validar_pasaporte(numero_documento)

    return {
        "valido": False,
        "documento": numero_documento,
        "mensaje": "Tipo de documento no válido."
    }

def validar_celular_cliente(tipo_documento, telefono):
    """Valida el telefono del cliente segun reglas de longitud del sistema."""

    tipo = normalizar_tipo_documento(tipo_documento)
    telefono_limpio = limpiar_numeros(telefono)

    if tipo in ["cedula", "ruc"]:
        if len(telefono_limpio) != 10:
            return {
                "valido": False,
                "telefono": telefono_limpio,
                "mensaje": "El celular ecuatoriano debe tener 10 dígitos."
            }

        if not telefono_limpio.startswith("09"):
            return {
                "valido": False,
                "telefono": telefono_limpio,
                "mensaje": "El celular ecuatoriano debe iniciar con 09."
            }

    elif tipo == "pasaporte":
        if len(telefono_limpio) < 7 or len(telefono_limpio) > 15:
            return {
                "valido": False,
                "telefono": telefono_limpio,
                "mensaje": "El teléfono internacional debe tener entre 7 y 15 dígitos."
            }

    else:
        return {
            "valido": False,
            "telefono": telefono_limpio,
            "mensaje": "Tipo de documento no válido para validar teléfono."
        }

    return {
        "valido": True,
        "telefono": telefono_limpio,
        "mensaje": "Teléfono válido."
    }

def validar_correo_cliente(correo):
    """Valida y normaliza el correo usado para registro y recuperacion de acceso."""

    correo_limpio = limpiar_correo(correo)

    if not correo_limpio:
        return {
            "valido": False,
            "correo": correo_limpio,
            "mensaje": "El correo electrónico es obligatorio."
        }

    try:
        validate_email(correo_limpio)
    except ValidationError:
        return {
            "valido": False,
            "correo": correo_limpio,
            "mensaje": "El correo electrónico no tiene un formato válido."
        }

    return {
        "valido": True,
        "correo": correo_limpio,
        "mensaje": "Correo electrónico válido."
    }
