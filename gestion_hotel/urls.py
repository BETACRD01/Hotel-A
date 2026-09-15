"""Rutas de la app gestion_hotel para paginas publicas, cliente, pagos y gerente."""

from django.urls import path
from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.index, name="inicio"),

    # Autenticacion cliente
    path("login/", views.login_view, name="login"),
    path("login-staff/", views.login_staff_view, name="login_staff"),
    path("registro/", views.registro_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),

    # Recuperación de contraseña por código al correo
    path("recuperar-password/", views.recuperar_password, name="recuperar_password"),
    path("verificar-codigo/", views.verificar_codigo, name="verificar_codigo"),
    path("nueva-password/", views.nueva_password, name="nueva_password"),

    # Panel cliente
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("panel-cliente/", views.panel_cliente_view, name="panel_cliente"),
    path("mis-reservas/", views.mis_reservas_view, name="mis_reservas"),
    path("mis-reservas/cancelar/<int:id_reserva>/", views.cancelar_reserva_view, name="cancelar_reserva"),

    # Pagos manuales
    path("reservas/<int:id_reserva>/pago/", views.seleccionar_pago_view, name="seleccionar_pago"),
    path("reservas/<int:id_reserva>/pago/transferencia/", views.pago_transferencia_view, name="pago_transferencia"),

    # Páginas públicas
    path("habitaciones/", views.habitaciones_view, name="habitaciones"),
    path("cabanas/", views.cabanas_view, name="cabanas"),
    path("cine/", views.cine_view, name="cine"),
    path("resort-dia/", views.resort_dia_view, name="resort_dia"),
    path("resort/", views.resort_dia_view, name="resort"),
    path("sobre-nosotros/", views.sobre_nosotros_view, name="sobre_nosotros"),

    # Módulo Gerente
    path("gerente/", views.dashboard_gerente_view, name="gerente_dashboard"),
    path("gerente/reservas/", views.gerente_reservas_view, name="gerente_reservas"),
    path("gerente/habitaciones/", views.gerente_habitaciones_view, name="gerente_habitaciones"),
    path("gerente/cabanas/", views.gerente_cabanas_view, name="gerente_cabanas"),
    path("gerente/clientes/", views.gerente_clientes_view, name="gerente_clientes"),
    path("gerente/resort/", views.gerente_resort_view, name="gerente_resort"),
    path("gerente/cine/", views.gerente_cine_view, name="gerente_cine"),
    path("gerente/sobre-nosotros/", views.gerente_sobre_nosotros_view, name="gerente_sobre_nosotros"),
    path("gerente/informes/", views.gerente_informes_view, name="gerente_informes"),
    path("gerente/ocupacion/", views.gerente_ocupacion_view, name="gerente_ocupacion"),
    path("gerente/personal/", views.gerente_personal_view, name="gerente_personal"),
    path("gerente/comentarios/", views.gerente_comentarios_view, name="gerente_comentarios"),
    path("gerente/tarifas/", views.gerente_tarifas_view, name="gerente_tarifas"),
    path("gerente/<str:modulo>/nuevo/", views.gerente_form_modelo_view, name="gerente_modelo_nuevo"),
    path("gerente/<str:modulo>/<int:pk>/editar/", views.gerente_form_modelo_view, name="gerente_modelo_editar"),
]
