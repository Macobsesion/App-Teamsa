import sys
sys.path.insert(0, '/teamsa-app')

from app.nucleo.base_datos import sesion_bd
from app.modulos.usuarios.usuarios_modelo import Usuario
from sqlmodel import select

def migrate_permissions():
    print("Iniciando migración de permisos...")
    with sesion_bd() as db:
        usuarios = db.exec(select(Usuario)).all()
        count = 0
        for u in usuarios:
            cambio = False
            for attr in ['permisos_ver', 'permisos_crear', 'permisos_editar', 'permisos_eliminar']:
                perms = getattr(u, attr, []) or []
                if 'ordenes' in perms:
                    perms = [p if p != 'ordenes' else 'ordenes_trabajo' for p in perms]
                    setattr(u, attr, perms)
                    cambio = True
            
            if cambio:
                db.add(u)
                print(f"Usuario '{u.usuario}' actualizado.")
                count += 1
        
        db.commit()
        print(f"Migración completada. {count} usuarios actualizados.")

if __name__ == "__main__":
    migrate_permissions()
