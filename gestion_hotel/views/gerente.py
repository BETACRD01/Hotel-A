from .common import *

def requiere_gerente(request):
    usuario = obtener_usuario_sesion(request)
    if usuario is not None:
        if usuario.rol != 'gerente':
            messages.error(request, "No tienes permisos de gerente para acceder a esta sección.")
            return None
        return usuario

    auth_user = getattr(request, "user", None)
    if auth_user and auth_user.is_authenticated and auth_user.is_active and (auth_user.is_staff or auth_user.is_superuser):
        return SimpleNamespace(
            nombres=(auth_user.first_name or auth_user.username or "Gerente").strip(),
            apellidos=(auth_user.last_name or "").strip(),
            rol="gerente",
            admin_auth=True,
        )

    messages.error(request, "Debes iniciar sesión para acceder al panel gerencial.")
    return None


class GerenteStyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "gerente-checkbox"})
            else:
                field.widget.attrs.update({"class": "gerente-input"})

            if isinstance(field.widget, forms.DateInput):
                field.widget.input_type = "date"
            elif isinstance(field.widget, forms.TimeInput):
                field.widget.input_type = "time"


class GerenteClienteForm(GerenteStyledForm):
    password = forms.CharField(
        label="Contrasena",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="En edicion puedes dejarla vacia para conservar la contrasena actual.",
    )

    class Meta:
        model = Cliente
        fields = [
            "tipo_documento",
            "numero_documento",
            "nombres",
            "apellidos",
            "telefono_celular",
            "pais_origen",
            "ciudad",
            "correo_electronico",
            "password",
            "activo",
            "direccion",
        ]

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not self.instance.pk and not password:
            raise ValidationError("La contrasena es obligatoria para clientes nuevos.")
        return password

    def save(self, commit=True):
        cliente = super().save(commit=False)
        password = self.cleaned_data.get("password")
        cliente.rol = "cliente"
        if password:
            cliente.password = make_password(password)
        elif self.instance.pk:
            cliente.password = Cliente.objects.only("password").get(pk=self.instance.pk).password
        if commit:
            cliente.save()
        return cliente


GERENTE_FORM_CONFIG = {
    "habitaciones": {
        "model": Habitaciones,
        "fields": [
            "numero_habitacion",
            "tipo_habitacion",
            "precio_noche",
            "tipo_ocupacion_secundaria",
            "precio_2d1n_total",
            "precio_2d1n_secundaria",
            "precio_3d2n_total",
            "precio_3d2n_secundaria",
            "precio_4d3n_total",
            "precio_4d3n_secundaria",
            "estado",
            "capacidad",
            "descripcion",
            "imagen",
            "activo",
        ],
        "list_url": "gestion:gerente_habitaciones",
        "label": "Habitacion",
    },
    "cabanas": {
        "model": Cabanas,
        "fields": [
            "numero_cabana",
            "tipo_cabana",
            "capacidad",
            "precio_noche",
            "tipo_ocupacion_secundaria",
            "precio_2d1n_total",
            "precio_2d1n_secundaria",
            "precio_3d2n_total",
            "precio_3d2n_secundaria",
            "precio_4d3n_total",
            "precio_4d3n_secundaria",
            "estado",
            "descripcion",
            "servicios_incluidos",
            "imagen",
            "activo",
        ],
        "list_url": "gestion:gerente_cabanas",
        "label": "Cabana",
    },
    "clientes": {
        "form_class": GerenteClienteForm,
        "model": Cliente,
        "list_url": "gestion:gerente_clientes",
        "label": "Cliente",
    },
    "reservas": {
        "model": Reservas,
        "fields": [
            "id_cliente",
            "fecha_ingreso",
            "fecha_salida",
            "estado_reserva",
            "total",
            "observaciones",
            "estado_pago",
            "metodo_pago",
            "fecha_cancelacion",
            "motivo_cancelacion",
            "porcentaje_anticipo",
        ],
        "list_url": "gestion:gerente_reservas",
        "label": "Reserva",
    },
    "resort": {
        "model": ResortDia,
        "fields": [
            "nombre",
            "tipo_area",
            "descripcion",
            "capacidad_maxima",
            "requiere_reserva",
            "costo_adicional",
            "estado",
            "horario_apertura",
            "horario_cierre",
            "imagen",
            "activo",
        ],
        "list_url": "gestion:gerente_resort",
        "label": "Resort del Dia",
    },
    "cine": {
        "model": Cine,
        "fields": [
            "titulo_pelicula",
            "fecha_proyeccion",
            "hora_proyeccion",
            "precio_entrada",
            "descripcion",
            "duracion_minutos",
            "capacidad_sala",
            "imagen",
            "estado",
            "activo",
            "dia_funcion",
            "productos_adicionales",
            "observacion",
        ],
        "list_url": "gestion:gerente_cine",
        "label": "Funcion de Cine",
    },
}


