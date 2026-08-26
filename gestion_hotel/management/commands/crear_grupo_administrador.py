"""Crea el grupo operativo de administracion con permisos Django limitados."""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    """Sincroniza grupo, permisos y usuario administrador operativo."""

    help = 'Crea o actualiza el grupo Administrador Operativo con permisos operativos limitados y asigna al usuario administrador.'

    GROUP_NAME = 'Administrador Operativo'
    ADMIN_USERNAME = 'administrador'
    PERMISSIONS = [
        'view_habitaciones', 'add_habitaciones', 'change_habitaciones',
        'view_cabanas', 'add_cabanas', 'change_cabanas',
        'view_cine', 'add_cine', 'change_cine',
        'view_resortdia', 'add_resortdia', 'change_resortdia',
        'view_reservas', 'add_reservas', 'change_reservas',
        'view_detallehabitaciones', 'add_detallehabitaciones', 'change_detallehabitaciones',
        'view_detallecabanas', 'add_detallecabanas', 'change_detallecabanas',
        'view_detallecine', 'add_detallecine', 'change_detallecine',
        'view_detalleresort', 'add_detalleresort', 'change_detalleresort',
    ]

    def handle(self, *args, **options):
        """Crea o actualiza grupo, permisos y usuario operativo no superusuario."""

        user_model = get_user_model()
        group, created = Group.objects.get_or_create(name=self.GROUP_NAME)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Grupo creado: {self.GROUP_NAME}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Grupo existente encontrado: {self.GROUP_NAME}'))

        perms = Permission.objects.filter(
            content_type__app_label='gestion_hotel',
            codename__in=self.PERMISSIONS,
        ).order_by('codename')

        found_codenames = set(perms.values_list('codename', flat=True))
        missing = [codename for codename in self.PERMISSIONS if codename not in found_codenames]

        group.permissions.set(perms)
        total_assigned = perms.count()

        self.stdout.write(self.style.SUCCESS(f'Permisos asignados al grupo: {total_assigned}'))
        if missing:
            self.stdout.write(self.style.ERROR('Permisos no encontrados (revisar nombres de modelos o app_label):'))
            for codename in missing:
                self.stdout.write(f' - {codename}')
        else:
            self.stdout.write(self.style.SUCCESS('Todos los permisos indicados existen y fueron procesados.'))

        administrador, user_created = user_model.objects.get_or_create(username=self.ADMIN_USERNAME)
        administrador.is_active = True
        administrador.is_staff = True
        administrador.is_superuser = False
        administrador.save()
        administrador.groups.clear()
        administrador.groups.add(group)

        user_status = 'creado' if user_created else 'existente'
        self.stdout.write(self.style.SUCCESS(f'Usuario administrador {user_status}: {self.ADMIN_USERNAME}'))
        self.stdout.write(self.style.SUCCESS(f'Grupo asignado a {self.ADMIN_USERNAME}: {self.GROUP_NAME}'))

        assigned_permissions = group.permissions.order_by('content_type__app_label', 'codename')
        self.stdout.write(self.style.SUCCESS(f'Cantidad de permisos asignados al grupo: {assigned_permissions.count()}'))
        self.stdout.write('Lista de permisos asignados:')
        for perm in assigned_permissions:
            self.stdout.write(f' - {perm.content_type.app_label}.{perm.codename}')

        if user_created:
            self.stdout.write(self.style.WARNING(
                'El usuario administrador fue creado sin contraseña. Asigna una contraseña con el comando `python manage.py changepassword administrador`.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'El usuario administrador existente se actualizó para ser activo, staff y no superuser, y se le asignó solo el grupo Administrador Operativo.'
            ))
