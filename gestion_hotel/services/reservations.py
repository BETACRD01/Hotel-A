"""Servicios de negocio para calculos y mantenimiento de reservas."""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from gestion_hotel.models import Reservas


def convertir_decimal(valor):
    """Convierte importes a Decimal con dos decimales para evitar errores de redondeo."""

    return Decimal(str(valor or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def obtener_noches_por_programa(programa):
    """Traduce el codigo o texto de programa de hospedaje a cantidad de noches."""

    if not programa:
        return 1

    p = str(programa).upper()
    if "2D1N" in p or ("2" in p and ("1" in p or "NOCHE" in p)):
        return 1
    if "3D2N" in p or ("3" in p and ("2" in p or "NOCHE" in p)):
        return 2
    if "4D3N" in p or ("4" in p and ("3" in p or "NOCHE" in p)):
        return 3

    import re
    match = re.search(r"(\d+)\s*NOCHE", p)
    if match:
        return max(1, int(match.group(1)))

    match_dias = re.search(r"(\d+)\s*D[IÍ]A", p)
    if match_dias:
        return max(1, int(match_dias.group(1)) - 1)

    return 1


def resolver_programa_y_noches(programa, fecha_ingreso_obj, fecha_salida_obj=None):
    """
    Normaliza el programa escrito o seleccionado y resuelve la cantidad de noches y fecha de salida.
    Retorna (programa_codigo, programa_guardar, noches, fecha_salida_obj).
    """

    p = (programa or "").strip()
    p_upper = p.upper()

    programa_codigo = None
    if p_upper == "2D1N" or ("2" in p_upper and ("1" in p_upper or "NOCHE" in p_upper)):
        programa_codigo = "2D1N"
        programa_guardar = "2D1N"
        noches_base = 1
    elif p_upper == "3D2N" or ("3" in p_upper and ("2" in p_upper or "NOCHE" in p_upper)):
        programa_codigo = "3D2N"
        programa_guardar = "3D2N"
        noches_base = 2
    elif p_upper == "4D3N" or ("4" in p_upper and ("3" in p_upper or "NOCHE" in p_upper)):
        programa_codigo = "4D3N"
        programa_guardar = "4D3N"
        noches_base = 3
    else:
        programa_codigo = None
        programa_guardar = p[:20] if p else "Personalizado"
        noches_base = obtener_noches_por_programa(p)

    if fecha_salida_obj and fecha_salida_obj > fecha_ingreso_obj:
        noches = (fecha_salida_obj - fecha_ingreso_obj).days
    else:
        noches = noches_base
        fecha_salida_obj = fecha_ingreso_obj + timedelta(days=noches)

    return programa_codigo, programa_guardar, noches, fecha_salida_obj


def calcular_precio_estadia(servicio, programa_codigo, tipo_ocupacion, noches):
    """Calcula el precio del hospedaje segun el programa o noches personalizadas."""

    if programa_codigo:
        precio = convertir_decimal(servicio.obtener_precio_programa(programa_codigo, tipo_ocupacion))
        if precio > 0:
            return precio

    precio_noche = getattr(servicio, "precio_noche", None)
    if precio_noche and precio_noche > 0:
        return convertir_decimal(precio_noche * noches)

    if getattr(servicio, "precio_4d3n_total", None) and servicio.precio_4d3n_total > 0:
        return convertir_decimal((servicio.precio_4d3n_total / 3) * noches)

    if getattr(servicio, "precio_2d1n_total", None) and servicio.precio_2d1n_total > 0:
        return convertir_decimal(servicio.precio_2d1n_total * noches)

    return Decimal("0.00")



def obtener_precio_tarifa(tarifa, tipo_ocupacion):
    """Obtiene el precio correcto para ocupacion total o secundaria desde una tarifa."""

    if not tarifa:
        return Decimal("0.00")

    if tipo_ocupacion == "Total":
        return convertir_decimal(tarifa.precio_ocupacion_total)

    return convertir_decimal(tarifa.precio_ocupacion_secundaria)


def normalizar_tipo_ocupacion(tarifa, tipo_ocupacion):
    """Devuelve la etiqueta de ocupacion que debe guardarse en el detalle de reserva."""

    if tipo_ocupacion == "Total":
        return "Total"

    return tarifa.tipo_ocupacion_secundaria


def obtener_tipo_ocupacion_final(servicio, tipo_ocupacion):
    """Resuelve la ocupacion final usando la configuracion del servicio reservado."""

    if tipo_ocupacion == "Total":
        return "Total"

    return servicio.tipo_ocupacion_secundaria


def calcular_valores_reserva(reserva):
    """Recalcula subtotales, anticipo y saldo despues de crear o modificar detalles."""

    reserva.refresh_from_db()
    reserva.calcular_valores_pago()
    reserva.save()
    return reserva


def cancelar_reservas_vencidas():
    """
    Cancela automaticamente reservas pendientes o confirmadas cuando vence
    el plazo de pago de 24 horas desde su registro.
    """
    limite_24h = timezone.now() - timedelta(days=1)
    vencidas = Reservas.objects.filter(
        estado_reserva__in=["Pendiente", "Confirmada"],
        estado_pago__in=[
            "Pendiente",
            "En revision",
            "Rechazado",
            "Cancelado",
            "Anulado",
        ],
        fecha_registro__lt=limite_24h,
    )

    total = vencidas.count()
    if total:
        vencidas.update(
            estado_reserva="Cancelada",
            estado_pago="Anulado",
            fecha_cancelacion=timezone.now(),
            motivo_cancelacion="Cancelada automaticamente por vencer el plazo de pago de 24 horas.",
        )
    return total
