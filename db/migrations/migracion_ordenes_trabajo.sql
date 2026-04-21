-- Migración: Crear tablas para Órdenes de Trabajo (Saneada)
-- SIN precios, descuentos ni totales

CREATE TABLE IF NOT EXISTS orden_trabajo (
    id SERIAL PRIMARY KEY,
    numero_ot VARCHAR NOT NULL UNIQUE,  -- Estandarizado a numero_ot como en el modelo
    
    -- Referencias
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    cotizacion_id INTEGER REFERENCES cotizaciones(id), -- Corregido a cotizaciones
    
    -- Snapshot del cliente (Estandarizado con el modelo actual)
    cliente_nombre VARCHAR,
    domicilio TEXT,
    contacto VARCHAR,
    
    -- Estado y fechas
    estado VARCHAR DEFAULT 'pendiente' NOT NULL,
    fecha_programada DATE,
    hora_programada VARCHAR, -- Estandarizado
    duracion INTEGER DEFAULT 1,
    unidad_duracion VARCHAR DEFAULT 'horas',
    
    -- Asignación
    tecnico_id INTEGER REFERENCES usuario(id),
    tecnico_nombre VARCHAR,
    
    -- Notas
    notas_publicas TEXT,
    notas_privadas TEXT,
    
    -- Auditoría
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_modificacion TIMESTAMP,
    creado_por VARCHAR,
    modificado_por VARCHAR
);

-- Índices para orden_trabajo
CREATE INDEX IF NOT EXISTS idx_orden_trabajo_cliente ON orden_trabajo(cliente_id);
CREATE INDEX IF NOT EXISTS idx_orden_trabajo_cotizacion ON orden_trabajo(cotizacion_id);
CREATE INDEX IF NOT EXISTS idx_orden_trabajo_estado ON orden_trabajo(estado);
CREATE INDEX IF NOT EXISTS idx_orden_trabajo_tecnico ON orden_trabajo(tecnico_id);
CREATE INDEX IF NOT EXISTS idx_orden_trabajo_numero ON orden_trabajo(numero_ot);

-- Comentarios
COMMENT ON TABLE orden_trabajo IS 'Órdenes de trabajo generadas desde cotizaciones - SIN precios ni totales';
COMMENT ON COLUMN orden_trabajo.numero_ot IS 'Número único formato OT-00001';
COMMENT ON COLUMN orden_trabajo.notas_publicas IS 'Notas públicas copiadas de cotización';


CREATE TABLE IF NOT EXISTS concepto_orden_trabajo (
    id SERIAL PRIMARY KEY,
    orden_id INTEGER NOT NULL REFERENCES orden_trabajo(id) ON DELETE CASCADE,
    
    -- Referencia al concepto original
    concepto_cotizacion_id INTEGER REFERENCES conceptocotizacion(id),
    
    -- Información del servicio (snapshot)
    descripcion TEXT NOT NULL,
    cantidad DECIMAL(10,2) DEFAULT 1.0 NOT NULL,
    unidad VARCHAR DEFAULT 'Servicio',
    
    estado VARCHAR DEFAULT 'pendiente',
    fecha_completado TIMESTAMP,
    colaboradores_nombres TEXT,
    
    -- Auditoría parcial para el concepto
    creado_por VARCHAR,
    fecha_creacion TIMESTAMP DEFAULT NOW()
);

-- Índices para concepto_orden_trabajo
CREATE INDEX IF NOT EXISTS idx_concepto_ot_orden ON concepto_orden_trabajo(orden_id);
CREATE INDEX IF NOT EXISTS idx_concepto_ot_ref ON concepto_orden_trabajo(concepto_cotizacion_id);

-- Comentarios
COMMENT ON TABLE concepto_orden_trabajo IS 'Conceptos de órdenes de trabajo - Snapshot del trabajo a realizar';
