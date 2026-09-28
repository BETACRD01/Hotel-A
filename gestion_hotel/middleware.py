"""Middleware reservado para reglas de navegacion entre admin y panel gerencial."""


class GerenteAdminRedirectMiddleware:
    """Redirige al panel gerencial exclusivamente a usuarios con rol gerente al entrar a /admin/."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.is_staff
            and request.path.startswith("/admin/")
            and request.path != "/admin/logout/"
        ):
            es_administrador = (
                request.user.is_superuser
                or request.user.username.lower() in {"admin", "administrador"}
                or request.user.groups.filter(name__icontains="admin").exists()
            )
            if not es_administrador:
                from django.shortcuts import redirect
                return redirect("/gerente/")

        return self.get_response(request)
