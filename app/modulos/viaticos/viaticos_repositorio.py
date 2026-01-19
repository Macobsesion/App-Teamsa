"""Repositorio para viáticos."""
from datetime import date
from decimal import Decimal
from sqlmodel import Session, select  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.base.constantes import PREFIJO_NUMERO_VIATICO
from app.modulos.viaticos.viaticos_modelo import Viatico, GastoViatico


class RepositorioViatico(RepositorioCRUD[Viatico]):
    """Repositorio de viáticos con lógica de numeración y cálculos."""
    
    modelo = Viatico
    campos_filtrables = {"estado", "responsable_id"}
    campos_actualizables = {
        "responsable_id", "proyecto", "cliente", "destino",
        "fecha_inicio", "fecha_fin", "estado", "notas", "observaciones",
        "modificado_por"
    }
    campos_busqueda = {"numero": "icontains", "proyecto": "icontains", "cliente": "icontains"}
    orden_por_defecto = ("numero", True)  # Descendente (más reciente primero)
    
    def generar_siguiente_numero(self) -> str:
        """
        Genera el siguiente número de viático secuencial.
        
        Returns:
            Número en formato VIA-00001, VIA-00002, etc.
        """
        # Buscar el último número usado
        ultimo_viatico = self.db.exec(
            select(Viatico).order_by(Viatico.id.desc()).limit(1)
        ).first()
        
        if ultimo_viatico and ultimo_viatico.numero:
            # Extraer el número de "VIA-00123" -> 123
            try:
                ultimo_numero_str = ultimo_viatico.numero.split("-")[-1]
                ultimo_numero = int(ultimo_numero_str)
                siguiente_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                siguiente_numero = 1
        else:
            siguiente_numero = 1
        
        # Formatear con ceros a la izquierda: VIA-00001
        return f"{PREFIJO_NUMERO_VIATICO}-{siguiente_numero:05d}"
    
    def calcular_dias(self, fecha_inicio: date, fecha_fin: date) -> int:
        """Calcula los días del viaje usando el servicio de dominio."""
        from app.modulos.viaticos.servicios import ServicioCalculadoraViatico
        return ServicioCalculadoraViatico.calcular_dias(fecha_inicio, fecha_fin)
    
    def obtener_gastos(self, viatico_id: int) -> list[GastoViatico]:
        """Obtiene todos los gastos de un viático."""
        return list(self.db.exec(
            select(GastoViatico)
            .where(GastoViatico.viatico_id == viatico_id)
            .order_by(GastoViatico.fecha_gasto, GastoViatico.id)
        ).all())
    
    def recalcular_totales(self, viatico_id: int) -> None:
        """
        Recalcula totales por categoría usando el servicio de dominio.
        """
        from app.modulos.viaticos.servicios import ServicioCalculadoraViatico
        
        gastos = self.obtener_gastos(viatico_id)
        
        # Delegar cálculo al servicio
        totales = ServicioCalculadoraViatico.calcular_totales(gastos)
        
        # Actualizar viático
        viatico = self.db.get(Viatico, viatico_id)
        if viatico:
            viatico.total_transporte = totales["transporte"]
            viatico.total_alojamiento = totales["alojamiento"]
            viatico.total_alimentos = totales["alimentos"]
            viatico.total_otros = totales["otros"]
            viatico.total_general = totales["general"]
            
            self.db.add(viatico)
            self.db.commit()
            self.db.refresh(viatico)


class RepositorioGasto:
    """Repositorio para gastos de viáticos."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def crear(
        self,
        viatico_id: int,
        categoria: str,
        concepto: str,
        cantidad: Decimal,
        precio_unitario: Decimal,
        fecha_gasto: date,
        tiene_factura: bool = False,
        numero_factura: str | None = None,
    ) -> GastoViatico:
        """Crea un gasto y recalcula totales del viático."""
        # Calcular importe
        importe = cantidad * precio_unitario
        
        # Crear gasto
        gasto = GastoViatico(
            viatico_id=viatico_id,
            categoria=categoria,
            concepto=concepto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            importe=importe,
            fecha_gasto=fecha_gasto,
            tiene_factura=tiene_factura,
            numero_factura=numero_factura,
        )
        
        self.db.add(gasto)
        self.db.commit()
        self.db.refresh(gasto)
        
        # Recalcular totales del viático
        repo_viatico = RepositorioViatico(self.db)
        repo_viatico.recalcular_totales(viatico_id)
        
        return gasto
    
    def eliminar(self, gasto_id: int, viatico_id: int) -> None:
        """Elimina un gasto y recalcula totales del viático."""
        gasto = self.db.get(GastoViatico, gasto_id)
        if gasto:
            self.db.delete(gasto)
            self.db.commit()
            
            # Recalcular totales
            repo_viatico = RepositorioViatico(self.db)
            repo_viatico.recalcular_totales(viatico_id)
