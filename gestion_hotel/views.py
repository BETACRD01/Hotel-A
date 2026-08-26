from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from urllib.parse import urlencode
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
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.utils import ProgrammingError
from django.forms import modelform_factory
from .validators import validate_password_strength
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import ClienteLoginForm, ClienteRegistroForm
from .models import (
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
from .utils.validaciones import (
    validar_documento_cliente,
    validar_celular_cliente,
    validar_correo_cliente,
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
    user_model = get_user_model()
    username = gerente.correo_electronico or f"gerente_{gerente.id_cliente}"
    auth_user, _ = user_model.objects.get_or_create(username=username)

    auth_user.email = gerente.correo_electronico or ""
    auth_user.first_name = gerente.nombres or ""
    auth_user.last_name = gerente.apellidos or ""
    auth_user.is_active = True
    auth_user.is_staff = True
    auth_user.is_superuser = True
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
    usuario = obtener_usuario_sesion(request)
    if usuario is None:
        return None
    if usuario.rol not in roles:
        messages.error(request, mensaje)
        return None
    return usuario


def puede_cancelar_reserva(usuario, reserva):
    if usuario.rol in {"admin", "gerente"}:
        return True
    return usuario.id_cliente == reserva.id_cliente_id and reserva.estado_reserva in {"Pendiente", "Confirmada"}


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


def convertir_fecha_formulario(valor, nombre_campo="fecha"):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"La {nombre_campo} es obligatoria o no tiene un formato vÃ¡lido.")


def calcular_valores_reserva(reserva):
    reserva.refresh_from_db()
    reserva.calcular_valores_pago()
    reserva.save()
    return reserva


def cancelar_reservas_vencidas():
    """
    Cancela automÃ¡ticamente las reservas cuyo plazo de pago ya venciÃ³.

    El plazo es de 24 horas desde el registro de la reserva: si hoy se
    reserva y en 1 dÃ­a no se ha pagado, la reserva queda cancelada.
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
            motivo_cancelacion="Cancelada automÃ¡ticamente por vencer el plazo de pago de 24 horas.",
        )
    return total


# ============================================================
# PÃGINA PÃšBLICA
# ============================================================

def index(request):
    """
    Muestra la pÃ¡gina pÃºblica principal.
    """
    usuario = obtener_usuario_sesion(request)

    config = ConfiguracionInicio.objects.first()

    def primera_imagen(modelo):
        obj = modelo.objects.exclude(imagen=None).exclude(imagen="").first()
        return obj.imagen if obj else None

    return render(
        request,
        "index.html",
        {
            "usuario": usuario,
            "imagen_habitaciones": (config.imagen_habitaciones if config and config.imagen_habitaciones else primera_imagen(Habitaciones)),
            "imagen_cabanas": (config.imagen_cabanas if config and config.imagen_cabanas else primera_imagen(Cabanas)),
            "imagen_cine": (config.imagen_cine if config and config.imagen_cine else primera_imagen(Cine)),
            "imagen_resort": (config.imagen_resort if config and config.imagen_resort else primera_imagen(ResortDia)),
            "imagen_hero": (config.imagen_hero if config and config.imagen_hero else None),
        }
    )


def sobre_nosotros_view(request):
    """
    PÃ¡gina pÃºblica 'Sobre nosotros'.
    """
    usuario = obtener_usuario_sesion(request)

    config = ConfiguracionInicio.objects.first()

    def valor(campo, defecto):
        return getattr(config, campo, None) or defecto if config else defecto

    contexto = {
        "usuario": usuario,
        "mision": valor("mision", (
            "Ofrecer experiencias memorables de descanso, recreaciÃ³n y contacto con la naturaleza "
            "en la AmazonÃ­a ecuatoriana, brindando un servicio cÃ¡lido, responsable y de calidad."
        )),
        "vision": valor("vision", (
            "Convertirnos en el eco-resort de referencia en la AmazonÃ­a ecuatoriana, reconocido por "
            "su hospitalidad, sostenibilidad y por ser el destino ideal para el bienestar y la autenticidad."
        )),
        "imagen_sobre_nosotros": (
            config.imagen_sobre_nosotros if config and config.imagen_sobre_nosotros else None
        ),
        "hero_titulo": valor("sn_hero_titulo", "Conoce la esencia de Arahuana"),
        "hero_parrafo": valor("sn_hero_parrafo", (
            "Somos mÃ¡s que un resort. Somos un espacio donde la naturaleza, "
            "el confort y la cultura se unen para ofrecer experiencias "
            "inolvidables en la AmazonÃ­a ecuatoriana."
        )),
        "stat_1_numero": valor("sn_stat_1_numero", "5+"),
        "stat_1_etiqueta": valor("sn_stat_1_etiqueta", "AÃ±os de experiencia"),
        "stat_2_numero": valor("sn_stat_2_numero", "Miles"),
        "stat_2_etiqueta": valor("sn_stat_2_etiqueta", "HuÃ©spedes felices"),
        "stat_3_numero": valor("sn_stat_3_numero", "4.8"),
        "stat_3_etiqueta": valor("sn_stat_3_etiqueta", "CalificaciÃ³n promedio"),
        "stat_4_numero": valor("sn_stat_4_numero", "Tena, Napo"),
        "stat_4_etiqueta": valor("sn_stat_4_etiqueta", "Ecuador"),
        "historia_titulo": valor("sn_historia_titulo", "Un lugar para reconectar con la naturaleza"),
        "historia_parrafo_1": valor("sn_historia_parrafo_1", (
            "Arahuana Eco-Resort & Spa naciÃ³ con el propÃ³sito de compartir "
            "la belleza de la AmazonÃ­a ecuatoriana, ofreciendo un lugar donde "
            "cada huÃ©sped pueda descansar, disfrutar y vivir experiencias memorables."
        )),
        "historia_parrafo_2": valor("sn_historia_parrafo_2", (
            "Nuestra propuesta combina hospedaje cÃ³modo, espacios recreativos, "
            "cine, cabaÃ±as y resort del dÃ­a en un entorno natural pensado para "
            "familias, parejas y visitantes."
        )),
        "historia_imagen": (
            config.sn_historia_imagen if config and config.sn_historia_imagen else None
        ),
        "valor_1_titulo": valor("sn_valor_1_titulo", "Sostenibilidad"),
        "valor_1_texto": valor("sn_valor_1_texto", (
            "Cuidamos nuestro entorno natural y promovemos una experiencia responsable."
        )),
        "valor_2_titulo": valor("sn_valor_2_titulo", "Hospitalidad"),
        "valor_2_texto": valor("sn_valor_2_texto", (
            "Brindamos atenciÃ³n cÃ¡lida, cercana y personalizada para cada huÃ©sped."
        )),
        "valor_3_titulo": valor("sn_valor_3_titulo", "Autenticidad"),
        "valor_3_texto": valor("sn_valor_3_texto", (
            "Resaltamos la cultura amazÃ³nica y la riqueza natural de nuestro entorno."
        )),
        "valor_4_titulo": valor("sn_valor_4_titulo", "Bienestar"),
        "valor_4_texto": valor("sn_valor_4_texto", (
            "Creamos experiencias que renuevan el cuerpo, la mente y el espÃ­ritu."
        )),
        "compromiso_titulo": valor("sn_compromiso_titulo", "Una experiencia pensada para ti"),
        "compromiso_parrafo": valor("sn_compromiso_parrafo", (
            "Trabajamos dÃ­a a dÃ­a para que cada visita sea especial, "
            "cuidando cada detalle del servicio y ofreciendo espacios seguros, "
            "cÃ³modos y conectados con la naturaleza."
        )),
        "compromiso_imagen": (
            config.sn_compromiso_imagen if config and config.sn_compromiso_imagen else None
        ),
        "cta_titulo": valor("sn_cta_titulo", "Vive la experiencia de la AmazonÃ­a"),
        "cta_parrafo": valor("sn_cta_parrafo", (
            "Reserva tu prÃ³xima visita y disfruta descanso, naturaleza "
            "y bienestar en un solo lugar."
        )),
    }

    return render(request, "sobre_nosotros.html", contexto)


# ============================================================
# AUTENTICACIÃ“N
# ============================================================

def login_view(request):
    """
    Procesa el inicio de sesiÃ³n de clientes.
    """
    next_url = request.POST.get("next") or request.GET.get("next", "")
    usuario_actual = obtener_usuario_sesion(request)

    if usuario_actual:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(next_url)
        return redirect("gestion:dashboard")

    form = ClienteLoginForm(request.POST or None)

    if request.method == "POST":
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return render(request, "login.html", {"form": form, "next": next_url})

        correo_electronico = form.cleaned_data["correo_electronico"]
        password = form.cleaned_data["password"]

        try:
            usuario = Cliente.objects.get(
                correo_electronico__iexact=correo_electronico,
                activo=True,
            )
        except Cliente.DoesNotExist:
            messages.error(
                request,
                "Correo o contraseÃ±a incorrectos o la cuenta estÃ¡ inactiva."
            )
            return render(request, "login.html", {"form": form, "next": next_url})

        password_correcta = False

        if usuario.password.startswith(
            ("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")
        ):
            password_correcta = check_password(password, usuario.password)
        else:
            password_correcta = usuario.password == password
            if password_correcta:
                usuario.password = make_password(password)
                usuario.save(update_fields=["password"])

        if not password_correcta:
            messages.error(
                request,
                "Correo o contraseÃ±a incorrectos."
            )
            return render(request, "login.html", {"form": form, "next": next_url})

        nombre_formateado = f"{usuario.nombres} {usuario.apellidos}".strip().title()

        if usuario.rol == 'gerente':
            sincronizar_acceso_admin_gerente(request, usuario, password)
            request.session["usuario_id"] = usuario.id_cliente
            request.session["usuario_nombre"] = nombre_formateado
            request.session["usuario_rol"] = "gerente"
            request.session["cliente_id"] = usuario.id_cliente
            request.session["cliente_nombre"] = nombre_formateado
            messages.success(request, f"Bienvenido, {usuario.nombres.strip().title()}.")
            return redirect("gestion:gerente_dashboard")

        if usuario.rol != 'cliente':
            messages.error(
                request,
                "Este acceso es solo para clientes. Ingrese desde el Panel de GestiÃ³n."
            )
            return render(request, "login.html", {"form": form, "next": next_url})

        request.session["cliente_id"] = usuario.id_cliente
        request.session["cliente_nombre"] = nombre_formateado
        request.session["cliente_correo"] = usuario.correo_electronico or ""
        request.session["cliente_telefono"] = usuario.telefono_celular or ""
        request.session["cliente_documento"] = usuario.numero_documento or ""
        if usuario.ciudad or usuario.pais_origen:
            request.session["cliente_ubicacion"] = ", ".join(
                part for part in [usuario.ciudad, usuario.pais_origen] if part
            )
        else:
            request.session["cliente_ubicacion"] = ""
        request.session["usuario_id"] = usuario.id_cliente
        request.session["usuario_nombre"] = nombre_formateado
        request.session["usuario_rol"] = "cliente"

        messages.success(request, f"Bienvenido, {usuario.nombres.strip().title()}.")

        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(next_url)

        return redirect("gestion:dashboard")

    return render(request, "login.html", {"form": form, "next": next_url})


def registro_view(request):
    """
    Registra un nuevo cliente en el sistema.
    """
    if request.method == "POST":
        tipo_documento = request.POST.get("tipo_documento")
        numero_documento = request.POST.get("numero_documento")
        telefono_celular = request.POST.get("telefono_celular")
        correo_electronico = request.POST.get("correo_electronico")

        # Validar documento
        resultado_documento = validar_documento_cliente(
            tipo_documento,
            numero_documento
        )

        if not resultado_documento["valido"]:
            messages.error(request, resultado_documento["mensaje"])
            return redirect("gestion:registro")

        numero_documento = resultado_documento["documento"]

        # Validar celular
        resultado_telefono = validar_celular_cliente(
            tipo_documento,
            telefono_celular
        )

        if not resultado_telefono["valido"]:
            messages.error(request, resultado_telefono["mensaje"])
            return redirect("gestion:registro")

        telefono_celular = resultado_telefono["telefono"]

        # Validar correo
        resultado_correo = validar_correo_cliente(correo_electronico)

        if not resultado_correo["valido"]:
            messages.error(request, resultado_correo["mensaje"])
            return redirect("gestion:registro")

        correo_electronico = resultado_correo["correo"]

        # Verificar duplicados
        if Cliente.objects.filter(numero_documento=numero_documento).exists():
            messages.error(request, "Ya existe una cuenta registrada con este nÃºmero de documento.")
            return redirect("gestion:registro")

        if Cliente.objects.filter(correo_electronico__iexact=correo_electronico).exists():
            messages.error(request, "Ya existe una cuenta registrada con este correo electrÃ³nico.")
            return redirect("gestion:registro")

        form = ClienteRegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Tu cuenta de cliente fue creada correctamente. Ahora inicia sesiÃ³n."
            )
            return redirect("gestion:login")

        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
        return render(request, "registro.html", {"form": form})

    return render(request, "registro.html", {"form": ClienteRegistroForm()})


def recuperar_password(request):
    """
    Recuperar contraseÃ±a por correo electrÃ³nico usando cÃ³digo de verificaciÃ³n.
    """
    if request.method == "POST":
        correo_electronico = request.POST.get("correo_electronico", "").strip().lower()
        cliente = Cliente.objects.filter(
            correo_electronico__iexact=correo_electronico,
            rol="cliente",
            activo=True,
        ).first()

        if cliente:
            codigo = str(random.randint(100000, 999999))
            asunto = "CÃ³digo de recuperaciÃ³n - Hotel Arahuana"
            mensaje = f"""
Hola {cliente.nombres},

Recibimos una solicitud para restablecer tu contraseÃ±a.

Tu cÃ³digo de recuperaciÃ³n es:

{codigo}

No compartas este cÃ³digo con nadie.

Si no solicitaste este cambio, ignora este mensaje.

Hotel Arahuana Eco-Resort & Spa
"""
            try:
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [cliente.correo_electronico],
                    fail_silently=False,
                )
                request.session["reset_cliente_id"] = cliente.id_cliente
                request.session["reset_codigo"] = codigo
                request.session["reset_correo"] = cliente.correo_electronico
                request.session["reset_codigo_validado"] = False

                messages.success(
                    request,
                    "Se enviÃ³ un cÃ³digo de recuperaciÃ³n a tu correo electrÃ³nico."
                )
                return redirect("gestion:verificar_codigo")
            except (TimeoutError, socket.timeout, smtplib.SMTPException) as e:
                print("Error SMTP recuperaciÃ³n contraseÃ±a:", type(e).__name__, str(e))
                messages.error(
                    request,
                    "No se pudo enviar el cÃ³digo porque la conexiÃ³n con el servidor de correo fue bloqueada o tardÃ³ demasiado. Intenta desde otra red o verifica tu conexiÃ³n."
                )
                return redirect("gestion:recuperar_password")
            except Exception as e:
                print("Error SMTP recuperaciÃ³n contraseÃ±a:", type(e).__name__, str(e))
                messages.error(
                    request,
                    "No se pudo enviar el cÃ³digo porque la conexiÃ³n con el servidor de correo fue bloqueada o tardÃ³ demasiado. Intenta desde otra red o verifica tu conexiÃ³n."
                )
                return redirect("gestion:recuperar_password")

        messages.success(
            request,
            "Si el correo estÃ¡ registrado, recibirÃ¡s un cÃ³digo de recuperaciÃ³n."
        )
        return render(request, "recuperar_password.html")

    return render(request, "recuperar_password.html")


def verificar_codigo(request):
    """
    Verifica el cÃ³digo de recuperaciÃ³n guardado en sesiÃ³n.
    """
    if not request.session.get("reset_cliente_id") or not request.session.get("reset_codigo"):
        messages.error(request, "Debe iniciar el flujo de recuperaciÃ³n de contraseÃ±a primero.")
        return redirect("gestion:recuperar_password")

    if request.method == "POST":
        codigo_ingresado = request.POST.get("codigo", "").strip()
        codigo_sesion = request.session.get("reset_codigo")

        if codigo_ingresado and codigo_sesion and codigo_ingresado == codigo_sesion:
            request.session["reset_codigo_validado"] = True
            return redirect("gestion:nueva_password")

        messages.error(request, "CÃ³digo incorrecto. IntÃ©ntalo nuevamente.")

    return render(request, "verificar_codigo.html")


def nueva_password(request):
    """
    Permite al cliente crear una nueva contraseÃ±a luego de verificar el cÃ³digo.
    """
    cliente_id = request.session.get("reset_cliente_id")
    codigo_validado = request.session.get("reset_codigo_validado")

    if not cliente_id or not codigo_validado:
        messages.error(request, "El flujo de recuperaciÃ³n no es vÃ¡lido. Intenta nuevamente.")
        return redirect("gestion:recuperar_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Las contraseÃ±as no coinciden.")
            return render(request, "nueva_password.html")

        if len(password) < 8:
            messages.error(request, "La contraseÃ±a debe tener al menos 8 caracteres.")
            return render(request, "nueva_password.html")

        usuario = Cliente.objects.filter(
            id_cliente=cliente_id,
            rol="cliente",
            activo=True,
        ).first()

        if usuario is None:
            messages.error(request, "No se encontrÃ³ el cliente para actualizar la contraseÃ±a.")
            return redirect("gestion:recuperar_password")

        usuario.password = make_password(password)
        usuario.save(update_fields=["password"])

        for key in [
            "reset_cliente_id",
            "reset_codigo",
            "reset_correo",
            "reset_codigo_validado",
        ]:
            request.session.pop(key, None)

        messages.success(
            request,
            "ContraseÃ±a actualizada correctamente. Ya puedes iniciar sesiÃ³n."
        )
        return redirect("gestion:login")

    return render(request, "nueva_password.html")


def recuperar_contrasena_view(request):
    """
    Muestra el formulario para recuperar contraseÃ±a por correo.
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        usuario = Cliente.objects.filter(
            correo_electronico__iexact=email,
            rol="cliente",
            activo=True,
        ).first()

        if usuario:
            token = signing.dumps({
                "usuario_id": usuario.id_cliente,
                "email": usuario.correo_electronico,
            })
            enlace = request.build_absolute_uri(
                reverse("gestion:restablecer_contrasena", args=[token])
            )
            send_mail(
                subject="RecuperaciÃ³n de contraseÃ±a - Arahuana",
                message=(
                    f"Hola {usuario.nombres},\n\n"
                    f"Recibimos una solicitud para restablecer tu contraseÃ±a. "
                    f"Haz clic en el siguiente enlace:\n\n{enlace}\n\n"
                    "Este enlace expira en 1 hora. Si no solicitaste este cambio, "
                    "ignora este correo."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@arahuana.com"),
                recipient_list=[usuario.correo_electronico],
                fail_silently=True,
            )

        messages.success(
            request,
            "Si el correo estÃ¡ registrado, recibirÃ¡s instrucciones para restablecer tu contraseÃ±a."
        )
        return render(request, "recuperar_contrasena.html")

    return render(request, "recuperar_contrasena.html")


def restablecer_contrasena_view(request, token):
    """
    Valida el token de recuperaciÃ³n y actualiza la contraseÃ±a.
    """
    try:
        datos = signing.loads(token, max_age=3600)
        usuario_id = datos.get("usuario_id")
        email = datos.get("email")
    except (signing.BadSignature, signing.SignatureExpired):
        messages.error(
            request,
            "El enlace de recuperaciÃ³n no es vÃ¡lido o ha expirado."
        )
        return render(request, "restablecer_contrasena.html", {"token_error": True})

    usuario = Cliente.objects.filter(
        id_cliente=usuario_id,
        correo_electronico__iexact=email,
        rol="cliente",
        activo=True,
    ).first()

    if usuario is None:
        messages.error(
            request,
            "El enlace de recuperaciÃ³n no es vÃ¡lido o ha expirado."
        )
        return render(request, "restablecer_contrasena.html", {"token_error": True})

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirmar_password = request.POST.get("confirmar_password", "")

        if password != confirmar_password:
            messages.error(request, "Las contraseÃ±as no coinciden.")
            return render(request, "restablecer_contrasena.html", {"token": token})

        try:
            validate_password_strength(password)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, "restablecer_contrasena.html", {"token": token})

        usuario.password = make_password(password)
        usuario.save(update_fields=["password"])

        messages.success(
            request,
            "ContraseÃ±a actualizada correctamente. Ya puedes iniciar sesiÃ³n."
        )
        return redirect("gestion:login")

    return render(request, "restablecer_contrasena.html", {"token": token})


def logout_view(request):
    """
    Cierra la sesiÃ³n del usuario.
    """
    request.session.flush()

    messages.info(
        request,
        "La sesiÃ³n se cerrÃ³ correctamente."
    )

    return redirect("gestion:inicio")


# ============================================================
# PANEL DEL CLIENTE
# ============================================================

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
# HABITACIONES
# ============================================================

def habitaciones_view(request):
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
        tipo_ocupacion = request.POST.get("tipo_ocupacion", "Total")
        fecha_ingreso = request.POST.get("fecha_ingreso")
        cantidad_personas = request.POST.get("cantidad_personas")
        observaciones = request.POST.get("observaciones", "")
        metodo_pago = obtener_metodo_pago_formulario(request)

        if programa not in ["2D1N", "3D2N", "4D3N"]:
            messages.error(request, "Debes seleccionar un programa de hospedaje vÃ¡lido.")
            return redirect("gestion:habitaciones")

        try:
            fecha_ingreso_obj = convertir_fecha_formulario(fecha_ingreso, "fecha de ingreso")
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

        cantidad_personas_int = convertir_entero(cantidad_personas, 1)

        if cantidad_personas_int > habitacion.capacidad:
            messages.error(
                request,
                f"La habitaciÃ³n seleccionada permite mÃ¡ximo {habitacion.capacidad} persona(s)."
            )
            return redirect("gestion:habitaciones")

        tipo_ocupacion_final = obtener_tipo_ocupacion_final(habitacion, tipo_ocupacion)
        precio_programa = convertir_decimal(
            habitacion.obtener_precio_programa(programa, tipo_ocupacion)
        )

        if precio_programa <= 0:
            messages.error(
                request,
                "La habitaciÃ³n seleccionada no tiene configurado el precio para ese programa."
            )
            return redirect("gestion:habitaciones")

        noches = obtener_noches_por_programa(programa)
        fecha_salida_obj = fecha_ingreso_obj + timedelta(days=noches)

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
                programa=programa,
                tipo_ocupacion=tipo_ocupacion_final,
                precio_programa=precio_programa,
                cantidad_personas=cantidad_personas_int,
            )

            calcular_valores_reserva(reserva)

        messages.success(
            request,
            "Reserva de habitaciÃ³n creada correctamente. Ahora puedes completar el pago."
        )
        return redirigir_segun_metodo_pago(reserva, metodo_pago)

    contexto = {
        "habitaciones": habitaciones,
        "usuario": request.session.get("cliente_id"),
        "fondo_habitaciones": _config_fondo("fondo_habitaciones"),
    }

    return render(request, "habitaciones.html", contexto)


