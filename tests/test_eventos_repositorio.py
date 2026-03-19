import pytest
from app.base.eventos import BusEventos
from app.modulos.clientes.clientes_repositorio import RepositorioCliente

def test_repositorio_dispara_eventos_cliente(session):
    BusEventos.limpiar()
    
    eventos_capturados = []
    
    def on_creado(entidad):
        eventos_capturados.append(("creado", entidad))
        
    def on_actualizado(entidad):
        eventos_capturados.append(("actualizado", entidad))
        
    def on_eliminado(entidad):
        eventos_capturados.append(("eliminado", entidad))

    # Suscribir
    BusEventos.suscribir("Cliente.creado", on_creado)
    BusEventos.suscribir("Cliente.actualizado", on_actualizado)
    BusEventos.suscribir("Cliente.eliminado", on_eliminado)
    
    repo = RepositorioCliente(session)
    
    # 1. Probar CREAR
    nuevo = repo.crear(
        nombre="PruebaEventosCliente",
        rfc="XAXX010101000",
        creado_por="test_user"
    )
    assert len(eventos_capturados) == 1
    accion, ent = eventos_capturados[0]
    assert accion == "creado"
    assert ent.nombre == "PruebaEventosCliente"
    
    # 2. Probar ACTUALIZAR
    eventos_capturados.clear()
    actualizado = repo.actualizar(nuevo.id, {"nombre": "PruebaEventosModificado", "modificado_por": "test_user"})
    assert len(eventos_capturados) == 1
    accion, ent = eventos_capturados[0]
    assert accion == "actualizado"
    assert ent.nombre == "PruebaEventosModificado"

    # 3. Probar ELIMINAR
    eventos_capturados.clear()
    id_cli = nuevo.id
    repo.eliminar(id_cli)
    assert len(eventos_capturados) == 1
    accion, ent = eventos_capturados[0]
    assert accion == "eliminado"
    assert ent.id == id_cli
