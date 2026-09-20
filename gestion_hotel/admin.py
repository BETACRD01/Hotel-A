"""Configuracion del panel Django Admin para inventario, clientes, reservas, pagos y portada."""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.html import format_html
from .forms import ClienteAdminForm
from .models import (
    Cliente,
    Habitaciones,
    Cabanas,
    Cine,
    ResortDia,
    Reservas,
    DetalleHabitaciones,
    DetalleCabanas,
    DetalleCine,
    DetalleResort,
    PagoReserva,
    ConfiguracionInicio,
)

User = get_user_model()


# ============================================================
# PROTECCION: Los gerentes NUNCA deben ser superusuarios
# ============================================================


class SafeUserAdmin(UserAdmin):
    """UserAdmin que impide marcar is_superuser en usuarios gerente."""

    def save_model(self, request, obj, form, change):
        from gestion_hotel.models import Cliente
        tiene_gerente = Cliente.objects.filter(
            correo_electronico__iexact=obj.email,
            rol='gerente',
            activo=True,
        ).exists()
        if tiene_gerente:
            obj.is_superuser = False
        super().save_model(request, obj, form, change)


admin.site.unregister(User)
admin.site.register(User, SafeUserAdmin)


# ============================================================
# PANEL DE USUARIOS DEL ADMINISTRADOR
# ============================================================


class RoleBasedAdminMixin:
    """Centraliza permisos para que superusuarios conserven acceso total en el admin."""

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return super().has_delete_permission(request, obj)



