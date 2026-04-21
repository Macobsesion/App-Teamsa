-- Migración manual para agregar campos de Snapshot (Congelamiento Histórico) a Viáticos
-- TABLA: viaticos

ALTER TABLE viaticos ADD COLUMN IF NOT EXISTS cliente_direccion VARCHAR;
ALTER TABLE viaticos ADD COLUMN IF NOT EXISTS cliente_ciudad VARCHAR;
ALTER TABLE viaticos ADD COLUMN IF NOT EXISTS cliente_cp VARCHAR(5);
ALTER TABLE viaticos ADD COLUMN IF NOT EXISTS cliente_email VARCHAR;

-- Script de Data Migration para llenar retroactivamente las filas existentes
-- Utilizando los datos de la relación actual con el cliente
UPDATE viaticos
SET cliente_nombre = c.nombre,
    cliente_rfc = c.rfc,
    cliente_direccion = c.direccion,
    cliente_ciudad = c.ciudad,
    cliente_cp = c.cp,
    cliente_email = c.email_facturacion
FROM cliente c
WHERE viaticos.cliente_id = c.id
  AND viaticos.cliente_direccion IS NULL;
