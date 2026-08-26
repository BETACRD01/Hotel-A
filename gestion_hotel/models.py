import re

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from django.utils import timezone

PROGRAMA_HOSPEDAJE_CHOICES = [
    ('2D1N', '2 días / 1 noche'),
    ('3D2N', '3 días / 2 noches'),
    ('4D3N', '4 días / 3 noches'),
]

TIPO_OCUPACION_CHOICES = [
    ('Total', 'Ocupación total'),
    ('Sencilla', 'Ocupación sencilla'),
    ('Doble', 'Ocupación doble'),
]

from .validators import (
    validate_cedula_ruc,
    validate_email_format,
    validate_letters_only,
    validate_password_strength,
    validate_phone,
)

# ==========================================
# 1. GRUPO DE TABLAS MAESTRAS (CATÁLOGOS)
# ==========================================

ROLES_USUARIO = [
    ('cliente', 'Cliente'),
    ('admin', 'Administrador'),
    ('gerente', 'Gerente'),
]


class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    tipo_documento = models.CharField(
        max_length=20,
        choices=[('Cedula', 'Cedula'), ('RUC', 'RUC'), ('Pasaporte', 'Pasaporte')],
        default='Cedula',
        verbose_name='Tipo de documento'
    )
    numero_documento = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_cedula_ruc],
        verbose_name='Número de documento'
    )
    nombres = models.CharField(
        max_length=150,
        validators=[validate_letters_only],
        verbose_name='Nombres'
    )
    apellidos = models.CharField(
        max_length=150,
        validators=[validate_letters_only],
        verbose_name='Apellidos'
    )
    telefono_celular = models.CharField(
        max_length=20,
        validators=[validate_phone],
        verbose_name='Teléfono celular'
    )
    pais_origen = models.CharField(
        max_length=80,
        blank=True,
        default='',
        verbose_name='País de origen'
    )
    ciudad = models.CharField(
        max_length=80,
        blank=True,
        default='',
        verbose_name='Ciudad'
    )
    correo_electronico = models.EmailField(
        unique=True,
        validators=[validate_email_format],
        verbose_name='Correo electrónico'
    )
    password = models.CharField(
        max_length=255,
        validators=[validate_password_strength],
        verbose_name='Contraseña'
    )
    rol = models.CharField(
        max_length=20,
        choices=ROLES_USUARIO,
        default='cliente',
        verbose_name='Rol'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    direccion = models.CharField(max_length=200, blank=True, null=True, verbose_name='Dirección')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')
    ultimo_acceso = models.DateTimeField(blank=True, null=True, verbose_name='Último acceso')

    @property
    def id_usuario(self):
        return self.id_cliente

    @property
    def cedula_ruc(self):
        return self.numero_documento

    @property
    def nombre(self):
        return self.nombres

    @property
    def apellido(self):
        return self.apellidos

    @property
    def telefono(self):
        return self.telefono_celular

    @property
    def email(self):
        return self.correo_electronico

    @property
    def is_active(self):
        return self.activo

    def clean(self):
        super().clean()

        if self.rol != 'cliente':
            raise ValidationError({
                'rol': (
                    'El modelo Cliente solo admite el rol cliente. '
                    'Los administradores y gerentes deben crearse en Autenticación y autorización.'
                )
            })

        if self.password and not self.password.startswith(("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")):
            validate_password_strength(self.password)

    def save(self, *args, **kwargs):
        if not self.direccion:
            partes_direccion = [self.ciudad.strip(), self.pais_origen.strip()]
            self.direccion = ', '.join([parte for parte in partes_direccion if parte]) or ''
        elif self.ciudad or self.pais_origen:
            partes_direccion = [self.ciudad.strip(), self.pais_origen.strip()]
            self.direccion = ', '.join([parte for parte in partes_direccion if parte]) or self.direccion

        self.full_clean(exclude=['password'])
        return super().save(*args, **kwargs)

    def is_cliente(self):
        return self.rol == 'cliente'

    def is_admin(self):
        return self.rol == 'admin'

    def is_gerente(self):
        return self.rol == 'gerente'

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.rol})"

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

