#!/usr/bin/env python
"""Entrada de comandos Django para ejecutar servidor, migraciones, tests y comandos propios."""
import os
import sys


def main():
    """Carga settings del proyecto y delega la ejecucion al CLI de Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arahuana_resort.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
