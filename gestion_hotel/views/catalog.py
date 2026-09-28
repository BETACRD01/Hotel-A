"""Vistas del catalogo publico que tambien crean reservas por tipo de servicio."""

from .common import *
from .common import _config_fondo
from .payments import obtener_metodo_pago_formulario, redirigir_segun_metodo_pago

def habitaciones_view(request):
    """Muestra habitaciones disponibles y procesa reservas de hospedaje."""

    cancelar_reservas_vencidas()

    habitaciones = Habitaciones.objects.filter(
        activo=True
    ).order_by("numero_habitacion")

    if request.method == "POST":
        cliente_id = request.session.get("cliente_id")

        if not cliente_id:
            messages.warning(request, "Debes iniciar sesiÃ³n para reservar.")
            return redirect("gestion:login")

        id_habitacion = request.POST.get("id_habitacion")
        programa = request.POST.get("programa")
        tipo_ocupacion = "Total"
        fecha_ingreso = request.POST.get("fecha_ingreso")
        fecha_salida = request.POST.get("fecha_salida")
        cantidad_personas = request.POST.get("cantidad_personas")
        observaciones = request.POST.get("observaciones", "")
        metodo_pago = obtener_metodo_pago_formulario(request)

        if not (programa or "").strip():
            messages.error(request, "Debes ingresar o seleccionar un programa de hospedaje.")
            return redirect("gestion:habitaciones")

        try:
            fecha_ingreso_obj = convertir_fecha_formulario(fecha_ingreso, "fecha de ingreso")
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("gestion:habitaciones")

        fecha_salida_obj = None
        if fecha_salida:
            try:
                fecha_salida_obj = convertir_fecha_formulario(fecha_salida, "fecha de salida")
                if fecha_salida_obj <= fecha_ingreso_obj:
                    messages.error(request, "La fecha de salida debe ser posterior a la fecha de ingreso.")
                    return redirect("gestion:habitaciones")
            except ValueError as error:
                messages.error(request, str(error))
                return redirect("gestion:habitaciones")

        habitacion = get_object_or_404(
            Habitaciones,
            id_habitacion=id_habitacion,
            activo=True
        )

        cliente = get_object_or_404(
            Cliente,
            id_cliente=cliente_id,
            activo=True
        )

        try:
            cantidad_personas_int = obtener_entero_positivo(cantidad_personas, "personas", minimo=1)
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("gestion:habitaciones")

        if cantidad_personas_int > habitacion.capacidad:
            messages.error(
                request,
                f"La habitación seleccionada permite máximo {habitacion.capacidad} persona(s)."
            )
            return redirect("gestion:habitaciones")

        tipo_ocupacion_final = obtener_tipo_ocupacion_final(habitacion, tipo_ocupacion)
        programa_codigo, programa_guardar, noches, fecha_salida_obj = resolver_programa_y_noches(
            programa, fecha_ingreso_obj, fecha_salida_obj
        )

        precio_programa = calcular_precio_estadia(
            habitacion, programa_codigo, tipo_ocupacion_final, noches
        )

        if precio_programa <= 0:
            messages.error(
                request,
                "No se pudo determinar el precio para el programa o las fechas seleccionadas."
            )
            return redirect("gestion:habitaciones")

        with transaction.atomic():
            reserva = Reservas.objects.create(
                id_cliente=cliente,
                fecha_ingreso=fecha_ingreso_obj,
                fecha_salida=fecha_salida_obj,
                estado_reserva="Pendiente",
                estado_pago="Pendiente",
                metodo_pago=metodo_pago,
                total=precio_programa,
                subtotal=precio_programa,
                observaciones=observaciones,
            )

            DetalleHabitaciones.objects.create(
                id_reserva=reserva,
                id_habitacion=habitacion,
                cantidad_noches=noches,
                subtotal=precio_programa,
                fecha_entrada=fecha_ingreso_obj,
                fecha_salida=fecha_salida_obj,
                precio_unitario=precio_programa,
                programa=programa_guardar,
                tipo_ocupacion=tipo_ocupacion_final,
                precio_programa=precio_programa,
                cantidad_personas=cantidad_personas_int,
            )

            calcular_valores_reserva(reserva)

        messages.success(
            request,
            "Reserva de habitación creada correctamente. Ahora puedes completar el pago."
        )
        return redirigir_segun_metodo_pago(reserva, metodo_pago)

    config = ConfiguracionInicio.objects.first()
    contexto = {
        "habitaciones": habitaciones,
        "usuario": request.session.get("cliente_id"),
        "fondo_habitaciones": _config_fondo("fondo_habitaciones"),
        "hero_kicker": getattr(config, "habitaciones_hero_kicker", None) or "Habitaciones",
        "hero_titulo": getattr(config, "habitaciones_hero_titulo", None) or "Confort y descanso en plena naturaleza",
        "hero_parrafo": getattr(config, "habitaciones_hero_parrafo", None) or "Espacios diseñados para tu bienestar, donde cada detalle te conecta con la tranquilidad de la Amazonía.",
    }

    return render(request, "public/habitaciones.html", contexto)


