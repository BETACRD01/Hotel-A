"""Middleware reservado para reglas de navegacion entre admin y panel gerencial."""


class GerenteAdminRedirectMiddleware:
    """Redirige al panel gerencial a usuarios gerente que entren a /admin/."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.is_staff
            and request.path.startswith("/admin/")
            and request.path != "/admin/logout/"
        ):
            from gestion_hotel.models import Cliente

            cliente = Cliente.objects.filter(
                correo_electronico__iexact=request.user.email,
                rol="gerente",
                activo=True,
            ).first()

            if cliente:
                from django.shortcuts import redirect
                return redirect("/gerente/")

        return self.get_response(request)
