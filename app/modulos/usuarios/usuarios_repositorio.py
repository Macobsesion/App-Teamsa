"""Repositorio de usuarios.

Se apoya en `RepositorioCRUD` para crear/actualizar y consultas genéricas.
El método obtener_por_username ahora se reemplaza por obtener_por_campo("usuario", username).
"""

from typing import Any, Mapping
from app.base.repositorio import RepositorioCRUD
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.nucleo.cls_autenticacion import obtener_gestor_autenticacion


class RepositorioUsuario(RepositorioCRUD[Usuario]):
    """Repositorio de usuarios con lógica de seguridad encapsulada."""
    
    modelo = Usuario
    campos_filtrables = {"usuario", "rol", "id"}
    campos_busqueda = {"nombres": "icontains", "correo": "icontains", "area": "icontains"}
    campos_actualizables = {
        "nombres", "correo", "rol", "area", "contrasena", "modificado_por",
        "permisos_ver", "permisos_crear", "permisos_editar", "permisos_eliminar"
    }
    orden_por_defecto = ("id", False)

    def _hashear_contrasena(self, contrasena: str) -> str:
        return obtener_gestor_autenticacion().obtener_hash_contrasena(contrasena)

    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        """Aplica valores por defecto y hashea contraseña."""
        datos_procesados = datos.copy()
        
        # Default rol
        if not datos_procesados.get("rol"):
            datos_procesados["rol"] = "funcionario"
            
        # Hashear password
        if "contrasena" in datos_procesados:
            datos_procesados["contrasena"] = self._hashear_contrasena(datos_procesados["contrasena"])
            
        return datos_procesados

    def _pre_procesar_cambios(self, cambios: Mapping[str, Any]) -> Mapping[str, Any]:
        """Detecta cambio de contraseña y la hashea."""
        if "contrasena" not in cambios:
            return cambios
            
        cambios_procesados = dict(cambios)
        passwd = cambios_procesados["contrasena"]
        
        # Si la contraseña no está vacía, hashearla. Si es vacía, quitarla para no borrarla.
        if passwd:
            cambios_procesados["contrasena"] = self._hashear_contrasena(passwd)
        else:
            # Si viene vacía (o None), no actualizar password
            del cambios_procesados["contrasena"]
            
        return cambios_procesados
    def eliminar(self, entidad_id: int) -> None:
        """
        Elimina un usuario con guardias de seguridad para evitar pérdida de acceso.
        """
        from app.base.excepciones import ReglaNegocioError
        
        usuario_bd = self.obtener_por_id(entidad_id)
        
        # 1. No permitir borrar el admin principal
        if usuario_bd.usuario == "admin":
            raise ReglaNegocioError("No se puede eliminar el usuario administrador principal.")
        
        # 2. Otros guardias (ej. no auto-borrado si tuviéramos acceso al actor_id aquí)
        # Por ahora, nos enfocamos en el admin principal
        
        return super().eliminar(entidad_id)
