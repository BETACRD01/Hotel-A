from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from gestion_hotel.models import Reservas


def convertir_decimal(valor):
    return Decimal(str(valor or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def obtener_noches_por_programa(programa):
    programas = {
        "2D1N": 1,
        "3D2N": 2,
        "4D3N": 3,
    }
    return programas.get(programa, 1)


def obtener_precio_tarifa(tarifa, tipo_ocupacion):
    if not tarifa:
        return Decimal("0.00")

    if tipo_ocupacion == "Total":
        return convertir_decimal(tarifa.precio_ocupacion_total)

    return convertir_decimal(tarifa.precio_ocupacion_secundaria)


def normalizar_tipo_ocupacion(tarifa, tipo_ocupacion):
    if tipo_ocupacion == "Total":
        return "Total"

    return tarifa.tipo_ocupacion_secundaria


def obtener_tipo_ocupacion_final(servicio, tipo_ocupacion):
    if tipo_ocupacion == "Total":
        return "Total"

    return servicio.tipo_ocupacion_secundaria


def calcular_valores_reserva(reserva):
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
