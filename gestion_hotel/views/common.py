"""Imports y helpers compartidos por las vistas de cliente, catalogo, pagos y gerente."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
import random
import re
import socket
import smtplib
import uuid

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.utils import ProgrammingError
from django.forms import modelform_factory
from ..validators import validate_password_strength
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from ..forms import ClienteLoginForm, ClienteRegistroForm
from ..models import (
    Cabanas,
    Cine,
    Cliente,
    DetalleCabanas,
    DetalleCine,
    DetalleHabitaciones,
    DetalleResort,
    Habitaciones,
    PagoReserva,
    Reservas,
    ResortDia,
    ConfiguracionInicio,
    ESTADO_HABITACION_CHOICES,
    ESTADO_RESERVA_CHOICES,
)
from ..utils.validaciones import (
    validar_documento_cliente,
    validar_celular_cliente,
    validar_correo_cliente,
)
from ..services.reservations import (
    calcular_valores_reserva,
    cancelar_reservas_vencidas,
    convertir_decimal,
    normalizar_tipo_ocupacion,
    obtener_noches_por_programa,
    obtener_precio_tarifa,
    obtener_tipo_ocupacion_final,
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_usuario_sesion(request):
    """
    Obtiene el usuario que iniciÃ³ sesiÃ³n.

    Retorna:
        Cliente: cuando existe una sesiÃ³n vÃ¡lida.
        None: cuando no existe una sesiÃ³n vÃ¡lida.
    """
    usuario_id = request.session.get("cliente_id") or request.session.get("usuario_id")

    if not usuario_id:
        return None

    usuario = Cliente.objects.filter(
        id_cliente=usuario_id
    ).first()

    if usuario is None or not usuario.activo:
        request.session.flush()
        return None

    if usuario.rol not in {'cliente', 'gerente'}:
        request.session.flush()
        return None

    return usuario


def sincronizar_acceso_admin_gerente(request, gerente, password):
    """Crea o actualiza el usuario auth que permite al gerente entrar al admin Django."""

    user_model = get_user_model()
    username = gerente.correo_electronico or f"gerente_{gerente.id_cliente}"
    auth_user, _ = user_model.objects.get_or_create(username=username)

    auth_user.email = gerente.correo_electronico or ""
    auth_user.first_name = gerente.nombres or ""
    auth_user.last_name = gerente.apellidos or ""
    auth_user.is_active = True
    auth_user.is_staff = True
    auth_user.is_superuser = False
    auth_user.set_password(password)
    auth_user.save()

    auth_login(request, auth_user)
    return auth_user


def _config_fondo(campo):
    """
    Retorna el archivo de imagen de un campo de fondo de ConfiguracionInicio,
    o None si no existe configuraciÃ³n o no hay imagen cargada.
    """
    config = ConfiguracionInicio.objects.first()
    if not config:
        return None
    valor = getattr(config, campo, None)
    return valor if valor else None


def normalizar_combo_cabana(valor, cabana=None):
    """Convierte la seleccion de cabana del formulario en un texto consistente para guardar."""

    if cabana is not None:
        return f"CabaÃ±a {cabana.numero_cabana}"

    texto = (valor or "").strip()
    if not texto:
        return "Sin selecciÃ³n"

    match = re.search(r"c(?:abaÃ±a|abaÃ±as)?\s*([A-Za-z0-9]+)", texto, flags=re.IGNORECASE)
    if match:
        return f"CabaÃ±a {match.group(1)}"

    return texto


def validar_acceso(request):
    """
    Verifica si existe una sesiÃ³n activa para clientes.
    """
    usuario = obtener_usuario_sesion(request)

    if usuario is None:
        messages.error(
            request,
            "Debes iniciar sesiÃ³n como cliente para acceder a esta pÃ¡gina."
        )

    return usuario


def convertir_entero(valor, predeterminado=1):
    """
    Convierte un valor a entero y evita cantidades menores que uno.
    """
    try:
        numero = int(valor)
        return numero if numero > 0 else predeterminado
    except (TypeError, ValueError):
        return predeterminado


def obtener_entero_positivo(valor, campo, minimo=1, permitir_cero=False):
    """
    Intenta convertir `valor` a entero validando reglas bÃ¡sicas.

    Args:
        valor: valor recibido (string, number, etc.).
        campo: nombre del campo usado en mensajes de error.
        minimo: mÃ­nimo aceptable (por defecto 1).
        permitir_cero: si True permite 0 como valor vÃ¡lido.

    Returns:
        int: valor convertido si es vÃ¡lido.

    Raises:
        ValueError: con mensaje apropiado si el valor no es vÃ¡lido.
    """
    if valor is None:
        raise ValueError(f"La cantidad para {campo} es requerida.")

    valor_str = str(valor).strip()
    if valor_str == "":
        raise ValueError(f"La cantidad para {campo} es requerida.")

    # Reject decimals (como '1.0' o '2.5') y cualquier texto no numÃ©rico
    if not valor_str.isdigit():
        raise ValueError(f"La cantidad de {campo} debe ser un nÃºmero entero vÃ¡lido.")

    numero = int(valor_str)

    if permitir_cero:
        if numero < 0:
            raise ValueError(f"La cantidad de {campo} no puede ser negativa.")
    else:
        if numero < minimo:
            if minimo == 1:
                raise ValueError(f"La cantidad de {campo} debe ser mayor o igual a 1.")
            raise ValueError(f"La cantidad de {campo} debe ser vÃ¡lida y al menos {minimo}.")

    return numero


def generar_codigo_reserva():
    """Genera un cÃ³digo ARH Ãºnico para una reserva."""
    while True:
        codigo = f"ARH-{uuid.uuid4().hex[:6].upper()}"
        if not Reservas.objects.filter(codigo_reserva=codigo).exists():
            return codigo


def requiere_rol(request, roles, mensaje="No tienes permisos para realizar esta acciÃ³n."):
    """Devuelve el usuario de sesion solo si su rol pertenece a los roles permitidos."""

    usuario = obtener_usuario_sesion(request)
    if usuario is None:
        return None
    if usuario.rol not in roles:
        messages.error(request, mensaje)
        return None
    return usuario


def puede_cancelar_reserva(usuario, reserva):
    """Determina si el usuario puede cancelar una reserva segun rol, dueno y estado."""

    if usuario.rol in {"admin", "gerente"}:
        return True
    return usuario.id_cliente == reserva.id_cliente_id and reserva.estado_reserva in {"Pendiente", "Confirmada"}



def convertir_fecha_formulario(valor, nombre_campo="fecha"):
    """Convierte fechas HTML yyyy-mm-dd en objetos date y produce errores claros."""

    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"La {nombre_campo} es obligatoria o no tiene un formato vÃ¡lido.")



# ============================================================
# PÃGINA PÃšBLICA
# ============================================================