def gerente_form_modelo_view(request, modulo, pk=None):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    config = GERENTE_FORM_CONFIG.get(modulo)
    if not config:
        messages.error(request, "Modulo gerencial no encontrado.")
        return redirect("gestion:gerente_dashboard")

    model = config["model"]
    obj = get_object_or_404(model, pk=pk) if pk else None
    form_class = config.get("form_class") or modelform_factory(
        model,
        form=GerenteStyledForm,
        fields=config["fields"],
    )

    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            accion = "actualizado" if obj else "creado"
            messages.success(request, f"{config['label']} {accion} correctamente.")
            return redirect(config["list_url"])
    else:
        form = form_class(instance=obj)

    contexto = {
        "usuario": usuario,
        "form": form,
        "obj": obj,
        "modulo": modulo,
        "titulo": f"{'Editar' if obj else 'Nuevo'} {config['label']}",
        "list_url": config["list_url"],
    }
    return render(request, "gerente/formulario.html", contexto)


def _mes_actual():
    return timezone.now().date().replace(day=1)


def _primer_dia_mes(anio, mes):
    from datetime import date
    return date(anio, mes, 1)


def _ultimo_dia_mes(anio, mes):
    import calendar
    from datetime import date
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, ultimo)


def dashboard_gerente_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    hoy = timezone.now().date()
    primer_dia_mes = _mes_actual()
    ultimo_dia_mes = _ultimo_dia_mes(hoy.year, hoy.month)
    if hoy.month == 1:
        anio_mes_anterior = hoy.year - 1
        mes_anterior = 12
    else:
        anio_mes_anterior = hoy.year
        mes_anterior = hoy.month - 1

    total_reservas_mes = Reservas.objects.filter(
        fecha_registro__date__gte=primer_dia_mes,
        fecha_registro__date__lte=ultimo_dia_mes,
    ).count()

    reservas_pendientes = Reservas.objects.filter(
        estado_reserva='Pendiente'
    ).count()

    ingresos_mes = Reservas.objects.filter(
        estado_pago='Pagado',
        fecha_registro__date__gte=primer_dia_mes,
        fecha_registro__date__lte=ultimo_dia_mes,
    ).aggregate(total=Sum('total'))['total'] or 0

    pagos_revision = Reservas.objects.filter(
        estado_pago='En revision',
        fecha_registro__date__gte=primer_dia_mes,
        fecha_registro__date__lte=ultimo_dia_mes,
    ).count()

    monto_revision = Reservas.objects.filter(
        estado_pago='En revision',
        fecha_registro__date__gte=primer_dia_mes,
        fecha_registro__date__lte=ultimo_dia_mes,
    ).aggregate(total=Sum('total'))['total'] or 0

    total_habitaciones = Habitaciones.objects.filter(activo=True).count()
    habitaciones_ocupadas = Habitaciones.objects.filter(estado='Ocupada').count()
    total_cabanas = Cabanas.objects.filter(activo=True).count()
    cabanas_ocupadas = Cabanas.objects.filter(estado='Ocupada').count()

    capacidad_total = total_habitaciones + total_cabanas
    ocupadas = habitaciones_ocupadas + cabanas_ocupadas
    porcentaje_ocupacion = round((ocupadas / capacidad_total * 100), 1) if capacidad_total > 0 else 0

    total_clientes = Cliente.objects.filter(rol='cliente', activo=True).count()

    total_reservas = Reservas.objects.count()

    ultimas_reservas = Reservas.objects.select_related('id_cliente').order_by('-fecha_registro')[:10]

    reservas_por_estado = []
    for estado in ['Pendiente', 'Confirmada', 'En curso', 'Finalizada', 'Cancelada']:
        count = Reservas.objects.filter(estado_reserva=estado).count()
        reservas_por_estado.append({'estado': estado, 'count': count})

    habitaciones_info = Habitaciones.objects.filter(activo=True).values(
        'numero_habitacion', 'tipo_habitacion', 'estado', 'precio_noche'
    )[:10]

    cabanas_info = Cabanas.objects.filter(activo=True).values(
        'numero_cabana', 'tipo_cabana', 'estado', 'precio_noche'
    )[:10]

    comentarios_mes = PagoReserva.objects.exclude(
        observacion__isnull=True
    ).exclude(
        observacion=''
    ).filter(
        fecha_creacion__date__gte=primer_dia_mes,
        fecha_creacion__date__lte=ultimo_dia_mes,
    )
    total_comentarios_mes = comentarios_mes.count()
    feedback_top = comentarios_mes.order_by('-fecha_creacion').values_list('observacion', flat=True).first()

    detalle_habitacion_top = DetalleHabitaciones.objects.filter(
        id_reserva__fecha_registro__date__gte=primer_dia_mes,
        id_reserva__fecha_registro__date__lte=ultimo_dia_mes,
    ).values(
        'id_habitacion__numero_habitacion',
        'id_habitacion__tipo_habitacion',
    ).annotate(
        reservas=Count('id_detalle_hab'),
        ingresos=Sum('subtotal'),
    ).order_by('-reservas', '-ingresos').first()

    detalle_cabana_top = DetalleCabanas.objects.filter(
        id_reserva__fecha_registro__date__gte=primer_dia_mes,
        id_reserva__fecha_registro__date__lte=ultimo_dia_mes,
    ).values(
        'id_cabana__numero_cabana',
        'id_cabana__tipo_cabana',
    ).annotate(
        reservas=Count('id_detalle_cab'),
        ingresos=Sum('subtotal'),
    ).order_by('-reservas', '-ingresos').first()

    detalle_cine_top = DetalleCine.objects.filter(
        id_reserva__fecha_registro__date__gte=primer_dia_mes,
        id_reserva__fecha_registro__date__lte=ultimo_dia_mes,
    ).values(
        'id_funcion__titulo_pelicula',
    ).annotate(
        reservas=Count('id_detalle_cine'),
        ingresos=Sum('subtotal'),
        uso=Sum('cantidad_asientos'),
    ).order_by('-reservas', '-ingresos').first()

    detalle_resort_top = DetalleResort.objects.filter(
        id_reserva__fecha_registro__date__gte=primer_dia_mes,
        id_reserva__fecha_registro__date__lte=ultimo_dia_mes,
    ).values(
        'id_resort_dia__nombre',
    ).annotate(
        reservas=Count('id_detalle_resort'),
        ingresos=Sum('subtotal'),
        uso=Sum('cantidad_personas'),
    ).order_by('-reservas', '-ingresos').first()

    rendimiento_categorias = [
        {
            'categoria': 'Habitaciones',
            'nombre': (
                f"{detalle_habitacion_top['id_habitacion__numero_habitacion']} - "
                f"{detalle_habitacion_top['id_habitacion__tipo_habitacion']}"
                if detalle_habitacion_top else 'Sin reservas este mes'
            ),
            'actividad': f"{detalle_habitacion_top['reservas']} reservas" if detalle_habitacion_top else '0 reservas',
            'ingresos': detalle_habitacion_top['ingresos'] if detalle_habitacion_top else 0,
        },
        {
            'categoria': 'Cabanas',
            'nombre': (
                f"{detalle_cabana_top['id_cabana__numero_cabana']} - "
                f"{detalle_cabana_top['id_cabana__tipo_cabana'] or 'Sin tipo'}"
                if detalle_cabana_top else 'Sin reservas este mes'
            ),
            'actividad': f"{detalle_cabana_top['reservas']} reservas" if detalle_cabana_top else '0 reservas',
            'ingresos': detalle_cabana_top['ingresos'] if detalle_cabana_top else 0,
        },
        {
            'categoria': 'Cine',
            'nombre': detalle_cine_top['id_funcion__titulo_pelicula'] if detalle_cine_top else 'Sin reservas este mes',
            'actividad': f"{detalle_cine_top['uso'] or 0} entradas" if detalle_cine_top else '0 entradas',
            'ingresos': detalle_cine_top['ingresos'] if detalle_cine_top else 0,
        },
        {
            'categoria': 'Resort Dia',
            'nombre': detalle_resort_top['id_resort_dia__nombre'] if detalle_resort_top else 'Sin reservas este mes',
            'actividad': f"{detalle_resort_top['uso'] or 0} personas" if detalle_resort_top else '0 personas',
            'ingresos': detalle_resort_top['ingresos'] if detalle_resort_top else 0,
        },
    ]

    mejor_categoria = max(rendimiento_categorias, key=lambda item: item['ingresos'] or 0)
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    meses_largos = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    indicadores_mes = [
        {
            'indicador': 'Mejor categoria del mes',
            'detalle': mejor_categoria['categoria'],
            'conteo': mejor_categoria['actividad'],
            'ingresos': mejor_categoria['ingresos'],
            'tiene_ingresos': True,
        },
        {
            'indicador': 'Reservas registradas',
            'detalle': f"{meses_nombres[hoy.month - 1]} {hoy.year}",
            'conteo': total_reservas_mes,
            'ingresos': ingresos_mes,
            'tiene_ingresos': True,
        },
        {
            'indicador': 'Pagos en revision',
            'detalle': 'Reservas por validar',
            'conteo': pagos_revision,
            'ingresos': monto_revision,
            'tiene_ingresos': True,
        },
        {
            'indicador': 'Observaciones recibidas',
            'detalle': feedback_top or 'Sin observaciones del mes',
            'conteo': total_comentarios_mes,
            'ingresos': None,
            'tiene_ingresos': False,
        },
    ]

    reservas_mes_anterior = Reservas.objects.filter(
        fecha_registro__date__gte=_primer_dia_mes(anio_mes_anterior, mes_anterior),
        fecha_registro__date__lte=_ultimo_dia_mes(anio_mes_anterior, mes_anterior),
    ).count()

    ingresos_mes_anterior = Reservas.objects.filter(
        estado_pago='Pagado',
        fecha_registro__date__gte=_primer_dia_mes(anio_mes_anterior, mes_anterior),
        fecha_registro__date__lte=_ultimo_dia_mes(anio_mes_anterior, mes_anterior),
    ).aggregate(total=Sum('total'))['total'] or 0

    datos_mensuales = []
    for i in range(6):
        mes_num = hoy.month - i
        anio = hoy.year
        if mes_num <= 0:
            mes_num += 12
            anio -= 1
        from datetime import date as date_class
        f_inicio = date_class(anio, mes_num, 1)
        f_fin = _ultimo_dia_mes(anio, mes_num)
        r_count = Reservas.objects.filter(fecha_registro__date__gte=f_inicio, fecha_registro__date__lte=f_fin).count()
        i_total = Reservas.objects.filter(
            estado_pago='Pagado',
            fecha_registro__date__gte=f_inicio,
            fecha_registro__date__lte=f_fin,
        ).aggregate(total=Sum('total'))['total'] or 0
        datos_mensuales.append({
            'mes': meses_nombres[mes_num - 1],
            'reservas': r_count,
            'ingresos': float(i_total),
        })
    datos_mensuales.reverse()

    contexto = {
        "usuario": usuario,
        "total_reservas_mes": total_reservas_mes,
        "reservas_pendientes": reservas_pendientes,
        "ingresos_mes": float(ingresos_mes),
        "porcentaje_ocupacion": porcentaje_ocupacion,
        "total_clientes": total_clientes,
        "total_reservas": total_reservas,
        "total_habitaciones": total_habitaciones,
        "habitaciones_ocupadas": habitaciones_ocupadas,
        "total_cabanas": total_cabanas,
        "cabanas_ocupadas": cabanas_ocupadas,
        "ultimas_reservas": ultimas_reservas,
        "reservas_por_estado": reservas_por_estado,
        "habitaciones_info": habitaciones_info,
        "cabanas_info": cabanas_info,
        "reservas_mes_anterior": reservas_mes_anterior,
        "ingresos_mes_anterior": float(ingresos_mes_anterior),
        "datos_mensuales": datos_mensuales,
        "mes_actual": meses_nombres[hoy.month - 1],
        "mes_actual_largo": meses_largos[hoy.month - 1],
        "anio_actual": hoy.year,
        "pagos_revision": pagos_revision,
        "monto_revision": float(monto_revision),
        "rendimiento_categorias": rendimiento_categorias,
        "indicadores_mes": indicadores_mes,
        "total_comentarios_mes": total_comentarios_mes,
    }

    return render(request, "gerente/dashboard.html", contexto)


