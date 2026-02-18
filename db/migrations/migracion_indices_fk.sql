-- Migración: Agregar índices a claves foráneas opcionales
-- Fecha: 2026-02-18
-- Motivo: Estandarizar índices en FK para mejorar rendimiento en JOINs y búsquedas
--
-- Tablas afectadas:
--   - cotizaciones.cotizacion_original_id  → búsquedas de versiones de cotización
--   - conceptocotizacion.servicio_id       → trazabilidad al catálogo de servicios
--   - detalle_orden_compra.servicio_proveedor_id → referencia al catálogo de compra
--
-- Nota: Estos campos son opcionales (NULL), PostgreSQL los indexa eficientemente.
-- Nota: IF NOT EXISTS garantiza que la migración es idempotente (segura de re-ejecutar).

CREATE INDEX IF NOT EXISTS ix_cotizaciones_cotizacion_original_id
    ON cotizaciones (cotizacion_original_id);

CREATE INDEX IF NOT EXISTS ix_conceptocotizacion_servicio_id
    ON conceptocotizacion (servicio_id);

CREATE INDEX IF NOT EXISTS ix_detalle_orden_compra_servicio_proveedor_id
    ON detalle_orden_compra (servicio_proveedor_id);