ESTADO_HABITACION_CHOICES = [
    ('Disponible', 'Disponible'),
    ('Reservada', 'Reservada'),
    ('Ocupada', 'Ocupada'),
    ('Mantenimiento', 'Mantenimiento'),
    ('Inactiva', 'Inactiva'),
]


class Habitaciones(models.Model):
    id_habitacion = models.AutoField(primary_key=True)
    numero_habitacion = models.CharField(max_length=10, unique=True, verbose_name='Numero de habitacion')
    tipo_habitacion = models.CharField(max_length=50, verbose_name='Tipo de habitacion')
    precio_noche = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)], verbose_name='Precio por noche')
    tipo_ocupacion_secundaria = models.CharField(
        max_length=20,
        choices=[
            ('Sencilla', 'Ocupacion sencilla'),
            ('Doble', 'Ocupacion doble'),
        ],
        default='Sencilla',
        verbose_name='Tipo de ocupacion secundaria'
    )
    precio_2d1n_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='2D/1N - Ocupacion total'
    )
    precio_2d1n_secundaria = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='2D/1N - Ocupacion secundaria'
    )
    precio_3d2n_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='3D/2N - Ocupacion total'
    )
    precio_3d2n_secundaria = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='3D/2N - Ocupación secundaria'
    )
    precio_4d3n_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='4D/3N - Ocupación total'
    )
    precio_4d3n_secundaria = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='4D/3N - Ocupación secundaria'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_HABITACION_CHOICES,
        default='Disponible',
        verbose_name='Estado'
    )
    imagen = models.ImageField(
        upload_to='habitaciones/',
        blank=True,
        null=True,
        help_text='Sube una imagen de la habitación (JPG, PNG, GIF).',
        verbose_name='Imagen'
    )
    capacidad = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Capacidad')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def obtener_precio_programa(self, programa, tipo_ocupacion):
        precios = {
            '2D1N': {
                'Total': self.precio_2d1n_total,
                'Secundaria': self.precio_2d1n_secundaria,
            },
            '3D2N': {
                'Total': self.precio_3d2n_total,
                'Secundaria': self.precio_3d2n_secundaria,
            },
            '4D3N': {
                'Total': self.precio_4d3n_total,
                'Secundaria': self.precio_4d3n_secundaria,
            },
        }

        grupo = precios.get(programa)

        if not grupo:
            return Decimal('0.00')

        if tipo_ocupacion == 'Total':
            return grupo['Total']

        return grupo['Secundaria']

    @property
    def precio_desde_hospedaje(self):
        precios = [
            self.precio_2d1n_total,
            self.precio_2d1n_secundaria,
            self.precio_3d2n_total,
            self.precio_3d2n_secundaria,
            self.precio_4d3n_total,
            self.precio_4d3n_secundaria,
        ]

        precios_validos = [precio for precio in precios if precio and precio > 0]
        return min(precios_validos) if precios_validos else Decimal('0.00')

    def __str__(self):
        return f"Habitación {self.numero_habitacion} - {self.tipo_habitacion}"

    class Meta:
        verbose_name = 'Habitación'
        verbose_name_plural = 'Habitaciones'


