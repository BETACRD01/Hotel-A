"""
Configuracion WSGI del proyecto Arahuana Resort.

Expone ``application`` para servidores compatibles con WSGI.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arahuana_resort.settings')

application = get_wsgi_application()
