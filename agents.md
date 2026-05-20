# Handbook del Agente - TEAMSA App

Este documento es la fuente de verdad para cualquier IA que trabaje en el proyecto TEAMSA App. Define la visión, arquitectura y estándares que deben mantenerse sin excepción.

## 🌟 Visión del Proyecto
**TEAMSA App** es un ERP personalizado diseñado para gestionar el ciclo comercial y operativo de TEAMSA.
- **Clientes y Proveedores**: Catálogos base.
- **Servicios y Servicios Proveedores**: Catálogos de productos/labores y su relación con proveedores.
- **Cotizaciones**: Documentos comerciales con versionamiento.
- **Órdenes de Trabajo (OT)**: Ejecución de servicios con snapshots históricos.
- **Órdenes de Compra (OC)**: Abastecimiento con proveedores.
- **Viáticos**: Gastos de viaje asociados a cotizaciones y OTs.
- **Cronograma**: Vista consolidada de la agenda operativa.

## 🛠 Stack Tecnológico
- **Backend**: Python 3.11+, FastAPI, SQLModel (SQLAlchemy 2.0).
- **Frontend**: HTML5, Jinja2, HTMX (Hipermedia), CSS Nativo.
- **Base de Datos**: PostgreSQL (Alembic para migraciones).
- **Documentación**: WeasyPrint para renders PDF.

## 📐 Reglas de Oro Arquitectónicas (KISS)

### 1. Modelado y SQLModel
- **Herencia de Esquemas**: Definir campos en `modulo_esquemas.py` (ej. `ClienteBase`). El modelo en `modulo_modelo.py` hereda de esta clase `table=True`.
- **Nombres en Español**: Tablas y campos deben ir en español (`fecha_creacion`, `activo`).
- **Auditoría**: Toda tabla principal debe heredar de `AuditMixin` para tracking de fechas y usuarios.
- **Importaciones de Field**: PROHIBIDO sombrear `Field` de `sqlmodel` con `pydantic.Field` en el mismo archivo. Usar `PYField` como alias para Pydantic si coexisten. Los modelos SQLModel DEBEN usar la versión de `sqlmodel` para no perder metadatos de DB (claves foráneas).

### 2. Capa de Datos (Repositorios)
- **Seguridad RLS**: Implementar el hook `aplicar_seguridad_filtro` en `RepositorioCRUD` para forzar filtros dinámicos (ej: que un técnico solo vea sus propias OTs). No filtrar en el controlador.
- **Cero HTTPException**: Los routers NO deben lanzar `HTTPException` ni usar `try/except` para errores de negocio comunes.
- **Validación de Existencia (Routers UI)**: Toda ruta de detalle (`/id/detalle`) DEBE validar la existencia del objeto y lanzar `RecursoNoEncontradoError` si es nulo.
- **Excepciones de Dominio**: Lanzar `RecursoNoEncontradoError` o `ReglaNegocioError`. El middleware global en `app_factory.py` se encarga de la respuesta.
- **Factory CRUD**: El 80% del CRUD se genera mediante `crear_modulo_crud_estandar()` de `factory_modulo.py`. No reinventar la rueda si el factory lo resuelve.

### 3. Frontend y Reactividad
- **HTMX Primero**: Prohibido usar `fetch` o `axios` crudos si HTMX puede hacerlo (`hx-get`, `hx-post`, etc.).
- **Macros de Jinja**: Usar componentes en `web/templates/ui/macros/components.html` (ej. `comp.status_badge`, `comp.money`, `comp.info_row`) para garantizar uniformidad visual y estética "Premium".
- **Robustez de Datos (Filtros Security)**: PROHIBIDO usar métodos de Python directamente en plantillas sobre campos que puedan ser `None` (como `.strftime()`, `.upper()`). Es OBLIGATORIO usar los filtros de seguridad `| fmt_date`, `| fmt_currency`, etc., que manejan nulos con un fallback de `-`.
- **Columnas Virtuales**: Usar `columnas_incluir` en el descriptor para mostrar campos que no existen en el modelo (virtuales). El sistema en `utiles_esquema.py` permite esto.
- **Navegación Robusta**: Usar `hx-boost="false"` en enlaces que naveguen a módulos diferentes o detalles profundos para evitar errores de renderizado parcial.
- **Snapshots**: Los documentos transaccionales (Cotizaciones, OT, OC) deben guardar una copia plana de los datos del cliente/proveedor para integridad histórica.
- **Nunca usar print()**: Usar el logger de la aplicación (`logging.getLogger("teamsa.modulo")`).
- **Nunca usar alert()**: Usar `mostrarError(mensaje)` en el frontend.

### 4. Servicios de Aplicación (`*_servicios.py`)
- **Cuándo usarlos**: Si un repositorio necesita instanciar otro repositorio de un módulo diferente, ese código pertenece a un **Servicio de Aplicación** (`modulo_servicios.py`), no al repositorio.
- **Template Method**: `ServicioDocumentoFinanciero` en `app/base/servicios_documentos.py` estandariza la creación de documentos financieros (Cotizaciones, OCs).
- **Ejemplo canónico**: `cotizaciones_servicios.py → ServicioAplicacionCotizacion` orquesta consultas que cruzan `RepositorioCotizacion` y `RepositorioOrden`.

### 5. Módulos del Sistema (RBAC)
- **Fuente de verdad**: Usar `ModuloSistema` (en `app/base/modulos_sistema.py`) para referenciar módulos. Nunca usar strings literales para nombres de módulos.
- **Permisos granulares**: `para_modulo(modulo, accion)` de `app/rutas/permisos.py`. Acciones: `ver`, `crear`, `editar`, `eliminar`.
- **Para agregar módulo nuevo**: 1) Añadir a `ModuloSistema`, 2) Crear carpeta en `app/modulos/`, 3) Registrar router en `app_factory.py`.

## 🚀 Áreas de Oportunidad Continuas
- **Validadores SQLModel**: Usar siempre `check_fields=False` en `@field_validator` para evitar conflictos de metadatos con SQLModel.
- **Service Layers**: Migrar lógica compleja de los repositorios hacia clases de `Servicio`.
- **Estandarización de Wizard**: Asegurar que las interacciones del Wizard de Cotizaciones y Órdenes de Compra sean homólogas.

---
*Este manual debe ser consultado antes de iniciar cualquier refactorización o nueva funcionalidad.*
