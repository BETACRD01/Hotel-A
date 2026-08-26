from decimal import Decimal, ROUND_HALF_UP

from .common import *

METODOS_PAGO_DISPONIBLES = {
    "Transferencia": "Transferencia bancaria",
    "Recepcion": "Pago en recepciÃ³n",
}


def obtener_metodo_pago_formulario(request):
    metodo_pago = (request.POST.get("metodo_pago") or "").strip()
    if metodo_pago not in METODOS_PAGO_DISPONIBLES:
        return "Sin seleccionar"
    return metodo_pago


def redirigir_segun_metodo_pago(reserva, metodo_pago):
    if metodo_pago == "Transferencia":
        return redirect("gestion:pago_transferencia", id_reserva=reserva.id_reserva)
    return redirect("gestion:mis_reservas")


# ============================================================
# PAGOS
# ============================================================

def obtener_reserva_del_cliente(id_reserva, cliente_id):
    return get_object_or_404(
        Reservas,
        id_reserva=id_reserva,
        id_cliente_id=cliente_id,
    )


def obtener_monto_anticipo(reserva):
    monto = reserva.anticipo_minimo or reserva.total or Decimal("0.00")
    return Decimal(str(monto)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def datos_bancarios_contexto():
    return [
        {
            "nombre": settings.BANCO_1_NOMBRE,
            "tipo": settings.BANCO_1_TIPO,
            "cuenta": settings.BANCO_1_CUENTA,
            "titular": settings.BANCO_1_TITULAR,
            "identificacion": settings.BANCO_1_IDENTIFICACION,
            "correo": settings.BANCO_1_CORREO,
        },
    ]


def crear_pago_base(reserva, metodo_pago, estado="Pendiente"):
    monto_anticipo = obtener_monto_anticipo(reserva)

    pago = PagoReserva.objects.create(
        reserva=reserva,
        metodo_pago=metodo_pago,
        estado=estado,
        monto_total=reserva.total or 0,
        monto_anticipo=monto_anticipo,
        saldo_pendiente=reserva.saldo_pendiente or 0,
    )

    return pago


def seleccionar_pago_view(request, id_reserva):
    cancelar_reservas_vencidas()

    cliente_id = request.session.get("cliente_id")

    if not cliente_id:
        messages.warning(request, "Debes iniciar sesiÃ³n para pagar tu reserva.")
        return redirect("gestion:login")

    reserva = obtener_reserva_del_cliente(id_reserva, cliente_id)

    if reserva.estado_pago == "Pagado":
        messages.info(request, "Esta reserva ya se encuentra pagada.")
        return redirect("gestion:mis_reservas")

    contexto = {
        "reserva": reserva,
        "monto_anticipo": obtener_monto_anticipo(reserva),
    }

    return render(request, "payments/seleccionar_pago.html", contexto)


def pago_transferencia_view(request, id_reserva):
    cancelar_reservas_vencidas()

    cliente_id = request.session.get("cliente_id")

    if not cliente_id:
        messages.warning(request, "Debes iniciar sesiÃ³n para registrar la transferencia.")
        return redirect("gestion:login")

    reserva = obtener_reserva_del_cliente(id_reserva, cliente_id)

    if reserva.estado_pago == "Pagado":
        messages.info(request, "Esta reserva ya se encuentra pagada.")
        return redirect("gestion:mis_reservas")

    if request.method == "POST":
        banco_origen = request.POST.get("banco_origen", "").strip()
        numero_cuenta = request.POST.get("numero_cuenta", "").strip()
        numero_comprobante = request.POST.get("numero_comprobante", "").strip()
        observacion = request.POST.get("observacion", "").strip()
        comprobante = request.FILES.get("comprobante")

        if not banco_origen:
            messages.error(request, "Debes ingresar el banco desde donde realizaste la transferencia.")
            return redirect("gestion:pago_transferencia", id_reserva=reserva.id_reserva)

        if not numero_cuenta:
            messages.error(request, "Debes ingresar el nÃºmero de cuenta desde donde realizaste la transferencia.")
            return redirect("gestion:pago_transferencia", id_reserva=reserva.id_reserva)

        if not numero_cuenta.isdigit() or not (8 <= len(numero_cuenta) <= 30):
            messages.error(request, "El nÃºmero de cuenta debe contener solo dÃ­gitos y tener entre 8 y 30 caracteres.")
            return redirect("gestion:pago_transferencia", id_reserva=reserva.id_reserva)

        if not numero_comprobante:
            messages.error(request, "Debes ingresar el nÃºmero de comprobante.")
            return redirect("gestion:pago_transferencia", id_reserva=reserva.id_reserva)

        if not comprobante:
            messages.error(request, "Debes subir la imagen del comprobante.")
            return redirect("gestion:pago_transferencia", id_reserva=reserva.id_reserva)

        pago = crear_pago_base(
            reserva=reserva,
            metodo_pago="Transferencia",
            estado="En revision",
        )

        pago.banco_origen = banco_origen
        pago.numero_cuenta_origen = numero_cuenta
        pago.numero_comprobante = numero_comprobante
        pago.comprobante = comprobante
        pago.observacion = observacion or "Comprobante de transferencia enviado por el cliente."
        pago.save()

        reserva.metodo_pago = "Transferencia"
        reserva.estado_pago = "En revision"
        reserva.save()

        messages.success(
            request,
            "Comprobante enviado correctamente. El administrador revisarÃ¡ el pago.",
        )
        return redirect("gestion:mis_reservas")

    contexto = {
        "reserva": reserva,
        "monto_anticipo": obtener_monto_anticipo(reserva),
        "bancos": datos_bancarios_contexto(),
    }

    return render(request, "payments/pago_transferencia.html", contexto)


# ============================================================
# MÓDULO GERENTE
# ============================================================
