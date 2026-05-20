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

- `web/templates/base.html`
  - Layout principal. Incluye logo, bloque de mensajes y la barra de navegación (`partials/nav.html`).
  - Bloques Jinja: `title`, `customCSS`, `content`, `customJS`.
  - El menú no se muestra en la ruta `/` (login).

- `web/templates/partials/nav.html`
  - Menú con enlaces a los módulos del sistema. Resalta el activo según `request.url.path`.
  - Incluye enlace "Salir" (`/auth/salir`) que limpia la cookie y redirige a `/`.

- `web/templates/crud_page.html`
  - Vista CRUD genérica. Define:
    - Botón "Agregar" que abre un modal y carga el formulario con `hx-get`.
    - Tabla con `<tbody id="tbody-lista">` que se pobla con `hx-get` al cargar y cuando se dispara el evento `refrescarLista`.
    - Script que cierra el modal cuando el servidor emite el trigger HTMX `modalClose`.

- Parciales por módulo (ejemplos):
  - Clientes: `web/templates/ui/clientes/_filas.html`, `web/templates/ui/clientes/_form.html`
  - Cotizaciones: `web/templates/ui/cotizaciones/_filas.html`, `_form.html`
  - Órdenes de Trabajo: `web/templates/ui/ordenes_trabajo/_filas.html`

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

- Estáticos: `web/static/css/app.css`, `web/static/images/*`, `web/static/js/autenticacion.js` (maneja el login), `web/static/js/teamsa-common.js` (utilidades compartidas).

--

## Autenticación y navegación

- Login (`/`): `web/templates/frm_login.html` + `web/static/js/autenticacion.js`
  - Envia `txtNombre` y `txtPassword` a `POST /auth/validaUsuario`.
  - El backend valida y setea una cookie HTTPOnly (JWT) con nombre configurable (`settings.ACCESS_COOKIE_NAME`).
  - Tras éxito, el cliente redirige a `/usuarios`.

- Logout (`GET /auth/salir`): `app/rutas/rt_autenticacion.py`
  - Limpia la cookie y redirige a `/`.

- Dependencias comunes: `app/rutas/dependencias.py`
  - `dp_usuario_actual` valida el JWT desde cookie y retorna identidad (usuario y rol).

- RBAC Dinámico: `app/rutas/permisos.py`
  - `para_modulo(modulo, accion)` retorna una dependencia FastAPI que verifica arrays JSON de permisos del usuario.
  - Acciones: `ver`, `crear`, `editar`, `eliminar`.

--

## Rutas HTML (páginas)

- `app/rutas/rt_paginas.py`
  - Renderiza las páginas principales de cada módulo mediante `render_crud_page`.
  - Módulos disponibles: Usuarios, Clientes, Proveedores, Servicios, Servicios Proveedores, Cotizaciones, Órdenes de Trabajo, Órdenes de Compra, Viáticos, Cronograma.

--

## Manejo de errores

- `app/nucleo/app_factory.py`
  - Handlers globales devuelven HTML para páginas no-API (usando `web/templates/error.html`) y JSON para API.
  - CORS configurable via `settings.CORS_ALLOW_ORIGINS`.
  - Excepciones de dominio (`RecursoNoEncontradoError`, `ReglaNegocioError`, `PermisoDenegadoError`) se transforman a respuestas HTTP apropiadas.

--

## Backend: descriptores, repositorios y builders

- Repositorio genérico: `app/base/repositorio.py`
  - CRUD con filtros (`igual`, `IN`, búsquedas `ilike`), orden y transacciones.
  - Cada módulo lo extiende y puede añadir métodos especializados.
  - Hook `aplicar_seguridad_filtro` para seguridad a nivel de fila (RLS).
  - Hook `_validar_eliminacion` para protección de borrado por dependencias.

- Descriptor CRUD: `app/base/descriptor_crud.py`
  - Describe label, base_url, esquemas Pydantic, campos editables/creables, filtros permitidos y mensajes.
  - `build_hooks()` prepara payloads de creación/actualización y valida unicidad según módulo.
  - `frontend_config()` serializa columnas y metadatos para la vista.
  - `columnas_incluir`: controla el orden de columnas. Este orden se respeta en thead y tbody.

