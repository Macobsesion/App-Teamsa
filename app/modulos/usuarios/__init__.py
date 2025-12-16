# Paquete de usuarios: evita importar submódulos pesados en __init__ para
# prevenir ciclos de importación. Importa directamente desde
# app.modulos.usuarios.usuarios_router cuando sea necesario.

__all__ = []
