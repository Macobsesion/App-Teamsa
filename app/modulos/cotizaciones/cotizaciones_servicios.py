"""
Servicio de Aplicación para Cotizaciones.

Orquesta operaciones que cruzan más de un repositorio o módulo.
Este es el punto de entrada correcto para el próximo módulo que necesite
interactuar con Cotizaciones y Órdenes simultáneamente.

Regla: Los repositorios individuales NO deben instanciarse entre sí.
       Solo este servicio (u otro ServicioAplicacion) puede hacerlo.
"""
from sqlmodel import Session
from decimal import Decimal
from datetime import date
from typing import List, Dict, Any

from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.ordenes.ordenes_repositorio import RepositorioOrden
from app.modulos.clientes.clientes_modelo import Cliente
from app.base.servicios_documentos import ServicioDocumentoFinanciero


class ServicioCreacionCotizacion(ServicioDocumentoFinanciero[Cotizacion, ConceptoCotizacion]):
    """
    Servicio especializado en la creación de cotizaciones completas.
    Hereda de ServicioDocumentoFinanciero para usar el flujo estandarizado (Template Method).
    """

    def _crear_instancia_cabecera(self, data: Dict[str, Any]) -> Cotizacion:
        """Paso 1: Crear instancia base con snapshot de cliente."""
        # 1. Enriquecer datos con snapshot del cliente
        cliente = self.db.get(Cliente, data['cliente_id'])
        if not cliente:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Cliente no encontrado")

        return Cotizacion(
            cliente_id=data['cliente_id'],
            cliente_nombre=cliente.nombre,
            cliente_rfc=cliente.rfc,
            cliente_direccion=cliente.direccion,
            cliente_ciudad=cliente.ciudad,
            cliente_cp=cliente.cp,
            cliente_telefono=cliente.telefono,
            cliente_email=cliente.email,
            metodo_pago=data.get('metodo_pago', 'POR_DEFINIR'),
            forma_pago=data.get('forma_pago', '99'),
            notas=data.get('notas'),
            notas_privadas=data.get('notas_privadas'),
            fecha_emision=date.today(),
            estado='borrador',
            # El folio temporal lo asigna la clase base
            creado_por=data.get('usuario_id', 'SISTEMA'),
            modificado_por=data.get('usuario_id', 'SISTEMA'),
            numero="", # Provisional
            numero_version="" # Provisional
        )

    def _generar_folio_final(self, documento: Cotizacion) -> str | None:
        """Paso 2: Generar folio y número definitivo."""
        from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
        repo = RepositorioCotizacion(self.db)
        nuevo_numero = repo.generar_numero_desde_id(documento.id, documento.fecha_emision) # type: ignore
        documento.numero = nuevo_numero
        documento.numero_version = nuevo_numero
        documento.actualizar_vigencia()
        return nuevo_numero

    def _procesar_detalles(self, documento: Cotizacion, items_data: List[Dict[str, Any]]) -> List[ConceptoCotizacion]:
        """Paso 3: Crear conceptos individuales."""
        detalles_orm = []
        for s in items_data:
            detalle = ConceptoCotizacion.crear_desde_servicio(
                cotizacion_id=documento.id,
                servicio_id=s.get('servicio_id'),
                codigo_sat=s.get('codigo_sat', ''),
                descripcion=s.get('descripcion', ''),
                unidad=s.get('unidad', 'pieza'),
                cantidad=Decimal(str(s.get('cantidad', 1))),
                precio_unitario=Decimal(str(s.get('precio_unitario', 0))),
                descuento_porcentaje=Decimal(str(s.get('descuento_porcentaje', 0))),
            )
            detalles_orm.append(detalle)
        return detalles_orm

    def crear_cotizacion_completa(self, data: Dict[str, Any], usuario_nombre: str) -> Cotizacion:
        """Wrapper de compatibilidad para el router."""
        data['usuario_id'] = usuario_nombre
        items = data.get('servicios', [])
        return self.crear_documento(data, items)


class ServicioAplicacionCotizacion:
    """
    Orquestador de lógica de aplicación que cruza Cotizaciones y Órdenes.
    """

    def __init__(self, db: Session):
        self.db = db
        self._repo_cot = RepositorioCotizacion(db)
        self._repo_ordenes = RepositorioOrden(db)

    def obtener_estado_conceptos(self, cotizacion_id: int) -> dict[int, dict]:
        """
        Obtiene el estado de ejecución (OT) para cada concepto de una cotización.
        """
        conceptos = self._repo_cot.obtener_conceptos(cotizacion_id)
        concepto_ids = [c.id for c in conceptos if c.id is not None]

        if not concepto_ids:
            return {}

        return self._repo_ordenes.obtener_estado_por_conceptos_cotizacion(concepto_ids)

    def obtener_detalle_completo(self, cotizacion_id: int) -> dict:
        """
        Devuelve la cotización con sus conceptos y sus estados de ejecución en OT.
        """
        cotizacion = self._repo_cot.obtener_por_id(cotizacion_id)
        conceptos = self._repo_cot.obtener_conceptos(cotizacion_id)
        estados = self.obtener_estado_conceptos(cotizacion_id)

        return {
            "cotizacion": cotizacion,
            "conceptos": conceptos,
            "estados_ot": estados,
        }