# ============================================================
# CABAÃ‘AS
# ============================================================

def cabanas_view(request):
    cancelar_reservas_vencidas()

    cabanas = Cabanas.objects.filter(
        activo=True
    ).order_by("numero_cabana")

    if request.method == "POST":
        cliente_id = request.session.get("cliente_id")

        if not cliente_id:
            messages.warning(request, "Debes iniciar sesiÃ³n para reservar.")
            return redirect("gestion:login")

        id_cabana = request.POST.get("id_cabana")
        programa = request.POST.get("programa")
        tipo_ocupacion = request.POST.get("tipo_ocupacion", "Total")
        fecha_ingreso = request.POST.get("fecha_ingreso")
        cantidad_personas = request.POST.get("cantidad_personas")
        observaciones = request.POST.get("observaciones", "")
        metodo_pago = obtener_metodo_pago_formulario(request)

        if programa not in ["2D1N", "3D2N", "4D3N"]:
            messages.error(request, "Debes seleccionar un programa de hospedaje vÃ¡lido.")
            return redirect("gestion:cabanas")

        try:
            fecha_ingreso_obj = convertir_fecha_formulario(fecha_ingreso, "fecha de ingreso")
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

        cantidad_personas_int = convertir_entero(cantidad_personas, 1)

        if cantidad_personas_int > cabana.capacidad:
            messages.error(
                request,
                f"La cabaÃ±a seleccionada permite mÃ¡ximo {cabana.capacidad} persona(s)."
            )
            return redirect("gestion:cabanas")

        tipo_ocupacion_final = obtener_tipo_ocupacion_final(cabana, tipo_ocupacion)
        precio_programa = convertir_decimal(
            cabana.obtener_precio_programa(programa, tipo_ocupacion)
        )

        if precio_programa <= 0:
            messages.error(
                request,
                "La cabaÃ±a seleccionada no tiene configurado el precio para ese programa."
            )
            return redirect("gestion:cabanas")

        noches = obtener_noches_por_programa(programa)
        fecha_salida_obj = fecha_ingreso_obj + timedelta(days=noches)

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
                programa=programa,
                tipo_ocupacion=tipo_ocupacion_final,
                precio_programa=precio_programa,
                cantidad_personas=cantidad_personas_int,
            )

            calcular_valores_reserva(reserva)

        messages.success(
            request,
            "Reserva de cabaÃ±a creada correctamente. Ahora puedes completar el pago."
        )
        return redirigir_segun_metodo_pago(reserva, metodo_pago)

    contexto = {
        "cabanas": cabanas,
        "usuario": request.session.get("cliente_id"),
        "fondo_cabanas": _config_fondo("fondo_cabanas"),
    }

    return render(request, "cabanas.html", contexto)


