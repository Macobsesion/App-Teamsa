---
description: Reglas de Arquitectura y Desarrollo a Seguir para el AI
---

# Reglas Arquitectónicas de TEAMSA App

Al operar o modificar este proyecto, la IA **DEBE SIEMPRE** someterse a las siguientes directrices sin excepción, favoreciendo la filosofía KISS (Keep It Simple, Stupid) y nuestra abstracción preestablecida.

## 1. Patrones de Base de Datos y Modelado (SQLModel)
- **Catálogos Limpios**: Cuando se modifiquen atributos de entidades planas (como `Cliente`, `Proveedor`), el AI debe usar la Herencia SQLModel. Las propiedades con `Field(...)` deben residir **una única vez** en el archivo `modulo_esquemas.py` (ej: `clientes_esquemas.py` -> `class ClienteBase(SQLModel)`). El modelo físico en `modulo_modelo.py` (ej: `clientes_modelo.py`) DEBE heredar de dicha clase sin reescribir los atributos.
- **Evitar la "Magia" Pydantic**: No crear metaclases dinámicas ni constructores abstractos que oculten el autocompletado del IDE para esquemas de Actualización (`Update`).
- **Nombres Hispánicos**: Variables, funciones y Tablas SQL van en Español (`modificado_por`, `fecha_creacion`).

## 2. Reglas de Controladores y Endpoints (Routers)
- **Cero Try-Catch HTTP**: Los Endpoints de FastAPI (`_router.py`) NUNCA deben usar un bloque `try-except` para atrapar un error explícito del negocio. NUNCA lanzar `HTTPException`.
- **Excepciones de Dominio**: Si un repositorio no puede encontrar un ID, solo usa `raise RecursoNoEncontradoError("Mensaje")`. Si hay un candado de negocio, se debe levantar únicamente `raise ReglaNegocioError("Causa")`. El middleware de `app/nucleo/app_factory.py` es el único responsable de transformar las fallas a JSON o HTML (400, 404, 500).
- **Validadores SQLModel**: Al usar `@field_validator` en campos de SQLModel, SIEMPRE incluir `check_fields=False` para evitar conflictos con los metadatos de Pydantic v2.

## 3. Frontend Interactivo (HTMX + Jinja2)
- **Prohibido Fetch/Axios JS Crudos**: Toda la interacción Reactiva y Asíncrona con el Backend debe manejarse con directivas de base de `htmx.org` (`hx-get`, `hx-post`, `hx-target`, `hx-swap`). Evitar introducir librerías de JS espagueti innecesarias si HTMX puede resolverlo.
- **Componentes Macro Dinámicos**: Usar los imports de Jinja `{% macro %}` alojados en `web/templates/ui/macros/` para renderizar Botones, Alertas y Tablas transversales, garantizando homogeneidad visual.

## 4. Evolución Hacia Service Layers
- Las validaciones extensas y cálculos de negocio "inteligentes" (ej: "Saber si las fechas de un Técnico empalman la nueva OT") DEBEN alejarse gradualmente de los Repositorios de Base de Datos (`_repositorio.py`), cuya única razón de existir es hacer queries SQL. Estas reglas pesadas deben extraerse a un `Servicio` del Dominio (`_servicios.py`).

## 5. Auditorías de Desarrollo y Preferencias
- La IA debe utilizar estos principios cuando el usuario pida refactorizar código sin sobreescribir las funcionalidades de las transacciones (Ordenes, Ordenes_compra y Cotizaciones) que usan `MixinDetalleFinanciero` para estandarizar subtotales e IVAs.
