# Guía del Proyecto (Backend FastAPI + HTMX/Jinja)

Esta guía explica cómo está estructurado el proyecto y cómo extenderlo sin romper consistencia (KISS). Incluye una lista de funciones importantes y cómo usarlas.

En la UI se usa HTML renderizado en servidor con Jinja y HTMX para intercambiar parciales, evitando JavaScript personalizado. Bootstrap se usa desde CDN para estilos y componentes.

--

## Resumen de arquitectura

- Páginas HTML (Jinja) renderizadas por FastAPI.
- HTMX para cargar parciales: filas de tabla y cuerpo de modales.
- Dos routers por módulo de dominio:
  - API JSON (CRUD) generado por un builder genérico.
  - UI HTML (HTMX) generado por un builder genérico.
- Reglas de negocio compartidas mediante un descriptor por módulo (DescriptorCRUD) y sus hooks.
 - Los listados HTML usan macros genéricas de celdas y acciones, alimentadas desde el descriptor para evitar plantillas duplicadas.

--

## Plantillas y estáticos

- `web/templates/base.html:1`
  - Layout principal. Incluye logo, bloque de mensajes y la barra de navegación (`partials/nav.html`).
  - Bloques Jinja: `title`, `customCSS`, `content`, `customJS`.
  - El menú no se muestra en la ruta `/` (login).

- `web/templates/partials/nav.html:1`
  - Menú con enlaces a Usuarios, Foros y Programas. Resalta el activo según `request.url.path`.
  - Incluye enlace “Salir” (`/auth/salir`) que limpia la cookie y redirige a `/`.

- `web/templates/crud_page.html`
  - Vista CRUD genérica. Define:
    - Botón “Agregar” que abre un modal y carga el formulario con `hx-get`.
    - Tabla con `<tbody id="tbody-lista">` que se pobla con `hx-get` al cargar y cuando se dispara el evento `refrescarLista`.
    - Script que cierra el modal cuando el servidor emite el trigger HTMX `modalClose`.

- Páginas por módulo (extienden `crud_page.html`):
  - `web/templates/usuarios.html:1`
  - `web/templates/foros.html:1`
  - `web/templates/programas.html:1`

- Parciales por módulo (ejemplos):
  - Usuarios: `web/templates/ui/usuarios/_filas.html`, `web/templates/ui/usuarios/_form.html`
  - Foros: `web/templates/ui/foros/_filas.html`, `web/templates/ui/foros/_form.html` (sin imágenes)
  - Programas: `web/templates/ui/programas/_filas.html`, `web/templates/ui/programas/_form.html`
  - Invitados/Testimonios: `web/templates/ui/invitados/_filas.html`, `_form.html`; `web/templates/ui/testimonios/_filas.html`, `_form.html`

- Filtros y helpers Jinja: `app/web/jinja.py`
  - `fmt_date` (datetime/date ISO de forma segura), `fmt_currency` (formato moneda con símbolo), `fmt_dt` (ISO extendido), `fmt_time` (hora), `fmt_none` (fallback para None).
  - Estos filtros son **obligatorios** para evitar errores 500 cuando un campo es `None`.
  - `get_templates()` registra los filtros y devuelve una instancia compartida para render.
   - `getv(obj, name)`: acceso seguro a atributos o claves para plantillas dinámicas.

- Macros Jinja reutilizables:
  - `web/templates/ui/macros/components.html`: Componentes **Premium** para vistas de detalle (`status_badge`, `money`, `info_row`, `totals_row`).
  - `web/templates/partials/forms.html`: Macros de inputs (`field_input`, `field_select`, `field_file`, …).
  - `web/templates/partials/actions.html`: Macro `acciones(...)` para la columna Acciones en listados.
  - `web/templates/partials/rows.html`: Macro `celdas(item, columnas)` que pinta celdas automáticas en listados.

- Estáticos: `web/static/css/app.css:1`, `web/static/img/*`, `web/static/js/autenticacion.js:1` (maneja el login).

--

## Autenticación y navegación

- Login (`/`): `web/templates/frm_login.html:1` + `web/static/js/autenticacion.js:1`
  - Envia `txtNombre` y `txtPassword` a `POST /auth/validaUsuario`.
  - El backend valida y setea una cookie HTTPOnly (JWT) con nombre configurable (`settings.ACCESS_COOKIE_NAME`).
  - Tras éxito, el cliente redirige a `/usuarios`.