class EstadoHabitacionFilter(admin.SimpleListFilter):
    """Filtro reutilizable para revisar inventario por estado operativo."""

    title = 'Estado'
    parameter_name = 'estado'

    def lookups(self, request, model_admin):
        return (
            ('Disponible', 'Disponible'),
            ('Reservada', 'Reservada'),
            ('Ocupada', 'Ocupada'),
            ('Mantenimiento', 'Mantenimiento'),
            ('Inactiva', 'Inactiva'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(estado=self.value())
        return queryset


class DetalleCabanasInlineInventory(admin.TabularInline):
    model = DetalleCabanas
    fk_name = 'id_cabana'
    extra = 0
    verbose_name = "Detalle de cabaña"
    verbose_name_plural = "Detalles de cabañas"


class DetalleHabitacionesInlineInventory(admin.TabularInline):
    model = DetalleHabitaciones
    fk_name = 'id_habitacion'
    extra = 0
    verbose_name = "Detalle de habitación"
    verbose_name_plural = "Detalles de habitaciones"


class DetalleCineInlineInventory(admin.TabularInline):
    model = DetalleCine
    fk_name = 'id_funcion'
    extra = 0
    verbose_name = "Detalle de función"
    verbose_name_plural = "Detalles de funciones"


class DetalleResortInlineInventory(admin.TabularInline):
    model = DetalleResort
    fk_name = 'id_resort_dia'
    extra = 0
    verbose_name = "Detalle de resort"
    verbose_name_plural = "Detalles de resort"


class DetalleCabanasInlineReserva(admin.TabularInline):
    model = DetalleCabanas
    fk_name = 'id_reserva'
    extra = 0


class DetalleHabitacionesInlineReserva(admin.TabularInline):
    model = DetalleHabitaciones
    fk_name = 'id_reserva'
    extra = 0


class DetalleCineInlineReserva(admin.TabularInline):
    model = DetalleCine
    fk_name = 'id_reserva'
    extra = 0


class DetalleResortInlineReserva(admin.TabularInline):
    model = DetalleResort
    fk_name = 'id_reserva'
    extra = 0


# Remove custom admin site permission override to rely on Django's normal
# admin authentication and permission system for staff users.


@admin.register(Cabanas)
class CabanasAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """Admin de cabanas con acciones de disponibilidad y tarifas por programa."""

    inlines = [DetalleCabanasInlineInventory]

    list_display = (
        'id_cabana',
        'numero_cabana',
        'tipo_cabana',
        'capacidad',
        'precio_desde_hospedaje',
        'estado',
        'activo',
        'imagen_preview',
    )

    list_filter = (
        'estado',
        'tipo_cabana',
        'activo',
    )

    search_fields = (
        'numero_cabana',
        'tipo_cabana',
    )

    ordering = (
        'numero_cabana',
    )

    readonly_fields = (
        'imagen_preview',
    )

    fieldsets = (
        ('Datos principales de la cabaña', {
            'fields': (
                'numero_cabana',
                'tipo_cabana',
                'capacidad',
                'estado',
                'activo',

                'tipo_ocupacion_secundaria',
                'precio_2d1n_total',
                'precio_2d1n_secundaria',
                'precio_3d2n_total',
                'precio_3d2n_secundaria',
                'precio_4d3n_total',
                'precio_4d3n_secundaria',

                'precio_noche',
                'descripcion',
                'servicios_incluidos',
                'imagen',
                'imagen_preview',
            )
        }),
    )

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="max-width: 120px; max-height: 120px; object-fit: cover; border-radius: 8px;" />',
                obj.imagen.url,
            )
        return 'Sin imagen'

    imagen_preview.short_description = 'Vista previa'


class ClienteFormAdmin(ClienteAdminForm):
    """Adaptador del formulario de clientes para usarlo dentro de Django Admin."""

    class Meta(ClienteAdminForm.Meta):
        model = Cliente
        fields = '__all__'


    class Media:
        js = ('js/password_eye.js',)


@admin.register(Cliente)
class ClienteAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """Admin de clientes, limitado a cuentas de rol cliente dentro de esta app."""

    form = ClienteFormAdmin
    list_display = (
        'numero_documento',
        'tipo_documento_badge',
        'nombres',
        'apellidos',
        'telefono_celular',
        'correo_electronico',
        'activo',
    )
    list_filter = ('activo', 'fecha_registro')
    search_fields = ('numero_documento', 'nombres', 'apellidos', 'correo_electronico', 'telefono_celular')
    ordering = ('id_cliente',)
    readonly_fields = ('fecha_registro', 'ultimo_acceso')
    fieldsets = (
        ('Datos personales', {
            'fields': (
                'tipo_documento',
                'numero_documento',
                'nombres',
                'apellidos',
                'telefono_celular',
                'correo_electronico',
                'direccion',
                'pais_origen',
                'ciudad',
                'activo',
            )
        }),
        ('Acceso', {
            'fields': ('rol', 'password')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'ultimo_acceso')
        }),
    )
 
    def tipo_documento_badge(self, obj):
        tipo = (obj.tipo_documento or "").strip().lower()
        tipo = tipo.replace("é", "e")

        if tipo == "cedula":
            return format_html(
                '<span style="background:#d1fae5; color:#047857; padding:4px 10px; border-radius:999px; font-weight:700;">{}</span>',
                "Cédula"
            )

        if tipo == "ruc":
            return format_html(
                '<span style="background:#e5e7eb; color:#374151; padding:4px 10px; border-radius:999px; font-weight:700;">{}</span>',
                "RUC"
            )

        if tipo == "pasaporte":
            return format_html(
                '<span style="background:#ffedd5; color:#c2410c; padding:4px 10px; border-radius:999px; font-weight:700;">{}</span>',
                "Pasaporte ✈"
            )

        return obj.tipo_documento or "Sin tipo"

    tipo_documento_badge.short_description = "Tipo Doc."

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        # In gestion_hotel admin, role is managed elsewhere; keep it readonly for all
        readonly_fields.append('rol')
        return readonly_fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(rol='cliente')

    def save_model(self, request, obj, form, change):
        # Gestion_Hotel -> Cliente must only contain clientes.
        if obj.rol != 'cliente':
            raise PermissionDenied(
                'Los administradores y gerentes deben crearse en Autenticación y autorización, no en Clientes.'
            )

        obj.rol = 'cliente'

        # Ensure password is hashed before saving
        password = getattr(obj, 'password', None)
        if password:
            try:
                from django.contrib.auth.hashers import identify_hasher

                identify_hasher(password)
                password_is_hashed = True
            except Exception:
                password_is_hashed = False

            if not password_is_hashed:
                obj.password = make_password(password)

        super().save_model(request, obj, form, change)