- Builder API JSON: `app/base/enrutador_crud.py`
  - Endpoints: `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}`, `GET /metadata`.
  - Lee filtros desde querystring y aplica paginación básica.
  - Usa dependencias pasadas por el módulo (sesión y autorización).
  - Validaciones:
    - `validar_unicidad(repo, payload_create) -> str | None` (400 si retorna mensaje)
    - `validar_actualizacion(repo, payload_update, id) -> str | None` (400 en PATCH si retorna mensaje)

- Builder UI HTMX: `app/base/ui_crud.py`
  - Endpoints: `GET /filas`, `GET /form`, `POST /crear`, `POST /{id}/actualizar`, `DELETE /{id}`.
  - Reutiliza hooks del descriptor, por lo que la lógica es única para API y UI.
  - Permisos granulares: `create_dependency`, `update_dependency`, `delete_dependency`.
  - Emite eventos HTMX estándar:
    - `refrescarLista`: fuerza recarga del `<tbody>` de la tabla.
    - `modalClose`: cierra el modal genérico.
    - `flash`: muestra un banner en la parte superior del layout (manejado en `base.html`).
  - Mensajes flash por defecto se derivan del `label` (por ejemplo: "Cliente creado").
  - Parámetros importantes:
    - `validar_form_creacion(datos) -> str | None` y `validar_form_actualizacion(datos, entidad_actual) -> str | None`: devuelven mensaje para re-renderizar el modal (status 200) en caso de error suave.
    - `extra_context_provider(db) -> dict`: inyecta listas para selects.
    - `columnas`: pasa `descriptor.frontend_config()["columnas"]` para que la macro `celdas(...)` pinte las filas en el mismo orden que thead.
    - `file_fields`: para manejo de archivos (PDFs).

- Fábrica de módulos: `app/base/factory_modulo.py`
  - `crear_modulo_crud_estandar()` — wrapper principal que configura permisos RBAC granulares automáticamente.
  - Genera routers API + UI + Select en una sola llamada.

--

## Módulos de dominio (patrón)

Cada módulo contiene estas piezas principales:

1) **Modelo SQLModel** (con auditoría)
- `app/base/auditoria.py` provee `AuditMixin` (fechas y usuarios de creación/modificación).
- Ejemplo: `app/modulos/clientes/clientes_modelo.py`.

2) **Esquemas Pydantic**
- Creación, actualización y lectura. Formatean fechas/horas para la vista.
- Ejemplo: `app/modulos/clientes/clientes_esquemas.py`.

3) **Repositorio especializado**
- Extiende `RepositorioCRUD[T]` y ajusta filtros, búsqueda y orden.
- Ejemplo: `app/modulos/clientes/clientes_repositorio.py`.

4) **Router del módulo**
- Usa `crear_modulo_crud_estandar()` con el `DescriptorCRUD` del módulo.
- El router combinado se expone como `router` y es incluido por `app/nucleo/app_factory.py`.

### Módulos activos del sistema

| Módulo | Ruta API | Tipo |
|--------|----------|------|
| Clientes | `/api/clientes` | Catálogo |
| Proveedores | `/api/proveedores` | Catálogo |
| Servicios | `/api/servicios` | Catálogo |
| Servicios Proveedores | `/api/servicios-proveedores` | Catálogo |
| Cotizaciones | `/api/cotizaciones` | Transaccional |
| Órdenes de Trabajo | `/api/ordenes-trabajo` | Transaccional |
| Órdenes de Compra | `/api/ordenes-compra` | Transaccional |
| Viáticos | `/api/viaticos` | Transaccional |
| Cronograma | `/api/cronograma` | Vista |
| Usuarios | `/api/usuarios` | Admin |

