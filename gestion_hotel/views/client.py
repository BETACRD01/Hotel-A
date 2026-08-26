from .common import *

def panel_cliente_view(request):
    """
    Muestra el panel propio del cliente autenticado con sus datos y reservas.
    """
    cliente_id = request.session.get("cliente_id") or request.session.get("usuario_id")
    usuario_rol = request.session.get("usuario_rol")

    if not cliente_id or not usuario_rol:
        messages.error(request, "Debe iniciar sesiÃ³n para continuar.")
        return redirect("gestion:login")

    if usuario_rol != "cliente":
        messages.error(request, "Este panel es solo para clientes.")
        return redirect("gestion:login")

    usuario = Cliente.objects.filter(
        id_cliente=cliente_id,
        rol="cliente",
        activo=True,
    ).first()

    if usuario is None:
        request.session.flush()
        messages.error(request, "Debe iniciar sesiÃ³n para continuar.")
        return redirect("gestion:login")

    if not request.session.get("cliente_nombre"):
        request.session["cliente_nombre"] = f"{usuario.nombres} {usuario.apellidos}".strip().title()
    if request.session.get("cliente_correo") is None:
        request.session["cliente_correo"] = usuario.correo_electronico or ""
    if request.session.get("cliente_telefono") is None:
        request.session["cliente_telefono"] = usuario.telefono_celular or ""
    if request.session.get("cliente_documento") is None:
        request.session["cliente_documento"] = usuario.numero_documento or ""
    if request.session.get("cliente_ubicacion") is None:
        if usuario.ciudad or usuario.pais_origen:
            request.session["cliente_ubicacion"] = ", ".join(
                part for part in [usuario.ciudad, usuario.pais_origen] if part
            )
        else:
            request.session["cliente_ubicacion"] = ""

    try:
        reservas_usuario = Reservas.objects.filter(id_cliente=usuario).order_by("-fecha_registro")
        total_reservas = reservas_usuario.count()
        reservas_pendientes = reservas_usuario.filter(estado_reserva="Pendiente").count()
        reservas_confirmadas = reservas_usuario.filter(estado_reserva="Confirmada").count()
        reservas_canceladas = reservas_usuario.filter(estado_reserva="Cancelada").count()
        reservas_finalizadas = reservas_usuario.filter(estado_reserva="Finalizada").count()
        ultimas_reservas = reservas_usuario[:5]
    except ProgrammingError:
        total_reservas = 0
        reservas_pendientes = 0
        reservas_confirmadas = 0
        reservas_canceladas = 0
        reservas_finalizadas = 0
        ultimas_reservas = []

    config = ConfiguracionInicio.objects.first()

    def primera_imagen(modelo):
        obj = modelo.objects.exclude(imagen=None).exclude(imagen="").first()
        return obj.imagen if obj else None

    contexto = {
        "usuario": usuario,
        "total_reservas": total_reservas,
        "reservas_pendientes": reservas_pendientes,
        "reservas_confirmadas": reservas_confirmadas,
        "reservas_canceladas": reservas_canceladas,
        "reservas_finalizadas": reservas_finalizadas,
        "ultimas_reservas": ultimas_reservas,
        "imagen_habitaciones": (config.imagen_habitaciones if config and config.imagen_habitaciones else primera_imagen(Habitaciones)),
        "imagen_cabanas": (config.imagen_cabanas if config and config.imagen_cabanas else primera_imagen(Cabanas)),
        "imagen_cine": (config.imagen_cine if config and config.imagen_cine else primera_imagen(Cine)),
        "imagen_resort": (config.imagen_resort if config and config.imagen_resort else primera_imagen(ResortDia)),
    }

    return render(
        request,
        "panel_cliente.html",
        contexto
    )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_view(request):
    """
    Muestra el panel principal del usuario.
    """
    cancelar_reservas_vencidas()

    usuario = obtener_usuario_sesion(request)

    if usuario is None:
        return redirect("gestion:login")

    if usuario.rol == "cliente":
        return redirect("gestion:panel_cliente")

    try:
        reservas_usuario = Reservas.objects.filter(id_cliente=usuario)
        reservas_pendientes = reservas_usuario.filter(estado_reserva="Pendiente").count()
        reservas_confirmadas = reservas_usuario.filter(estado_reserva="Confirmada").count()
        ultimas_reservas = reservas_usuario.order_by("-fecha_registro")[:3]
        ultimas_reservas_count = len(ultimas_reservas)
    except ProgrammingError:
        reservas_pendientes = 0
        reservas_confirmadas = 0
        ultimas_reservas = []
        ultimas_reservas_count = 0

    contexto = {
        "usuario": usuario,
        "total_habitaciones": Habitaciones.objects.filter(
            estado="Disponible"
        ).count(),
        "total_cabanas": Cabanas.objects.filter(
            estado="Disponible"
        ).count(),
        "total_cine": Cine.objects.count(),
        "total_resort": ResortDia.objects.count(),
        "reservas_pendientes": reservas_pendientes,
        "reservas_confirmadas": reservas_confirmadas,
        "ultimas_reservas_count": ultimas_reservas_count,
    }

    return render(
        request,
        "dashboard.html",
        contexto
    )


# ============================================================
# MÃ‰TODOS DE PAGO DISPONIBLES AL RESERVAR
# ============================================================
