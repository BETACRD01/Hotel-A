"""Comando para cancelar reservas que excedieron el plazo de pago."""

from django.core.management.base import BaseCommand

from gestion_hotel.services.reservations import cancelar_reservas_vencidas


class Command(BaseCommand):
    """Expone el servicio de cancelacion automatica como comando manage.py."""

    help = "Cancela las reservas no pagadas cuyo plazo de pago (fecha_limite_pago) ya venció."

    def handle(self, *args, **options):
        """Ejecuta la cancelacion y muestra el total afectado."""

        total = cancelar_reservas_vencidas()
        self.stdout.write(self.style.SUCCESS(
            f"Reservas vencidas canceladas: {total}."
        ))