def gerente_reservas_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    reservas = Reservas.objects.select_related('id_cliente').order_by('-fecha_registro')

    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        reservas = reservas.filter(estado_reserva=estado_filtro)

    contexto = {
        "usuario": usuario,
        "reservas": reservas,
        "estado_filtro": estado_filtro,
        "estados": ESTADO_RESERVA_CHOICES,
    }
    return render(request, "gerente/reservas.html", contexto)


def gerente_habitaciones_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    habitaciones = Habitaciones.objects.all().order_by('numero_habitacion')

    contexto = {
        "usuario": usuario,
        "habitaciones": habitaciones,
        "estados": ESTADO_HABITACION_CHOICES,
    }
    return render(request, "gerente/habitaciones.html", contexto)


def gerente_cabanas_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    cabanas = Cabanas.objects.all().order_by('numero_cabana')

    contexto = {
        "usuario": usuario,
        "cabanas": cabanas,
        "estados": ESTADO_HABITACION_CHOICES,
    }
    return render(request, "gerente/cabanas.html", contexto)


def gerente_clientes_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    clientes = Cliente.objects.filter(rol='cliente').order_by('-fecha_registro')

    contexto = {
        "usuario": usuario,
        "clientes": clientes,
    }
    return render(request, "gerente/clientes.html", contexto)


