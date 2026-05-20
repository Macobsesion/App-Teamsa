from fastapi import APIRouter
from app.modulos.usuarios.logs_router import router as logs_router

router = APIRouter()

# Incluir funcionalidades administrativas
router.include_router(logs_router)
