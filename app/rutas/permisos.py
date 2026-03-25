"""
Módulo de control de acceso dinámico (RBAC).

Reemplaza los diccionarios quemados en código estático.
Expone la dependencia FastAPI que interroga a la base de datos 
para leer los arrays JSON de permisos del usuario.
"""
from typing import Callable
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.base.excepciones import PermisoDenegadoError
from app.base.modulos_sistema import ModuloSistema

def para_modulo(modulo: str | ModuloSistema, accion: str = "editar") -> Callable:
    """
    Retorna la dependencia FastAPI de autorización dinámica para el módulo dado.
    accion debe ser una de: "ver", "crear", "editar", "eliminar".
    
    Uso en routers:
        write_dependency=Depends(para_modulo("ordenes_compra", "editar"))
    """
    def _verificar(
        identidad: UsuarioIdentity = Depends(dp_usuario_actual),
        db: Session = Depends(obtener_sesion_bd)
    ) -> Usuario:
        # Extraer de BD para leer arrays JSON en tiempo real
        usuario = db.exec(select(Usuario).where(Usuario.usuario == identidad.usuario)).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado en la base de datos",
            )
            
        # Eliminamos el bypass de admin para que el backend sea estrictamente reactivo a los checkboxes.
        # if usuario.rol == "admin":
        #    return usuario
            
        # Determinar qué lista revisar dinámicamente
        lista_permisos = getattr(usuario, f"permisos_{accion}", []) or []
        
        if modulo not in lista_permisos:
            raise PermisoDenegadoError(
                f"No cuentas con el permiso para {accion} en {modulo}"
            )
        return usuario
        
    return _verificar

# Mapa de ruta HTML para renderizado, derivado de ModuloSistema (fuente de verdad).
# La clave usa guiones (convención URL) y el valor es el módulo del sistema.
RUTAS_MODULO: dict[str, str] = {
    f"/{m.value.replace('_', '-')}": m.value for m in ModuloSistema
}

__all__ = ["para_modulo", "RUTAS_MODULO", "ModuloSistema"]