@admin.register(Habitaciones)
class HabitacionesAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """Admin de habitaciones con inventario, ocupacion y precios visibles."""

    inlines = [DetalleHabitacionesInlineInventory]

    list_display = (
        'id_habitacion',
        'numero_habitacion',
        'tipo_habitacion',
        'capacidad',
        'precio_desde_hospedaje',
        'estado',
        'activo',
        'imagen_preview',
    )

    list_filter = (
        'estado',
        'tipo_habitacion',
        'activo',
    )

    search_fields = (
        'numero_habitacion',
        'tipo_habitacion',
    )

    ordering = (
        'numero_habitacion',
    )

    readonly_fields = (
        'imagen_preview',
    )

    fieldsets = (
        ('Datos principales de la habitación', {
            'fields': (
                'numero_habitacion',
                'tipo_habitacion',
                'capacidad',
                'estado',
                'activo',

                'tipo_ocupacion_secundaria',
                'precio_2d1n_total',
                'precio_2d1n_secundaria',
                'precio_3d2n_total',
                'precio_3d2n_secundaria',
                'precio_4d3n_total',
                'precio_4d3n_secundaria',

                'precio_noche',
                'descripcion',
                'imagen',
                'imagen_preview',
            )
        }),
    )

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="max-width: 120px; max-height: 120px; object-fit: cover; border-radius: 8px;" />',
                obj.imagen.url,
            )
        return 'Sin imagen'

    imagen_preview.short_description = 'Vista previa'


@admin.register(Cine)
class CineAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """Admin de funciones de cine disponibles para reserva."""

    inlines = [DetalleCineInlineInventory]
    list_display = ('id_funcion', 'titulo_pelicula', 'fecha_proyeccion', 'hora_proyeccion', 'precio_entrada', 'capacidad_sala', 'estado', 'activo', 'imagen_preview')
    list_filter = ('estado', 'activo', 'fecha_proyeccion')
    search_fields = ('titulo_pelicula',)
    ordering = ('fecha_proyeccion', 'hora_proyeccion')
    readonly_fields = ('imagen_preview',)
    fieldsets = (
        (None, {
            'fields': ('titulo_pelicula', 'fecha_proyeccion', 'hora_proyeccion', 'duracion_minutos', 'capacidad_sala', 'precio_entrada', 'estado', 'activo')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'imagen', 'imagen_preview')
        }),
    )

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="max-width: 120px; max-height: 120px; object-fit: cover; border-radius: 8px;" />', obj.imagen.url)
        return 'Sin imagen'

    imagen_preview.short_description = 'Vista previa'


@admin.register(ResortDia)
class ResortDiaAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """Admin de paquetes de resort por dia."""

    inlines = [DetalleResortInlineInventory]
    list_display = ('id_resort_dia', 'nombre', 'tipo_area', 'estado', 'capacidad_maxima', 'requiere_reserva', 'costo_adicional', 'activo', 'imagen_preview')
    list_filter = ('tipo_area', 'estado', 'activo', 'requiere_reserva')
    search_fields = ('nombre', 'descripcion')
    ordering = ('id_resort_dia',)
    readonly_fields = ('imagen_preview',)
    fieldsets = (
        (None, {
            'fields': ('nombre', 'tipo_area', 'descripcion', 'capacidad_maxima', 'requiere_reserva', 'costo_adicional', 'estado', 'horario_apertura', 'horario_cierre', 'activo')
        }),
        ('Detalles', {
            'fields': ('imagen', 'imagen_preview')
        }),
    )

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="max-width: 120px; max-height: 120px; object-fit: cover; border-radius: 8px;" />', obj.imagen.url)
        return 'Sin imagen'

    imagen_preview.short_description = 'Vista previa'


@admin.register(DetalleHabitaciones)
class DetalleHabitacionesAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ('id_detalle_hab', 'id_reserva', 'id_habitacion', 'fecha_entrada', 'fecha_salida', 'cantidad_noches', 'precio_unitario', 'subtotal')
    list_filter = ('fecha_entrada', 'fecha_salida', 'id_habitacion__tipo_habitacion')
    search_fields = ('id_reserva__codigo_reserva', 'id_habitacion__numero_habitacion', 'id_habitacion__tipo_habitacion')
    ordering = ('-id_detalle_hab',)
    autocomplete_fields = ('id_reserva', 'id_habitacion')
    fieldsets = (
        (None, {
            'fields': ('id_reserva', 'id_habitacion', 'fecha_entrada', 'fecha_salida')
        }),
        ('Detalle económico', {
            'fields': ('cantidad_noches', 'precio_unitario', 'subtotal')
        }),
    )