# ============================================================
# CABAÃ‘AS
# ============================================================

def cabanas_view(request):
    """Muestra cabanas disponibles y procesa reservas de hospedaje."""

    cancelar_reservas_vencidas()

    cabanas = Cabanas.objects.filter(
        activo=True
    ).order_by("numero_cabana")

    if request.method == "POST":
        cliente_id = request.session.get("cliente_id")

        if not cliente_id:
            messages.warning(request, "Debes iniciar sesión para reservar.")
            return redirect("gestion:login")

        id_cabana = request.POST.get("id_cabana")
        programa = request.POST.get("programa")
        tipo_ocupacion = "Total"
        fecha_ingreso = request.POST.get("fecha_ingreso")
        fecha_salida = request.POST.get("fecha_salida")
        cantidad_personas = request.POST.get("cantidad_personas")
        observaciones = request.POST.get("observaciones", "")
        metodo_pago = obtener_metodo_pago_formulario(request)

        if not (programa or "").strip():
            messages.error(request, "Debes ingresar o seleccionar un programa de hospedaje.")
            return redirect("gestion:cabanas")

        try:
            fecha_ingreso_obj = convertir_fecha_formulario(fecha_ingreso, "fecha de ingreso")
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("gestion:cabanas")

        fecha_salida_obj = None
        if fecha_salida:
            try:
                fecha_salida_obj = convertir_fecha_formulario(fecha_salida, "fecha de salida")
                if fecha_salida_obj <= fecha_ingreso_obj:
                    messages.error(request, "La fecha de salida debe ser posterior a la fecha de ingreso.")
                    return redirect("gestion:cabanas")
            except ValueError as error:
                messages.error(request, str(error))
                return redirect("gestion:cabanas")

        cabana = get_object_or_404(
            Cabanas,
            id_cabana=id_cabana,
            activo=True
        )

        cliente = get_object_or_404(
            Cliente,
            id_cliente=cliente_id,
            activo=True
        )

        try:
            cantidad_personas_int = obtener_entero_positivo(cantidad_personas, "personas", minimo=1)
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("gestion:cabanas")

        if cantidad_personas_int > cabana.capacidad:
            messages.error(
                request,
                f"La cabaña seleccionada permite máximo {cabana.capacidad} persona(s)."
            )
            return redirect("gestion:cabanas")

        tipo_ocupacion_final = obtener_tipo_ocupacion_final(cabana, tipo_ocupacion)
        programa_codigo, programa_guardar, noches, fecha_salida_obj = resolver_programa_y_noches(
            programa, fecha_ingreso_obj, fecha_salida_obj
        )

        precio_programa = calcular_precio_estadia(
            cabana, programa_codigo, tipo_ocupacion_final, noches
        )

        if precio_programa <= 0:
            messages.error(
                request,
                "No se pudo determinar el precio para el programa o las fechas seleccionadas."
            )
            return redirect("gestion:cabanas")

        with transaction.atomic():
            reserva = Reservas.objects.create(
                id_cliente=cliente,
                fecha_ingreso=fecha_ingreso_obj,
                fecha_salida=fecha_salida_obj,
                estado_reserva="Pendiente",
                estado_pago="Pendiente",
                metodo_pago=metodo_pago,
                total=precio_programa,
                subtotal=precio_programa,
                observaciones=observaciones,
            )

            DetalleCabanas.objects.create(
                id_reserva=reserva,
                id_cabana=cabana,
                cantidad_noches=noches,
                subtotal=precio_programa,
                fecha_entrada=fecha_ingreso_obj,
                fecha_salida=fecha_salida_obj,
                precio_unitario=precio_programa,
                programa=programa_guardar,
                tipo_ocupacion=tipo_ocupacion_final,
                precio_programa=precio_programa,
                cantidad_personas=cantidad_personas_int,
            )

            calcular_valores_reserva(reserva)

        messages.success(
            request,
            "Reserva de cabaña creada correctamente. Ahora puedes completar el pago."
        )
        return redirigir_segun_metodo_pago(reserva, metodo_pago)

    config = ConfiguracionInicio.objects.first()
    contexto = {
        "cabanas": cabanas,
        "usuario": request.session.get("cliente_id"),
        "fondo_cabanas": _config_fondo("fondo_cabanas"),
        "hero_kicker": getattr(config, "cabanas_hero_kicker", None) or "Cabañas",
        "hero_titulo": getattr(config, "cabanas_hero_titulo", None) or "Vive la experiencia de la Amazonía con privacidad",
        "hero_parrafo": getattr(config, "cabanas_hero_parrafo", None) or "Cabañas rodeadas de naturaleza para disfrutar paz, comodidad y una conexión especial con el entorno.",
    }

    return render(request, "public/cabanas.html", contexto)


