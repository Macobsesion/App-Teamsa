-- ============================================================================
-- Script: Reiniciar IDs de todas las tablas excepto usuarios
-- Fecha: 2026-02-17
-- Propósito: Limpiar datos de prueba manteniendo usuarios para login
-- ============================================================================
-- 
-- ADVERTENCIA: Este script eliminará TODOS los datos excepto usuarios.
-- Asegúrate de tener un respaldo antes de ejecutar.
--
-- ============================================================================

BEGIN;

-- Deshabilitar triggers temporalmente para evitar problemas de FK
SET session_replication_role = 'replica';

-- ============================================================================
-- PASO 1: Eliminar registros de tablas de detalle (hijos primero)
-- ============================================================================

-- Detalles de cotizaciones
TRUNCATE TABLE conceptocotizacion RESTART IDENTITY CASCADE;

-- Detalles de órdenes de compra
TRUNCATE TABLE detalle_orden_compra RESTART IDENTITY CASCADE;

-- Detalles de órdenes de trabajo
TRUNCATE TABLE concepto_orden_trabajo RESTART IDENTITY CASCADE;

-- ============================================================================
-- PASO 2: Eliminar registros de tablas maestras (documentos)
-- ============================================================================

-- Órdenes de trabajo
TRUNCATE TABLE orden_trabajo RESTART IDENTITY CASCADE;

-- Cotizaciones
TRUNCATE TABLE cotizaciones RESTART IDENTITY CASCADE;

-- Órdenes de compra
TRUNCATE TABLE orden_compra RESTART IDENTITY CASCADE;

-- ============================================================================
-- PASO 3: Eliminar catálogos y entidades relacionadas
-- ============================================================================

-- Servicios de proveedores (catálogo de compra)
TRUNCATE TABLE servicio_proveedor RESTART IDENTITY CASCADE;

-- Servicios (catálogo de venta)
TRUNCATE TABLE servicio RESTART IDENTITY CASCADE;

-- Clientes
TRUNCATE TABLE cliente RESTART IDENTITY CASCADE;

-- Proveedores
TRUNCATE TABLE proveedor RESTART IDENTITY CASCADE;

-- ============================================================================
-- PASO 4: NO tocar la tabla de usuarios (para mantener login)
-- ============================================================================
-- La tabla "usuario" NO se limpia para poder seguir logueándose

-- ============================================================================
-- PASO 5: Reactivar triggers
-- ============================================================================
SET session_replication_role = 'origin';

COMMIT;

-- ============================================================================
-- Verificación: Contar registros restantes
-- ============================================================================
SELECT 'usuario' as tabla, COUNT(*) as registros FROM usuario
UNION ALL
SELECT 'cliente', COUNT(*) FROM cliente
UNION ALL
SELECT 'proveedor', COUNT(*) FROM proveedor
UNION ALL
SELECT 'servicio', COUNT(*) FROM servicio
UNION ALL
SELECT 'servicio_proveedor', COUNT(*) FROM servicio_proveedor
UNION ALL
SELECT 'cotizaciones', COUNT(*) FROM cotizaciones
UNION ALL
SELECT 'conceptocotizacion', COUNT(*) FROM conceptocotizacion
UNION ALL
SELECT 'orden_compra', COUNT(*) FROM orden_compra
UNION ALL
SELECT 'detalle_orden_compra', COUNT(*) FROM detalle_orden_compra
UNION ALL
SELECT 'orden_trabajo', COUNT(*) FROM orden_trabajo
UNION ALL
SELECT 'concepto_orden_trabajo', COUNT(*) FROM concepto_orden_trabajo;