@admin.register(DetalleCabanas)
class DetalleCabanasAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ('id_detalle_cab', 'id_reserva', 'id_cabana', 'fecha_entrada', 'fecha_salida', 'cantidad_noches', 'precio_unitario', 'subtotal')
    list_filter = ('fecha_entrada', 'fecha_salida', 'id_cabana__tipo_cabana')
    search_fields = ('id_reserva__codigo_reserva', 'id_cabana__numero_cabana')
    ordering = ('-id_detalle_cab',)
    autocomplete_fields = ('id_reserva', 'id_cabana')
    fieldsets = (
        (None, {
            'fields': ('id_reserva', 'id_cabana', 'fecha_entrada', 'fecha_salida')
        }),
        ('Detalle económico', {
            'fields': ('cantidad_noches', 'precio_unitario', 'subtotal')
        }),
    )


@admin.register(DetalleCine)
class DetalleCineAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ('id_detalle_cine', 'id_reserva', 'id_funcion', 'fecha_uso', 'cantidad_asientos', 'precio_unitario', 'subtotal')
    list_filter = ('fecha_uso', 'id_funcion__estado')
    search_fields = ('id_reserva__codigo_reserva', 'id_funcion__titulo_pelicula')
    ordering = ('-id_detalle_cine',)
    autocomplete_fields = ('id_reserva', 'id_funcion')
    fieldsets = (
        (None, {
            'fields': ('id_reserva', 'id_funcion', 'fecha_uso')
        }),
        ('Detalle económico', {
            'fields': ('cantidad_asientos', 'precio_unitario', 'subtotal')
        }),
    )


@admin.register(DetalleResort)
class DetalleResortAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ('id_detalle_resort', 'id_reserva', 'id_resort_dia', 'fecha_uso', 'cantidad_personas', 'precio_unitario', 'subtotal')
    list_filter = ('fecha_uso', 'id_resort_dia__activo')
    search_fields = ('id_reserva__codigo_reserva', 'id_resort_dia__nombre')
    ordering = ('-id_detalle_resort',)
    autocomplete_fields = ('id_reserva', 'id_resort_dia')
    fieldsets = (
        (None, {
            'fields': ('id_reserva', 'id_resort_dia', 'fecha_uso')
        }),
        ('Detalle económico', {
            'fields': ('cantidad_personas', 'precio_unitario', 'subtotal')
        }),
    )


@admin.register(Reservas)
class ReservasAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """Admin de reservas con sus detalles y estados de pago/reserva."""

    inlines = [
        DetalleHabitacionesInlineReserva,
        DetalleCabanasInlineReserva,
        DetalleCineInlineReserva,
        DetalleResortInlineReserva,
    ]
    list_display = ('id_reserva', 'codigo_reserva', 'id_cliente', 'fecha_registro', 'fecha_ingreso', 'fecha_salida', 'estado_reserva', 'estado_pago', 'metodo_pago', 'total')
    list_filter = ('estado_reserva', 'estado_pago', 'metodo_pago', 'fecha_registro', 'fecha_ingreso')
    search_fields = ('codigo_reserva', 'id_cliente__nombres', 'id_cliente__apellidos', 'id_cliente__correo_electronico', 'id_cliente__numero_documento')
    ordering = ('-fecha_registro',)
    readonly_fields = ('fecha_registro',)
    autocomplete_fields = ('id_cliente',)
    fieldsets = (
        (None, {
            'fields': ('id_cliente', 'codigo_reserva', 'fecha_ingreso', 'fecha_salida', 'estado_reserva', 'estado_pago', 'metodo_pago', 'total')
        }),
        ('Pagos', {
            'fields': ('subtotal', 'porcentaje_anticipo', 'anticipo_minimo', 'saldo_pendiente', 'fecha_limite_pago')
        }),
        ('Observaciones', {
            'fields': ('observaciones', 'fecha_cancelacion', 'motivo_cancelacion')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro',)
        }),
    )


@admin.action(description="Aprobar pagos seleccionados")
def aprobar_pagos(modeladmin, request, queryset):
    """Accion masiva que marca pagos en revision como aprobados y sincroniza la reserva."""

    for pago in queryset:
        pago.estado = "Pagado"
        pago.save()

        reserva = pago.reserva
        reserva.metodo_pago = pago.metodo_pago
        reserva.estado_pago = "Pagado"

        if reserva.estado_reserva == "Pendiente":
            reserva.estado_reserva = "Confirmada"

        reserva.save()