- Logout (`GET /auth/salir`): `app/rutas/rt_autenticacion.py:1`
  - Limpia la cookie y redirige a `/`.

- Dependencias comunes: `app/rutas/dependencias.py:1`
  - `dp_usuario_actual` valida el JWT desde cookie y retorna identidad (usuario y rol).
  - `exigir_roles("admin", ...)` protege rutas por rol.

--

## Rutas HTML (páginas)

- `app/rutas/rt_paginas.py:1`
  - `render_crud_page(request, template, descriptor, ui_base)` renderiza una CRUD con:
    - `crud_config = descriptor.frontend_config()` (columnas, filtros, textos, etc.).
    - `ui_base`: prefijo de rutas HTMX del módulo (ej. `/ui/usuarios`).
  - Páginas definidas:
    - `/usuarios` (sólo admin)
    - `/foros` (admin, productor)
    - `/programas` (admin, productor)

--

## Manejo de errores

- `app/nucleo/app_factory.py:1`
  - Handlers globales devuelven HTML para páginas no-API (usando `web/templates/error.html:1`) y JSON para API.
  - CORS configurable via `settings.CORS_ALLOW_ORIGINS`.

--

## Backend: descriptores, repositorios y builders

- Repositorio genérico: `app/base/repositorio.py:1`
  - CRUD con filtros (`igual`, `IN`, búsquedas `ilike`), orden y transacciones.
  - Cada módulo lo extiende y puede añadir métodos especializados (ej. `obtener_por_username`).

- Descriptor CRUD: `app/base/descriptor_crud.py:1`
  - Describe label, base_url, esquemas Pydantic, campos editables/creables, filtros permitidos y mensajes.
  - `build_hooks()` prepara payloads de creación/actualización y valida unicidad según módulo.
  - `frontend_config()` serializa columnas y metadatos para la vista.
  - `columnas_incluir`: controla el orden de columnas. Este orden se respeta en thead y tbody.
  - `to_api_router(...)` construye el router JSON sin repetir parámetros.

- Builder API JSON: `app/base/enrutador_crud.py:1`
  - Endpoints: `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}`, `GET /metadata`.
  - Lee filtros desde querystring y aplica paginación básica.
  - Usa dependencias pasadas por el módulo (sesión y autorización).
  - `GET /{id}`: Devuelve una entidad individual por su ID (genérico para todos los módulos).
  - Validaciones:
    - `validar_unicidad(repo, payload_create) -> str | None` (400 si retorna mensaje)
    - `validar_actualizacion(repo, payload_update, id) -> str | None` (400 en PATCH si retorna mensaje)

- Builder UI HTMX: `app/base/ui_crud.py:1`
  - Endpoints: `GET /filas`, `GET /form`, `POST /crear`, `POST /{id}/actualizar`, `DELETE /{id}`.
  - Reutiliza hooks del descriptor, por lo que la lógica es única para API y UI.
  - Emite eventos HTMX estándar:
    - `refrescarLista`: fuerza recarga del `<tbody>` de la tabla.
    - `modalClose`: cierra el modal genérico.
    - `flash`: muestra un banner en la parte superior del layout (manejado en `base.html`).
  - Mensajes flash por defecto se derivan del `label` (por ejemplo: “Usuario creado”).
  - Parámetros importantes:
    - `validar_form_creacion(datos) -> str | None` y `validar_form_actualizacion(datos, entidad_actual) -> str | None`: devuelven mensaje para re-renderizar el modal (status 200) en caso de error suave.
    - `extra_context_provider(db) -> dict`: inyecta listas para selects (p.ej. foros, programas, invitados, testimonios).
    - `columnas`: pasa `descriptor.frontend_config()["columnas"]` para que la macro `celdas(...)` pinte las filas en el mismo orden que thead.
    - `file_fields`: hoy sólo usamos PDFs; las imágenes de Foros se eliminaron del flujo.

--

## Módulos de dominio (patrón)

Cada módulo contiene cuatro piezas principales:

1) Modelo SQLModel (con auditoría)
- `app/base/auditoria.py:1` provee `AuditMixin` (fechas y usuarios de creación/modificación).
- Ejemplos: `app/modulos/usuarios/usuarios_modelo.py:1`, `app/modulos/foros/foros_modelo.py:1`, `app/modulos/programas/programas_modelo.py:1`.