# ============================================================
# CINE
# ============================================================

def cine_view(request):
    """Muestra funciones de cine y procesa reservas de asientos."""

    cancelar_reservas_vencidas()

    funciones = Cine.objects.filter(activo=True).order_by("fecha_proyeccion", "hora_proyeccion")

    if request.method == "POST":
        cliente_id = request.session.get("cliente_id")

        if not cliente_id:
            messages.warning(request, "Debes iniciar sesión para reservar.")
            return redirect("gestion:login")

        id_funcion = request.POST.get("id_funcion")
        cantidad_asientos = int(request.POST.get("cantidad_asientos") or 1)
        productos_adicionales = request.POST.get("productos_adicionales", "")
        observaciones = request.POST.get("observaciones", "")
        metodo_pago = obtener_metodo_pago_formulario(request)

        funcion = get_object_or_404(Cine, id_funcion=id_funcion)
        cliente = get_object_or_404(Cliente, id_cliente=cliente_id)

        precio_entrada = convertir_decimal(funcion.precio_entrada)
        subtotal = precio_entrada * cantidad_asientos

        reserva = Reservas.objects.create(
            id_cliente=cliente,
            fecha_ingreso=funcion.fecha_proyeccion,
            fecha_salida=funcion.fecha_proyeccion,
            estado_reserva="Pendiente",
            estado_pago="Pendiente",
            metodo_pago=metodo_pago,
            total=subtotal,
            subtotal=subtotal,
            observaciones=observaciones,
        )

        DetalleCine.objects.create(
            id_reserva=reserva,
            id_funcion=funcion,
            cantidad_asientos=cantidad_asientos,
            subtotal=subtotal,
            productos_adicionales=productos_adicionales,
            total_productos=0,
        )

        calcular_valores_reserva(reserva)

        messages.success(
            request,
            "Reserva de cine creada correctamente. Ahora puedes completar el pago."
        )
        return redirigir_segun_metodo_pago(reserva, metodo_pago)

    config = ConfiguracionInicio.objects.first()
    contexto = {
        "funciones": funciones,
        "usuario": request.session.get("cliente_id"),
        "fondo_cine": _config_fondo("fondo_cine"),
        "hero_kicker": getattr(config, "cine_hero_kicker", None) or "Cine Arahuana",
        "hero_titulo": getattr(config, "cine_hero_titulo", None) or "Noches de cine bajo las estrellas",
        "hero_parrafo": getattr(config, "cine_hero_parrafo", None) or "Disfruta de películas en un ambiente acogedor, rodeado de naturaleza, buena compañía y momentos especiales.",
    }

    return render(request, "public/cine.html", contexto)


