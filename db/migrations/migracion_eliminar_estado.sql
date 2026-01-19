-- Migración: Eliminar columna "estado" de cliente y proveedor
-- Fecha: 2025-12-18
-- Motivo: Simplificar modelo de datos - el campo estado (texto) no se usa para gestión de ubicaciones

-- Eliminar columna estado de cliente (tabla en singular)
ALTER TABLE IF EXISTS cliente DROP COLUMN IF EXISTS estado;

-- Eliminar columna estado de proveedor (tabla en singular)
ALTER TABLE IF EXISTS proveedor DROP COLUMN IF EXISTS estado;

-- Nota: Esta migración es segura porque:
-- 1. Los campos son NULL por defecto
-- 2. No son FK ni tienen índices críticos
-- 3. Se eliminan del modelo y todos los esquemas
