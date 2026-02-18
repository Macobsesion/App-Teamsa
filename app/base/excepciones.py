"""
Excepciones de Dominio.
Definen errores semánticos que la aplicación sabe manejar y traducir a respuestas HTTP.
"""

class AppError(Exception):
    """Clase base para todas las excepciones de la aplicación."""
    def __init__(self, mensaje: str, codigo: str = "ERROR_GENERICO"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo

class RecursoNoEncontradoError(AppError):
    """El recurso solicitado no existe (Mapea a 404)."""
    def __init__(self, mensaje: str = "Recurso no encontrado", codigo: str = "NO_ENCONTRADO"):
        super().__init__(mensaje, codigo)

class ReglaNegocioError(AppError):
    """Operación inválida por reglas de negocio (Mapea a 409 o 422)."""
    def __init__(self, mensaje: str, codigo: str = "REGLA_NEGOCIO"):
        super().__init__(mensaje, codigo)

class PermisoDenegadoError(AppError):
    """El usuario no tiene permisos para realizar la acción (Mapea a 403)."""
    def __init__(self, mensaje: str = "Permiso denegado", codigo: str = "ACCESO_DENEGADO"):
        super().__init__(mensaje, codigo)
