from .models import ConfiguracionInicio

def configuracion_sitio_context(request):
    """
    Context processor para proveer los colores, fuentes y configuración
    del sitio en todas las plantillas automáticamente.
    """
    config = ConfiguracionInicio.objects.first()
    return {
        'config_sitio': config,
    }
