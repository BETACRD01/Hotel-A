from .common import *

def mis_reservas_view(request):
    cancelar_reservas_vencidas()

    cliente_id = request.session.get("cliente_id")

    if not cliente_id:
        messages.warning(request, "Debes iniciar sesiÃ³n para ver tus reservas.")
        return redirect("gestion:login")

    reservas_base = Reservas.objects.filter(
        id_cliente_id=cliente_id
    )

    reservas = reservas_base.exclude(
        estado_reserva="Cancelada"
    ).prefetch_related(
        "detallehabitaciones_set",
        "detallecabanas_set",
        "detallecine_set",
        "detalleresort_set",
        "pagos",
    ).order_by("-fecha_registro")

    reservas_pago_pendiente = reservas.exclude(
        estado_pago__in=["Pagado", "En revision", "Anulado", "Cancelado"]
    )

    contexto = {
        "reservas": reservas,
        "reservas_canceladas_ocultas": reservas_base.filter(estado_reserva="Cancelada").count(),
        "reservas_pago_pendiente_count": reservas_pago_pendiente.count(),
        "proxima_reserva_pago": reservas_pago_pendiente.order_by("fecha_limite_pago").first(),
    }

    return render(request, "client/mis_reservas.html", contexto)


def cancelar_reserva_view(request, id_reserva):
    """
    Cancela una reserva propia del cliente autenticado mediante POST.
    """
    cliente_id = request.session.get("cliente_id") or request.session.get("usuario_id")
    usuario_rol = request.session.get("usuario_rol")

    if not cliente_id or not usuario_rol:
        messages.error(request, "Debe iniciar sesiÃ³n para continuar.")
        return redirect("gestion:login")

    if usuario_rol != "cliente":
        messages.error(request, "Este panel es solo para clientes.")
        return redirect("gestion:login")

    try:
        cliente = Cliente.objects.get(id_cliente=cliente_id, activo=True)
    except Cliente.DoesNotExist:
        request.session.flush()
        messages.error(request, "Debe iniciar sesiÃ³n para continuar.")
        return redirect("gestion:login")

    if request.method != "POST":
        messages.error(request, "No puede cancelar esta reserva.")
        return redirect("gestion:mis_reservas")

    reserva = Reservas.objects.filter(id_reserva=id_reserva, id_cliente=cliente).first()

    if reserva is None:
        messages.error(request, "No tiene permiso para cancelar esta reserva.")
        return redirect("gestion:mis_reservas")

    if reserva.estado_reserva not in {"Pendiente", "Confirmada"}:
        messages.error(request, "No puede cancelar esta reserva.")
        return redirect("gestion:mis_reservas")

    reserva.estado_reserva = "Cancelada"
    reserva.estado_pago = "Anulado"
    reserva.fecha_cancelacion = timezone.now()
    reserva.motivo_cancelacion = "Cancelada por el cliente desde el sistema."
    reserva.save(update_fields=["estado_reserva", "estado_pago", "fecha_cancelacion", "motivo_cancelacion"])

    messages.success(request, "Reserva cancelada correctamente.")
    return redirect("gestion:mis_reservas")


# ============================================================
# PAGOS MANUALES
# ============================================================
