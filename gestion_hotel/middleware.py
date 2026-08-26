"""Middleware reservado para reglas de navegacion entre admin y panel gerencial."""


class GerenteAdminRedirectMiddleware:
    """Punto de extension para redirecciones del gerente sin tocar las vistas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