class Cabanas(models.Model):
    id_cabana = models.AutoField(primary_key=True)
    numero_cabana = models.CharField(max_length=50, unique=True, verbose_name='Número de cabaña')
    capacidad = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Capacidad')
    precio_noche = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)], verbose_name='Precio por noche')
    tipo_ocupacion_secundaria = models.CharField(
        max_length=20,
        choices=[
            ('Sencilla', 'Ocupacion sencilla'),
            ('Doble', 'Ocupacion doble'),
        ],
        default='Sencilla',
        verbose_name='Tipo de ocupacion secundaria'
    )
    precio_2d1n_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='2D/1N - Ocupacion total'
    )
    precio_2d1n_secundaria = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='2D/1N - Ocupacion secundaria'
    )
    precio_3d2n_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='3D/2N - Ocupacion total'
    )
    precio_3d2n_secundaria = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='3D/2N - Ocupación secundaria'
    )
    precio_4d3n_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='4D/3N - Ocupación total'
    )
    precio_4d3n_secundaria = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='4D/3N - Ocupación secundaria'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_HABITACION_CHOICES,
        default='Disponible',
        verbose_name='Estado'
    )
    tipo_cabana = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipo de cabaña')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    servicios_incluidos = models.TextField(blank=True, null=True, verbose_name='Servicios incluidos')
    imagen = models.ImageField(upload_to='cabanas/', blank=True, null=True, verbose_name='Imagen')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def obtener_precio_programa(self, programa, tipo_ocupacion):
        precios = {
            '2D1N': {
                'Total': self.precio_2d1n_total,
                'Secundaria': self.precio_2d1n_secundaria,
            },
            '3D2N': {
                'Total': self.precio_3d2n_total,
                'Secundaria': self.precio_3d2n_secundaria,
            },
            '4D3N': {
                'Total': self.precio_4d3n_total,
                'Secundaria': self.precio_4d3n_secundaria,
            },
        }

        grupo = precios.get(programa)

        if not grupo:
            return Decimal('0.00')

        if tipo_ocupacion == 'Total':
            return grupo['Total']

        return grupo['Secundaria']

    @property
    def precio_desde_hospedaje(self):
        precios = [
            self.precio_2d1n_total,
            self.precio_2d1n_secundaria,
            self.precio_3d2n_total,
            self.precio_3d2n_secundaria,
            self.precio_4d3n_total,
            self.precio_4d3n_secundaria,
        ]

        precios_validos = [precio for precio in precios if precio and precio > 0]
        return min(precios_validos) if precios_validos else Decimal('0.00')

    def __str__(self):
        return f"Cabaña {self.numero_cabana} - {self.tipo_cabana}"

    class Meta:
        verbose_name = 'Cabaña'
        verbose_name_plural = 'Cabañas'


class Cine(models.Model):
    id_funcion = models.AutoField(primary_key=True)
    titulo_pelicula = models.CharField(max_length=150, verbose_name='Titulo de la pelicula')
    fecha_proyeccion = models.DateField(verbose_name='Fecha de proyeccion')
    hora_proyeccion = models.TimeField(verbose_name='Hora de proyeccion')
    precio_entrada = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)], verbose_name='Precio de entrada')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripcion')
    duracion_minutos = models.IntegerField(default=90, validators=[MinValueValidator(1)], verbose_name='Duración en minutos')
    capacidad_sala = models.IntegerField(default=30, validators=[MinValueValidator(1)], verbose_name='Capacidad de la sala')
    imagen = models.ImageField(upload_to='cine/', blank=True, null=True, verbose_name='Imagen')
    estado = models.CharField(
        max_length=20,
        choices=[('Activa', 'Activa'), ('Cancelada', 'Cancelada'), ('Finalizada', 'Finalizada')],
        default='Activa',
        verbose_name='Estado'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    dia_funcion = models.CharField(
        max_length=30,
        default='Sabado',
        verbose_name='Dia de funcion'
    )
    productos_adicionales = models.TextField(
        blank=True,
        null=True,
        default='Canguil, Coca-Cola, hamburguesa',
        verbose_name='Productos adicionales'
    )
    observacion = models.TextField(
        blank=True,
        null=True,
        default='Funcion disponible solo fines de semana.',
        verbose_name='Observacion'
    )

    def __str__(self):
        return f"{self.titulo_pelicula} - {self.fecha_proyeccion}"

    class Meta:
        verbose_name = 'Cine'
        verbose_name_plural = 'Cine'


class ResortDia(models.Model):
    TIPO_AREA_CHOICES = [
        ('piscina', 'Piscina'),
        ('habitacion_dia', 'Habitacion del Dia'),
        ('area_recreativa', 'Area Recreativa'),
        ('area_consumo', 'Area de Consumo'),
        ('restaurante', 'Restaurante'),
        ('spa', 'Spa'),
        ('cancha', 'Cancha'),
        ('otro', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('Disponible', 'Disponible'),
        ('Mantenimiento', 'Mantenimiento'),
        ('Inactivo', 'Inactivo'),
    ]

    id_resort_dia = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, verbose_name='Nombre del area o servicio')
    tipo_area = models.CharField(max_length=30, choices=TIPO_AREA_CHOICES, verbose_name='Tipo de area')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripcion')
    capacidad_maxima = models.IntegerField(verbose_name='Capacidad maxima')
    requiere_reserva = models.BooleanField(default=False, verbose_name='Requiere reserva')
    costo_adicional = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Costo adicional')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Disponible', verbose_name='Estado')
    horario_apertura = models.TimeField(blank=True, null=True, verbose_name='Horario de apertura')
    horario_cierre = models.TimeField(blank=True, null=True, verbose_name='Horario de cierre')
    imagen = models.ImageField(upload_to='resort_dia/', blank=True, null=True, verbose_name='Imagen')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    combo_cabanas = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        default='Combo con cabañas desde la C3 hasta la C8',
        verbose_name='Combo de cabañas'
    )
    incluye = models.TextField(
        blank=True,
        null=True,
        default='Uso de instalaciones del resort. Incluye 2 shampoo y 2 jabones.',
        verbose_name='Incluye'
    )
    indicaciones = models.TextField(
        blank=True,
        null=True,
        default='Las toallas se solicitan en Vistro. Vistro es el punto de atención para clientes del resort del día.',
        verbose_name='Indicaciones'
    )
    punto_atencion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default='Vistro',
        verbose_name='Punto de atención'
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Resort Día'
        verbose_name_plural = 'Resort Día'