2) Esquemas Pydantic
- Creación, actualización y lectura. Formatean fechas/horas para la vista.
- Ejemplos: `app/modulos/usuarios/usuarios_esquemas.py:1`, etc.

3) Repositorio especializado
- Extiende `RepositorioCRUD` y ajusta filtros, búsqueda y orden.
- Ejemplos: `app/modulos/usuarios/usuarios_repositorio.py:1`, etc.

4) Router del módulo
- Declara `descriptor = DescriptorCRUD(...)` con hooks propios (auditoría, unicidad, hashing de contraseña si aplica).
- API JSON: `api_router = descriptor.to_api_router(...)`.
- UI HTMX: `ui_router = construir_enrutador_ui(...)` con los dos parciales (`_filas.html`, `_form.html`).
- El router combinado se expone como `router` y es incluido por `app/nucleo/app_factory.py:1`.

### Casos especiales implementados
- Usuarios
  - Hash de contraseña en creación/edición.
  - Mapeo rol→área centralizado: `app/base/mapas.py` (`area_por_rol`).

- Programas
  - Validación de roles para productor/conductores por ID.
  - Form con selects: `productor_asignado_id` y `conductores_ids` usan label `nombres`.

- Invitados y Testimonios
  - PDF de identificación con previsualización dentro del modal (iframe) y reemplazo directo.
  - Campos JSONB: `programas_visitados`, `fechas_visita` (listas). Se alimentan desde Reservaciones.

- Reservaciones
  - Validación suave (UI y API JSON): si asocias invitado/testimonio, exige `programa_id`.
  - Hook post-crear/actualizar: agrega nombre de programa y fecha a Invitado/Testimonio (sin duplicados).
  - Form con selects para foros/programas/invitados/testimonios; `solicitante` se autocompleta con el usuario creador.

--

## Cómo crear un nuevo módulo CRUD

1) Modelo y esquemas
- Declara el modelo SQLModel (idealmente heredando de `AuditMixin`).
- Define `Create`, `Update` y `Read` con validadores de serialización si necesitas (fechas/horas).

2) Repositorio
- Extiende `RepositorioCRUD[T]` y configura:
  - `campos_filtrables`, `campos_busqueda`, `campos_actualizables`, `orden_por_defecto`.

3) Router y descriptor
- Crea `descriptor = DescriptorCRUD(...)` con:
  - `label`, `base_url`, `repo_factory`, `schema_read`, `schema_create`, `schema_update`.
  - Hooks extra para auditoría o hashing.
- Genera routers:
  - `api_router = descriptor.to_api_router(obtener_sesion=..., list_dependencies=[Depends(dp_usuario_actual)], write_dependency=exigir_roles('admin'))`
  - `ui_router = construir_enrutador_ui(prefix='/ui/tu_modulo', repo_factory=..., schema_create=..., schema_update=..., hooks=descriptor.build_hooks(), obtener_sesion=..., list_dependencies=[Depends(dp_usuario_actual)], write_dependency=exigir_roles('admin'), ui=DescriptorUI(tpl_filas='ui/tu_modulo/_filas.html', tpl_form='ui/tu_modulo/_form.html'), label=descriptor.label, columnas=descriptor.frontend_config()["columnas"])`

4) Plantillas
- Crea `web/templates/tu_modulo.html` extendiendo `crud_page.html`.
- Crea `web/templates/ui/tu_modulo/_filas.html` y `.../_form.html`.
- En `_filas.html` importa y usa:
  - `{% from 'partials/rows.html' import celdas %}`
  - `{% from 'partials/actions.html' import acciones %}`
  - En cada `<tr>`: `{{ celdas(item, columnas) }}` y después `{{ acciones(ui_base, item.id, puede_editar) }}`.

5) Página HTML
- En `app/rutas/rt_paginas.py:1`, añade una ruta que haga `render_crud_page(request, template='tu_modulo.html', descriptor=tu_descriptor, ui_base='/ui/tu_modulo')` con `Depends(exigir_roles(...))` si corresponde.

Listo: tendrás operaciones de listar/crear/editar/eliminar funcionando con una tabla y un modal reutilizables, sin escribir JS adicional.

--

## Ejecución y configuración

