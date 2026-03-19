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
5. **Idioma**:
   El código y la base de datos se manejan exclusivamente en **Español**.
