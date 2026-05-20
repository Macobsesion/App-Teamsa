import sys
import os

sys.path.append(os.getcwd())

from app.nucleo.base_datos import obtener_motor
from sqlmodel import Session, select
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.modulos.servicios.servicios_modelo import Servicio

def run_test():
    engine = obtener_motor()
    with Session(engine) as db:
        # 1. Obtener cliente y cotizacion de prueba
        cliente = db.exec(select(Cliente)).first()
        cotizacion = db.exec(select(Cotizacion).where(Cotizacion.cliente_id == cliente.id)).first()
        
        usuario = db.exec(select(Usuario)).first()
        
        user_id = "usuario_auditor"
        
        viatico_data = {
            "cliente_id": cliente.id,
            "cotizacion_id": cotizacion.id,
            "proyecto": "Test Auditoría",
            "costo_transporte": 500.0,
            "creado_por": user_id,
            "modificado_por": user_id,
            "estado": "borrador",
            "responsable_id": usuario.id if usuario else 1,
            "origen": "CDMX",
            "destino": "MTY"
        }
        
        print("Creando viatico...")
        repo = RepositorioViatico(db)
        viatico = repo.crear(viatico_data)
        
        print(f"Viatico creado_por: {viatico.creado_por}")
        assert viatico.creado_por == user_id
        
        concepto = db.exec(
            select(ConceptoCotizacion).where(ConceptoCotizacion.viatico_id == viatico.id)
        ).first()
        
        print(f"Concepto creado_por: {concepto.creado_por if concepto else 'NINGUNO'}")
        if concepto:
            assert concepto.creado_por == user_id
            print("EXITO: Auditoria propagada.")
            db.delete(concepto)
            
        db.delete(viatico)
        db.commit()

if __name__ == "__main__":
    run_test()