- Docker Compose: `compose.yaml:1` define el servicio `aplicacion` y `db` (Postgres) con healthchecks. Variables de entorno en `.env` (ver `.env.example:1`).
- CORS configurable: `settings.CORS_ALLOW_ORIGINS` en `app/nucleo/configuracion.py:1` (lista separada por comas o `*`).
- La cookie de sesión es HTTPOnly. En producción se recomienda marcar `secure=True` en `app/nucleo/sesion.py`.
- 404 HTML consistente (incluye estáticos): `app/nucleo/app_factory.py` añade un middleware que renderiza `error.html` cuando no se encuentra una ruta no-API.

--

## Preguntas frecuentes

- ¿Dónde personalizo los textos flash?
  - Al construir el UI puedes pasarlos en `DescriptorUI`; si no, se derivan del `label` automáticamente.

- ¿Cómo formateo fechas y horas en las tablas y detalles?
  - **REGLA DE ORO**: Usa siempre filtros de seguridad: `| fmt_date` para fechas, `| fmt_currency` para dinero, `| fmt_none` para textos opcionales.
  - NUNCA uses métodos de Python como `.strftime()` ya que rompen la página (Error 500) si el dato es nulo.

- ¿Cómo protejo una página por rol?
  - Añade `Depends(exigir_roles('admin', ...))` en la ruta HTML y/o en los routers API/UI.

- ¿Puedo consumir la API desde otro frontend?
  - Sí. Los endpoints `/api/...` responden JSON y autentican con la cookie; CORS se controla en settings.

- ¿Cómo subo archivos?
  - PDFs: usa el nombre de campo del modelo (p.ej. `pdf_identificacion_path`) y el macro `field_file(...)`. En create el builder guarda temporal y mueve a `uploads/<plural>/<id>/identificacion.pdf`. En update escribe directo. Asegúrate de `enctype="multipart/form-data"` y `hx-encoding="multipart/form-data"` en el form.
  - Imágenes de Foros: se eliminaron del flujo.

--

Con este enfoque, la mayor parte del trabajo al crear nuevas pantallas se reduce a describir el módulo (descriptor + plantillas parciales). El resto (rutas, validaciones, flujos HTMX y mensajes, filas/acciones) se resuelve de forma genérica y consistente.

--

## Funciones y utilidades importantes (resumen rápido)

- `DescriptorCRUD` (app/base/descriptor_crud.py)
  - Define la “contrato” del módulo (esquemas, editables, filtros y columnas). Usa `columnas_incluir` para el orden de thead/tbody.

- `construir_enrutador_crud` (app/base/enrutador_crud.py)
  - Construye API JSON. Soporta `validar_unicidad` (POST) y `validar_actualizacion` (PATCH) para 400 suaves.

- `construir_enrutador_ui` (app/base/ui_crud.py)
  - Construye UI HTMX. Soporta validaciones suaves, contexto extra, columnas y archivos (PDFs).
  - Emite triggers HTMX (`refrescarLista`, `modalClose`, `flash`).

- `RepositorioCRUD` (app/base/repositorio.py)
  - CRUD de bajo nivel con filtros/orden. Cada módulo lo especializa.

- `archivos.py` (app/nucleo/archivos.py)
  - PDFs: `save_pdf_temp`, `move_pdf_to_entity`, `save_pdf_for_entity`. `delete_upload_rel_path` elimina un path relativo bajo `/uploads`.

- `area_por_rol` (app/base/mapas.py)
  - Devuelve el área por defecto a partir del rol, usado en creación/edición de usuarios.

- `Reservaciones` (app/modulos/reservaciones)
  - `_validar_reserva`, `_validar_actualizacion_reserva` exigen `programa_id` si hay invitado/testimonio.
  - `RepositorioReservacion._propagar_visita` añade programa/fecha a Invitados/Testimonios (sin duplicados).

- `app_factory` (app/nucleo/app_factory.py)
  - Registra middlewares, estáticos `/uploads`, handlers HTML/JSON y 404 HTML.

- Migraciones compat (app/nucleo/base_datos.py)
  - `ensure_table_columns(...)` aplica columnas comunes para módulos afines (Invitado/Testimonio). También crea índices útiles en Reservación/Programa/Invitado/Testimonio.

--

## Playbook de Cambios (paso a paso)

Sigue estas recetas para hacer cambios típicos sin perder consistencia.