### Documentos transaccionales
- **Cotizaciones**: Documentos comerciales con versionamiento (COT-AAMM01-B). Incorporan Conceptos con snapshots de precios.
- **Órdenes de Trabajo (OT)**: Se generan a partir de Cotizaciones finalizadas. Guardan un snapshot del cliente al crearse.
- **Órdenes de Compra (OC)**: Abastecimiento con Proveedores usando `ServiciosProveedores`.
- **Viáticos**: Gastos asociados a Cotizaciones y OTs.

### Patrones avanzados implementados
- **Mixins Financieros** (`MixinDetalleFinanciero`): Cálculos de importe para líneas de detalle.
- **Snapshots Históricos** (`MixinSnapshotCliente`, `MixinSnapshotProveedor`): Persistencia plana de datos de catálogo en documentos.
- **Folios Secuenciales**: Generación automática de folios con prefijo temporal (COT-AAMM01).
- **Eventos de Dominio** (`BusEventos`): Comunicación desacoplada entre módulos (ej: cascading de estados).
- **Wizard de Creación**: Flujo multi-paso para Cotizaciones y Órdenes de Compra.

--

## Cómo crear un nuevo módulo CRUD

1) **Modelo y esquemas**
- Declara el modelo SQLModel heredando de `AuditMixin`.
- Define `Create`, `Update` y `Read` con validadores de serialización si necesitas.

2) **Repositorio**
- Extiende `RepositorioCRUD[T]` y configura:
  - `campos_filtrables`, `campos_busqueda`, `campos_actualizables`, `orden_por_defecto`.

3) **Router y descriptor**
- Crea `descriptor = DescriptorCRUD(...)` con:
  - `label`, `base_url`, `repo_factory`, `schema_read`, `schema_create`, `schema_update`.
- Genera el router con:
  - `router = crear_modulo_crud_estandar(descriptor=descriptor, nombre_modulo="tu_modulo")`

4) **Plantillas**
- Crea `web/templates/ui/tu_modulo/_filas.html` y `.../_form.html`.
- En `_filas.html` importa y usa:
  - `{% from 'partials/rows.html' import celdas %}`
  - `{% from 'partials/actions.html' import acciones %}`
  - En cada `<tr>`: `{{ celdas(item, columnas) }}` y después `{{ acciones(ui_base, item.id, puede_editar) }}`.

5) **Registrar en app_factory**
- En `app/nucleo/app_factory.py`, importa y añade `app.include_router(tu_router)`.
- Añade el módulo a `ModuloSistema` en `app/base/modulos_sistema.py`.

Listo: tendrás operaciones de listar/crear/editar/eliminar funcionando con una tabla y un modal reutilizables, sin escribir JS adicional.

--

## Ejecución y configuración

- Docker Compose: `compose.yaml` define el servicio `aplicacion` y `db` (Postgres) con healthchecks. Variables de entorno en `.env`.
- CORS configurable: `settings.CORS_ALLOW_ORIGINS` en `app/nucleo/configuracion.py` (lista separada por comas o `*`).
- La cookie de sesión es HTTPOnly. En producción se recomienda marcar `secure=True` en `app/nucleo/sesion.py`.
- 404 HTML consistente: `app/nucleo/app_factory.py` añade un middleware que renderiza `error.html` cuando no se encuentra una ruta no-API.

--

## Preguntas frecuentes

- ¿Dónde personalizo los textos flash?
  - Al construir el UI puedes pasarlos en `DescriptorUI`; si no, se derivan del `label` automáticamente.

- ¿Cómo formateo fechas y horas en las tablas y detalles?
  - **REGLA DE ORO**: Usa siempre filtros de seguridad: `| fmt_date` para fechas, `| fmt_currency` para dinero, `| fmt_none` para textos opcionales.
  - NUNCA uses métodos de Python como `.strftime()` ya que rompen la página (Error 500) si el dato es nulo.

- ¿Cómo protejo una página por rol/módulo?
  - Usa `para_modulo(nombre_modulo, accion)` de `app/rutas/permisos.py`.

- ¿Puedo consumir la API desde otro frontend?
  - Sí. Los endpoints `/api/...` responden JSON y autentican con la cookie; CORS se controla en settings.

