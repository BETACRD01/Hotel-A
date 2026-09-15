"""Vistas de autenticacion publica: login, registro, recuperacion y logout."""

from .common import *

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
            return render(request, "auth/login.html", {"form": form, "next": next_url})

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
            return render(request, "auth/login.html", {"form": form, "next": next_url})

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
            return render(request, "auth/login.html", {"form": form, "next": next_url})

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
            return render(request, "auth/login.html", {"form": form, "next": next_url})

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

    return render(request, "auth/login.html", {"form": form, "next": next_url})


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
        return render(request, "auth/registro.html", {"form": form})

    return render(request, "auth/registro.html", {"form": ClienteRegistroForm()})


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
            except (TimeoutError, socket.timeout, smtplib.SMTPException):
                messages.error(
                    request,
                    "No se pudo enviar el cÃ³digo porque la conexiÃ³n con el servidor de correo fue bloqueada o tardÃ³ demasiado. Intenta desde otra red o verifica tu conexiÃ³n."
                )
                return redirect("gestion:recuperar_password")
            except Exception:
                messages.error(
                    request,
                    "No se pudo enviar el cÃ³digo porque la conexiÃ³n con el servidor de correo fue bloqueada o tardÃ³ demasiado. Intenta desde otra red o verifica tu conexiÃ³n."
                )
                return redirect("gestion:recuperar_password")

        messages.success(
            request,
            "Si el correo estÃ¡ registrado, recibirÃ¡s un cÃ³digo de recuperaciÃ³n."
        )
        return render(request, "auth/recuperar_password.html")

    return render(request, "auth/recuperar_password.html")


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

    return render(request, "auth/verificar_codigo.html")


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
            return render(request, "auth/nueva_password.html")

        if len(password) < 8:
            messages.error(request, "La contraseÃ±a debe tener al menos 8 caracteres.")
            return render(request, "auth/nueva_password.html")

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

    return render(request, "auth/nueva_password.html")

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