def gerente_resort_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    areas = ResortDia.objects.all().order_by('nombre')

    contexto = {
        "usuario": usuario,
        "areas": areas,
    }
    return render(request, "gerente/resort.html", contexto)


def gerente_cine_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    funciones = Cine.objects.annotate(
        reservas_count=Count(
            'detallecine',
            filter=~Q(detallecine__id_reserva__estado_reserva='Cancelada'),
        ),
        asientos_reservados=Sum(
            'detallecine__cantidad_asientos',
            filter=~Q(detallecine__id_reserva__estado_reserva='Cancelada'),
        ),
        ingresos_pagados=Sum(
            'detallecine__subtotal',
            filter=Q(detallecine__id_reserva__estado_pago='Pagado'),
        ),
    ).order_by('fecha_proyeccion', 'hora_proyeccion')

    contexto = {
        "usuario": usuario,
        "funciones": funciones,
        "total_funciones": funciones.count(),
        "funciones_activas": funciones.filter(activo=True, estado='Activa').count(),
    }
    return render(request, "gerente/cine.html", contexto)


def gerente_sobre_nosotros_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    config = ConfiguracionInicio.objects.first()

    contexto = {
        "usuario": usuario,
        "config": config,
    }
    return render(request, "gerente/sobre_nosotros.html", contexto)


