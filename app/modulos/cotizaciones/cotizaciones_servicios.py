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

from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.ordenes.ordenes_repositorio import RepositorioOrden
from app.modulos.clientes.clientes_modelo import Cliente


class ServicioCreacionCotizacion:
    """
    Servicio especializado en la creación de cotizaciones completas desde el wizard.
    Maneja la lógica de snapshot de datos del cliente y persistencia de conceptos.
    """

    def __init__(self, db: Session):
        self.db = db
        self._repo_cot = RepositorioCotizacion(db)
        self._repo_con = RepositorioConcepto(db)

    def crear_cotizacion_completa(self, data: dict, usuario_nombre: str) -> Cotizacion:
        """
        Crea una cotización y sus conceptos en un solo flujo.
        Aplica snapshot de datos del cliente para persistencia histórica.
        """
        datos_cot = data.copy()
        servicios = datos_cot.pop('servicios', [])

        # 1. Enriquecer datos con snapshot del cliente
        cliente = self.db.get(Cliente, datos_cot['cliente_id'])
        if cliente:
            datos_cot['cliente_nombre'] = cliente.nombre
            datos_cot['cliente_rfc'] = cliente.rfc
            datos_cot['cliente_direccion'] = cliente.direccion
            datos_cot['cliente_ciudad'] = cliente.ciudad
            datos_cot['cliente_cp'] = cliente.cp
            datos_cot['cliente_telefono'] = cliente.telefono
            datos_cot['cliente_email'] = cliente.email
        
        datos_cot['creado_por'] = usuario_nombre
        datos_cot['modificado_por'] = usuario_nombre

        # 2. Crear cabecera mediante el repositorio CRUD
        cotizacion = self._repo_cot.crear(datos_cot)

        # 3. Crear conceptos individuales
        for s in servicios:
            # Nota: el RepositorioConcepto ya dispara recalcular_totales en _post_guardar,
            # pero para eficiencia lo haremos una sola vez al final si quisiéramos.
            # Sin embargo, siguiendo el patrón actual del repo:
            self._repo_con.crear_concepto(
                cotizacion_id=cotizacion.id,
                servicio_id=s.get('servicio_id'),
                codigo_sat=s.get('codigo_sat', ''),
                descripcion=s.get('descripcion', ''),
                unidad=s.get('unidad', 'pieza'),
                cantidad=Decimal(str(s.get('cantidad', 1))),
                precio_unitario=Decimal(str(s.get('precio_unitario', 0))),
                descuento_porcentaje=Decimal(str(s.get('descuento_porcentaje', 0))),
            )

        # 4. Asegurar recálculo final y refrescar entidad
        self._repo_cot.recalcular_totales(cotizacion.id)
        self.db.refresh(cotizacion)
        
        return cotizacion


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
