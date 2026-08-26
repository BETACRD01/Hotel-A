"""Registra servicios iniciales de resort dia para pruebas o carga base local."""

from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand

from gestion_hotel.models import ResortDia


class Command(BaseCommand):
    """Crea o actualiza paquetes de resort dia semilla por nombre."""

    help = 'Registra servicios iniciales de Resort del día para el Eco-Resort Arahuana.'

    def handle(self, *args, **kwargs):
        """Crea o actualiza servicios semilla de resort por nombre."""

        servicios = [
            {
                'nombre': 'Piscina Principal',
                'tipo_area': 'piscina',
                'capacidad_maxima': 50,
                'requiere_reserva': True,
                'costo_adicional': Decimal('5.00'),
                'estado': 'Disponible',
                'horario_apertura': time(9, 0),
                'horario_cierre': time(18, 0),
                'descripcion': 'Área de piscina para disfrutar durante el día en un ambiente natural.',
                'activo': True,
            },
            {
                'nombre': 'Área Recreativa Familiar',
                'tipo_area': 'area_recreativa',
                'capacidad_maxima': 30,
                'requiere_reserva': True,
                'costo_adicional': Decimal('3.00'),
                'estado': 'Disponible',
                'horario_apertura': time(9, 0),
                'horario_cierre': time(17, 0),
                'descripcion': 'Espacio ideal para compartir en familia con actividades de recreación.',
                'activo': True,
            },
            {
                'nombre': 'Zona de Descanso Natural',
                'tipo_area': 'otro',
                'capacidad_maxima': 20,
                'requiere_reserva': True,
                'costo_adicional': Decimal('4.00'),
                'estado': 'Disponible',
                'horario_apertura': time(10, 0),
                'horario_cierre': time(17, 0),
                'descripcion': 'Zona tranquila para relajarse y disfrutar del entorno amazónico.',
                'activo': True,
            },
        ]

        for servicio in servicios:
            obj, created = ResortDia.objects.update_or_create(
                nombre=servicio['nombre'],
                defaults=servicio,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Servicio {obj.nombre} creado.'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Servicio {obj.nombre} actualizado.'))

        self.stdout.write(self.style.SUCCESS('Servicios iniciales de Resort del día registrados correctamente.'))