# ==========================================
# 2. TABLA CENTRAL DE CONTROL (ORQUESTACION)
# ==========================================

ESTADO_RESERVA_CHOICES = [
    ('Pendiente', 'Pendiente'),
    ('Confirmada', 'Confirmada'),
    ('Cancelada', 'Cancelada'),
    ('No presentado', 'No presentado'),
    ('En curso', 'En curso'),
    ('Finalizada', 'Finalizada'),
]


class Reservas(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name='Cliente')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')
    fecha_ingreso = models.DateField(verbose_name='Fecha de ingreso')
    fecha_salida = models.DateField(verbose_name='Fecha de salida')
    estado_reserva = models.CharField(
        max_length=20,
        choices=ESTADO_RESERVA_CHOICES,
        default='Pendiente',
        verbose_name='Estado de reserva'
    )
    codigo_reserva = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name='Código de reserva')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name='Total')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    estado_pago = models.CharField(
        max_length=30,
        choices=[
            ('Pendiente', 'Pendiente'),
            ('En revision', 'En revision'),
            ('Pagado', 'Pagado'),
            ('Rechazado', 'Rechazado'),
            ('Cancelado', 'Cancelado'),
            ('Anulado', 'Anulado'),
        ],
        default='Pendiente',
        verbose_name='Estado de pago'
    )
    metodo_pago = models.CharField(
        max_length=30,
        choices=[
            ('Sin seleccionar', 'Sin seleccionar'),
            ('Transferencia', 'Deposito o transferencia'),
            ('Recepcion', 'Pago en recepcion'),
            ('Efectivo', 'Efectivo'),
            ('Tarjeta', 'Tarjeta'),
        ],
        default='Sin seleccionar',
        verbose_name='Método de pago'
    )
    fecha_cancelacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de cancelación')
    motivo_cancelacion = models.TextField(blank=True, null=True, verbose_name='Motivo de cancelación')
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Subtotal'
    )
    porcentaje_anticipo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50,
        verbose_name='Porcentaje de anticipo'
    )
    anticipo_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Anticipo mínimo'
    )
    saldo_pendiente = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Saldo pendiente'
    )
    fecha_limite_pago = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha límite de pago'
    )

    def calcular_valores_pago(self):
        total_decimal = Decimal(str(self.total or '0')).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        porcentaje = Decimal(str(self.porcentaje_anticipo or '50')).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        anticipo = (total_decimal * porcentaje / Decimal('100')).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        saldo = (total_decimal - anticipo).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        self.subtotal = total_decimal
        self.anticipo_minimo = anticipo
        self.saldo_pendiente = saldo

        base_fecha = self.fecha_registro.date() if self.fecha_registro else timezone.now().date()
        limite = base_fecha + timedelta(days=1)
        if self.fecha_ingreso and limite > self.fecha_ingreso:
            limite = self.fecha_ingreso
        self.fecha_limite_pago = limite

    def generar_codigo_reserva(self):
        ultimo = Reservas.objects.order_by('-id_reserva').first()
        if ultimo and ultimo.codigo_reserva:
            coincidencia = re.search(r"(\d+)$", ultimo.codigo_reserva)
            siguiente_numero = int(coincidencia.group(1)) + 1 if coincidencia else ultimo.id_reserva + 1
        else:
            ultimo_id = Reservas.objects.order_by('-id_reserva').values_list('id_reserva', flat=True).first()
            siguiente_numero = (ultimo_id or 0) + 1
        return f"RES-{siguiente_numero:04d}"

    def save(self, *args, **kwargs):
        self.calcular_valores_pago()
        if not self.codigo_reserva:
            self.codigo_reserva = self.generar_codigo_reserva()
        super().save(*args, **kwargs)

    @property
    def id_usuario(self):
        return self.id_cliente

    def __str__(self):
        return f"Reserva #{self.id_reserva} - {self.id_cliente.apellidos}"

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'


