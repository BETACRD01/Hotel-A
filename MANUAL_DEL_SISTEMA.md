# Manual del Sistema - Hotel Arahuana Eco-Resort & Spa

Este documento es una **guía integral y didáctica** que explica qué hace cada parte del sistema, cómo está estructurado el código, cómo interactúan sus componentes y cómo se gestiona el ciclo de vida de las reservas y su infraestructura.

---

## Índice

1. [Visión General del Sistema](#1-visión-general-del-sistema)
2. [Estructura del Proyecto (Árbol de Directorios)](#2-estructura-del-proyecto-árbol-de-directorios)
3. [Base de Datos y Modelos (`models.py`)](#3-base-de-datos-y-modelos-modelspy)
4. [Capa de Negocio y Servicios (`services/reservations.py`)](#4-capa-de-negocio-y-servicios-servicesreservationspy)
5. [Vistas y Controladores (`views/`)](#5-vistas-y-controladores-views)
6. [Plantillas y Experiencia de Usuario (`templates/` y `static/`)](#6-plantillas-y-experiencia-de-usuario-templates-y-static)
7. [Ciclo de Vida de una Reserva (Flujo Paso a Paso)](#7-ciclo-de-vida-de-una-reserva-flujo-paso-a-paso)
8. [Reglas Clave Recientes (Programa Libre y Bloqueo de Duplicados)](#8-reglas-clave-recientes-programa-libre-y-bloqueo-de-duplicados)
9. [Despliegue e Infraestructura en Google Cloud](#9-despliegue-e-infraestructura-en-google-cloud)
10. [Comandos Frecuentes de Mantenimiento](#10-comandos-frecuentes-de-mantenimiento)

---

## 1. Visión General del Sistema

El sistema del **Hotel Arahuana Eco-Resort & Spa** es una plataforma web desarrollada en **Python** con el framework **Django**.

### Objetivos Principales:
- **Catálogo público:** Mostrar habitaciones, cabañas, cine y paquetes de resort de día.
- **Reservas en línea:** Permitir a clientes autenticados reservar habitaciones o cabañas según programas de hospedaje (2D1N, 3D2N, 4D3N o programas personalizados).
- **Control de disponibilidad:** Bloquear automáticamente unidades reservadas para impedir que dos usuarios reserven la misma habitación o cabaña en fechas coincidentes.
- **Gestión de pagos:** Procesar pagos por transferencia bancaria con carga de comprobante y validación administrativa.
- **Panel gerencial y administrativo:** Administrar inventario, validar pagos, ver reportes y cancelar reservas vencidas.

---

## 2. Estructura del Proyecto (Árbol de Directorios)

```text
Hotel-A/
│
├── arahuana_resort/             # CONFIGURACIÓN GLOBAL DE DJANGO
│   ├── settings.py              # Variables de configuración, base de datos, apps y seguridad
│   ├── urls.py                  # Enrutador principal de URLs del proyecto
│   ├── wsgi.py                  # Punto de entrada para el servidor web Gunicorn
│   └── asgi.py                  # Soporte asíncrono si se requiere
│
├── gestion_hotel/               # APLICACIÓN PRINCIPAL DEL NEGOCIO
│   ├── models.py                # Definición de tablas y entidades de la base de datos
│   ├── forms.py                 # Formularios de login, registro y validación
│   ├── middleware.py            # Middleware de redirección según el rol del usuario
│   ├── validators.py            # Validadores (Cédula/RUC ecuatoriano, contraseñas, teléfonos)
│   │
│   ├── services/                # LÓGICA DE NEGOCIO PURA
│   │   └── reservations.py      # Cálculos de precios, resolución de programas y disponibilidad
│   │
│   ├── views/                   # CONTROLADORES Y VISTAS MODULARES
│   │   ├── common.py            # Imports y utilidades compartidas
│   │   ├── public.py            # Portada principal y página "Sobre nosotros"
│   │   ├── catalog.py           # Catálogo de habitaciones/cabañas y creación de reservas
│   │   ├── auth.py              # Login, registro y recuperación de contraseña
│   │   ├── client.py            # Panel del cliente y perfil
│   │   ├── reservations.py      # Mis reservas y cancelación voluntaria
│   │   ├── payments.py          # Proceso de pago y subida de comprobante bancario
│   │   └── gerente.py           # Panel administrativo del gerente
│   │
│   ├── templates/               # INTERFACES VISUALES (HTML con Django Templates)
│   │   ├── base.html            # Plantilla maestra con cabecera y pie de página
│   │   ├── public/              # Habitaciones, cabañas, cine, resort y portada
│   │   ├── auth/                # Pantallas de login y registro
│   │   ├── client/              # Dashboard del cliente y listado de reservas
│   │   ├── payments/            # Pantallas para subir comprobante de pago
│   │   └── gerente/             # Vistas del panel de control gerencial
│   │
│   ├── static/                  # ARCHIVOS ESTÁTICOS
│   │   ├── css/                 # Hojas de estilo modularizadas (resort, catálogo, panel)
│   │   ├── js/                  # Scripts de interacción (modales, fechas, cálculos)
│   │   └── img/                 # Logos, íconos y fotos institucionales
│   │
│   ├── management/commands/     # COMANDOS DE TERMINAL
│   │   ├── cancelar_reservas_vencidas.py    # Tarea cron para cancelar impagos a las 24h
│   │   └── limpiar_imagenes_inexistentes.py # Limpieza de rutas rotas en base de datos
│   │
│   └── migrations/              # HISTORIAL DE MIGRACIONES DE BASE DE DATOS
│
├── media/                       # ARCHIVOS DINÁMICOS SUBIDOS POR USUARIOS
│   ├── habitaciones/            # Fotografías subidas de habitaciones
│   ├── cabanas/                 # Fotografías subidas de cabañas
│   └── comprobantes_transferencia/ # Fotos de transferencias bancarias
│
├── staticfiles/                 # Directorio generado por collectstatic para Nginx
├── manage.py                    # Script ejecutor de comandos Django
├── requirements.txt             # Dependencias de Python
└── README.md                    # Resumen rápido del repositorio
```

---

## 3. Base de Datos y Modelos (`models.py`)

Cada modelo representa una tabla en la base de datos PostgreSQL:

### A. Catálogos y Usuarios
- **`Cliente`**: Registra tanto a clientes como a usuarios administradores y gerentes. Contiene validación estricta de cédula/RUC ecuatoriano (`validate_cedula_ruc`), correo electrónico único y contraseñas cifradas.
- **`Habitaciones`**: Inventario de habitaciones. Almacena número, tipo (Simple, Doble, Familiar), capacidad máxima, tarifas por programa (`precio_2d1n_total`, `precio_3d2n_total`, `precio_4d3n_total`), precio por noche y estado (`Disponible`, `Reservada`, `Ocupada`, `Mantenimiento`, `Inactiva`).
- **`Cabanas`**: Mismo funcionamiento que habitaciones pero adaptado a cabañas con campos de servicios incluidos.

### B. Reservas y Detalles
- **`Reservas`**: Cabecera maestra de la transacción. Almacena:
  - `id_cliente`: Cliente que realiza la reserva.
  - `fecha_ingreso` y `fecha_salida`: Periodo general de estancia.
  - `estado_reserva`: `Pendiente`, `Confirmada`, `Cancelada`, `Completada`.
  - `estado_pago`: `Pendiente`, `En revision`, `Pagado`, `Anulado`.
  - `metodo_pago`: `Transferencia` o `Recepcion`.
  - `total`, `subtotal`, `anticipo_requerido`, `saldo_pendiente`.
  - `fecha_limite_pago`: 24 horas después de la reserva para transferencias.
- **`DetalleHabitaciones`**: Guarda la habitación reservada, número de personas, fechas exactas de estancia (`fecha_entrada`, `fecha_salida`), programa elegido y subtotal. Es la base para validar solapamientos.
- **`DetalleCabanas`**: Equivalente a `DetalleHabitaciones` para el caso de cabañas.

### C. Pagos
- **`PagoReserva`**: Guarda los datos de la transferencia: banco emisor, número de transacción/referencia, monto transferido, fecha y la imagen del comprobante (`comprobante_imagen`).

---

## 4. Capa de Negocio y Servicios (`services/reservations.py`)

Esta capa separa la lógica empresarial de las vistas para mantener el código ordenado y reutilizable:

| Función | ¿Qué hace? |
|---|---|
| `resolver_programa_y_noches(programa, fecha_ingreso, fecha_salida)` | Analiza el programa seleccionado o escrito libremente. Si es 2D1N (1 noche), 3D2N (2 noches) o 4D3N (3 noches), fija las fechas automáticamente. Si el usuario escribe otro texto o selecciona fechas libres, calcula las noches por diferencia de fechas. |
| `calcular_precio_estadia(servicio, programa_codigo, tipo_ocupacion, noches)` | Determina el costo total de la reserva según la tarifa configurada para el programa o multiplicando el precio por noche por la duración. |
| `actualizar_estados_hospedaje()` | **Sincronizador automático**: Revisa todas las habitaciones y cabañas activas. Si tienen reservas activas (`Pendiente` o `Confirmada`), marca su estado como **`Reservada`**. Si no tienen reservas activas, las regresa a **`Disponible`**. Respeta estados manuales como `Mantenimiento`. |
| `cancelar_reservas_vencidas()` | Identifica reservas pendientes que superaron el plazo de 24 horas sin pago, las pasa a `Cancelada`, anula el pago pendiente y llama a `actualizar_estados_hospedaje()` para liberar la habitación. |

---

## 5. Vistas y Controladores (`views/`)

### `catalog.py` (Catálogo y Creación de Reservas)
- **`habitaciones_view` y `cabanas_view`**:
  1. Ejecutan el mantenimiento inicial (`cancelar_reservas_vencidas` y `actualizar_estados_hospedaje`).
  2. Muestran las tarjetas de habitaciones/cabañas con insignias de color (`status-disponible` en verde, `status-reservada` en rojo).
  3. Al enviar el formulario (POST):
     - Valida sesión de cliente activa.
     - Valida campos del formulario (fechas, huéspedes, programa).
     - **Regla de Bloqueo 1:** Comprueba que `habitacion.estado == "Disponible"`. Si está reservada, rechaza la operación.
     - **Regla de Bloqueo 2:** Verifica en `DetalleHabitaciones` que no existan reservas activas que se crucen en esas fechas.
     - **Transacción Atómica (`transaction.atomic`):** Crea `Reservas`, crea `DetalleHabitaciones`, y cambia inmediatamente el estado de la habitación a `'Reservada'`.
     - Redirige al cliente a la pantalla de pago.

### `reservations.py` (Gestión de Reservas)
- **`mis_reservas_view`**: Permite al cliente consultar sus reservas activas, ver fechas de ingreso/salida, montos y acceder al pago.
- **`cancelar_reserva_view`**: Permite al cliente cancelar una reserva pendiente. Al hacerlo, actualiza el estado de la reserva a `Cancelada` y llama a `actualizar_estados_hospedaje()`, liberando la habitación de inmediato para otros clientes.

### `payments.py` (Procesamiento de Pagos)
- Muestra los datos de la cuenta bancaria del hotel (Pichincha, Guayaquil, etc.).
- Permite subir la foto o captura de la transferencia bancaria.
- Cambia el estado del pago a `En revision` para que el administrador lo apruebe.

### `gerente.py` (Panel Gerencial)
- Muestra métricas de ocupación, reservas recientes y pagos por verificar.
- Permite a los gerentes confirmar o rechazar comprobantes de transferencia.

---

## 6. Plantillas y Experiencia de Usuario (`templates/` y `static/`)

### Catálogo de Habitaciones y Cabañas
- **Insignia Dinámica de Estado:**
  ```html
  <span class="catalog-status status-{{ hab.estado|lower }}">
      {{ hab.estado }}
  </span>
  ```
  - Si el estado es `Disponible`: Fondo verde con texto visible.
  - Si el estado es `Reservada` u `Ocupada`: Fondo rojo con texto visible.

- **Botón de Acción Bloqueable:**
  ```html
  {% if hab.estado == "Disponible" %}
      <button type="button" class="abrir-modal" ...>Reservar ahora</button>
  {% else %}
      <button type="button" disabled>
          <i class="fa-solid fa-circle-xmark"></i> No disponible
      </button>
  {% endif %}
  ```
  Esto garantiza que el cliente no pueda abrir el modal de reserva si la unidad ya está reservada.

- **Campo Editable con Datalist para Programa de Hospedaje:**
  ```html
  <input type="text" id="modalPrograma" name="programa" list="listaProgramas"
         placeholder="Selecciona o escribe un programa (ej. 2 días / 1 noche)" required>
  <datalist id="listaProgramas">
      <option value="2 días / 1 noche"></option>
      <option value="3 días / 2 noches"></option>
      <option value="4 días / 3 noches"></option>
  </datalist>
  ```
  Permite al cliente elegir una de las sugerencias rápidas o escribir un programa personalizado con su teclado.

---

## 7. Ciclo de Vida de una Reserva (Flujo Paso a Paso)

```text
[ Cliente navega en el Catálogo ]
                │
                ▼
¿Unidad disponible? ─── NO ───► Muestra botón "No disponible" (Bloqueado)
                │
               SÍ
                ▼
[ Abre Modal y elige/escribe Programa y Fechas ]
                │
                ▼
[ Envío de Formulario POST ]
                │
                ├─► Valida sesión del cliente
                ├─► Valida capacidad de personas
                ├─► Valida estado == "Disponible"
                └─► Valida que no haya reservas activas solapadas
                                │
                                ▼
         [ Transacción Atómica en Base de Datos ]
                │
                ├─► Crea registro en 'Reservas' (Estado: Pendiente)
                ├─► Crea registro en 'DetalleHabitaciones'
                └─► Actualiza unidad a estado 'Reservada'
                                │
                                ▼
               [ Redirige a Proceso de Pago ]
                                │
          ┌─────────────────────┴─────────────────────┐
          ▼                                           ▼
[ Pago en Recepción ]                     [ Transferencia Bancaria ]
          │                                           │
          ▼                                           ▼
Reserva queda registrada                  Cliente sube comprobante
para pago presencial.                     (Estado pago: "En revision")
                                                      │
                                                      ▼
                                           Gerente aprueba pago en panel
                                           (Estado reserva: "Confirmada")
```

---

## 8. Reglas Clave Recientes

1. **Campo de Programa Personalizable:**
   - Anteriormente era un `<select>` cerrado. Ahora es un `<input list="datalist">`.
   - Si el usuario escribe por ejemplo "5 noches" o "Plan personalizado", el backend en `resolver_programa_y_noches()` procesa la estancia calculando las noches y prorrateando la tarifa correctamente.

2. **Restricción contra Doble Reserva:**
   - Cuando un usuario crea una reserva, la unidad cambia inmediatamente a `Reservada`.
   - La insignia en el catálogo cambia a roja y el botón se desactiva con la leyenda `No disponible`.
   - En el backend, cualquier intento de POST sobre una habitación no disponible o con fechas solapadas es rechazado arrojando un mensaje de advertencia.
   - Si una reserva vence después de 24 horas sin pago o es cancelada por el cliente, el sistema la libera automáticamente volviendo el estado a `Disponible`.

---

## 9. Despliegue e Infraestructura en Google Cloud

El sistema está alojado en una máquina virtual de **Google Cloud Compute Engine**:
- **Instancia:** `free-ubuntu-vm`
- **Zona:** `us-central1-a`
- **Proyecto:** `delivery-109f4`
- **Dominio:** `hoteleroarahuana.duckdns.org` con certificado HTTPS SSL/TLS (Let's Encrypt).
- **Servidor Web:** Nginx (puertos 80 y 443), que actúa como Reverse Proxy hacia Gunicorn.
- **Servidor de Aplicaciones:** Gunicorn gestionado por systemd como servicio `hotel.service` escuchando en `127.0.0.1:8001`.

---

## 10. Comandos Frecuentes de Mantenimiento

Para conectarse al servidor en la nube vía Google Cloud SDK:

```bash
gcloud compute ssh free-ubuntu-vm --zone=us-central1-a --project=delivery-109f4 --tunnel-through-iap
```

Dentro del servidor (`/home/ubuntu/Hotel-A`):

- **Descargar últimos cambios de código:**
  ```bash
  sudo -u ubuntu git pull origin main
  ```
- **Recopilar archivos estáticos (CSS / JS / Imágenes):**
  ```bash
  sudo -u ubuntu /usr/bin/python3 manage.py collectstatic --noinput
  ```
- **Aplicar migraciones pendientes:**
  ```bash
  sudo -u ubuntu /usr/bin/python3 manage.py migrate
  ```
- **Reiniciar el servicio web para aplicar cambios:**
  ```bash
  sudo systemctl restart hotel
  ```
- **Ver logs en tiempo real ante errores:**
  ```bash
  sudo journalctl -u hotel -f
  ```
