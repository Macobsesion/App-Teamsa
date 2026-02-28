-- Migración: Auditoría completa en ConceptoOrdenTrabajo
-- Agrega campos creado_por y fecha_creacion para rastrear quién y cuándo
-- se creó el snapshot de cada servicio en una Orden de Trabajo.
--
-- Ejecutar dentro del contenedor:
--   docker-compose -f compose.yaml exec aplicacion psql $DATABASE_URL -f scripts/migrate_auditoria_concepto_ot.sql

ALTER TABLE concepto_orden_trabajo
    ADD COLUMN IF NOT EXISTS creado_por    VARCHAR NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now();

-- Comentario
COMMENT ON COLUMN concepto_orden_trabajo.creado_por    IS 'Usuario que creó este concepto (snapshot) en la OT';
COMMENT ON COLUMN concepto_orden_trabajo.fecha_creacion IS 'Marca temporal exacta en que se creó el snapshot';
