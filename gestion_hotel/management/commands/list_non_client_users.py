from django.core.management.base import BaseCommand
from gestion_hotel.models import Cliente


class Command(BaseCommand):
    help = 'Lista registros en gestion_hotel.Cliente cuyo rol no es cliente (solo lectura)'

    def handle(self, *args, **options):
        bad = Cliente.objects.filter(rol__in=['admin', 'gerente'])
        if not bad.exists():
            self.stdout.write(self.style.SUCCESS('No se encontraron registros con rol admin o gerente en gestion_hotel.Cliente'))
            return

        self.stdout.write(self.style.WARNING('Registros encontrados:'))
        for u in bad:
            self.stdout.write(f'- id={u.id_cliente} cedula={u.numero_documento} nombre={u.nombres} {u.apellidos} email={u.correo_electronico} rol={u.rol}')
        self.stdout.write(self.style.ERROR('Aviso: estos registros no permiten acceder al /admin/. Considere migrarlos manualmente a Django auth si son administradores del panel.'))