# ==========================================
# 3. TABLAS DE DETALLES DE CONSUMO
# ==========================================

class DetalleHabitaciones(models.Model):
    id_detalle_hab = models.AutoField(primary_key=True)
    id_reserva = models.ForeignKey(Reservas, on_delete=models.CASCADE, verbose_name='Reserva')
    id_habitacion = models.ForeignKey(Habitaciones, on_delete=models.CASCADE, verbose_name='Habitación')
    cantidad_noches = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Cantidad de noches')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Subtotal')
    fecha_entrada = models.DateField(blank=True, null=True, verbose_name='Fecha de entrada')
    fecha_salida = models.DateField(blank=True, null=True, verbose_name='Fecha de salida')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name='Precio unitario')
    programa = models.CharField(
        max_length=20,
        choices=PROGRAMA_HOSPEDAJE_CHOICES,
        default='2D1N',
        verbose_name='Programa'
    )
    tipo_ocupacion = models.CharField(
        max_length=20,
        choices=TIPO_OCUPACION_CHOICES,
        default='Total',
        verbose_name='Tipo de ocupación'
    )
    precio_programa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Precio del programa'
    )
    cantidad_personas = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad de personas'
    )

    class Meta:
        verbose_name = 'Detalle de Habitación'
        verbose_name_plural = 'Detalles de Habitaciones'


class DetalleCabanas(models.Model):
    id_detalle_cab = models.AutoField(primary_key=True)
    id_reserva = models.ForeignKey(Reservas, on_delete=models.CASCADE, verbose_name='Reserva')
    id_cabana = models.ForeignKey(Cabanas, on_delete=models.CASCADE, verbose_name='Cabaña')
    cantidad_noches = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Cantidad de noches')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Subtotal')
    fecha_entrada = models.DateField(blank=True, null=True, verbose_name='Fecha de entrada')
    fecha_salida = models.DateField(blank=True, null=True, verbose_name='Fecha de salida')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name='Precio unitario')
    programa = models.CharField(
        max_length=20,
        choices=PROGRAMA_HOSPEDAJE_CHOICES,
        default='2D1N',
        verbose_name='Programa'
    )
    tipo_ocupacion = models.CharField(
        max_length=20,
        choices=TIPO_OCUPACION_CHOICES,
        default='Total',
        verbose_name='Tipo de ocupación'
    )
    precio_programa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Precio del programa'
    )
    cantidad_personas = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad de personas'
    )

    class Meta:
        verbose_name = 'Detalle de Cabaña'
        verbose_name_plural = 'Detalles de Cabañas'


class DetalleCine(models.Model):
    id_detalle_cine = models.AutoField(primary_key=True)
    id_reserva = models.ForeignKey(Reservas, on_delete=models.CASCADE, verbose_name='Reserva')
    id_funcion = models.ForeignKey(Cine, on_delete=models.CASCADE, verbose_name='Función')
    cantidad_asientos = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Cantidad de asientos')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Subtotal')
    fecha_uso = models.DateField(blank=True, null=True, verbose_name='Fecha de uso')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name='Precio unitario')
    productos_adicionales = models.TextField(
        blank=True,
        null=True,
        verbose_name='Productos adicionales'
    )
    total_productos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Total productos adicionales'
    )

    class Meta:
        verbose_name = 'Detalle de Cine'
        verbose_name_plural = 'Detalles de Cine'


