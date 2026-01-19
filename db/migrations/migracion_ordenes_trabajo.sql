-- Migración: Crear tablas para Órdenes de Trabajo
-- SIN precios, descuentos ni totales

CREATE TABLE IF NOT EXISTS ordentrabajo (
    id SERIAL PRIMARY KEY,
    numero VARCHAR NOT NULL UNIQUE,
    
    -- Referencias
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    cotizacion_id INTEGER REFERENCES cotizacion(id),
    
    -- Estado y fechas
    estado VARCHAR DEFAULT 'pendiente' NOT NULL,
    fecha_programada DATE,
    fecha_inicio DATE,
    fecha_completada DATE,
    
    -- Asignación
    tecnico_asignado_id INTEGER REFERENCES usuario(id),
    
    -- Notas (solo públicas, NO privadas)
    notas TEXT,
    observaciones_tecnicas TEXT,
    
    -- Auditoría
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_modificacion TIMESTAMP,
    creado_por VARCHAR,
    modificado_por VARCHAR
);

-- Índices para ordentrabajo
CREATE INDEX IF NOT EXISTS idx_ordentrabajo_cliente ON ordentrabajo(cliente_id);
CREATE INDEX IF NOT EXISTS idx_ordentrabajo_cotizacion ON ordentrabajo(cotizacion_id);
CREATE INDEX IF NOT EXISTS idx_ordentrabajo_estado ON ordentrabajo(estado);
CREATE INDEX IF NOT EXISTS idx_ordentrabajo_tecnico ON ordentrabajo(tecnico_asignado_id);
CREATE INDEX IF NOT EXISTS idx_ordentrabajo_numero ON ordentrabajo(numero);

-- Comentarios
COMMENT ON TABLE ordentrabajo IS 'Órdenes de trabajo generadas desde cotizaciones - SIN precios ni totales';
COMMENT ON COLUMN ordentrabajo.numero IS 'Número único formato OT-00001';
COMMENT ON COLUMN ordentrabajo.notas IS 'Notas públicas copiadas de cotización';
COMMENT ON COLUMN ordentrabajo.observaciones_tecnicas IS 'Observaciones técnicas del trabajo realizado';


CREATE TABLE IF NOT EXISTS conceptoordentrabajo (
    id SERIAL PRIMARY KEY,
    orden_trabajo_id INTEGER NOT NULL REFERENCES ordentrabajo(id) ON DELETE CASCADE,
    
    -- Referencia opcional al servicio
    servicio_id INTEGER REFERENCES servicio(id),
    
    -- Información del servicio (SIN precios)
    descripcion TEXT NOT NULL,
    cantidad DECIMAL(10,2) DEFAULT 1.0 NOT NULL,
    unidad VARCHAR DEFAULT 'Servicio',
    codigo_unidad VARCHAR DEFAULT 'E48',
    codigo_sat VARCHAR
);

-- Índices para conceptoordentrabajo
CREATE INDEX IF NOT EXISTS idx_conceptoot_orden ON conceptoordentrabajo(orden_trabajo_id);
CREATE INDEX IF NOT EXISTS idx_conceptoot_servicio ON conceptoordentrabajo(servicio_id);

-- Comentarios
COMMENT ON TABLE conceptoordentrabajo IS 'Conceptos de órdenes de trabajo - SIN precio_unitario, descuento ni subtotal';
COMMENT ON COLUMN conceptoordentrabajo.cantidad IS 'Cantidad a realizar (no tiene precio asociado)';
COMMENT ON COLUMN conceptoordentrabajo.descripcion IS 'Descripción del servicio a realizar';
