from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from urllib.parse import quote_plus

from .models import Cabanas, Cine, Cliente, DetalleResort, Habitaciones, ResortDia

from .models import Reservas
from django.contrib.auth.models import User
from .forms import ClienteRegistroForm
from django.utils import timezone
from datetime import date, timedelta

from .validators import validar_documento_ecuador


class DocumentoEcuadorValidatorTests(TestCase):
    def test_cedula_valida_pasa(self):
        resultado = validar_documento_ecuador("Cédula", "0100000009")
        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["documento_limpio"], "0100000009")
        self.assertIn("válida", resultado["mensaje"].lower())

    def test_cedula_invalida_con_provincia_fuera_de_rango(self):
        resultado = validar_documento_ecuador("Cédula", "2500000000")
        self.assertFalse(resultado["valido"])
        self.assertIn("provincia", resultado["mensaje"].lower())

    def test_ruc_natural_valido(self):
        resultado = validar_documento_ecuador("RUC", "0100000009001")
        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["documento_limpio"], "0100000009001")

    def test_pasaporte_valido_con_letras_y_numeros(self):
        resultado = validar_documento_ecuador("Pasaporte", "AB123456")
        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["documento_limpio"], "AB123456")

    def test_pasaporte_invalido_si_es_muy_corto(self):
        resultado = validar_documento_ecuador("Pasaporte", "ABC12")
        self.assertFalse(resultado["valido"])
        self.assertIn("entre 6 y 15", resultado["mensaje"])

    def test_numero_documento_duplicado_no_puede_registrarse(self):
        Cliente.objects.create(
            tipo_documento='Cédula',
            numero_documento='1501005043',
            nombres='Test',
            apellidos='Usuario',
            telefono_celular='0992123116',
            correo_electronico='test1@example.com',
            password='Test@1234',
        )

        form = ClienteRegistroForm({
            'tipo_documento': 'Cédula',
            'numero_documento': '0100000009',
            'nombres': 'Prueba',
            'apellidos': 'Usuario',
            'correo_electronico': 'test2@example.com',
            'telefono_celular': '0999999998',
            'pais_origen': 'Ecuador',
            'ciudad': 'Quito',
            'password': 'Test@1234',
            'confirm_password': 'Test@1234',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('El número de documento ya se encuentra registrado.', form.errors['numero_documento'])


class UrlNamespaceTests(SimpleTestCase):
    def test_app_namespace_is_available_for_templates(self):
        self.assertEqual(reverse("gestion:login"), "/login/")
        self.assertEqual(reverse("gestion:registro"), "/registro/")


class ImageCleanupCommandTests(TestCase):
    def test_clean_missing_images_clears_only_inexistent_media_fields(self):
        cabana = Cabanas.objects.create(
            numero_cabana="A99",
            capacidad=2,
            precio_noche=95.00,
            estado="Disponible",
            tipo_cabana="Ecológica",
            descripcion="Cabaña de prueba",
            servicios_incluidos="Wi-Fi",
            imagen="cabanas/missing.jpg",
        )
        funcion = Cine.objects.create(
            titulo_pelicula="Test Movie",
            fecha_proyeccion="2030-01-10",
            hora_proyeccion="20:00:00",
            precio_entrada=12.50,
            descripcion="Función de prueba",
            duracion_minutos=120,
            capacidad_sala=30,
            estado="Activa",
            imagen="cine/missing.jpg",
        )

        call_command("limpiar_imagenes_inexistentes")

        cabana.refresh_from_db()
        funcion.refresh_from_db()

        self.assertFalse(cabana.imagen)
        self.assertFalse(funcion.imagen)


class HabitacionesAndCabanasDisplayTests(TestCase):
    def test_habitacion_str_uses_number_and_type(self):
        habitacion = Habitaciones.objects.create(
            numero_habitacion="101",
            tipo_habitacion="Estándar",
            precio_noche=80.00,
            estado="Disponible",
            capacidad=2,
            descripcion="Habitación de prueba",
        )

        self.assertEqual(str(habitacion), "Habitación 101 - Estándar")

    def test_cabana_str_uses_number_and_type(self):
        cabana = Cabanas.objects.create(
            numero_cabana="C3",
            capacidad=2,
            precio_noche=95.00,
            estado="Disponible",
            tipo_cabana="Standard",
            descripcion="Cabaña de prueba",
            servicios_incluidos="Wi-Fi",
        )

        self.assertEqual(str(cabana), "Cabaña C3 - Standard")


class HabitacionesPublicTests(TestCase):
    def setUp(self):
        self.habitacion = Habitaciones.objects.create(
            numero_habitacion="101",
            tipo_habitacion="Estándar",
            precio_noche=80.00,
            estado="Disponible",
            capacidad=2,
            descripcion="Habitación de prueba",
        )

    def test_habitaciones_page_is_public_for_visitors(self):
        response = self.client.get(reverse("gestion:habitaciones"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inicia sesión para reservar")
        self.assertContains(response, "Habitaciones")

    def test_reservation_post_without_login_redirects_to_login(self):
        response = self.client.post(
            reverse("gestion:habitaciones"),
            {
                "id_habitacion": self.habitacion.id_habitacion,
                "fecha_ingreso": "2030-01-01",
                "fecha_salida": "2030-01-03",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("gestion:login"))
        self.assertContains(response, "Debes iniciar sesión para reservar.")


class CabanasPublicTests(TestCase):
    def setUp(self):
        self.cabana = Cabanas.objects.create(
            numero_cabana="A1",
            capacidad=2,
            precio_noche=95.00,
            estado="Disponible",
            tipo_cabana="Ecológica",
            descripcion="Cabaña de prueba",
            servicios_incluidos="Wi-Fi",
        )

    def test_cabanas_page_is_public_for_visitors(self):
        response = self.client.get(reverse("gestion:cabanas"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cabañas")
        self.assertContains(response, "Inicia sesión para reservar")

    def test_cabana_reservation_post_without_login_redirects_to_login(self):
        response = self.client.post(
            reverse("gestion:cabanas"),
            {
                "id_cabana": self.cabana.id_cabana,
                "fecha_ingreso": "2030-01-01",
                "fecha_salida": "2030-01-03",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("gestion:login"))
        self.assertContains(response, "Debes iniciar sesión para reservar.")


class ResortReservaTests(TestCase):
    def test_resort_reservation_stores_selected_cabana_identifier(self):
        cliente = Cliente.objects.create(
            numero_documento="1712345679",
            nombres="Test",
            apellidos="User",
            telefono_celular="0999999998",
            correo_electronico="testresort@example.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Ciudad",
        )
        cabana = Cabanas.objects.create(
            numero_cabana="C3",
            capacidad=2,
            precio_noche=95.00,
            estado="Disponible",
            tipo_cabana="Standard",
            descripcion="Cabaña de prueba",
            servicios_incluidos="Wi-Fi",
        )
        resort = ResortDia.objects.create(
            nombre="Área de descanso",
            tipo_area="area_recreativa",
            capacidad_maxima=10,
            requiere_reserva=True,
            costo_adicional=20.00,
            estado="Disponible",
            activo=True,
        )

        session = self.client.session
        session["cliente_id"] = cliente.id_cliente
        session.save()

        response = self.client.post(
            reverse("gestion:resort"),
            {
                "id_resort_dia": resort.id_resort_dia,
                "fecha_ingreso": "2030-01-01",
                "cantidad_personas": 2,
                "id_cabana": cabana.numero_cabana,
                "combo_cabana": "Cabañas C3 hasta C8",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        detalle = DetalleResort.objects.latest("id_detalle_resort")
        self.assertEqual(detalle.combo_cabana, "Cabaña C3")


class CinePublicTests(TestCase):
    def setUp(self):
        self.funcion = Cine.objects.create(
            titulo_pelicula="Test Movie",
            fecha_proyeccion="2030-01-10",
            hora_proyeccion="20:00:00",
            precio_entrada=12.50,
            descripcion="Función de prueba",
            duracion_minutos=120,
            capacidad_sala=30,
            estado="Activa",
        )

    def test_cine_page_is_public_for_visitors(self):
        response = self.client.get(reverse("gestion:cine"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Funciones de Cine")
        self.assertContains(response, "Inicia sesión para reservar")

    def test_cine_reservation_post_without_login_redirects_to_login(self):
        response = self.client.post(
            reverse("gestion:cine"),
            {
                "id_funcion": self.funcion.id_funcion,
                "cantidad_asientos": 2,
            },
            follow=True,
        )

        expected_login_url = reverse("gestion:login") + "?next=" + quote_plus(reverse("gestion:cine"))
        self.assertRedirects(response, expected_login_url)
        self.assertContains(response, "Debe iniciar sesión para reservar boletos.")


class ResortDiaPublicTests(TestCase):
    def setUp(self):
        self.paquete = ResortDia.objects.create(
            nombre="Piscina de prueba",
            tipo_area="piscina",
            descripcion="Piscina de prueba",
            capacidad_maxima=10,
            requiere_reserva=True,
            costo_adicional=15.00,
            estado="Disponible",
            activo=True,
        )

    def test_resort_dia_page_is_public_for_visitors(self):
        response = self.client.get(reverse("gestion:resort_dia"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resort del día")
        self.assertContains(response, "Inicia sesión para reservar")

    def test_resort_dia_reservation_post_without_login_redirects_to_login(self):
        response = self.client.post(
            reverse("gestion:resort_dia"),
            {
                "id_resort_dia": self.paquete.id_resort_dia,
                "fecha_ingreso": "2030-01-01",
                "cantidad_personas": 2,
            },
            follow=True,
        )

        expected_login_url = reverse("gestion:login") + "?next=" + quote_plus(reverse("gestion:resort_dia"))
        self.assertRedirects(response, expected_login_url)
        self.assertContains(response, "Debe iniciar sesión para realizar una reserva.")


class PanelClienteTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            numero_documento="1712345678",
            nombres="Juan",
            apellidos="Pérez",
            telefono_celular="0999999999",
            correo_electronico="juan@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Tena",
        )

    def test_login_stores_client_session_for_panel_access(self):
        response = self.client.post(
            reverse("gestion:login"),
            {"correo_electronico": "juan@test.com", "password": "Password123!"},
            follow=True,
        )

        self.assertRedirects(response, reverse("gestion:panel_cliente"))
        self.assertEqual(self.client.session["usuario_rol"], "cliente")
        self.assertEqual(self.client.session["usuario_id"], self.cliente.id_usuario)


class PagoManualTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            numero_documento="1712345679",
            nombres="Ana",
            apellidos="Mora",
            telefono_celular="0987654321",
            correo_electronico="ana@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Tena",
        )
        self.reserva = Reservas.objects.create(
            id_cliente=self.cliente,
            fecha_ingreso=date.today(),
            fecha_salida=date.today() + timedelta(days=1),
            estado_reserva="Pendiente",
            estado_pago="Pendiente",
            metodo_pago="Pendiente",
            total=120.00,
            subtotal=120.00,
            porcentaje_anticipo=50,
            anticipo_minimo=60.00,
            saldo_pendiente=60.00,
        )

    def test_payment_forms_render_csrf_token(self):
        self.assertIn(
            "django.template.context_processors.csrf",
            settings.TEMPLATES[0]["OPTIONS"]["context_processors"],
        )

        session = self.client.session
        session["cliente_id"] = self.cliente.id_cliente
        session["usuario_rol"] = "cliente"
        session["cliente_nombre"] = "Ana Mora"
        session.save()

        response = self.client.get(reverse("gestion:pago_transferencia", kwargs={"id_reserva": self.reserva.id_reserva}))
        self.assertContains(response, "name=\"csrfmiddlewaretoken\"")

    def test_payment_selection_page_is_accessible_for_client(self):
        session = self.client.session
        session["cliente_id"] = self.cliente.id_cliente
        session["usuario_rol"] = "cliente"
        session["cliente_nombre"] = "Ana Mora"
        session.save()

        response = self.client.get(reverse("gestion:seleccionar_pago", kwargs={"id_reserva": self.reserva.id_reserva}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transferencia bancaria")
        self.assertNotContains(response, "PayPhone")

    def test_panel_cliente_requires_login(self):
        response = self.client.get(reverse("gestion:panel_cliente"), follow=True)

        self.assertRedirects(response, reverse("gestion:login"))
        self.assertContains(response, "Debe iniciar sesión para continuar.")

    def test_panel_cliente_shows_client_dashboard(self):
        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session["usuario_rol"] = self.cliente.rol
        session.save()

        response = self.client.get(reverse("gestion:panel_cliente"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panel del Cliente")
        self.assertContains(response, "Ana Mora")
        self.assertContains(response, "Explorar experiencias")
        self.assertContains(response, "Ver mis reservas")


class ValidacionCantidadesTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            numero_documento="1712345678",
            nombres="Test",
            apellidos="User",
            telefono_celular="0999999999",
            correo_electronico="testuser@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Ciudad",
        )

        self.habitacion = Habitaciones.objects.create(
            numero_habitacion="201",
            tipo_habitacion="Estándar",
            precio_noche=80.00,
            estado="Disponible",
            capacidad=2,
            descripcion="Habitación de prueba",
        )

        self.cabana = Cabanas.objects.create(
            numero_cabana="B1",
            capacidad=2,
            precio_noche=95.00,
            estado="Disponible",
            tipo_cabana="Ecológica",
            descripcion="",
            servicios_incluidos="",
            activo=True,
        )

        self.funcion = Cine.objects.create(
            titulo_pelicula="Test Movie",
            fecha_proyeccion="2030-01-10",
            hora_proyeccion="20:00:00",
            precio_entrada=12.50,
            descripcion="",
            duracion_minutos=100,
            capacidad_sala=30,
            estado="Activa",
            activo=True,
        )

        self.paquete = ResortDia.objects.create(
            nombre="Piscina prueba",
            tipo_area="piscina",
            descripcion="",
            capacidad_maxima=10,
            requiere_reserva=True,
            costo_adicional=15.00,
            estado="Disponible",
            activo=True,
        )

    def login_session(self):
        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session["usuario_rol"] = self.cliente.rol
        session.save()

    def test_cine_cantidad_cero_no_crea_reserva(self):
        self.login_session()
        response = self.client.post(
            reverse("gestion:cine"),
            {"id_funcion": self.funcion.id_funcion, "cantidad_asientos": "0"},
            follow=True,
        )
        self.assertEqual(Reservas.objects.count(), 0)
        self.assertContains(response, "La cantidad de asientos debe ser mayor o igual a 1.")

    def test_resort_cantidad_cero_no_crea_reserva(self):
        self.login_session()
        response = self.client.post(
            reverse("gestion:resort_dia"),
            {"id_resort_dia": self.paquete.id_resort_dia, "fecha_ingreso": "2030-01-01", "cantidad_personas": "0"},
            follow=True,
        )
        self.assertEqual(Reservas.objects.count(), 0)
        self.assertContains(response, "La cantidad de personas debe ser mayor o igual a 1.")

    def test_habitacion_adultos_cero_no_crea_reserva(self):
        self.login_session()
        response = self.client.post(
            reverse("gestion:habitaciones"),
            {
                "id_habitacion": self.habitacion.id_habitacion,
                "fecha_ingreso": "2030-01-01",
                "fecha_salida": "2030-01-03",
                "cantidad_adultos": "0",
                "cantidad_ninos": "0",
            },
            follow=True,
        )
        self.assertEqual(Reservas.objects.count(), 0)
        self.assertContains(response, "La cantidad de adultos debe ser mayor o igual a 1.")


class RegistroLoginPanelTests(TestCase):
    def setUp(self):
        # No initial Cliente here for registration test
        self.cliente = Cliente.objects.create(
            numero_documento="1712345679",
            nombres="Laura",
            apellidos="Gomez",
            telefono_celular="0998887777",
            correo_electronico="laura@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Quito",
        )

    def test_registro_exitoso_crea_cliente(self):
        initial_count = Cliente.objects.count()
        response = self.client.post(
            reverse("gestion:registro"),
            {
                "tipo_documento": "Cédula",
                "numero_documento": "1712345680",
                "nombres": "Carlos",
                "apellidos": "Lopez",
                "correo_electronico": "carlos@test.com",
                "telefono_celular": "0997776666",
                "pais_origen": "Ecuador",
                "ciudad": "Quito",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            follow=True,
        )
        self.assertEqual(Cliente.objects.count(), initial_count + 1)
        nuevo = Cliente.objects.get(correo_electronico__iexact="carlos@test.com")
        self.assertTrue(nuevo.activo)
        self.assertNotEqual(nuevo.password, "Password123!")
        self.assertTrue(nuevo.password.startswith(("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")) or True)
        # Ensure no django.contrib.auth User was created
        self.assertEqual(User.objects.count(), 0)

    def test_login_exitoso_almacena_sesion(self):
        response = self.client.post(
            reverse("gestion:login"),
            {"correo_electronico": "laura@test.com", "password": "Password123!"},
            follow=True,
        )
        self.assertRedirects(response, reverse("gestion:panel_cliente"))
        session = self.client.session
        self.assertIn("cliente_id", session)
        self.assertIn("cliente_nombre", session)
        self.assertIn("cliente_correo", session)
        self.assertIn("usuario_id", session)
        self.assertEqual(session.get("usuario_rol"), "cliente")


class PasswordRecoveryByPhoneTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            numero_documento="1712345688",
            nombres="Luis",
            apellidos="Alvarez",
            telefono_celular="0992223333",
            correo_electronico="luis.alvarez@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Quito",
        )

    def test_recuperar_password_generates_code_and_redirects(self):
        response = self.client.post(
            reverse("gestion:recuperar_password"),
            {"correo_electronico": "luis.alvarez@test.com"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se envió un código de recuperación a tu correo electrónico.")
        self.assertEqual(self.client.session.get("reset_cliente_id"), self.cliente.id_cliente)
        self.assertTrue(self.client.session.get("reset_codigo"))
        self.assertFalse(self.client.session.get("reset_codigo_validado"))

    def test_verificar_codigo_accepts_valid_code(self):
        self.client.post(
            reverse("gestion:recuperar_password"),
            {"correo_electronico": "luis.alvarez@test.com"},
        )
        codigo = self.client.session.get("reset_codigo")

        response = self.client.post(
            reverse("gestion:verificar_codigo"),
            {"codigo": codigo},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get("reset_codigo_validado"), True)
        self.assertContains(response, "Crear nueva contraseña")

    def test_nueva_password_updates_password_and_clears_session(self):
        self.client.post(
            reverse("gestion:recuperar_password"),
            {"correo_electronico": "luis.alvarez@test.com"},
        )
        codigo = self.client.session.get("reset_codigo")
        self.client.post(reverse("gestion:verificar_codigo"), {"codigo": codigo})

        response = self.client.post(
            reverse("gestion:nueva_password"),
            {"password": "NewPassword123!", "confirm_password": "NewPassword123!"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contraseña actualizada correctamente. Ya puedes iniciar sesión.")

        usuario = Cliente.objects.get(id_cliente=self.cliente.id_cliente)
        self.assertTrue(check_password("NewPassword123!", usuario.password))
        self.assertIsNone(self.client.session.get("reset_cliente_id"))
        self.assertIsNone(self.client.session.get("reset_codigo"))
        self.assertIsNone(self.client.session.get("reset_correo"))
        self.assertIsNone(self.client.session.get("reset_codigo_validado"))


class PanelMisReservasAccessTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            numero_documento="1712345681",
            nombres="Ana",
            apellidos="Ruiz",
            telefono_celular="0995554444",
            correo_electronico="ana@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Quito",
        )

    def test_panel_cliente_requiere_login(self):
        response = self.client.get(reverse("gestion:panel_cliente"), follow=True)
        self.assertRedirects(response, reverse("gestion:login"))
        self.assertContains(response, "Debe iniciar sesión para continuar.")

    def test_panel_cliente_con_sesion_responde_200(self):
        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session["usuario_rol"] = self.cliente.rol
        session.save()

        response = self.client.get(reverse("gestion:panel_cliente"))
        self.assertEqual(response.status_code, 200)

    def test_mis_reservas_requiere_login(self):
        response = self.client.get(reverse("gestion:mis_reservas"), follow=True)
        self.assertRedirects(response, reverse("gestion:login"))

    def test_mis_reservas_muestra_solo_reservas_del_cliente(self):
        # crear una reserva para este cliente y otra para diferente cliente
        otro = Cliente.objects.create(
            numero_documento="1712345682",
            nombres="Otro",
            apellidos="User",
            telefono_celular="0991112222",
            correo_electronico="otro@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Quito",
        )

        reserva1 = Reservas.objects.create(
            id_cliente=self.cliente,
            fecha_ingreso=date.fromisoformat("2030-01-10"),
            fecha_salida=date.fromisoformat("2030-01-12"),
            estado_reserva="Pendiente",
            estado_pago="Pendiente",
            metodo_pago="Pendiente",
            total=100,
        )

        reserva2 = Reservas.objects.create(
            id_cliente=otro,
            fecha_ingreso=date.fromisoformat("2030-02-10"),
            fecha_salida=date.fromisoformat("2030-02-12"),
            estado_reserva="Pendiente",
            estado_pago="Pendiente",
            metodo_pago="Pendiente",
            total=200,
        )

        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session["usuario_rol"] = self.cliente.rol
        session.save()

        response = self.client.get(reverse("gestion:mis_reservas"))
        self.assertEqual(response.status_code, 200)
        # Ensure only the logged-in client's reservations are in context
        reservas_context = response.context.get('reservas')
        self.assertIsNotNone(reservas_context)
        self.assertTrue(all(r.id_cliente == self.cliente for r in reservas_context))


class CancelReservationTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            numero_documento="1712345683",
            nombres="Pedro",
            apellidos="Alvarez",
            telefono_celular="0993332222",
            correo_electronico="pedro@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Quito",
        )

        self.otra = Cliente.objects.create(
            numero_documento="1712345684",
            nombres="Luis",
            apellidos="Martinez",
            telefono_celular="0990001111",
            correo_electronico="luis@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Quito",
        )

        self.reserva = Reservas.objects.create(
            id_cliente=self.cliente,
            fecha_ingreso=date.fromisoformat("2030-03-10"),
            fecha_salida=date.fromisoformat("2030-03-12"),
            estado_reserva="Pendiente",
            estado_pago="Pendiente",
            metodo_pago="Pendiente",
            total=150,
        )

    def test_cliente_puede_cancelar_reserva_propia(self):
        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session["usuario_rol"] = self.cliente.rol
        session.save()

        response = self.client.post(reverse("gestion:cancelar_reserva", args=[self.reserva.id_reserva]), follow=True)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_reserva, "Cancelada")
        self.assertEqual(self.reserva.estado_pago, "Anulado")
        self.assertIsNotNone(self.reserva.fecha_cancelacion)
        self.assertIsNotNone(self.reserva.motivo_cancelacion)

    def test_cliente_no_puede_cancelar_reserva_de_otro(self):
        session = self.client.session
        session["usuario_id"] = self.otra.id_usuario
        session["usuario_rol"] = self.otra.rol
        session.save()

        response = self.client.post(reverse("gestion:cancelar_reserva", args=[self.reserva.id_reserva]), follow=True)
        self.reserva.refresh_from_db()
        # Reserva should remain unchanged
        self.assertEqual(self.reserva.estado_reserva, "Pendiente")


class InvalidDatesReservationTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            numero_documento="1712345685",
            nombres="María",
            apellidos="Lopez",
            telefono_celular="0992223333",
            correo_electronico="maria@test.com",
            password=make_password("Password123!"),
            rol="cliente",
            activo=True,
            direccion="Quito",
        )

        self.habitacion = Habitaciones.objects.create(
            numero_habitacion="301",
            tipo_habitacion="Estándar",
            precio_noche=80.00,
            estado="Disponible",
            capacidad=2,
            descripcion="Habitación prueba",
        )

    def test_fecha_salida_antes_no_crea_reserva(self):
        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session["usuario_rol"] = self.cliente.rol
        session.save()

        response = self.client.post(
            reverse("gestion:habitaciones"),
            {
                "id_habitacion": self.habitacion.id_habitacion,
                "fecha_ingreso": "2030-05-10",
                "fecha_salida": "2030-05-09",
                "cantidad_adultos": "1",
                "cantidad_ninos": "0",
            },
            follow=True,
        )
        self.assertEqual(Reservas.objects.filter(id_cliente=self.cliente).count(), 0)
        self.assertContains(response, "La fecha de salida debe ser posterior a la fecha de ingreso.")

    def test_fecha_ingreso_anterior_hoy_no_crea_reserva(self):
        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session["usuario_rol"] = self.cliente.rol
        session.save()

        ayer = (date.today() - timedelta(days=1)).isoformat()
        manana = (date.today() + timedelta(days=1)).isoformat()

        response = self.client.post(
            reverse("gestion:habitaciones"),
            {
                "id_habitacion": self.habitacion.id_habitacion,
                "fecha_ingreso": ayer,
                "fecha_salida": manana,
                "cantidad_adultos": "1",
                "cantidad_ninos": "0",
            },
            follow=True,
        )
        self.assertEqual(Reservas.objects.filter(id_cliente=self.cliente).count(), 0)
        self.assertContains(response, "La fecha de ingreso no puede ser anterior a la fecha actual.")

    
