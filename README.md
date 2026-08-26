# Sistema Hotelero Arahuana

Sistema web para la gestión de clientes, habitaciones, cabañas, funciones de cine, resort del día y reservas del hotel Arahuana.

## Tecnologías
- Python
- Django
- PostgreSQL
- HTML, CSS y JavaScript
- Jazzmin
- Django REST Framework

## Requisitos
- Python 3.10 o superior
- PostgreSQL
- PowerShell en Windows

## INSTALACIÓN Y EJECUCIÓN EN WINDOWS

1. Abrir PowerShell en la carpeta del proyecto.

2. Crear el entorno virtual:

```powershell
python -m venv env
```

3. Activar el entorno virtual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\env\Scripts\Activate.ps1
```

4. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

5. Crear el archivo `.env` a partir de `.env.example`.

6. Verificar que el proyecto esté bien configurado:

```powershell
python manage.py check
```

7. Ejecutar el servidor:

```powershell
python manage.py runserver
```

8. Abrir el navegador en:

```text
http://127.0.0.1:8000/
```

## VARIABLES DEL ARCHIVO .env

El archivo `.env` debe contener estas variables:

```env
SECRET_KEY=tu_secret_key
DEBUG=True
DB_NAME=nombre_base_datos
DB_USER=usuario_postgresql
DB_PASSWORD=contraseña_postgresql
DB_HOST=localhost
DB_PORT=5432
```

No colocar contraseñas reales ni datos privados. Solo completar los valores correspondientes.

## ARCHIVOS QUE NO DEBEN INCLUIRSE EN LA ENTREGA

No se deben incluir en el ZIP final:

- `env/`
- `.venv/`
- `venv/`
- `.env`
- `__pycache__/`
- `*.pyc`
- `*.pyo`
- `*.log`
- `*.bak`
- `db.sqlite3`
- `*.sqlite3`
- `staticfiles/`
- `backups/`
- `*.zip antiguos`

Sí deben incluirse:

- `.env.example`
- `requirements.txt`
- `manage.py`
- `README.md`
- `arahuana_resort/`
- `gestion_hotel/`
- `media/`

## RUTAS PRINCIPALES

- Inicio: http://127.0.0.1:8000/
- Sobre nosotros: http://127.0.0.1:8000/sobre-nosotros/
- Habitaciones: http://127.0.0.1:8000/habitaciones/
- Cabañas: http://127.0.0.1:8000/cabanas/
- Cine: http://127.0.0.1:8000/cine/
- Resort del día: http://127.0.0.1:8000/resort/
- Login: http://127.0.0.1:8000/login/
- Registro: http://127.0.0.1:8000/registro/
- Panel cliente: http://127.0.0.1:8000/panel-cliente/
- Mis reservas: http://127.0.0.1:8000/mis-reservas/
- Panel administrativo: http://127.0.0.1:8000/admin/

## NOTA SOBRE POSTGRESQL

Este proyecto utiliza PostgreSQL. Antes de ejecutar el sistema, verificar que PostgreSQL esté iniciado y que la base de datos indicada en `.env` exista.

Si aparece el error:

```text
fe_sendauth: no password supplied
```

significa que falta configurar `DB_PASSWORD` en el archivo `.env`.

## Notas finales
- El proyecto está preparado para PostgreSQL y usa Jazzmin para el panel administrativo.
- La configuración sensible debe manejarse mediante variables de entorno.
