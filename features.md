# Features — TEAMSA App v2.0 (Dev)

Listado de nuevas funcionalidades implementadas en la versión de desarrollo respecto a la versión de producción actual.

---

## 🆕 Módulos Nuevos

### 1. Módulo de Auditoría (`auditoria/`)
Panel administrativo para consultar el historial de actividad de usuarios en el sistema.

- **Tabla `logs_actividad`**: Registra cada acción relevante (CREAR, EDITAR, ELIMINAR, LOGIN, COMPLETAR_CONCEPTO, FINALIZAR, CANCELAR, REASIGNAR, REPROGRAMAR).
- **Filtros por módulo, usuario, acción y búsqueda libre** (campo `q`).
- **Trazabilidad completa**: Se registra usuario, fecha/hora, módulo afectado, detalles descriptivos e IP del cliente.
- **Arquitectura desacoplada**: `ServicioLogs` usa una sesión independiente para que los logs se guarden incluso si la operación principal falla.
- **Archivos**: `auditoria_repositorio.py`, `auditoria_router.py`, `logs_modelo.py`, `logs_servicio.py`.

### 2. Módulo de Cronograma (`cronograma/`)
Vista de calendario mensual que muestra OTs y Viáticos de forma visual.

- **Renderizado por mes** con navegación entre meses.
- **API de eventos** (`/api/cronograma/eventos`) que retorna OTs y Viáticos como JSON.
- **Filtro por rol**: Los técnicos solo ven sus OTs y viáticos asignados.
- **Soporte multi-día**: OTs con duración en días se muestran como bloques.
- **Estados visuales dinámicos** (programada, en_curso, fase_final).

---

## 🔄 Refactorizaciones Mayores

### 3. Renombrado de Módulo: `ordenes/` → `ordenes_trabajo/`
- **Tabla SQL**: `ordentrabajo` → `orden_trabajo` (migración incluida).
- **Archivos**: Todos renombrados de `ordenes_*` a `ordenes_trabajo_*`.
- **Módulo en `ModuloSistema`**: Cambiado de `"ordenes"` a `"ordenes_trabajo"`.
- **Herencia de esquemas**: El modelo `OrdenTrabajo` ahora hereda de `OrdenTrabajoBase` (esquema compartido), cumpliendo la Regla 1 de catálogos limpios.

### 4. Estado de Cotización: `ENVIADA` → `EMITIDA`
- Nomenclatura más precisa del dominio fiscal mexicano.
- Migración de datos incluida para actualizar registros existentes.

### 5. Firma de `RepositorioCRUD.crear()` unificada
- **Antes**: `crear(**kwargs)` (keyword arguments)
- **Ahora**: `crear(datos: Mapping)` (dict positional)
- Permite pre-procesamiento de datos con el hook `_pre_procesar_datos_creacion()`.
- Blindaje de auditoría: `creado_por` y `modificado_por` nunca son nulos.

---

## 🏗️ Infraestructura y Mixins

### 6. Sistema de Auditoría Automática (AuditMixin + ContextVar)
- **`contexto.py`**: `ContextVar` para almacenar identidad del usuario en el hilo actual.
- **`eventos_inicializar.py`**: Registro centralizado de suscriptores a eventos de dominio.
- **`AuditMixin` mejorado**: Ahora incluye listeners de SQLAlchemy (`before_insert`/`before_update`) que inyectan automáticamente `creado_por`/`modificado_por` desde el contexto.
- **Middleware de identidad**: Extrae el usuario del JWT y lo establece en el `ContextVar` para cada petición.

### 7. Mixins de Dominio Nuevos
- **`MixinEstadoDocumento`**: Transiciones polimórficas de estado (finalizar/cancelar) que buscan automáticamente el valor correcto del Enum.
- **`MixinFolioMensual`**: Generación de folios con secuencia mensual reutilizable (`PREFIJO-YYMM-NN`).
- **`SnapshotClienteMixin` / `SnapshotProveedorMixin`**: Capturan datos históricos de catálogos con `capturar_datos_cliente()` / `capturar_datos_proveedor()` + Value Objects de Dirección.

### 8. Zona Horaria Centralizada (`timezone.py`)
- **`ahora_mexico()`**: datetime actual en UTC-6 (CDMX).
- **`hoy_mexico()`**: fecha actual en UTC-6.
- **`calcular_estado_temporal()`**: Cálculo dinámico de estados visuales basado en fechas.
- Elimina la dependencia de `date.today()` / `datetime.now()` que asumían zona del servidor.

---

## 📈 Mejoras de Funcionalidad

### 9. OTs con Duración en Días
- **Nuevo campo**: `unidad_duracion` (horas/días) en `OrdenTrabajoBase`.
- **Estado visual dinámico**: `estado_visual` calcula si la OT está `en_curso` o en `fase_final` basándose en fechas y zona horaria de México.
- **Detección de empalme mejorada**: `verificar_empalme_tecnico()` ahora maneja solapamiento de rangos de fecha para OTs multi-día y también detecta empalmes con Viáticos.