1) Agregar una columna visible en una tabla existente
- Edita los esquemas Pydantic del módulo (Create/Update/Read) en `app/modulos/<modulo>/<modulo>_esquemas.py` y agrega el campo.
- Si aplica, agrega el campo al modelo SQLModel en `app/modulos/<modulo>/<modulo>_modelo.py` (usa tipos compatibles; para JSONB usa `sa_type=JSONB`).
- En el repositorio `app/modulos/<modulo>/<modulo>_repositorio.py`, añade el campo a `campos_actualizables` si será editable.
- En el descriptor del router `app/modulos/<modulo>/<modulo>_router.py`, agrega el nombre a `columnas_incluir` en la posición deseada. Ese orden se usará en thead y tbody.
- Si debe estar en el formulario, añade el input en `web/templates/ui/<modulo>/_form.html` usando macros de `partials/forms.html`.
- Si es campo nuevo de DB, asegúrate que la migración “compat” lo cree (ver receta 6).

2) Añadir un select con datos de otra tabla (HTMX)
- En el router del módulo, pasa datos al formulario con `extra_context_provider` de `construir_enrutador_ui`:
  - `extra_context_provider=lambda db: {"otra_lista": RepositorioOtra(db).listar()}`
- En el formulario, usa `field_select('campo','Etiqueta', otra_lista, ...)` y ajusta `label_attr` si quieres mostrar un atributo diferente (p. ej. `nombres`, `nombre_completo`).

3) Validación suave en UI (crear/editar)
- Para crear: pasa `validar_form_creacion=lambda datos: 'mensaje' o None` al builder UI.
- Para editar: pasa `validar_form_actualizacion=lambda datos, entidad: 'mensaje' o None`.
- El modal se re-renderiza con el mensaje (status 200) y no cierra.

4) Validación suave en la API JSON (PATCH)
- En el descriptor del módulo (`DescriptorCRUD`), define `validar_actualizacion(repo, payload_update, id)` y retorna un string con el error o None.
- El builder API responde 400 con el mensaje si no pasa la validación.

5) Subida de archivos (PDF) en formularios
- Usa el macro `field_file('pdf_identificacion_path', 'PDF', required=..., current_url=item.pdf_identificacion_path)` en el formulario.
- Asegura atributos del `<form>`: `enctype="multipart/form-data"` y `hx-encoding="multipart/form-data"`.
- El builder guarda temporalmente en create y mueve a `uploads/<plural>/<id>/identificacion.pdf`. En update escribirá directo en la ruta final.
- Para evitar caché tras reemplazo, añade un query param al iframe: `?v={{ item.fecha_modificacion|fmt_dt }}`.

6) Crear columnas (compat) e índices sin Alembic
- Declara las columnas en el modelo SQLModel.
- En `app/nucleo/base_datos.py` añade la columna a `ensure_table_columns(...)` (si aplica a múltiples tablas) o llama `ensure_column(...)` de forma puntual.
- Para rendimiento, añade índices con `CREATE INDEX IF NOT EXISTS ...` dentro del bloque `with engine.begin():`.

7) Agregar un botón extra a la columna “Acciones”
- En el parcial de filas, construye la lista de extras:
  - `{% set extras = [{'hx_get': '/ui/<modulo>/visor?id=' ~ item.id, 'label': 'Ver PDF'}] %}`
- Llama el macro: `{{ acciones(ui_base, item.id, puede_editar, extras) }}`.

8) Crear un módulo nuevo desde cero
- Modelo + esquemas + repositorio (ver patrón de Módulos de dominio).
- En el router: arma el `DescriptorCRUD` y luego:
  - `api_router = descriptor.to_api_router(...)`
  - `ui_router = construir_enrutador_ui(..., ui=DescriptorUI(...), columnas=descriptor.frontend_config()["columnas"])`
- Crea plantillas `web/templates/<modulo>.html`, `web/templates/ui/<modulo>/_filas.html`, `_form.html` usando los macros `celdas` y `acciones`.
- Añade la página en `app/rutas/rt_paginas.py` con `render_crud_page`.

9) Hook posterior a crear/actualizar (ejemplo Reservaciones)
- Extiende el repositorio y overridea `crear`/`actualizar`, llama a la superclase y luego ejecuta la lógica de propagación (envolver en try/except para no romper la operación principal).
- Ejemplo: en `Reservaciones`, `_propagar_visita` añade (sin duplicados) `programas_visitados`/`fechas_visita` en Invitados/Testimonios vinculados.
