# Contexto del Proyecto TEAMSA App

## Visión General
Esta aplicación es un **Sistema Administrativo y Operativo (ERP Custom)** diseñado para TEAMSA. El sistema gestiona todo el ciclo comercial y operativo de la empresa, desde la prospección comercial hasta la ejecución en campo de servicios.

## Stack Tecnológico Principal
- **Backend**: Python 3.11+, FastAPI, SQLModel (SQLAlchemy 2.0).
- **Frontend**: HTML nativo, Jinja2 Templates, HTMX (para la hipermedia), Tailwind/CSS Nativo estandarizado.
- **Base de Datos**: PostgreSQL (o MySQL), manejado mediado por Alembic e interacciones con el repositorio abstracto.
- **Generación Documental**: WeasyPrint para renders PDF de comprobantes (Cotizaciones, Ordenes de Compra, etc).

## Flujo de Negocio Principal
1. **Clientes y Proveedores**: Entidades base (Catálogos).
2. **Servicios**: Productos o labores ofrecidas, enlazadas con códigos SAT (ej. "H87").
3. **Cotizaciones**: Documentos originados a clientes (maestros). Poseen **versiones** (ej. COT-001-B). Incorporan **Conceptos**.
4. **Órdenes de Trabajo (OT)**: Detonan la ejecución de una Cotización finalizada. Tienen fechas de agendamiento y guardan un *snapshot* irreversible de los datos del cliente al momento de crearse para evitar que ediciones futuras en el catálogo del cliente corrompan la orden histórica.
5. **Órdenes de Compra (OC)**: Detonan el abastecimiento con Proveedores mediante los `Servicios_Proveedores`.

## Patrones Arquitectónicos Clave
1. **Factoría y Repositorio Genérico (`enrutador_crud.py` | `repositorio.py`)**:
   El 80% de las rutas repetitivas de CRUD se generan dinámicamente usando fábricas para evitar duplicación, exponiendo Endpoints de API (`/api/modulo`) y Endpoints de Front (`/ui/modulo`).
2. **Excepciones Limpias (KISS)**:
   La aplicación posee un middleware transaccional en `app_factory.py`. Las subcapas (Modelos, Repos y Controladores/Routers) **NUNCA levantan HTTPException**; solo deben fallar en voz alta retornando Excepciones de Dominio locales como `RecursoNoEncontradoError()`, `ReglaNegocioError()`, dejándole al Global Handler convertirlos en el estado HTTP.
3. **Herencia de SQLModel (En Catálogos)**:
   Los módulos de catálogo (Clientes, Proveedores, Servicios) definen sus metadatos (index=True, max_length) en Esquemas Base que heredan directamente de `SQLModel` en `_esquemas.py`. Sus tablas en `_modelo.py` proceden luego a heredar de estos Base esquivas la duplicación.
4. **Mixins Financieros (En Transaccionales)**:
   Entidades pesadas como Cotizaciones y Ordenes extienden de Clases Base (`BaseDocumento`, `MixinDetalleFinanciero`) para aplicar lógicas polimórficas (como recalcular totales y el IVA).
5. **RBAC Dinámico (Permisos por Usuario)**:
   Se abandonó el sistema de tablas de permisos fijas por un sistema basado en **Listas JSON** dentro del modelo `Usuario` (`permisos_ver`, `permisos_crear`, etc.). Esto permite una gestión ágil desde la UI sin migraciones complejas.
6. **Template Method en Servicios (`ServicioDocumentoFinanciero`)**:
   La creación de documentos financieros (Cotizaciones, OCs) sigue un patrón de plantilla que estandariza la instanciación, el snapshot de cliente/proveedor, la generación de folios y el cálculo de conceptos. Todo nuevo servicio de creación DEBE heredar de esta clase base en `app/base/servicios_documentos.py`.
7. **Paginación y Búsqueda Automatizada**:
   El sistema de CRUD genérico integra paginación nativa a través de `RepositorioCRUD.contar()` y el enrutador de UI. Además, el buscador permite lógica personalizada mediante el hook `_condiciones_busqueda_personalizada` para realizar búsquedas en relaciones (ej: buscar cotizaciones por nombre de servicio).
8. **Interacción HTMX y Notificaciones Premium**:
   Se utilizan fragmentos HTML (parciales) para actualizaciones dinámicas. Los errores se notifican mediante un sistema unificado de **Toasts** inyectados desde el backend o lanzados por JS (`mostrarError()`) con estética "Premium" (barra de progreso y glassmorphism).

## Reglas de Oro para la IA
- **Nunca** uses `print()`; usa el logger de la aplicación.
- **Nunca** uses `alert()`; usa `mostrarError(mensaje)` en el frontend.
- **Nunca** levantes `HTTPException` en la capa de Repo o Servicio; usa excepciones de dominio.
- **Siempre** usa el repositorio para persistencia; evita usar la sesión de SQLModel directamente si ya existe un repo.
- **Idioma**: Mantén nombres de variables y comentarios en **Español**.