### 10. Estado `CANCELADO` en Conceptos de OT
- **Antes**: Solo `PENDIENTE` → `COMPLETADO`.
- **Ahora**: Incluye `CANCELADO` para conceptos que se cancelan por cascada.
- **Cascada al cancelar OT**: Todos los conceptos pendientes se marcan como `CANCELADO`.

### 11. Estado `FASE_FINAL` en OTs
- **Nuevo estado visual** (no persistido): Indica que el tiempo estimado expiró pero la OT no ha sido finalizada manualmente.
- Permite distinguir entre OTs en progreso y las que requieren atención del administrador.

### 12. Reprogramación de OTs con Sincronización
- **`reprogramar_orden()`**: Cambia fecha/hora de la OT y sincroniza automáticamente los viáticos vinculados.
- Valida empalmes del técnico antes de reprogramar.

### 13. Reasignación de Técnico con Sincronización
- **`reasignar_tecnico()`**: Cambia el técnico asignado y sincroniza automáticamente el `responsable_id` de los viáticos vinculados.

### 14. Constantes y Configuración Mejoradas
- **`STATIC_DIR`** y **`UPLOADS_DIR`** como constantes centralizadas.
- **`get_upload_root()`**: Función dinámica para resolver la ruta de uploads.
- **`FIRMA_PDF`**: Ruta a imagen de firma para PDFs.
- **`PREFIJO_NUMERO_ORDEN_COMPRA`**: Constante para folios de OC.
- **`PROJECT_NAME`** y **`DEBUG`**: Configuración mejorada con control de docs API.

### 15. Generador de PDF Mejorado (`GeneradorPDFDocumento`)
- **Template Method Pattern**: Clase abstracta `GeneradorPDFDocumento` con `_obtener_entidad()` y `_construir_contexto()`.
- **`imagen_a_data_uri()`**: Convierte imágenes a data URI con detección automática de MIME.
- **Soporte para firma**: Incluye `firma_responsable` en los assets del PDF.

### 16. Catálogo de Estados de México
- **`catalogos.py`**: Lista completa de 32 estados para formularios de dirección.

---

## 🛡️ Mejoras de Seguridad y Robustez

### 17. `RepositorioCRUD` Mejorado
- **`_validar_eliminacion()`**: Hook invocado antes de eliminar, permite validar dependencias y lanzar `ReglaNegocioError`.
- **`flush()` antes de `commit()`**: Atrapa constraints de BD antes del commit.
- **Logging de transacciones**: Errores loggeados con nombre del modelo.
- **`aplicar_seguridad_filtro()`**: Hook para Row-Level Security (RLS) basada en el actor.

### 18. Exception Handlers Mejorados
- **`RequestValidationError`**: Handler para errores de validación de formularios.
- **`_renderizar_pagina_de_error()`**: Inyecta contexto de usuario en páginas de error para que la navbar funcione.
- **Detección HTMX**: Los handlers distinguen entre peticiones HTML completas y fragmentos HTMX.

### 19. ServicioDocumentoFinanciero Mejorado
- **Inyección de repositorio** en lugar de sesión directa.
- **Guardado delegado al repositorio** para asegurar auditoría y Domain Events.

---

## 📁 Archivos Nuevos (Resumen)

| Archivo | Tipo |
|---------|------|
| `app/base/catalogos.py` | Datos |
| `app/base/logs_modelo.py` | Modelo |
| `app/base/logs_servicio.py` | Servicio |
| `app/base/mixin_estado.py` | Mixin |
| `app/base/mixin_repositorio.py` | Mixin |
| `app/base/mixins_snapshots.py` | Mixin |
| `app/base/timezone.py` | Utilidad |
| `app/nucleo/contexto.py` | Infraestructura |
| `app/nucleo/eventos_inicializar.py` | Infraestructura |
| `app/modulos/auditoria/*` | Módulo completo |
| `app/modulos/cronograma/*` | Módulo completo |
| `app/rutas/rt_admin.py` | Ruta |
| `app/rutas/rt_catalogos.py` | Ruta |

---

## 📊 Migraciones de Base de Datos

| # | ID | Descripción |
|---|-----|-------------|
| 6 | `ef321a123f4a` | FK `viatico_id` en `conceptocotizacion` |
| 7 | `a1347a9d9e40` | Snapshots y validadores en viáticos |
| 8 | `e63da54c712d` | Campos de snapshot adicionales (última con `ordentrabajo`) |
| 9 | `c7a8b9d0e1f2` | ★ Rename tabla `ordentrabajo` → `orden_trabajo` + FKs |
| 10 | `bf5b4b69df12` | Campos faltantes en viáticos (ya con `orden_trabajo`) |
| 11 | `2013841ebed6` | Auditoría en tablas de detalle |
| 12 | `d824c3e15993` | Elimina UNIQUE en `concepto_ot.concepto_cotizacion_id` |
| 13 | `a1b2c3d4e5f6` | Costos detallados viáticos (peajes, estacionamiento) |
| 14 | `567193e68bcd` | Tabla `logs_actividad` |
| 15 | `d8b9c0e1f2a3` | ★ Enum cotizaciones `enviada` → `emitida` |
