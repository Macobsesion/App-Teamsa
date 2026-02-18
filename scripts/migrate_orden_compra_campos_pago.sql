-- Migración: Reemplazar campos moneda/terminos_pago por metodo_pago/forma_pago en tabla orden_compra
-- Fecha: 2026-02-09
-- Descripción: Actualizar campos para usar catálogos SAT de métodos y formas de pago

-- IMPORTANTE: Hacer backup antes de ejecutar
-- pg_dump -U teamsa_user -h localhost -d teamsa_db -t orden_compra > backup_orden_compra.sql

BEGIN;

-- 1. Agregar las nuevas columnas
ALTER TABLE orden_compra 
ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(20) DEFAULT 'POR_DEFINIR',
ADD COLUMN IF NOT EXISTS forma_pago VARCHAR(2) DEFAULT '99';

-- 2. Migrar datos existentes (mapeo aproximado)
-- Si había moneda MXN y términos "Contado" -> PUE (Pago en Una Exhibición) + 01 (Efectivo)
-- Si había términos con "Crédito" -> PPD (Pago en Parcialidades) + 99 (Por definir)
UPDATE orden_compra
SET 
    metodo_pago = CASE 
        WHEN terminos_pago ILIKE '%crédito%' OR terminos_pago ILIKE '%credito%' THEN 'PPD'
        WHEN terminos_pago ILIKE '%contado%' THEN 'PUE'
        ELSE 'POR_DEFINIR'
    END,
    forma_pago = CASE
        WHEN terminos_pago ILIKE '%efectivo%' THEN '01'
        WHEN terminos_pago ILIKE '%transferencia%' THEN '03'
        WHEN terminos_pago ILIKE '%cheque%' THEN '02'
        ELSE '99'
    END
WHERE metodo_pago IS NULL OR forma_pago IS NULL;

-- 3. Eliminar las columnas antiguas
ALTER TABLE orden_compra 
DROP COLUMN IF EXISTS moneda,
DROP COLUMN IF EXISTS terminos_pago;

-- 4. Establecer los valores por defecto y NOT NULL si aplica
ALTER TABLE orden_compra 
ALTER COLUMN metodo_pago SET DEFAULT 'POR_DEFINIR',
ALTER COLUMN forma_pago SET DEFAULT '99';

COMMIT;

-- Verificar migración
SELECT id, folio, metodo_pago, forma_pago FROM orden_compra LIMIT 5;
