# Sistema Hotelero Arahuana

Sistema web en Django para gestionar la operacion del hotel Arahuana Eco-Resort & Spa: clientes, habitaciones, cabanas, funciones de cine, resort del dia, reservas, pagos por transferencia y panel gerencial.

## Tecnologias

- Python
- Django
- PostgreSQL
- Django Jazzmin
- Django REST Framework
- HTML, CSS y JavaScript

## 📖 Manual del Sistema y Documentación

Para una explicación exhaustiva paso a paso de cada módulo, flujo de reservas, base de datos y comandos de despliegue, consulta el:
👉 **[MANUAL_DEL_SISTEMA.md](MANUAL_DEL_SISTEMA.md)**

### ¿Qué hace cada parte del sistema?

- **`arahuana_resort/` (Configuración central):** Controla la configuración global de Django (`settings.py`), conexiones a PostgreSQL, variables de entorno y enrutamiento principal de URLs (`urls.py`).
- **`gestion_hotel/models.py` (Base de datos):** Define las tablas del sistema:
  - `Cliente`: Registro de clientes, administradores y validación de Cédula/RUC.
  - `Habitaciones` y `Cabanas`: Inventario físico con precios por programa (2D1N, 3D2N, 4D3N), precios por noche y estado (`Disponible`, `Reservada`, `Mantenimiento`, `Inactiva`).
  - `Reservas`: Cabecera de la transacción con fechas, estados (`Pendiente`, `Confirmada`, `Cancelada`) y estados de pago (`Pendiente`, `En revision`, `Pagado`).
  - `DetalleHabitaciones` / `DetalleCabanas`: Fechas específicas de estancia por unidad, programa contratado y subtotal.
  - `PagoReserva`: Registro de transferencias bancarias y subida del comprobante.
- **`gestion_hotel/services/reservations.py` (Lógica de negocio):**
  - `resolver_programa_y_noches`: Interpreta programas estándar (2D1N, 3D2N, 4D3N) o personalizados escritos libremente por el usuario.
  - `calcular_precio_estadia`: Calcula la tarifa según el programa o la cantidad de noches.
  - `actualizar_estados_hospedaje`: **Sincronizador automático** que pasa a `'Reservada'` cualquier habitación o cabaña con reservas activas, y la regresa a `'Disponible'` cuando concluye o se cancela.
  - `cancelar_reservas_vencidas`: Tarea que cancela automáticamente reservas que superen 24 horas sin pago y libera las unidades.
- **`gestion_hotel/views/` (Controladores y vistas):**
  - `catalog.py`: Presenta los catálogos públicos y procesa reservas de habitaciones y cabañas, bloqueando solicitudes duplicadas o solapadas.
  - `reservations.py`: Panel "Mis Reservas" del cliente y cancelación con liberación inmediata de habitación.
  - `payments.py`: Formulario para registrar el comprobante de transferencia y enviarlo a revisión.
  - `gerente.py`: Panel gerencial para validar pagos, ver reportes e inventario.
  - `auth.py`: Autenticación, registro, login y restablecimiento de contraseña.
- **`gestion_hotel/templates/` y `static/` (Interfaz visual):**
  - Catálogo con insignias dinámicas (`status-disponible` en verde, `status-reservada` en rojo).
  - Bloqueo visual con botón desactivado `"No disponible"` para evitar reservas duplicadas.
  - Modal con `<input list="datalist">` para elegir o escribir libremente el programa de hospedaje.

## Modulos Funcionales

- Inicio publico y pagina Sobre nosotros
- Registro, login, logout y recuperacion de contrasena por codigo
- Panel del cliente
- Habitaciones
- Cabanas
- Cine
- Resort del dia
- Mis reservas y cancelacion
- Seleccion de metodo de pago
- Registro de comprobantes por transferencia
- Panel gerencial
- Panel administrativo Django/Jazzmin

## Requisitos

- Python 3.10 o superior
- PostgreSQL
- Git
- PowerShell en Windows

## Instalacion Local

1. Entrar a la carpeta del proyecto:

```powershell
cd "C:\Users\HP\OneDrive\Desktop\hotel v2 mac y wid\Hotel A"
```

2. Crear y activar entorno virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

4. Crear el archivo `.env` desde `.env.example`:

```powershell
Copy-Item .env.example .env
```

5. Editar `.env` con la configuracion real de base de datos, correo y cuentas bancarias.

6. Aplicar migraciones:

```powershell
python manage.py migrate
```

7. Crear superusuario si se necesita acceso al admin:

```powershell
python manage.py createsuperuser
```

8. Ejecutar el servidor:

```powershell
python manage.py runserver
```

9. Abrir:

```text
http://127.0.0.1:8000/
```

## Variables de Entorno

El proyecto lee configuracion sensible desde `.env`.

Variables principales:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

DB_NAME=hotel_arahuana_db
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

BANCO_1_NOMBRE=
BANCO_1_TIPO=
BANCO_1_CUENTA=
BANCO_1_TITULAR=
BANCO_1_IDENTIFICACION=
BANCO_1_CORREO=
```

No subir `.env` al repositorio. `.env.example` debe contener solo placeholders.

## Rutas Principales

- Inicio: `/`
- Sobre nosotros: `/sobre-nosotros/`
- Habitaciones: `/habitaciones/`
- Cabanas: `/cabanas/`
- Cine: `/cine/`
- Resort del dia: `/resort/`
- Login: `/login/`
- Registro: `/registro/`
- Panel cliente: `/panel-cliente/`
- Mis reservas: `/mis-reservas/`
- Pago por transferencia: `/reservas/<id>/pago/transferencia/`
- Panel gerente: `/gerente/`
- Admin Django: `/admin/`

## Comandos Utiles

Verificar configuracion:

```powershell
python manage.py check
```

Ejecutar pruebas:

```powershell
python manage.py test
```

Cancelar reservas vencidas:

```powershell
python manage.py cancelar_reservas_vencidas
```

Limpiar imagenes inexistentes:

```powershell
python manage.py limpiar_imagenes_inexistentes
```

## Estado de Tests

La suite de pruebas existe en `gestion_hotel/tests.py`. En la revision actual `python manage.py check` pasa correctamente.

La suite completa de tests tiene fallos conocidos previos relacionados con textos codificados y expectativas antiguas de redireccion. Conviene corregir esos tests antes de usarlos como garantia de regresion completa.

## Seguridad

- Los secretos se configuran por variables de entorno.
- `.env` esta ignorado por Git.
- Los comprobantes de transferencia estan ignorados en `media/comprobantes_transferencia/`.
- CSRF se mantiene activo mediante middleware Django.
- Las vistas de cliente validan sesion antes de mostrar reservas o pagos.
- El panel gerente valida rol antes de permitir acceso.

## Notas de Mantenimiento

- No colocar nuevas funcionalidades grandes directamente en `views/common.py`.
- Si una vista crece con reglas de negocio, extraer esa logica a `gestion_hotel/services/`.
- Mantener URLs existentes salvo que exista una migracion clara y compatible.
- Evitar datos personales, bancarios o credenciales como valores por defecto en codigo.
- Mantener imagenes de usuario y comprobantes fuera del repositorio cuando sean privados.