- ¿Cómo subo archivos?
  - PDFs: usa el nombre de campo del modelo (p.ej. `pdf_path`) y el macro `field_file(...)`. En create el builder guarda temporal y mueve a `uploads/<plural>/<id>/archivo.pdf`. En update escribe directo. Asegúrate de `enctype="multipart/form-data"` y `hx-encoding="multipart/form-data"` en el form.

--

## Funciones y utilidades importantes (resumen rápido)

- `DescriptorCRUD` (app/base/descriptor_crud.py)
  - Define el "contrato" del módulo (esquemas, editables, filtros y columnas).

- `crear_modulo_crud_estandar` (app/base/factory_modulo.py)
  - Genera un router completo (API + UI + Select) con RBAC automático.

- `construir_enrutador_crud` (app/base/enrutador_crud.py)
  - Construye API JSON. Soporta `validar_unicidad` (POST) y `validar_actualizacion` (PATCH).

- `construir_enrutador_ui` (app/base/ui_crud.py)
  - Construye UI HTMX. Soporta validaciones suaves, contexto extra, columnas y archivos.
  - Emite triggers HTMX (`refrescarLista`, `modalClose`, `flash`).

- `RepositorioCRUD` (app/base/repositorio.py)
  - CRUD de bajo nivel con filtros/orden. Cada módulo lo especializa.

- `ServicioDocumentoFinanciero` (app/base/servicios_documentos.py)
  - Template Method para creación estandarizada de documentos financieros.

- `BusEventos` (app/base/eventos.py)
  - Publicación/suscripción de eventos de dominio para comunicación desacoplada.

- `ModuloSistema` (app/base/modulos_sistema.py)
  - Enumeración fuente de verdad para los módulos del sistema.

- `app_factory` (app/nucleo/app_factory.py)
  - Registra middlewares, estáticos `/uploads`, handlers HTML/JSON y 404 HTML.

--

## Playbook de Cambios (paso a paso)

Sigue estas recetas para hacer cambios típicos sin perder consistencia.

1) **Agregar una columna visible en una tabla existente**
- Edita los esquemas Pydantic del módulo (Create/Update/Read).
- Si aplica, agrega el campo al modelo SQLModel.
- En el repositorio, añade a `campos_actualizables` si será editable.
- En el descriptor, agrega a `columnas_incluir` en la posición deseada.
- Si debe estar en el formulario, añade el input en `_form.html`.

2) **Añadir un select con datos de otra tabla (HTMX)**
- Pasa datos al formulario con `extra_context_provider`:
  - `extra_context_provider=lambda db: {"otra_lista": RepositorioOtra(db).listar()}`
- En el formulario, usa `field_select('campo','Etiqueta', otra_lista, ...)`.

3) **Validación suave en UI (crear/editar)**
- Para crear: pasa `validar_form_creacion=lambda datos: 'mensaje' o None`.
- Para editar: pasa `validar_form_actualizacion=lambda datos, entidad: 'mensaje' o None`.
- El modal se re-renderiza con el mensaje (status 200) y no cierra.

4) **Validación suave en la API JSON (PATCH)**
- En el descriptor, define `validar_actualizacion(repo, payload_update, id)`.

5) **Subida de archivos (PDF) en formularios**
- Usa el macro `field_file('campo_path', 'PDF', required=..., current_url=item.campo_path)`.
- Asegura `enctype="multipart/form-data"` y `hx-encoding="multipart/form-data"` en el form.

6) **Crear un módulo nuevo desde cero**
- Modelo + esquemas + repositorio (ver patrón de Módulos de dominio).
- En el router: arma el `DescriptorCRUD` y usa `crear_modulo_crud_estandar()`.
- Crea plantillas `_filas.html` y `_form.html` usando los macros `celdas` y `acciones`.
- Registra en `app_factory.py` y `ModuloSistema`.

--

Con este enfoque, la mayor parte del trabajo al crear nuevas pantallas se reduce a describir el módulo (descriptor + plantillas parciales). El resto (rutas, validaciones, flujos HTMX y mensajes, filas/acciones) se resuelve de forma genérica y consistente.
