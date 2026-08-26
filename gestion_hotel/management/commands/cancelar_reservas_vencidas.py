from django.core.management.base import BaseCommand

from gestion_hotel.views import cancelar_reservas_vencidas


class Command(BaseCommand):
    help = "Cancela las reservas no pagadas cuyo plazo de pago (fecha_limite_pago) ya venció."

    def handle(self, *args, **options):
        total = cancelar_reservas_vencidas()
        self.stdout.write(self.style.SUCCESS(
            f"Reservas vencidas canceladas: {total}."
        ))
