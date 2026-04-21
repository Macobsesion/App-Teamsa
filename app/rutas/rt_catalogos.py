from fastapi import APIRouter
from app.modulos.clientes.clientes_router import router as clientes_router
from app.modulos.proveedores.proveedores_router import router as proveedores_router
from app.modulos.servicios.servicios_router import router as servicios_router
from app.modulos.servicios_proveedores.servicios_proveedores_router import router as servicios_proveedores_router

router = APIRouter()

# Incluir los catálogos básicos bajo este enrutador
router.include_router(clientes_router, tags=["Catálogos - Clientes"])
router.include_router(proveedores_router, tags=["Catálogos - Proveedores"])
router.include_router(servicios_router, tags=["Catálogos - Servicios"])
router.include_router(servicios_proveedores_router, tags=["Catálogos - Compra"])