class DetalleResort(models.Model):
    id_detalle_resort = models.AutoField(primary_key=True)
    id_reserva = models.ForeignKey(Reservas, on_delete=models.CASCADE, verbose_name='Reserva')
    id_resort_dia = models.ForeignKey(ResortDia, on_delete=models.CASCADE, verbose_name='Resort Día')
    cantidad_personas = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Cantidad de personas')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Subtotal')
    fecha_uso = models.DateField(blank=True, null=True, verbose_name='Fecha de uso')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name='Precio unitario')
    combo_cabana = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default='Cabañas C3 hasta C8',
        verbose_name='Combo de cabaña'
    )
    punto_atencion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default='Vistro',
        verbose_name='Punto de atención'
    )

    class Meta:
        verbose_name = 'Detalle Reserva'
        verbose_name_plural = 'Detalles de Reserva'


class PagoReserva(models.Model):
    METODOS_PAGO = [
        ('Transferencia', 'Transferencia bancaria'),
        ('Recepcion', 'Pago en recepcion'),
    ]

    ESTADOS_PAGO = [
        ('Pendiente', 'Pendiente'),
        ('En revision', 'En revision'),
        ('Pagado', 'Pagado'),
        ('Rechazado', 'Rechazado'),
        ('Cancelado', 'Cancelado'),
        ('Error', 'Error'),
    ]

    reserva = models.ForeignKey(
        Reservas,
        on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name='Reserva'
    )

    metodo_pago = models.CharField(
        max_length=30,
        choices=METODOS_PAGO,
        verbose_name='Metodo de pago'
    )

    estado = models.CharField(
        max_length=30,
        choices=ESTADOS_PAGO,
        default='Pendiente',
        verbose_name='Estado del pago'
    )

    monto_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Monto total'
    )

    monto_anticipo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Monto anticipo'
    )

    saldo_pendiente = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Saldo pendiente'
    )

    client_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        verbose_name='Client Transaction ID'
    )

    payphone_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='PayPhone Transaction ID'
    )

    authorization_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Código de autorización'
    )

    respuesta_payphone = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Respuesta PayPhone'
    )

    link_pago_payphone = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Link de pago PayPhone'
    )

    banco_origen = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Banco de origen'
    )

    numero_cuenta_origen = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name='Número de cuenta de origen'
    )

    numero_comprobante = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Número de comprobante'
    )

    comprobante = models.ImageField(
        upload_to='comprobantes_transferencia/',
        blank=True,
        null=True,
        verbose_name='Comprobante de transferencia'
    )

    observacion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observación'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pago de reserva'
        verbose_name_plural = 'Pagos de reservas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.reserva.codigo_reserva} - {self.metodo_pago} - {self.estado}"


