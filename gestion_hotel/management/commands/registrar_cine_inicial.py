"""Registra funciones iniciales de cine para pruebas o carga base local."""

from datetime import date, timedelta, time
from decimal import Decimal

from django.core.management.base import BaseCommand

from gestion_hotel.models import Cine


class Command(BaseCommand):
    """Crea o actualiza funciones de cine semilla por titulo."""

    help = "Registra funciones iniciales de cine del Hotel Arahuana"

    def handle(self, *args, **kwargs):
        """Crea o actualiza funciones semilla con fechas relativas al dia actual."""

        funciones = [
            {
                "titulo_pelicula": "Cine Bajo Las Estrellas: El Libro de la Selva",
                "fecha_proyeccion": date.today() + timedelta(days=2),
                "hora_proyeccion": time(20, 0),
                "duracion_minutos": 120,
                # Modelo exige precio >= 0.01
                "precio_entrada": Decimal("0.01"),
                "capacidad_sala": 45,
                "estado": "Activa",
                "activo": True,
                "descripcion": "Disfruta de una noche mágica en nuestro teatro/cine interactivo rodeado de los sonidos naturales de la Amazonía.",
            },
            {
                "titulo_pelicula": "Cine Familiar: Encanto",
                "fecha_proyeccion": date.today() + timedelta(days=3),
                "hora_proyeccion": time(17, 0),
                "duracion_minutos": 110,
                "precio_entrada": Decimal("3.50"),
                "capacidad_sala": 40,
                "estado": "Activa",
                "activo": True,
                "descripcion": "Función familiar animada ideal para niños y adultos durante la estadía en el hotel.",
            },
            {
                "titulo_pelicula": "Noche de Aventura: Jurassic World",
                "fecha_proyeccion": date.today() + timedelta(days=4),
                "hora_proyeccion": time(20, 30),
                "duracion_minutos": 130,
                "precio_entrada": Decimal("4.50"),
                "capacidad_sala": 50,
                "estado": "Activa",
                "activo": True,
                "descripcion": "Película de aventura para disfrutar una noche diferente dentro del Hotel Arahuana.",
            },
        ]

        for funcion in funciones:
            obj, created = Cine.objects.update_or_create(
                titulo_pelicula=funcion["titulo_pelicula"],
                defaults=funcion,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ Función {obj.titulo_pelicula} creada."))
            else:
                self.stdout.write(self.style.SUCCESS(f"✓ Función {obj.titulo_pelicula} actualizada."))

        self.stdout.write(self.style.SUCCESS("Funciones iniciales de cine registradas correctamente."))