def gerente_informes_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    hoy = timezone.now().date()
    primer_dia_mes = _mes_actual()
    ultimo_dia_mes = _ultimo_dia_mes(hoy.year, hoy.month)

    ingresos_totales = Reservas.objects.filter(
        estado_pago='Pagado'
    ).aggregate(total=Sum('total'))['total'] or 0

    ingresos_mes = Reservas.objects.filter(
        estado_pago='Pagado',
        fecha_registro__date__gte=primer_dia_mes,
        fecha_registro__date__lte=ultimo_dia_mes,
    ).aggregate(total=Sum('total'))['total'] or 0

    total_reservas = Reservas.objects.count()
    reservas_canceladas = Reservas.objects.filter(estado_reserva='Cancelada').count()

    contexto = {
        "usuario": usuario,
        "ingresos_totales": float(ingresos_totales),
        "ingresos_mes": float(ingresos_mes),
        "total_reservas": total_reservas,
        "reservas_canceladas": reservas_canceladas,
    }
    return render(request, "gerente/informes.html", contexto)


def gerente_ocupacion_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    total_habitaciones = Habitaciones.objects.filter(activo=True).count()
    habitaciones_ocupadas = Habitaciones.objects.filter(estado='Ocupada').count()
    habitaciones_disponibles = Habitaciones.objects.filter(estado='Disponible').count()
    habitaciones_mantenimiento = Habitaciones.objects.filter(estado='Mantenimiento').count()

    total_cabanas = Cabanas.objects.filter(activo=True).count()
    cabanas_ocupadas = Cabanas.objects.filter(estado='Ocupada').count()
    cabanas_disponibles = Cabanas.objects.filter(estado='Disponible').count()
    cabanas_mantenimiento = Cabanas.objects.filter(estado='Mantenimiento').count()

    contexto = {
        "usuario": usuario,
        "total_habitaciones": total_habitaciones,
        "habitaciones_ocupadas": habitaciones_ocupadas,
        "habitaciones_disponibles": habitaciones_disponibles,
        "habitaciones_mantenimiento": habitaciones_mantenimiento,
        "total_cabanas": total_cabanas,
        "cabanas_ocupadas": cabanas_ocupadas,
        "cabanas_disponibles": cabanas_disponibles,
        "cabanas_mantenimiento": cabanas_mantenimiento,
    }
    return render(request, "gerente/ocupacion.html", contexto)


