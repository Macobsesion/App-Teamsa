---
description: Reglas de Arquitectura y Desarrollo a Seguir para el AI
---

# Reglas Arquitectónicas de TEAMSA App

Al operar o modificar este proyecto, la IA **DEBE SIEMPRE** someterse a las siguientes directrices sin excepción, favoreciendo la filosofía KISS (Keep It Simple, Stupid) y nuestra abstracción preestablecida.

## 1. Patrones de Base de Datos y Modelado (SQLModel)
- **Catálogos Limpios**: Cuando se modifiquen atributos de entidades planas (como `Cliente`, `Proveedor`), el AI debe usar la Herencia SQLModel. Las propiedades con `Field(...)` deben residir **una única vez** en el archivo `modulo_esquemas.py` (ej: `clientes_esquemas.py` -> `class ClienteBase(SQLModel)`). El modelo físico en `modulo_modelo.py` (ej: `clientes_modelo.py`) DEBE heredar de dicha clase sin reescribir los atributos.
- **Evitar la "Magia" Pydantic**: No crear metaclases dinámicas ni constructores abstractos que oculten el autocompletado del IDE para esquemas de Actualización (`Update`).
- **Nombres Hispánicos**: Variables, funciones y Tablas SQL van en Español (`modificado_por`, `fecha_creacion`).
- **Prevención de Conflictos (Field)**: NUNCA importar `Field` de `pydantic` y `sqlmodel` en el mismo archivo sin aliasing. Usar `sqlmodel.Field` para modelos de DB para no romper la vinculación de claves foráneas por pérdida de metadatos.

## 2. Reglas de Capa de Datos y Seguridad (Repositorios)
- **RLS mediante Hooks**: El filtrado de seguridad por rol (ej: técnicos viendo solo sus OTs) DEBE implementarse en `RepositorioCRUD.aplicar_seguridad_filtro`. PROHIBIDO filtrar manualmente en los Routers para evitar fugas de datos en la API.
- **Cero Try-Catch HTTP**: Los Endpoints de FastAPI (`_router.py`) NUNCA deben usar un bloque `try-except` para atrapar un error explícito del negocio. NUNCA lanzar `HTTPException`.
- **Validación de Existencia (Routers UI)**: Toda ruta de detalle (`/id/detalle`) DEBE validar la existencia del objeto (ej. `if not objeto: raise RecursoNoEncontradoError`). Esto garantiza una respuesta 404 controlada y evita errores 500 en la capa de presentación.
- **Excepciones de Dominio**: Si un repositorio no puede encontrar un ID, solo usa `raise RecursoNoEncontradoError("Mensaje")`. Si hay un candado de negocio, se debe levantar únicamente `raise ReglaNegocioError("Causa")`. El middleware de `app/nucleo/app_factory.py` es el único responsable de transformar las fallas a JSON o HTML (400, 404, 500).
- **Validadores SQLModel**: Al usar `@field_validator` en campos de SQLModel, SIEMPRE incluir `check_fields=False` para evitar conflictos con los metadatos de Pydantic v2.

## 3. Frontend Interactivo (HTMX + Jinja2)
- **Prohibido Fetch/Axios JS Crudos**: Toda la interacción Reactiva y Asíncrona con el Backend debe manejarse con directivas de base de `htmx.org` (`hx-get`, `hx-post`, `hx-target`, `hx-swap`). Evitar introducir librerías de JS espagueti innecesarias si HTMX puede resolverlo.
- **Macros de Jinja Reutilizables**: Usar componentes en `web/templates/ui/macros/components.html` (ej. `comp.status_badge`, `comp.money`, `comp.info_row`) para garantizar homogeneidad visual y estética "Premium".
- **Robustez de Datos (Filtros Security)**: PROHIBIDO usar métodos de Python directamente en plantillas sobre campos que puedan ser `None` (como `.strftime()`, `.upper()`). Es OBLIGATORIO usar los filtros de seguridad `| fmt_date`, `| fmt_currency`, `| fmt_phone`, etc., definidos en `app/web/jinja.py`, que manejan nulos con un fallback de `-`.
- **Estandarización de Tablas**: Alinear montos a la derecha (`text-end`), estados al centro, y usar `text-nowrap` en folios/fechas.

## 4. Evolución Hacia Service Layers
- **Patrón de Servicios (Orquestadores)**: Estas reglas deben extraerse a un `Servicio` del Dominio (`_servicios.py`). Los servicios deben inyectar la `Session` de base de datos en su constructor y centralizar operaciones que involucren efectos secundarios (como inyectar conceptos en otros módulos) o validaciones multi-entidad. Se prefiere el uso de métodos de clase o estáticos solo para utilidades que no requieran estado complejo, pero para orquestación de flujo se deben instanciar.

## 5. Integridad de Snapshots e Inmutabilidad Histórica
- **Snapshots Físicos**: Los documentos financieros (`Cotizacion`, `OrdenCompra`, `OrdenTrabajo`) DEBEN persistir físicamente los datos del catálogo (`descripcion`, `unidad`, `precio`) en sus tablas de detalle. NUNCA se deben realizar `JOINs` al catálogo vivo para renderizar PDFs históricos.
- **Estrategia de Fusión (Merge)**: Al actualizar documentos con múltiples partidas, se debe usar una lógica que compare IDs de partidas existentes. NO se debe borrar y recrear todo (`delete all`), ya que esto puede causar pérdida de datos si el catálogo cambió o si el UI filtra elementos inactivos.
- **Independencia del Catálogo**: Un documento emitido debe ser legible (PDF) incluso si el Servicio o el Cliente asociado han sido eliminados o inactivados.
- **Pruebas de Inmutabilidad**: Cada nuevo campo de Snapshot añadido debe ser validado con una prueba que confirme que, tras modificar el registro original en el catálogo, el snapshot del documento histórico permanece intacto.

## 6. Protección de Borrado y RBAC Granular
- **Borrado Protegido**: Usar el hook `_validar_eliminacion(self, entidad)` en `RepositorioCRUD` para verificar dependencias antes de un `DB DELETE`. Se debe lanzar `ReglaNegocioError` con un mensaje amigable si el registro está en uso.
- **RBAC Independiente**: Los permisos de `ver`, `crear`, `editar` y `eliminar` son tratados como entidades separadas. Un agente de IA debe asegurar que las dependencias de FastAPI (FastAPI Depends) reflejen el permiso exacto de la acción (no usar 'editar' para proteger una ruta de 'borrar').
- **Preferencia por Inactivación**: Favorecer siempre el uso de `activo=False` sobre la eliminación física para mantener la integridad referencial del sistema.
