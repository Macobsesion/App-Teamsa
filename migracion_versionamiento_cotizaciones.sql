-- Migración: Agregar campos de versionamiento y notas privadas a cotizaciones
-- Fecha: 2025-12-29
-- Propósito: Implementar sistema de versionamiento automático de cotizaciones

-- 1. Agregar campos de versionamiento
ALTER TABLE cotizacion ADD COLUMN numero_version VARCHAR(50);
ALTER TABLE cotizacion ADD COLUMN version_letra VARCHAR(10);
ALTER TABLE cotizacion ADD COLUMN cotizacion_original_id INTEGER REFERENCES cotizacion(id);

-- 2. Agregar campo de notas privadas
ALTER TABLE cotizacion ADD COLUMN notas_privadas TEXT;

-- 3. Agregar campo para relación con orden de trabajo (FK se agregará después)
ALTER TABLE cotizacion ADD COLUMN orden_trabajo_id INTEGER;

-- 4. Crear índices para búsqueda eficiente
CREATE INDEX idx_cotizacion_numero_version ON cotizacion(numero_version);
CREATE INDEX idx_cotizacion_original_id ON cotizacion(cotizacion_original_id);

-- 5. Migrar datos existentes: copiar numero a numero_version para cotizaciones antiguas
UPDATE cotizacion
SET numero_version = numero,
    version_letra = NULL
WHERE numero_version IS NULL;

--6. Hacer numero_version NOT NULL después de la migración
ALTER TABLE cotizacion ALTER COLUMN numero_version SET NOT NULL;

-- 7. Comentarios para documentación
COMMENT ON COLUMN cotizacion.numero_version IS 'Número completo incluyendo versión, ej: COT-001-B';
COMMENT ON COLUMN cotizacion.version_letra IS 'Letra de versión: NULL (original), B, C, ..., Z, AA, AB, etc.';
COMMENT ON COLUMN cotizacion.cotizacion_original_id IS 'ID de la cotización original si esta es una versión';
COMMENT ON COLUMN cotizacion.notas_privadas IS 'Notas internas que NO se copian a órdenes de trabajo';
COMMENT ON COLUMN cotizacion.orden_trabajo_id IS 'Orden de trabajo generada desde esta cotización';