# ============================================================
# RESORT DEL DÍA
# ============================================================

def resort_dia_view(request):
    """Muestra paquetes de resort por dia y procesa reservas de visita."""

    cancelar_reservas_vencidas()

    areas_resort = ResortDia.objects.filter(activo=True).order_by("nombre")

    if request.method == "POST":
        cliente_id = request.session.get("cliente_id")

        if not cliente_id:
            messages.warning(request, "Debes iniciar sesión para reservar.")
            return redirect("gestion:login")

        id_resort_dia = request.POST.get("id_resort_dia")
        fecha_visita = request.POST.get("fecha_ingreso")
        fecha_visita_obj = convertir_fecha_formulario(fecha_visita, "fecha de ingreso")
        cantidad_personas = int(request.POST.get("cantidad_personas") or 1)
        combo_cabana = request.POST.get("combo_cabana", "")
        observaciones = request.POST.get("observaciones", "")
        metodo_pago = obtener_metodo_pago_formulario(request)

        cabana_id = request.POST.get("id_cabana") or request.POST.get("cabana_id") or request.POST.get("cabana")
        cabana = None

        if cabana_id:
            cabana = Cabanas.objects.filter(numero_cabana=cabana_id).first()
            if cabana is None:
                try:
                    cabana = Cabanas.objects.get(id_cabana=int(cabana_id))
                except (ValueError, Cabanas.DoesNotExist):
                    cabana = None

        combo_cabana = normalizar_combo_cabana(combo_cabana, cabana)

        resort = get_object_or_404(ResortDia, id_resort_dia=id_resort_dia)
        cliente = get_object_or_404(Cliente, id_cliente=cliente_id)

        precio_persona = convertir_decimal(resort.costo_adicional)
        total = precio_persona * cantidad_personas

        reserva = Reservas.objects.create(
            id_cliente=cliente,
            fecha_ingreso=fecha_visita_obj,
            fecha_salida=fecha_visita_obj,
            estado_reserva="Pendiente",
            estado_pago="Pendiente",
            metodo_pago=metodo_pago,
            total=total,
            subtotal=total,
            observaciones=observaciones,
        )

        DetalleResort.objects.create(
            id_reserva=reserva,
            id_resort_dia=resort,
            cantidad_personas=cantidad_personas,
            subtotal=total,
            combo_cabana=combo_cabana,
            punto_atencion=resort.punto_atencion or "Vistro",
        )

        calcular_valores_reserva(reserva)

        messages.success(
            request,
            "Reserva de Resort del Día creada correctamente. Ahora puedes completar el pago."
        )
        return redirigir_segun_metodo_pago(reserva, metodo_pago)

    config = ConfiguracionInicio.objects.first()
    contexto = {
        "areas_resort": areas_resort,
        "paquetes": areas_resort,
        "usuario": request.session.get("cliente_id"),
        "fondo_resort": _config_fondo("fondo_resort"),
        "hero_kicker": getattr(config, "resort_hero_kicker", None) or "Resort del día",
        "hero_titulo": getattr(config, "resort_hero_titulo", None) or "Relájate y disfruta de un día perfecto",
        "hero_parrafo": getattr(config, "resort_hero_parrafo", None) or "Accede a las áreas del resort para vivir bienestar, naturaleza, descanso y diversión en un solo lugar.",
    }

    return render(request, "public/resort_dia.html", contexto)


# ============================================================
# MIS RESERVAS
# ============================================================
