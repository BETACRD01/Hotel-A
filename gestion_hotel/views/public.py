"""Vistas publicas generales que no crean reservas."""

from .common import *
from .payments import obtener_metodo_pago_formulario, redirigir_segun_metodo_pago

def index(request):
    """
    Muestra la página pública principal.
    """
    usuario = obtener_usuario_sesion(request)

    config = ConfiguracionInicio.objects.first()

    def primera_imagen(modelo):
        obj = modelo.objects.exclude(imagen=None).exclude(imagen="").first()
        return obj.imagen if obj else None

    return render(
        request,
        "public/index.html",
        {
            "usuario": usuario,
            "imagen_habitaciones": (config.imagen_habitaciones if config and config.imagen_habitaciones else primera_imagen(Habitaciones)),
            "imagen_cabanas": (config.imagen_cabanas if config and config.imagen_cabanas else primera_imagen(Cabanas)),
            "imagen_cine": (config.imagen_cine if config and config.imagen_cine else primera_imagen(Cine)),
            "imagen_resort": (config.imagen_resort if config and config.imagen_resort else primera_imagen(ResortDia)),
            "imagen_hero": (config.imagen_hero if config and config.imagen_hero else None),
        }
    )


def sobre_nosotros_view(request):
    """
    Página pública 'Sobre nosotros'.
    """
    usuario = obtener_usuario_sesion(request)

    config = ConfiguracionInicio.objects.first()

    def valor(campo, defecto):
        return getattr(config, campo, None) or defecto if config else defecto

    contexto = {
        "usuario": usuario,
        "hero_kicker": valor("sn_hero_kicker", "Sobre nosotros"),
        "hero_titulo": valor("sn_hero_titulo", "Conoce la esencia de Arahuana"),
        "hero_parrafo": valor("sn_hero_parrafo", (
            "Somos más que un resort. Somos un espacio donde la naturaleza, "
            "el confort y la cultura se unen para ofrecer experiencias "
            "inolvidables en la Amazonía ecuatoriana."
        )),
        "imagen_sobre_nosotros": (
            config.imagen_sobre_nosotros if config and config.imagen_sobre_nosotros else None
        ),
        "stat_1_numero": valor("sn_stat_1_numero", "5+"),
        "stat_1_etiqueta": valor("sn_stat_1_etiqueta", "Años de experiencia"),
        "stat_2_numero": valor("sn_stat_2_numero", "Miles"),
        "stat_2_etiqueta": valor("sn_stat_2_etiqueta", "Huéspedes felices"),
        "stat_3_numero": valor("sn_stat_3_numero", "4.8"),
        "stat_3_etiqueta": valor("sn_stat_3_etiqueta", "Calificación promedio"),
        "stat_4_numero": valor("sn_stat_4_numero", "Tena, Napo"),
        "stat_4_etiqueta": valor("sn_stat_4_etiqueta", "Ecuador"),
        "historia_kicker": valor("sn_historia_kicker", "Nuestra historia"),
        "historia_titulo": valor("sn_historia_titulo", "Un lugar para reconectar con la naturaleza"),
        "historia_parrafo_1": valor("sn_historia_parrafo_1", (
            "Arahuana Eco-Resort & Spa nació con el propósito de compartir "
            "la belleza de la Amazonía ecuatoriana, ofreciendo un lugar donde "
            "cada huésped pueda descansar, disfrutar y vivir experiencias memorables."
        )),
        "historia_parrafo_2": valor("sn_historia_parrafo_2", (
            "Nuestra propuesta combina hospedaje cómodo, espacios recreativos, "
            "cine, cabañas y resort del día en un entorno natural pensado para "
            "familias, parejas y visitantes."
        )),
        "historia_imagen": (
            config.sn_historia_imagen if config and config.sn_historia_imagen else None
        ),
        "mv_kicker": valor("sn_mv_kicker", "Misión y Visión"),
        "mv_titulo": valor("sn_mv_titulo", "Lo que nos impulsa"),
        "mv_subtitulo": valor("sn_mv_subtitulo", "Nuestros propósitos guían cada experiencia que compartimos contigo."),
        "mision": valor("mision", (
            "Ofrecer experiencias memorables de descanso, recreación y contacto con la naturaleza "
            "en la Amazonía ecuatoriana, brindando un servicio cálido, responsable y de calidad."
        )),
        "vision": valor("vision", (
            "Convertirnos en el eco-resort de referencia en la Amazonía ecuatoriana, reconocido por "
            "su hospitalidad, sostenibilidad y por ser el destino ideal para el bienestar y la autenticidad."
        )),
        "valores_kicker": valor("sn_valores_kicker", "Nuestros valores"),
        "valores_titulo": valor("sn_valores_titulo", "Lo que nos define"),
        "valores_subtitulo": valor("sn_valores_subtitulo", (
            "Trabajamos con principios que fortalecen la atención, "
            "la organización y la experiencia del visitante."
        )),
        "valor_1_titulo": valor("sn_valor_1_titulo", "Sostenibilidad"),
        "valor_1_texto": valor("sn_valor_1_texto", (
            "Cuidamos nuestro entorno natural y promovemos una experiencia responsable."
        )),
        "valor_2_titulo": valor("sn_valor_2_titulo", "Hospitalidad"),
        "valor_2_texto": valor("sn_valor_2_texto", (
            "Brindamos atención cálida, cercana y personalizada para cada huésped."
        )),
        "valor_3_titulo": valor("sn_valor_3_titulo", "Autenticidad"),
        "valor_3_texto": valor("sn_valor_3_texto", (
            "Resaltamos la cultura amazónica y la riqueza natural de nuestro entorno."
        )),
        "valor_4_titulo": valor("sn_valor_4_titulo", "Bienestar"),
        "valor_4_texto": valor("sn_valor_4_texto", (
            "Creamos experiencias que renuevan el cuerpo, la mente y el espíritu."
        )),
        "compromiso_kicker": valor("sn_compromiso_kicker", "Nuestro compromiso"),
        "compromiso_titulo": valor("sn_compromiso_titulo", "Una experiencia pensada para ti"),
        "compromiso_parrafo": valor("sn_compromiso_parrafo", (
            "Trabajamos día a día para que cada visita sea especial, "
            "cuidando cada detalle del servicio y ofreciendo espacios seguros, "
            "cómodos y conectados con la naturaleza."
        )),
        "compromiso_imagen": (
            config.sn_compromiso_imagen if config and config.sn_compromiso_imagen else None
        ),
        "cta_kicker": valor("sn_cta_kicker", "Arahuana te espera"),
        "cta_titulo": valor("sn_cta_titulo", "Vive la experiencia de la Amazonía"),
        "cta_parrafo": valor("sn_cta_parrafo", (
            "Reserva tu próxima visita y disfruta descanso, naturaleza "
            "y bienestar en un solo lugar."
        )),
    }

    return render(request, "public/sobre_nosotros.html", contexto)


# ============================================================
# AUTENTICACIÓN
# ============================================================
