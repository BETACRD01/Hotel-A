import os

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from gestion_hotel.models import Cabanas, Cine


class Command(BaseCommand):
    help = "Limpia los campos de imagen de cabañas y funciones de cine cuando el archivo físico no existe."

    def handle(self, *args, **options):
        total_revisado = 0
        imagenes_inexistentes = 0
        registros_corregidos = 0

        for modelo, nombre_modelo in ((Cabanas, "cabañas"), (Cine, "funciones de cine")):
            queryset = modelo.objects.exclude(imagen='').exclude(imagen__isnull=True)
            total_revisado += queryset.count()

            for registro in queryset:
                if not registro.imagen:
                    continue

                nombre_archivo = registro.imagen.name
                if not nombre_archivo:
                    continue

                if not default_storage.exists(nombre_archivo):
                    imagenes_inexistentes += 1
                    registro.imagen = None
                    registro.save(update_fields=["imagen"])
                    registros_corregidos += 1

        self.stdout.write(self.style.SUCCESS(
            f"Revisión finalizada: {total_revisado} registros revisados, {imagenes_inexistentes} imágenes inexistentes encontradas y {registros_corregidos} registros corregidos."
        ))
