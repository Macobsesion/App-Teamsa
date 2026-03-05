-- Migración manual para agregar campos de Snapshot (Congelamiento Histórico) a Documentos Comerciales

-- TABLA: cotizaciones
-- Se agregan campos de espejo para el cliente
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS cliente_nombre VARCHAR;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS cliente_rfc VARCHAR(13);
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS cliente_direccion VARCHAR;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS cliente_ciudad VARCHAR;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS cliente_cp VARCHAR(5);
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS cliente_telefono VARCHAR;
ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS cliente_email VARCHAR;

-- TABLA: orden_compra
-- Se agregan campos de espejo para el proveedor
ALTER TABLE orden_compra ADD COLUMN IF NOT EXISTS proveedor_nombre VARCHAR;
ALTER TABLE orden_compra ADD COLUMN IF NOT EXISTS proveedor_rfc VARCHAR(13);
ALTER TABLE orden_compra ADD COLUMN IF NOT EXISTS proveedor_direccion VARCHAR;
ALTER TABLE orden_compra ADD COLUMN IF NOT EXISTS proveedor_ciudad VARCHAR;
ALTER TABLE orden_compra ADD COLUMN IF NOT EXISTS proveedor_cp VARCHAR(5);
ALTER TABLE orden_compra ADD COLUMN IF NOT EXISTS proveedor_telefono VARCHAR;
ALTER TABLE orden_compra ADD COLUMN IF NOT EXISTS proveedor_email VARCHAR;

-- (Opcional) Script de Data Migration para llenar retroactivamente las filas existentes
-- Utilizando los datos de la relación actual
UPDATE cotizaciones
SET cliente_nombre = c.nombre,
    cliente_rfc = c.rfc,
    cliente_direccion = c.direccion,
    cliente_ciudad = c.ciudad,
    cliente_cp = c.cp,
    cliente_telefono = c.telefono,
    cliente_email = c.email
FROM cliente c
WHERE cotizaciones.cliente_id = c.id
  AND cotizaciones.cliente_nombre IS NULL;

UPDATE orden_compra
SET proveedor_nombre = p.nombre,
    proveedor_rfc = p.rfc,
    proveedor_direccion = p.direccion,
    proveedor_ciudad = p.ciudad,
    proveedor_cp = p.cp,
    proveedor_telefono = p.telefono,
    proveedor_email = p.email
FROM proveedor p
WHERE orden_compra.proveedor_id = p.id
  AND orden_compra.proveedor_nombre IS NULL;
