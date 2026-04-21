from sqlmodel import Session, select
from app.nucleo.base_datos import obtener_motor
from app.modulos.usuarios.usuarios_modelo import Usuario

motor = obtener_motor()
with Session(motor) as session:
    usuario = session.exec(select(Usuario).where(Usuario.usuario == 'mjimenez')).first()
    if usuario:
        print(f"Usuario: {usuario.usuario}")
        print(f"Permisos Ver: {usuario.permisos_ver}")
        print(f"Permisos Crear: {usuario.permisos_crear}")
        print(f"Permisos Editar: {usuario.permisos_editar}")
    else:
        print("Usuario mjimenez no encontrado")