@admin.action(description="Rechazar pagos seleccionados")
def rechazar_pagos(modeladmin, request, queryset):
    """Accion masiva que rechaza pagos seleccionados sin eliminar el historial."""

    for pago in queryset:
        pago.estado = "Rechazado"
        pago.save()

        reserva = pago.reserva
        reserva.estado_pago = "Pendiente"
        reserva.save()


@admin.register(PagoReserva)
class PagoReservaAdmin(admin.ModelAdmin):
    """Admin de comprobantes, revisiones y trazabilidad de pagos de reservas."""

    list_display = (
        "reserva",
        "metodo_pago",
        "estado",
        "monto_total",
        "monto_anticipo",
        "saldo_pendiente",
        "ver_comprobante",
        "numero_comprobante",
        "fecha_creacion",
    )

    list_filter = (
        "metodo_pago",
        "estado",
        "fecha_creacion",
    )

    search_fields = (
        "reserva__codigo_reserva",
        "numero_comprobante",
        "banco_origen",
        "numero_cuenta_origen",
        "authorization_code",
    )

    readonly_fields = (
        "fecha_creacion",
        "fecha_actualizacion",
        "respuesta_payphone",
        "ver_comprobante",
    )

    fieldsets = (
        ("Información de la reserva", {
            "fields": (
                "reserva",
                "metodo_pago",
                "estado",
            )
        }),

        ("Valores del pago", {
            "fields": (
                "monto_total",
                "monto_anticipo",
                "saldo_pendiente",
            )
        }),

        ("Comprobante del cliente", {
            "fields": (
                "banco_origen",
                "numero_cuenta_origen",
                "numero_comprobante",
                "comprobante",
                "ver_comprobante",
                "observacion",
            )
        }),

        ("Fechas", {
            "fields": (
                "fecha_creacion",
                "fecha_actualizacion",
            )
        }),
    )

    actions = (
        aprobar_pagos,
        rechazar_pagos,
    )

    def ver_comprobante(self, obj):
        if obj.comprobante:
            return format_html(
                '<a href="{}" target="_blank" style="font-weight:700; color:#0b4b36;">Ver comprobante</a>',
                obj.comprobante.url
            )
        return "Sin comprobante"

    ver_comprobante.short_description = "Comprobante"


