-- Migración: Agregar campos de pago SAT y código de unidad
-- Fecha: 2025-12-16

-- 1. Agregar campo forma_pago a tabla cotizacion
ALTER TABLE cotizacion ADD COLUMN IF NOT EXISTS forma_pago VARCHAR(2) DEFAULT '99';

-- 2. Actualizar valores default de metodo_pago existentes  
UPDATE cotizacion SET metodo_pago = 'Por confirmar' WHERE metodo_pago = 'Transferencia SPEI' OR metodo_pago IS NULL;

-- 3. Agregar campo codigo_unidad a tabla servicio
ALTER TABLE servicio ADD COLUMN IF NOT EXISTS codigo_unidad VARCHAR(10) DEFAULT 'H87';

-- 4. Actualizar servicios existentes con códigos comunes
UPDATE servicio SET codigo_unidad = 'E48' WHERE unidad LIKE '%servicio%';
UPDATE servicio SET codigo_unidad = 'HUR' WHERE unidad LIKE '%hora%';
UPDATE servicio SET codigo_unidad = 'H87' WHERE codigo_unidad IS NULL OR codigo_unidad = '';

-- 5. Agregar campo codigo_unidad a tabla conceptocotizacion  
ALTER TABLE conceptocotizacion ADD COLUMN IF NOT EXISTS codigo_unidad VARCHAR(10) DEFAULT 'H87';

-- 6. Actualizar conceptos existentes basándose en la unidad
UPDATE conceptocotizacion SET codigo_unidad = 'E48' WHERE unidad LIKE '%servicio%';
UPDATE conceptocotizacion SET codigo_unidad = 'HUR' WHERE unidad LIKE '%hora%';
UPDATE conceptocotizacion SET codigo_unidad = 'H87' WHERE codigo_unidad IS NULL OR codigo_unidad = '';

-- Verificar cambios
SELECT 'Cotizaciones con forma_pago:' as info, COUNT(*) FROM cotizacion WHERE forma_pago IS NOT NULL;
SELECT 'Servicios con codigo_unidad:' as info, COUNT(*) FROM servicio WHERE codigo_unidad IS NOT NULL;
SELECT 'Conceptos con codigo_unidad:' as info, COUNT(*) FROM conceptocotizacion WHERE codigo_unidad IS NOT NULL;