def gerente_personal_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    admins = Cliente.objects.filter(rol='admin', activo=True)
    gerentes = Cliente.objects.filter(rol='gerente', activo=True)

    contexto = {
        "usuario": usuario,
        "admins": admins,
        "gerentes": gerentes,
    }
    return render(request, "gerente/personal.html", contexto)


def gerente_comentarios_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    pagos_con_observacion = PagoReserva.objects.exclude(
        observacion__isnull=True
    ).exclude(
        observacion=''
    ).select_related('reserva', 'reserva__id_cliente').order_by('-fecha_creacion')[:20]

    contexto = {
        "usuario": usuario,
        "comentarios": pagos_con_observacion,
    }
    return render(request, "gerente/comentarios.html", contexto)


def gerente_tarifas_view(request):
    usuario = requiere_gerente(request)
    if not usuario:
        return redirect("gestion:login")

    habitaciones = Habitaciones.objects.filter(activo=True).order_by('numero_habitacion')
    cabanas = Cabanas.objects.filter(activo=True).order_by('numero_cabana')
    funciones = Cine.objects.filter(activo=True).order_by('fecha_proyeccion', 'hora_proyeccion')

    contexto = {
        "usuario": usuario,
        "habitaciones": habitaciones,
        "cabanas": cabanas,
        "funciones": funciones,
    }
    return render(request, "gerente/tarifas.html", contexto)
