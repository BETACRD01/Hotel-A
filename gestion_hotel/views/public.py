from .common import *
from .payments import obtener_metodo_pago_formulario, redirigir_segun_metodo_pago

def index(request):
    """
    Muestra la pÃ¡gina pÃºblica principal.
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
    PÃ¡gina pÃºblica 'Sobre nosotros'.
    """
    usuario = obtener_usuario_sesion(request)

    config = ConfiguracionInicio.objects.first()

    def valor(campo, defecto):
        return getattr(config, campo, None) or defecto if config else defecto

    contexto = {
        "usuario": usuario,
        "mision": valor("mision", (
            "Ofrecer experiencias memorables de descanso, recreaciÃ³n y contacto con la naturaleza "
            "en la AmazonÃ­a ecuatoriana, brindando un servicio cÃ¡lido, responsable y de calidad."
        )),
        "vision": valor("vision", (
            "Convertirnos en el eco-resort de referencia en la AmazonÃ­a ecuatoriana, reconocido por "
            "su hospitalidad, sostenibilidad y por ser el destino ideal para el bienestar y la autenticidad."
        )),
        "imagen_sobre_nosotros": (
            config.imagen_sobre_nosotros if config and config.imagen_sobre_nosotros else None
        ),
        "hero_titulo": valor("sn_hero_titulo", "Conoce la esencia de Arahuana"),
        "hero_parrafo": valor("sn_hero_parrafo", (
            "Somos mÃ¡s que un resort. Somos un espacio donde la naturaleza, "
            "el confort y la cultura se unen para ofrecer experiencias "
            "inolvidables en la AmazonÃ­a ecuatoriana."
        )),
        "stat_1_numero": valor("sn_stat_1_numero", "5+"),
        "stat_1_etiqueta": valor("sn_stat_1_etiqueta", "AÃ±os de experiencia"),
        "stat_2_numero": valor("sn_stat_2_numero", "Miles"),
        "stat_2_etiqueta": valor("sn_stat_2_etiqueta", "HuÃ©spedes felices"),
        "stat_3_numero": valor("sn_stat_3_numero", "4.8"),
        "stat_3_etiqueta": valor("sn_stat_3_etiqueta", "CalificaciÃ³n promedio"),
        "stat_4_numero": valor("sn_stat_4_numero", "Tena, Napo"),
        "stat_4_etiqueta": valor("sn_stat_4_etiqueta", "Ecuador"),
        "historia_titulo": valor("sn_historia_titulo", "Un lugar para reconectar con la naturaleza"),
        "historia_parrafo_1": valor("sn_historia_parrafo_1", (
            "Arahuana Eco-Resort & Spa naciÃ³ con el propÃ³sito de compartir "
            "la belleza de la AmazonÃ­a ecuatoriana, ofreciendo un lugar donde "
            "cada huÃ©sped pueda descansar, disfrutar y vivir experiencias memorables."
        )),
        "historia_parrafo_2": valor("sn_historia_parrafo_2", (
            "Nuestra propuesta combina hospedaje cÃ³modo, espacios recreativos, "
            "cine, cabaÃ±as y resort del dÃ­a en un entorno natural pensado para "
            "familias, parejas y visitantes."
        )),
        "historia_imagen": (
            config.sn_historia_imagen if config and config.sn_historia_imagen else None
        ),
        "valor_1_titulo": valor("sn_valor_1_titulo", "Sostenibilidad"),
        "valor_1_texto": valor("sn_valor_1_texto", (
            "Cuidamos nuestro entorno natural y promovemos una experiencia responsable."
        )),
        "valor_2_titulo": valor("sn_valor_2_titulo", "Hospitalidad"),
        "valor_2_texto": valor("sn_valor_2_texto", (
            "Brindamos atenciÃ³n cÃ¡lida, cercana y personalizada para cada huÃ©sped."
        )),
        "valor_3_titulo": valor("sn_valor_3_titulo", "Autenticidad"),
        "valor_3_texto": valor("sn_valor_3_texto", (
            "Resaltamos la cultura amazÃ³nica y la riqueza natural de nuestro entorno."
        )),
        "valor_4_titulo": valor("sn_valor_4_titulo", "Bienestar"),
        "valor_4_texto": valor("sn_valor_4_texto", (
            "Creamos experiencias que renuevan el cuerpo, la mente y el espÃ­ritu."
        )),
        "compromiso_titulo": valor("sn_compromiso_titulo", "Una experiencia pensada para ti"),
        "compromiso_parrafo": valor("sn_compromiso_parrafo", (
            "Trabajamos dÃ­a a dÃ­a para que cada visita sea especial, "
            "cuidando cada detalle del servicio y ofreciendo espacios seguros, "
            "cÃ³modos y conectados con la naturaleza."
        )),
        "compromiso_imagen": (
            config.sn_compromiso_imagen if config and config.sn_compromiso_imagen else None
        ),
        "cta_titulo": valor("sn_cta_titulo", "Vive la experiencia de la AmazonÃ­a"),
        "cta_parrafo": valor("sn_cta_parrafo", (
            "Reserva tu prÃ³xima visita y disfruta descanso, naturaleza "
            "y bienestar en un solo lugar."
        )),
    }

    return render(request, "public/sobre_nosotros.html", contexto)


# ============================================================
# AUTENTICACIÃ“N
# ============================================================