# ============================================================
# CINE
# ============================================================

def cine_view(request):
    cancelar_reservas_vencidas()

    funciones = Cine.objects.filter(activo=True).order_by("fecha_proyeccion", "hora_proyeccion")

    if request.method == "POST":
        cliente_id = request.session.get("cliente_id")

        if not cliente_id:
            messages.warning(request, "Debes iniciar sesiÃ³n para reservar.")
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

    contexto = {
        "funciones": funciones,
        "usuario": request.session.get("cliente_id"),
        "fondo_cine": _config_fondo("fondo_cine"),
    }

    return render(request, "cine.html", contexto)


# ============================================================
# RESORT DEL DÃA
# ============================================================

def resort_dia_view(request):
    cancelar_reservas_vencidas()

    areas_resort = ResortDia.objects.filter(activo=True).order_by("nombre")

    if request.method == "POST":
        cliente_id = request.session.get("cliente_id")

        if not cliente_id:
            messages.warning(request, "Debes iniciar sesiÃ³n para reservar.")
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
            "Reserva de Resort del DÃ­a creada correctamente. Ahora puedes completar el pago."
        )
        return redirigir_segun_metodo_pago(reserva, metodo_pago)

    contexto = {
        "areas_resort": areas_resort,
        "paquetes": areas_resort,
        "usuario": request.session.get("cliente_id"),
        "fondo_resort": _config_fondo("fondo_resort"),
    }

    return render(request, "resort_dia.html", contexto)


# ============================================================
# MIS RESERVAS
# ============================================================

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

    return render(request, "mis_reservas.html", contexto)


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

    return render(request, "seleccionar_pago.html", contexto)


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

    return render(request, "pago_transferencia.html", contexto)


# ============================================================
# MÓDULO GERENTE
# ============================================================

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