class ConfiguracionInicio(models.Model):
    """
    Configuración de imágenes de la página de inicio.
    Solo debe existir un registro (id=1).
    """

    imagen_habitaciones = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Imagen de Habitaciones',
        help_text='Imagen de la tarjeta de Habitaciones en el inicio.',
    )
    imagen_cabanas = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Imagen de Cabañas',
        help_text='Imagen de la tarjeta de Cabañas en el inicio.',
    )
    imagen_cine = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Imagen de Cine',
        help_text='Imagen de la tarjeta de Cine en el inicio.',
    )
    imagen_resort = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Imagen de Resort del Día',
        help_text='Imagen de la tarjeta de Resort del Día en el inicio.',
    )
    imagen_hero = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Imagen de fondo del hero',
        help_text='Fondo principal de la portada del inicio.',
    )

    imagen_sobre_nosotros = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Imagen de Sobre nosotros',
        help_text='Imagen de la portada de la página "Sobre nosotros".',
    )

    mision = models.TextField(
        blank=True,
        null=True,
        verbose_name='Misión',
        help_text='Texto que se muestra en la sección de Misión de "Sobre nosotros".',
    )

    vision = models.TextField(
        blank=True,
        null=True,
        verbose_name='Visión',
        help_text='Texto que se muestra en la sección de Visión de "Sobre nosotros".',
    )

    fondo_habitaciones = models.ImageField(
        upload_to='inicio/fondos/',
        blank=True,
        null=True,
        verbose_name='Fondo de Habitaciones',
        help_text='Imagen de fondo de la portada de la página de Habitaciones.',
    )

    fondo_cabanas = models.ImageField(
        upload_to='inicio/fondos/',
        blank=True,
        null=True,
        verbose_name='Fondo de Cabañas',
        help_text='Imagen de fondo de la portada de la página de Cabañas.',
    )

    fondo_cine = models.ImageField(
        upload_to='inicio/fondos/',
        blank=True,
        null=True,
        verbose_name='Fondo de Cine',
        help_text='Imagen de fondo de la portada de la página de Cine.',
    )

    fondo_resort = models.ImageField(
        upload_to='inicio/fondos/',
        blank=True,
        null=True,
        verbose_name='Fondo de Resort del Día',
        help_text='Imagen de fondo de la portada de la página de Resort del Día.',
    )

    sn_hero_titulo = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Hero: título',
        help_text='Título principal de la página "Sobre nosotros".',
    )

    sn_hero_parrafo = models.TextField(
        blank=True,
        null=True,
        verbose_name='Hero: párrafo',
        help_text='Texto de presentación de la página "Sobre nosotros".',
    )

    sn_stat_1_numero = models.CharField(
        max_length=50, blank=True, null=True, verbose_name='Estadística 1: número',
    )
    sn_stat_1_etiqueta = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Estadística 1: etiqueta',
    )
    sn_stat_2_numero = models.CharField(
        max_length=50, blank=True, null=True, verbose_name='Estadística 2: número',
    )
    sn_stat_2_etiqueta = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Estadística 2: etiqueta',
    )
    sn_stat_3_numero = models.CharField(
        max_length=50, blank=True, null=True, verbose_name='Estadística 3: número',
    )
    sn_stat_3_etiqueta = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Estadística 3: etiqueta',
    )
    sn_stat_4_numero = models.CharField(
        max_length=50, blank=True, null=True, verbose_name='Estadística 4: número',
    )
    sn_stat_4_etiqueta = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Estadística 4: etiqueta',
    )

    sn_historia_titulo = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Historia: título',
        help_text='Título de la sección "Nuestra historia".',
    )
    sn_historia_parrafo_1 = models.TextField(
        blank=True, null=True, verbose_name='Historia: párrafo 1',
    )
    sn_historia_parrafo_2 = models.TextField(
        blank=True, null=True, verbose_name='Historia: párrafo 2',
    )
    sn_historia_imagen = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Historia: imagen',
        help_text='Imagen de la sección "Nuestra historia".',
    )

    sn_valor_1_titulo = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Valor 1: título',
    )
    sn_valor_1_texto = models.TextField(
        blank=True, null=True, verbose_name='Valor 1: descripción',
    )
    sn_valor_2_titulo = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Valor 2: título',
    )
    sn_valor_2_texto = models.TextField(
        blank=True, null=True, verbose_name='Valor 2: descripción',
    )
    sn_valor_3_titulo = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Valor 3: título',
    )
    sn_valor_3_texto = models.TextField(
        blank=True, null=True, verbose_name='Valor 3: descripción',
    )
    sn_valor_4_titulo = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Valor 4: título',
    )
    sn_valor_4_texto = models.TextField(
        blank=True, null=True, verbose_name='Valor 4: descripción',
    )

    sn_compromiso_titulo = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Compromiso: título',
        help_text='Título de la sección "Nuestro compromiso".',
    )
    sn_compromiso_parrafo = models.TextField(
        blank=True, null=True, verbose_name='Compromiso: párrafo',
    )
    sn_compromiso_imagen = models.ImageField(
        upload_to='inicio/',
        blank=True,
        null=True,
        verbose_name='Compromiso: imagen',
        help_text='Imagen de la sección "Nuestro compromiso".',
    )

    sn_cta_titulo = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='CTA: título',
        help_text='Título de la sección final de llamada a la acción.',
    )
    sn_cta_parrafo = models.TextField(
        blank=True, null=True, verbose_name='CTA: párrafo',
    )

    class Meta:
        verbose_name = 'Sobre nosotros'
        verbose_name_plural = 'Sobre nosotros'

    def __str__(self):
        return 'Sobre nosotros'