"""Carga tarifas base de habitaciones y cabanas segun reglas comerciales actuales."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from gestion_hotel.models import Habitaciones, Cabanas


def d(valor):
    """Normaliza importes de configuracion a Decimal con dos posiciones."""

    return Decimal(str(valor)).quantize(Decimal("0.01"))


PRECIOS_HABITACIONES = {
    "jr_suite_doble": {
        "tipo_ocupacion_secundaria": "Sencilla",
        "precio_2d1n_total": d("169.00"),
        "precio_2d1n_secundaria": d("129.00"),
        "precio_3d2n_total": d("321.10"),
        "precio_3d2n_secundaria": d("245.10"),
        "precio_4d3n_total": d("464.75"),
        "precio_4d3n_secundaria": d("354.75"),
    },
    "jr_suite_cuadruple": {
        "tipo_ocupacion_secundaria": "Doble",
        "precio_2d1n_total": d("229.00"),
        "precio_2d1n_secundaria": d("198.00"),
        "precio_3d2n_total": d("435.10"),
        "precio_3d2n_secundaria": d("376.20"),
        "precio_4d3n_total": d("629.75"),
        "precio_4d3n_secundaria": d("544.50"),
    },
}

PRECIOS_CABANAS = {
    "suite": {
        "tipo_ocupacion_secundaria": "Sencilla",
        "precio_2d1n_total": d("219.00"),
        "precio_2d1n_secundaria": d("169.00"),
        "precio_3d2n_total": d("416.10"),
        "precio_3d2n_secundaria": d("321.10"),
        "precio_4d3n_total": d("602.25"),
        "precio_4d3n_secundaria": d("464.75"),
    },
    "standard": {
        "tipo_ocupacion_secundaria": "Sencilla",
        "precio_2d1n_total": d("259.00"),
        "precio_2d1n_secundaria": d("219.00"),
        "precio_3d2n_total": d("492.10"),
        "precio_3d2n_secundaria": d("416.10"),
        "precio_4d3n_total": d("712.25"),
        "precio_4d3n_secundaria": d("602.25"),
    },
    "family": {
        "tipo_ocupacion_secundaria": "Sencilla",
        "precio_2d1n_total": d("329.00"),
        "precio_2d1n_secundaria": d("297.00"),
        "precio_3d2n_total": d("625.10"),
        "precio_3d2n_secundaria": d("564.30"),
        "precio_4d3n_total": d("904.75"),
        "precio_4d3n_secundaria": d("816.75"),
    },
}


def aplicar_precios(objeto, precios):
    """Aplica el bloque de precios a una habitacion o cabana y guarda el registro."""

    objeto.tipo_ocupacion_secundaria = precios["tipo_ocupacion_secundaria"]

    objeto.precio_2d1n_total = precios["precio_2d1n_total"]
    objeto.precio_2d1n_secundaria = precios["precio_2d1n_secundaria"]

    objeto.precio_3d2n_total = precios["precio_3d2n_total"]
    objeto.precio_3d2n_secundaria = precios["precio_3d2n_secundaria"]

    objeto.precio_4d3n_total = precios["precio_4d3n_total"]
    objeto.precio_4d3n_secundaria = precios["precio_4d3n_secundaria"]

    objeto.precio_noche = precios["precio_2d1n_secundaria"]

    objeto.save()


class Command(BaseCommand):
    """Actualiza tarifas de inventario existente sin crear habitaciones ni cabanas nuevas."""

    help = "Carga los precios oficiales de Arahuana directamente en Habitaciones y Cabañas."

    def handle(self, *args, **options):
        """Recorre inventario existente, clasifica cada registro y actualiza tarifas."""

        habitaciones_actualizadas = 0
        cabanas_actualizadas = 0

        for habitacion in Habitaciones.objects.all():
            texto = f"{habitacion.tipo_habitacion} {habitacion.numero_habitacion}".lower()

            if "cuad" in texto or habitacion.capacidad >= 4:
                aplicar_precios(habitacion, PRECIOS_HABITACIONES["jr_suite_cuadruple"])
                habitaciones_actualizadas += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Habitación {habitacion.numero_habitacion}: precios Jr. Suite Cuádruple cargados."
                    )
                )
            else:
                aplicar_precios(habitacion, PRECIOS_HABITACIONES["jr_suite_doble"])
                habitaciones_actualizadas += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Habitación {habitacion.numero_habitacion}: precios Jr. Suite Doble cargados."
                    )
                )

        for cabana in Cabanas.objects.all():
            texto = f"{cabana.tipo_cabana} {cabana.numero_cabana}".lower()

            if "family" in texto or "familiar" in texto or cabana.capacidad >= 5:
                aplicar_precios(cabana, PRECIOS_CABANAS["family"])
                cabanas_actualizadas += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Cabaña {cabana.numero_cabana}: precios Cabaña Family cargados."
                    )
                )

            elif "standard" in texto or "estandar" in texto or cabana.capacidad >= 4:
                aplicar_precios(cabana, PRECIOS_CABANAS["standard"])
                cabanas_actualizadas += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Cabaña {cabana.numero_cabana}: precios Cabaña Standard cargados."
                    )
                )

            else:
                aplicar_precios(cabana, PRECIOS_CABANAS["suite"])
                cabanas_actualizadas += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Cabaña {cabana.numero_cabana}: precios Cabaña Suite cargados."
                    )
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Carga de precios finalizada correctamente."))
        self.stdout.write(f"Habitaciones actualizadas: {habitaciones_actualizadas}")
        self.stdout.write(f"Cabañas actualizadas: {cabanas_actualizadas}")
