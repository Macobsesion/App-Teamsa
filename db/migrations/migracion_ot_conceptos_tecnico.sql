-- Migración: Nuevo flujo de Órdenes de Trabajo
-- Fecha: 2026-02-21
-- Cambios:
--   1. Nuevos campos en ordentrabajo: tecnico_id, tecnico_nombre
--   2. Nueva tabla: concepto_orden_trabajo (conceptos seleccionados para una OT)

-- ============================================================
-- 1. Campos de técnico en ordentrabajo
-- ============================================================
ALTER TABLE ordentrabajo
    ADD COLUMN IF NOT EXISTS tecnico_id INTEGER REFERENCES usuario(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS tecnico_nombre VARCHAR;

CREATE INDEX IF NOT EXISTS ix_ordentrabajo_tecnico_id ON ordentrabajo(tecnico_id);

-- ============================================================
-- 2. Nueva tabla concepto_orden_trabajo
-- ============================================================
CREATE TABLE IF NOT EXISTS concepto_orden_trabajo (
    id          SERIAL PRIMARY KEY,
    
    -- Relaciones
    orden_id                INTEGER NOT NULL REFERENCES ordentrabajo(id) ON DELETE CASCADE,
    concepto_cotizacion_id  INTEGER NOT NULL UNIQUE REFERENCES conceptocotizacion(id),
    -- UNIQUE garantiza que un concepto solo pueda estar en UNA OT
    
    -- Snapshot del concepto al crear la OT
    descripcion      VARCHAR NOT NULL,
    cantidad         NUMERIC(10, 2) NOT NULL,
    precio_unitario  NUMERIC(10, 2) NOT NULL,
    importe          NUMERIC(10, 2) NOT NULL,
    unidad           VARCHAR NOT NULL,
    
    -- Estado irreversible: pendiente → completado
    estado           VARCHAR NOT NULL DEFAULT 'pendiente',
    fecha_completado TIMESTAMP,
    completado_por   VARCHAR
);

CREATE INDEX IF NOT EXISTS ix_concepto_ot_orden_id ON concepto_orden_trabajo(orden_id);
CREATE INDEX IF NOT EXISTS ix_concepto_ot_estado   ON concepto_orden_trabajo(estado);
