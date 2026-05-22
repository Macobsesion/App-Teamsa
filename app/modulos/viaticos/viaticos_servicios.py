"""
Servicio de Aplicación para Viáticos.
Maneja la lógica de negocio, validaciones cruzadas y efectos secundarios
(como la inyección de conceptos en Cotizaciones).
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlmodel import Session, select
import uuid

from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError
from app.modulos.viaticos.enums import EstadoViatico
from app.base.servicios import ServicioDominio

class ServicioViaticos(ServicioDominio):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = RepositorioViatico(db)

    def crear_viatico(self, data: Dict[str, Any], usuario_nombre: str, confirmar: bool = True, inyectar_concepto: bool = True) -> Viatico:
        """Crea un viático y maneja sus efectos secundarios."""
        # 1. Preparar datos y snapshots
        cliente_id = data.get("cliente_id")
        cliente = self.db.get(Cliente, cliente_id) if cliente_id else None
        
        if not cliente and cliente_id:
             raise RecursoNoEncontradoError(f"Cliente {cliente_id} no encontrado")

        # 2. Inyectar snapshots manuales (Regla 4: Fuera del repo)
        data_modelo = dict(data)
        data_modelo["creado_por"] = usuario_nombre
        
        # 3. Calcular total antes de persistir
        total = self._calcular_total_viatico(data)
        data_modelo["total"] = total

        # 4. Crear vía repositorio (solo persistencia básica)
        viatico = self.repo.crear(data_modelo)

        # Capturar snapshots históricos usando el nuevo mixin
        if cliente:
            viatico.capturar_datos_cliente(cliente)
            self.db.add(viatico)

        # 5. Efecto secundario: Inyectar concepto en Cotización si aplica
        # Solo inyectar si skip_injection no está activo en el servicio (opcional)
        if viatico.cotizacion_id and inyectar_concepto:
            self.inyectar_en_cotizacion(viatico)

        if confirmar:
            self.db.commit()
            self.db.refresh(viatico)
        else:
            self.db.flush()
        return viatico

    def actualizar_viatico(self, viatico_id: int, cambios: Dict[str, Any], confirmar: bool = True, sincronizar_cotizacion: bool = True) -> Viatico:
        """Actualiza un viático y sincroniza dependencias."""
        viatico = self.repo.obtener_por_id(viatico_id)
        
        # Validar si es editable (Regla de negocio)
        if not viatico.es_editable and "estado" not in cambios:
             raise ReglaNegocioError(f"El viático {viatico.folio} no es editable en su estado actual.")

        # Actualizar via repo
        viatico_actualizado = self.repo.actualizar(viatico_id, cambios)

        # Recalcular total si cambia cualquier campo que afecte el cálculo
        campos_calculo = [
            "costo_transporte", "costo_alojamiento", "costo_alimentos", 
            "costo_peajes", "costo_estacionamiento", "costo_otros",
            "personas", "dias", "desayuno", "comida", "cena", "proyecto"
        ]
        if any(k in cambios for k in campos_calculo):
            viatico_actualizado.total = self._calcular_total_viatico(viatico_actualizado.__dict__)
            self.db.add(viatico_actualizado)
            
            if sincronizar_cotizacion:
                self.sincronizar_con_cotizacion(viatico_actualizado)

        # Capturar snapshots si cambió el cliente (Endurecimiento de relación)
        if 'cliente_id' in cambios:
            from app.modulos.clientes.clientes_modelo import Cliente
            cliente = self.db.get(Cliente, cambios['cliente_id'])
            if cliente:
                viatico_actualizado.capturar_datos_cliente(cliente)
                self.db.add(viatico_actualizado)

        if confirmar:
            self.db.commit()
            self.db.refresh(viatico_actualizado)
        else:
            self.db.flush()
        return viatico_actualizado

    def inyectar_en_cotizacion(self, viatico: Viatico):
        """Crea un concepto de cotización vinculado a este viático."""
        from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioConcepto
        repo_concepto = RepositorioConcepto(self.db)
        
        # Evitar duplicados si ya existe un concepto para este viático
        existente = self.db.exec(select(ConceptoCotizacion).where(ConceptoCotizacion.viatico_id == viatico.id)).first()
        if existente:
            return

        desc = f"Viáticos: {viatico.proyecto or 'Servicio asignado'} (Ref: {viatico.folio})"
        repo_concepto.crear_concepto(
            cotizacion_id=viatico.cotizacion_id,
            servicio_id=None,
            viatico_id=viatico.id,
            codigo_sat='78111500', 
            descripcion=desc,
            unidad='Viaje/Servicio',
            cantidad=1,
            precio_unitario=viatico.total,
            descuento_porcentaje=0
        )

    def sincronizar_con_cotizacion(self, viatico: Viatico):
        """Actualiza el concepto de cotización vinculado si el viático cambia."""
        # Buscar concepto vinculado
        concepto = self.db.exec(
            select(ConceptoCotizacion).where(ConceptoCotizacion.viatico_id == viatico.id)
        ).first()

        if concepto:
            concepto.precio_unitario = viatico.total
            # Solo autocompletar descripción si está vacía
            if not concepto.descripcion:
                concepto.descripcion = f"Viáticos: {viatico.proyecto or 'Servicio asignado'} (Ref: {viatico.folio})"
            # Recalcular importe del concepto
            concepto.importe = concepto.cantidad * concepto.precio_unitario
            self.db.add(concepto)
            
            # Forzar recalcular totales de la cotización padre para mantener consistencia
            if concepto.cotizacion:
                concepto.cotizacion.recalcular_totales()
                self.db.add(concepto.cotizacion)
        elif viatico.cotizacion_id:
            self.inyectar_en_cotizacion(viatico)

    def _calcular_total_viatico(self, data: Dict[str, Any]) -> Decimal:
        """
        Calcula la suma de todos los rubros del viático.
        Asegura que el costo de alimentos considere personas y días si hay desglose.
        """
        def d(v): return Decimal(str(v or 0))
        
        personas = int(data.get("personas") or 1)
        dias = int(data.get("dias") or 1)
        
        desayuno = d(data.get("desayuno"))
        comida = d(data.get("comida"))
        cena = d(data.get("cena"))
        
        # Si hay desglose de alimentos, lo usamos para calcular el costo total de alimentos
        if desayuno > 0 or comida > 0 or cena > 0:
            costo_alimentos = (desayuno + comida + cena) * personas * dias
        else:
            costo_alimentos = d(data.get("costo_alimentos"))
            
        return d(data.get("costo_transporte")) + \
               d(data.get("costo_alojamiento")) + \
               costo_alimentos + \
               d(data.get("costo_peajes")) + \
               d(data.get("costo_estacionamiento")) + \
               d(data.get("costo_otros"))

    def procesar_viaticos_wizard(self, cotizacion_id: int, cliente_id: int, viaticos_data: List[Dict[str, Any]], usuario: str) -> Dict[int, int]:
        """
        Lógica para centralizar la creación de viáticos durante el flujo del wizard.
        Desactiva commits y efectos secundarios automáticos para dejar el control al orquestador.
        """
        # 1. Obtener ID del responsable
        u = self.db.exec(select(Usuario).where(Usuario.usuario == usuario)).first()
        r_id = u.id if u else 1
        
        # CONFIGURACIÓN PARA WIZARD: No disparar inyección de conceptos individualmente (el orquestador lo hará)
        
        mapping = {}
        for idx, v_data in enumerate(viaticos_data):
            v_id = v_data.get("id")
            
            # Forzar sincronía con los datos maestros de la cotización
            v_data["cotizacion_id"] = cotizacion_id
            v_data["cliente_id"] = cliente_id
            
            if not v_data.get("responsable_id"):
                v_data["responsable_id"] = r_id

            if v_id:
                # Actualización sin commit y sin sincronizar cotización (el orquestador sincronizará todo al final)
                self.actualizar_viatico(v_id, v_data, confirmar=False, sincronizar_cotizacion=False)
                mapping[idx] = v_id
            else:
                # Creación sin commit y sin inyectar concepto (el orquestador inyectará/sincronizará al final)
                # El responsable_id queda nulo (Pendiente) hasta que se asigne en la OT
                nuevo_v = self.crear_viatico(v_data, usuario, confirmar=False, inyectar_concepto=False)
                mapping[idx] = nuevo_v.id

        return mapping

    def cambiar_estado(self, viatico_id: int, accion: str, usuario_id: str) -> Viatico:
        """Maneja las transiciones de estado de un viático con validaciones de negocio."""
        viatico = self.repo.obtener_por_id(viatico_id)
        
        # Lógica de transiciones (Simplificada: Solo Cancelar y Finalizar manualmente)
        if accion == "cancelar" and viatico.estado != EstadoViatico.CANCELADO.value:
            viatico.estado = EstadoViatico.CANCELADO.value
        elif accion == "finalizar" and viatico.estado not in [EstadoViatico.FINALIZADO.value, EstadoViatico.CANCELADO.value]:
            viatico.estado = EstadoViatico.FINALIZADO.value
        else:
            raise ReglaNegocioError(f"No se puede {accion} el viático en estado {viatico.estado}")
            
        viatico.modificado_por = usuario_id
        self.db.add(viatico)
        self.db.commit()
        self.db.refresh(viatico)

        # Auditoría: Cambio de estado
        self._auditar(
            usuario=usuario_id, 
            accion=accion.upper(), 
            modulo="viaticos", 
            detalles=f"Viático {viatico.folio} marcado como {accion.upper()}"
        )

        return viatico

    @staticmethod
    def capturar_snapshots_estaticos(db: Session, viatico: Viatico) -> None:
        """
        Captura los datos del cliente en el momento de la creación o actualización.
        Garantiza la Regla 5 de inmutabilidad histórica.
        """
        if not viatico.cliente_id:
            return
            
        cliente = db.get(Cliente, viatico.cliente_id)
        if cliente:
            viatico.capturar_datos_cliente(cliente)
