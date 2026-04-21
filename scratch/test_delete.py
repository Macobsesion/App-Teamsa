from app.nucleo.base_datos import obtener_motor
from sqlmodel import Session, select
from app.modulos.clientes.clientes_modelo import Cliente

def test_delete():
    engine = obtener_motor()
    with Session(engine) as session:
        # 1. Crear cliente temporal
        c = Cliente(nombre="BORRAME TEST", rfc="TEST000000AAA", activo=True)
        session.add(c)
        session.commit()
        session.refresh(c)
        c_id = c.id
        print(f"Creado cliente con ID: {c_id}")
        
    with Session(engine) as session:
        # 2. Intentar borrarlo
        c_bd = session.get(Cliente, c_id)
        if not c_bd:
            print("ERROR: No se encontro el cliente recien creado")
            return
        
        session.delete(c_bd)
        session.commit()
        print(f"Borrado cliente {c_id} y commiteado")
        
    with Session(engine) as session:
        # 3. Verificar persistencia
        c_v = session.get(Cliente, c_id)
        if c_v:
            print("FALLO: El cliente SIGUE en la base de datos")
        else:
            print("EXITO: El cliente fue borrado correctamente")

if __name__ == "__main__":
    test_delete()
