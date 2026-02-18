"""
Servicios de dominio para Cotizaciones.
"""
from decimal import Decimal
from datetime import date
from sqlmodel import Session
import uuid

from app.base.servicios import ServicioDominio, FabricaImpuestos
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.clientes.clientes_repositorio import RepositorioCliente

from app.base.servicios_documentos import ServicioDocumentoFinanciero

class ServicioCreacionCotizacion(ServicioDocumentoFinanciero[Cotizacion, ConceptoCotizacion]):
    """
    Servicio de Dominio encargado de la creación compleja de cotizaciones.
    Orquesta la validación, cálculo de impuestos y persistencia.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repo_cotizacion = RepositorioCotizacion(db)
        self.repo_concepto = RepositorioConcepto(db)
        self.repo_cliente = RepositorioCliente(db)
        
    
    def _crear_instancia_cabecera(self, data: dict) -> Cotizacion:
        """Implementación del paso: Crear instancia base."""
        # 1. Obtener cliente
        cliente_id = data.get('cliente_id')
        cliente = self.repo_cliente.obtener_por_id(cliente_id)
        if not cliente:
            raise ValueError(f"Cliente con ID {cliente_id} no encontrado")
            
        # 2. Crear Cotización
        temp_id = f"TEMP-{uuid.uuid4()}"
        cotizacion = Cotizacion(
            numero=temp_id, 
            numero_version=temp_id,
            cliente_id=cliente_id,
            estado=EstadoCotizacion.BORRADOR.value,
            metodo_pago=data.get('metodo_pago', 'POR_DEFINIR'),
            forma_pago=data.get('forma_pago', '99'),
            notas=data.get('notas'),
            fecha_emision=date.today(),
            creado_por=data.get('usuario_id', 'SISTEMA'),
            modificado_por=data.get('usuario_id', 'SISTEMA'),
        )
        
        # 3. Establecer vigencia inicial
        cotizacion.actualizar_vigencia()
        return cotizacion

    def _generar_folio_final(self, documento: Cotizacion) -> str | None:
        """Implementación del paso: Generar Folio."""
        # Delegamos al repositorio la generación del string
        # Nota: BaseDocumento tiene folio, pero Cotizacion usa numero/numero_version
        numero_real = self.repo_cotizacion.generar_numero_desde_id(documento.id, documento.fecha_emision)
        documento.numero = numero_real
        documento.numero_version = numero_real
        # Retornamos el mismo valor para que el template method asigne .folio si quisiera
        # pero aqui lo asignamos manual a los campos especificos
        return numero_real

    def _procesar_detalles(self, documento: Cotizacion, items_data: list) -> list[ConceptoCotizacion]:
        """Implementación del paso: Procesar Detalles."""
        conceptos = []
        for servicio_data in items_data:
            # Usar Factory Method del modelo Concepto
            concepto = ConceptoCotizacion.crear_desde_servicio(
                cotizacion_id=documento.id,
                servicio_id=servicio_data.get('servicio_id'),
                codigo_sat=servicio_data['codigo_sat'],
                descripcion=servicio_data['descripcion'],
                unidad=servicio_data['unidad'],
                cantidad=Decimal(str(servicio_data['cantidad'])),
                precio_unitario=Decimal(str(servicio_data['precio_unitario'])),
                descuento_porcentaje=Decimal(str(servicio_data.get('descuento_porcentaje', 0)))
            )
            conceptos.append(concepto)
        return conceptos

    def _calcular_impuestos(self, documento: Cotizacion, subtotal: Decimal) -> Decimal:
        """Override: Usar estrategia basada en cliente (ej. Frontera)."""
        # Necesitamos el cliente_id. Lo podemos sacar del documento
        cliente_id = documento.cliente_id
        cliente = self.repo_cliente.obtener_por_id(cliente_id)
        
        region = "MX_CENTRO"
        if cliente and cliente.cp and cliente.cp.startswith("22"): # Ejemplo TJ
            region = "MX_FRONTERA"
            
        estrategia = FabricaImpuestos.obtener_estrategia(region)
        return estrategia.calcular(subtotal)


    def crear_cotizacion_completa(self, data: dict, usuario_id: str) -> Cotizacion:
        """
        Wrapper de compatibilidad para el router.
        Extrae items y datos de cabecera.
        """
        # Aseguramos que el usuario_id esté en los datos para la cabecera
        data['usuario_id'] = usuario_id
        items = data.get('servicios', []) or data.get('conceptos', [])
        
        return self.crear_documento(data, items)
