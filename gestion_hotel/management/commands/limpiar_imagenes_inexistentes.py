"""Limpia y repara referencias a imagenes que ya no existen en el storage configurado."""

import os
import re

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    """Revisa registros con imagen y repara o limpia la referencia cuando falta el archivo."""

    help = "Revisa y repara referencias a imagenes en todos los modelos hoteleros, limpiando o reasignando segun disponibilidad."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar-todo",
            action="store_true",
            help="Si una imagen no existe y no tiene equivalente base, borra la referencia.",
        )

    def handle(self, *args, **options):
        """Revisa imagenes referenciadas, busca equivalentes base si hubo sufijo Django o limpia si corresponde."""

        total_revisado = 0
        imagenes_reparadas = 0
        imagenes_limpiadas = 0

        hotel_app = apps.get_app_config("gestion_hotel")

        for model in hotel_app.get_models():
            image_fields = [
                field for field in model._meta.get_fields()
                if isinstance(field, models.FileField)
            ]
            if not image_fields:
                continue

            for field in image_fields:
                campo_nombre = field.name
                queryset = model.objects.exclude(**{campo_nombre: ""}).exclude(**{campo_nombre + "__isnull": True})
                total_revisado += queryset.count()

                for registro in queryset:
                    archivo_field = getattr(registro, campo_nombre)
                    if not archivo_field or not archivo_field.name:
                        continue

                    nombre_archivo = archivo_field.name
                    if default_storage.exists(nombre_archivo):
                        continue

                    # Intenta buscar el archivo base sin el hash aleatorio de Django (ej: 1_ma0sjlY.jpg -> 1.jpg)
                    directorio = os.path.dirname(nombre_archivo)
                    archivo_base = os.path.basename(nombre_archivo)
                    nombre_curado = re.sub(r"_[A-Za-z0-9_-]{7,8}\.([a-zA-Z0-9]+)$", r".\1", archivo_base)
                    candidato = os.path.join(directorio, nombre_curado) if directorio else nombre_curado

                    if default_storage.exists(candidato):
                        setattr(registro, campo_nombre, candidato)
                        registro.save(update_fields=[campo_nombre])
                        imagenes_reparadas += 1
                        self.stdout.write(self.style.SUCCESS(
                            f"[{model.__name__} pk={registro.pk}] Reparado {campo_nombre}: {nombre_archivo} -> {candidato}"
                        ))
                    elif options.get("limpiar_todo"):
                        setattr(registro, campo_nombre, None)
                        registro.save(update_fields=[campo_nombre])
                        imagenes_limpiadas += 1
                        self.stdout.write(self.style.WARNING(
                            f"[{model.__name__} pk={registro.pk}] Limpiado {campo_nombre}: archivo ausente {nombre_archivo}"
                        ))

        self.stdout.write(self.style.SUCCESS(
            f"Proceso finalizado: {total_revisado} campos revisados. "
            f"{imagenes_reparadas} reparadas, {imagenes_limpiadas} limpiadas."
        ))

