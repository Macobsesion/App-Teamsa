"""
Servicios base y fábricas.
"""
from typing import Protocol, TYPE_CHECKING
from decimal import Decimal
from app.base.impuestos import CalculadoraImpuestos, ImpuestoEstandarMX, ImpuestoFronteraMX, ImpuestoTasaCero

if TYPE_CHECKING:
    from sqlmodel import Session

class ServicioDominio:
    """Clase base para servicios de dominio con inyección de sesión."""
    def __init__(self, db: "Session"):
        self.db = db

    def _auditar(self, usuario: str, accion: str, modulo: str, detalles: str) -> None:
        """Helper para auditoría estandarizada."""
        from app.base.logs_servicio import ServicioLogs
        ServicioLogs.registrar(usuario=usuario, accion=accion, modulo=modulo, detalles=detalles)

    def _confirmar(self) -> None:
        """Commit + manejo de sesión estandarizado."""
        self.db.commit()


class FabricaImpuestos:
    """
    Fábrica para crear estrategias de cálculo de impuestos.
    Implementa el patrón Factory Method basado en configuración o contexto.
    """
    
    @staticmethod
    def obtener_estrategia(region: str = "MX_CENTRO", regimen_fiscal: str | None = None) -> CalculadoraImpuestos:
        """
        Devuelve la estrategia de impuestos adecuada.
        
        Args:
            region: Región fiscal (MX_CENTRO, MX_FRONTERA, EXTRANJERO)
            regimen_fiscal: Régimen fiscal del cliente (opcional)
            
        Returns:
            Instancia de CalculadoraImpuestos
        """
        # Regla: Si el régimen es exento o tasa cero (simplificado)
        if regimen_fiscal in ["610", "611"]: # Ejemplos de claves SAT para residentes en el extranjero o sin obligaciones
             # OJO: Esto es simplificado, en realidad depende del producto también, 
             # pero para este demo asumimos que si el cliente es especial, aplica.
             return ImpuestoTasaCero()

        if region == "MX_FRONTERA":
            return ImpuestoFronteraMX()
            
        # Default: IVA 16%
        return ImpuestoEstandarMX()
