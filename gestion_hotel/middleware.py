"""Middleware reservado para reglas de navegacion entre admin y panel gerencial."""


class GerenteAdminRedirectMiddleware:
    """Redirige al panel gerencial a usuarios staff que no son superusuarios."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.is_staff
            and not request.user.is_superuser
            and request.path.startswith("/admin/")
            and request.path != "/admin/logout/"
        ):
            from django.shortcuts import redirect
            return redirect("/gerente/")

        return self.get_response(request)