@admin.register(ConfiguracionInicio)
class ConfiguracionInicioAdmin(admin.ModelAdmin):
    """Admin del contenido editable usado por las paginas publicas."""

    list_display = ('id',)
    readonly_fields = (
        'imagen_sobre_nosotros_preview',
        'imagen_habitaciones_preview',
        'imagen_cabanas_preview',
        'imagen_cine_preview',
        'imagen_resort_preview',
        'imagen_hero_preview',
        'fondo_habitaciones_preview',
        'fondo_cabanas_preview',
        'fondo_cine_preview',
        'fondo_resort_preview',
        'sn_historia_imagen_preview',
        'sn_compromiso_imagen_preview',
    )
    fieldsets = (
        ("Sobre nosotros", {
            "fields": (
                "imagen_sobre_nosotros",
                "imagen_sobre_nosotros_preview",
                "sn_hero_titulo",
                "sn_hero_parrafo",
            ),
        }),
        ("Estadísticas", {
            "fields": (
                "sn_stat_1_numero",
                "sn_stat_1_etiqueta",
                "sn_stat_2_numero",
                "sn_stat_2_etiqueta",
                "sn_stat_3_numero",
                "sn_stat_3_etiqueta",
                "sn_stat_4_numero",
                "sn_stat_4_etiqueta",
            ),
        }),
        ("Historia", {
            "fields": (
                "sn_historia_titulo",
                "sn_historia_parrafo_1",
                "sn_historia_parrafo_2",
                "sn_historia_imagen",
                "sn_historia_imagen_preview",
            ),
        }),
        ("Misión y Visión", {
            "fields": (
                "mision",
                "vision",
            ),
        }),
        ("Valores", {
            "fields": (
                "sn_valor_1_titulo",
                "sn_valor_1_texto",
                "sn_valor_2_titulo",
                "sn_valor_2_texto",
                "sn_valor_3_titulo",
                "sn_valor_3_texto",
                "sn_valor_4_titulo",
                "sn_valor_4_texto",
            ),
        }),
        ("Compromiso", {
            "fields": (
                "sn_compromiso_titulo",
                "sn_compromiso_parrafo",
                "sn_compromiso_imagen",
                "sn_compromiso_imagen_preview",
            ),
        }),
        ("Llamada a la acción final", {
            "fields": (
                "sn_cta_titulo",
                "sn_cta_parrafo",
            ),
        }),
        ("Imágenes de las tarjetas del inicio", {
            "fields": (
                "imagen_habitaciones",
                "imagen_habitaciones_preview",
                "imagen_cabanas",
                "imagen_cabanas_preview",
                "imagen_cine",
                "imagen_cine_preview",
                "imagen_resort",
                "imagen_resort_preview",
            ),
        }),
        ("Fondos de las páginas", {
            "fields": (
                "imagen_hero",
                "imagen_hero_preview",
                "fondo_habitaciones",
                "fondo_habitaciones_preview",
                "fondo_cabanas",
                "fondo_cabanas_preview",
                "fondo_cine",
                "fondo_cine_preview",
                "fondo_resort",
                "fondo_resort_preview",
            ),
        }),
    )

    IMAGENES_ORDEN = (
        ('imagen_habitaciones', 'Habitaciones'),
        ('imagen_cabanas', 'Cabañas'),
        ('imagen_cine', 'Cine'),
        ('imagen_resort', 'Resort del Día'),
    )

    def get_list_display(self, request):
        columnas = ['id']
        config = ConfiguracionInicio.objects.first()
        for campo, _etiqueta in self.IMAGENES_ORDEN:
            if config and getattr(config, campo, None):
                columnas.append(f'{campo}_preview')
        return tuple(columnas)

    def _preview(self, obj, campo):
        imagen = getattr(obj, campo, None)
        if imagen:
            return format_html(
                '<img src="{}" style="max-width: 140px; max-height: 100px; object-fit: cover; border-radius: 8px;" />',
                imagen.url
            )
        return 'Sin imagen'

    def imagen_sobre_nosotros_preview(self, obj):
        return self._preview(obj, 'imagen_sobre_nosotros')

    def imagen_habitaciones_preview(self, obj):
        return self._preview(obj, 'imagen_habitaciones')

    def imagen_cabanas_preview(self, obj):
        return self._preview(obj, 'imagen_cabanas')

    def imagen_cine_preview(self, obj):
        return self._preview(obj, 'imagen_cine')

    def imagen_resort_preview(self, obj):
        return self._preview(obj, 'imagen_resort')

    def imagen_hero_preview(self, obj):
        return self._preview(obj, 'imagen_hero')

    def fondo_habitaciones_preview(self, obj):
        return self._preview(obj, 'fondo_habitaciones')

    def fondo_cabanas_preview(self, obj):
        return self._preview(obj, 'fondo_cabanas')

    def fondo_cine_preview(self, obj):
        return self._preview(obj, 'fondo_cine')

    def fondo_resort_preview(self, obj):
        return self._preview(obj, 'fondo_resort')

    def sn_historia_imagen_preview(self, obj):
        return self._preview(obj, 'sn_historia_imagen')

    def sn_compromiso_imagen_preview(self, obj):
        return self._preview(obj, 'sn_compromiso_imagen')

    imagen_sobre_nosotros_preview.short_description = 'Sobre nosotros'
    imagen_habitaciones_preview.short_description = 'Habitaciones'
    imagen_cabanas_preview.short_description = 'Cabañas'
    imagen_cine_preview.short_description = 'Cine'
    imagen_resort_preview.short_description = 'Resort'
    imagen_hero_preview.short_description = 'Inicio'
    fondo_habitaciones_preview.short_description = 'Fondo Hab.'
    fondo_cabanas_preview.short_description = 'Fondo Cab.'
    fondo_cine_preview.short_description = 'Fondo Cine'
    fondo_resort_preview.short_description = 'Fondo Resort'
    sn_historia_imagen_preview.short_description = 'Imagen Historia'
    sn_compromiso_imagen_preview.short_description = 'Imagen Compromiso'
