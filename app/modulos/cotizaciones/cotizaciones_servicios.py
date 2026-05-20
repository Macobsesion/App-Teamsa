"""
Servicio de Aplicación para Cotizaciones.

Orquesta operaciones que cruzan más de un repositorio o módulo.
Este es el punto de entrada correcto para el próximo módulo que necesite
interactuar con Cotizaciones y Órdenes simultáneamente.

Regla: Los repositorios individuales NO deben instanciarse entre sí.
       Solo este servicio (u otro ServicioAplicacion) puede hacerlo.
"""
from sqlmodel import Session, select
from decimal import Decimal
from datetime import date
from typing import List, Dict, Any

from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.ordenes_trabajo.ordenes_trabajo_repositorio import RepositorioOrden
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.ordenes_trabajo.enums import EstadoOrden
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.modulos.viaticos.viaticos_servicios import ServicioViaticos
from app.base.servicios_documentos import ServicioDocumentoFinanciero


class ServicioCotizaciones:
    """
    Orquestador de lógica de aplicación para Cotizaciones y su relación con OTs y Viáticos.
    Unifica creación completa, actualización (sin versiones) y versionamiento.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = RepositorioCotizacion(db)



    def _procesar_conceptos_y_viaticos(self, cotizacion: Cotizacion, data: Dict[str, Any], usuario: str):
        """
        Orquesta el proceso de sincronización de conceptos y viáticos.
        Delega la lógica pesada de merge al modelo de dominio.
        """
        from app.modulos.viaticos.viaticos_servicios import ServicioViaticos
        from app.modulos.viaticos.viaticos_modelo import Viatico
        from sqlmodel import select

        items_data = data.get('servicios', [])
        viaticos_nuevos_data = data.get('viaticos_nuevos', [])

        # 1. Obtener viaticos previos para conciliación
        from app.modulos.viaticos.enums import EstadoViatico
        viaticos_previos = self.db.exec(select(Viatico).where(
            Viatico.cotizacion_id == cotizacion.id,
            Viatico.estado != EstadoViatico.CANCELADO.value
        )).all()

        # 2. Procesar viáticos nuevos del Wizard (Servicio de Aplicación Externo)
        viatico_mapping = {}
        if viaticos_nuevos_data:
            srv_v = ServicioViaticos(self.db)
            viatico_mapping = srv_v.procesar_viaticos_wizard(cotizacion.id, cotizacion.cliente_id, viaticos_nuevos_data, usuario)

        # 3. Enriquecer items_data con información real de los viáticos (Regla de negocio: Precio = Total Viático)
        for row in items_data:
            v_temp_id = row.get('viatico_temp_id')
            v_id_final = row.get('viatico_id')

            # Resolver mapping si es un viático recién creado
            if v_temp_id is not None:
                try:
                    idx_map = int(v_temp_id)
                    if idx_map in viatico_mapping:
                        v_id_final = viatico_mapping[idx_map]
                        row['viatico_id'] = v_id_final # Actualizar en el row para el modelo
                except (ValueError, TypeError):
                    pass

            if v_id_final:
                v_record = self.db.get(Viatico, v_id_final)
                if v_record:
                    # El precio unitario SIEMPRE debe ser el total del viático
                    row['precio_unitario'] = v_record.total
                    # Recomendación de descripción si viene vacía
                    if not row.get('descripcion'):
                        row['descripcion'] = f"Viáticos: {v_record.proyecto or 'Servicio asignado'} (Ref: {v_record.folio})"

        # 4. Delegar sincronización de conceptos al MODELO (OOP)
        # El modelo ahora recibe datos ya validados y enriquecidos
        viaticos_en_uso = cotizacion.sincronizar_conceptos(items_data)

        # 4. Vincular viáticos nuevos o actualizados que no estuvieran vinculados
        for v_id in viaticos_en_uso:
            v_obj = self.db.get(Viatico, v_id)
            if v_obj and v_obj.cotizacion_id != cotizacion.id:
                v_obj.cotizacion_id = cotizacion.id
                self.db.add(v_obj)

        # 5. Cancelar viáticos que ya no aparecen en los conceptos (Conciliación)
        for v_old in viaticos_previos:
            if v_old.id not in viaticos_en_uso:
                v_old.estado = EstadoViatico.CANCELADO.value
                self.db.add(v_old)

        self.db.add(cotizacion)
        self.db.flush()
        
        # Forzar recalculo de totales tras sincronizar conceptos y viáticos
        self.repo.recalcular_totales(cotizacion.id)

    def crear_cotizacion_completa(self, data: Dict[str, Any], usuario: str) -> Cotizacion:
        """Crea una cotización nueva con conceptos y viáticos vinculados."""
        cliente_id = data.get('cliente_id')
        cliente = self.db.get(Cliente, cliente_id)
        if not cliente:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError(f"Cliente {cliente_id} no encontrado")

        # Usar factory method para evitar IntegrityError con campos obligatorios (numero, folio)
        cotizacion = Cotizacion.crear_desde_wizard(
            cliente=cliente,
            metodo_pago=data.get('metodo_pago', 'POR_DEFINIR'),
            forma_pago=data.get('forma_pago', '99'),
            notas=data.get('notas'),
            usuario_id=usuario
        )
        
        self.db.add(cotizacion)
        self.db.flush() # Obtenemos ID real para vinculación de viáticos

        import logging
        logger = logging.getLogger("teamsa.cotizaciones.debug")
        logger.info(f"RECIBIENDO DATA PARA COTIZACION: {data.get('servicios')}")

        # Procesar detalles y viáticos
        self._procesar_conceptos_y_viaticos(cotizacion, data, usuario)
        
        # Generar número definitivo (atómico)
        self.repo._post_guardar(cotizacion, es_nuevo=True)

        # Sincronizar folios de viáticos con el nuevo número de cotización
        srv_v = ServicioViaticos(self.db)
        srv_v.repo.sincronizar_folios_con_cotizacion(cotizacion.id)

        self.db.commit()
        self.db.refresh(cotizacion)
        return cotizacion

    def actualizar_sin_versionar(self, cotizacion_id: int, data: Dict[str, Any], usuario: str) -> Cotizacion:
        """Actualiza una cotización existente preservando su número y versión."""
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Cotización no encontrada")

        cotizacion.metodo_pago = data.get('metodo_pago', cotizacion.metodo_pago)
        cotizacion.forma_pago = data.get('forma_pago', cotizacion.forma_pago)
        cotizacion.notas = data.get('notas', cotizacion.notas)
        cotizacion.modificado_por = usuario
        
        # Actualizar snapshot por si cambiaron datos del cliente
        cliente = self.db.get(Cliente, cotizacion.cliente_id)
        if cliente:
            cotizacion.capturar_datos_cliente(cliente)
        self.db.add(cotizacion)
        
        self._procesar_conceptos_y_viaticos(cotizacion, data, usuario)
        
        self.db.commit()
        self.db.refresh(cotizacion)
        return cotizacion

    def crear_nueva_version(self, cotizacion_id: int, data: Dict[str, Any], usuario: str) -> Cotizacion:
        """Crea una nueva versión (B, C...) de una cotización existente."""
        from app.modulos.cotizaciones.calculadora import ServicioCalculadoraCotizacion
        import uuid
        
        cotizacion_anterior = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion_anterior:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Cotización no encontrada")

        # 1. Identificar familia y calcular letra
        id_madre = cotizacion_anterior.cotizacion_original_id or cotizacion_anterior.id
        versiones = self.repo.obtener_versiones_familia(id_madre)
        letras_usadas = [v[1] for v in versiones]
        nueva_letra = ServicioCalculadoraCotizacion.calcular_siguiente_letra(letras_usadas)
        
        # 2. Marcar anterior como modificada
        from app.modulos.cotizaciones.enums import EstadoCotizacion
        cotizacion_anterior.estado = EstadoCotizacion.MODIFICADA.value
        self.db.add(cotizacion_anterior)

        # 3. Crear nueva instancia heredando datos
        # Generamos identificadores temporales para evitar IntegrityError en el flush
        uid = str(uuid.uuid4())
        folio_temp = f"TEMP-{uid}"
        
        nueva = Cotizacion(
            cliente_id=cotizacion_anterior.cliente_id,
            cotizacion_original_id=id_madre,
            version_letra=nueva_letra,
            metodo_pago=data.get('metodo_pago', cotizacion_anterior.metodo_pago),
            forma_pago=data.get('forma_pago', cotizacion_anterior.forma_pago),
            notas=data.get('notas'),
            estado=EstadoCotizacion.BORRADOR.value,
            folio=folio_temp,
            numero=folio_temp, # Temporal
            numero_version=folio_temp, # Temporal
            creado_por=usuario,
            modificado_por=usuario,
            fecha_emision=date.today()
        )
        # Actualizar snapshot por si cambiaron datos del cliente
        cliente = self.db.get(Cliente, cotizacion_anterior.cliente_id)
        if cliente:
            nueva.capturar_datos_cliente(cliente)
        nueva.actualizar_vigencia()
        
        self.db.add(nueva)
        self.db.flush()

        # 4. Procesar conceptos y transferir viáticos
        self._procesar_conceptos_y_viaticos(nueva, data, usuario)

        # Generar número definitivo (ej. COT-240101-B)
        self.repo._post_guardar(nueva, es_nuevo=True)

        # Sincronizar folios de viáticos con el nuevo número de cotización
        srv_v = ServicioViaticos(self.db)
        srv_v.repo.sincronizar_folios_con_cotizacion(nueva.id)

        self.db.commit()
        self.db.refresh(nueva)
        return nueva

    def cerrar_cotizacion(self, cotizacion_id: int, motivo: str, forzar: bool = False, estado_final: str = None) -> Cotizacion:
        """
        Cierra una cotización (estado 'cancelada' o 'finalizada').
        Valida dependencias y ofrece cierre en cascada.
        """
        from app.modulos.cotizaciones.enums import EstadoCotizacion
        if not estado_final:
            estado_final = EstadoCotizacion.CANCELADA.value
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Cotización no encontrada")
        
        # 1. Definir estados de exclusión según el destino
        from app.modulos.ordenes_trabajo.enums import EstadoOrden
        from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
        from app.modulos.viaticos.viaticos_modelo import Viatico
        from app.modulos.viaticos.enums import EstadoViatico

        es_cancelacion = estado_final == EstadoCotizacion.CANCELADA.value
        
        # SIEMPRE excluimos los estados terminales (no podemos re-cancelar ni re-finalizar algo ya cerrado)
        excluir_ot = [EstadoOrden.FINALIZADA.value, EstadoOrden.CANCELADA.value]
        excluir_via = [EstadoViatico.FINALIZADO.value, EstadoViatico.CANCELADO.value]

        ots_pendientes = self.db.exec(
            select(OrdenTrabajo).where(
                OrdenTrabajo.cotizacion_id == cotizacion_id,
                OrdenTrabajo.estado.notin_(excluir_ot)
            )
        ).all()

        viaticos_pendientes = self.db.exec(
            select(Viatico).where(
                Viatico.cotizacion_id == cotizacion_id,
                Viatico.estado.notin_(excluir_via)
            )
        ).all()

        if (ots_pendientes or viaticos_pendientes) and not forzar:
            from app.base.excepciones import ReglaNegocioError
            accion_txt = "cancelar" if es_cancelacion else "FINALIZAR"
            msg = f"Esta cotización tiene documentos pendientes:\n"
            if ots_pendientes:
                msg += f"- {len(ots_pendientes)} Ordenes de Trabajo\n"
            if viaticos_pendientes:
                msg += f"- {len(viaticos_pendientes)} Viáticos\n"
            msg += f"\n¿Confirmas que deseas {accion_txt} TODO en cascada?"
            raise ReglaNegocioError(msg, codigo="REQUIERE_CONFIRMACION_CASCADA")

        # 2. Cascada de estados
        if forzar:
            from app.modulos.ordenes_trabajo.enums import EstadoConceptoOT
            from datetime import datetime
            
            # Recuperar TODAS las OTs asociadas a la cotización para sincronizar sus conceptos,
            # incluso si la OT ya estaba marcada como terminal.
            todas_las_ots = self.db.exec(
                select(OrdenTrabajo).where(OrdenTrabajo.cotizacion_id == cotizacion_id)
            ).all()
            
            if es_cancelacion:
                for ot in ots_pendientes:
                    ot.cancelar(usuario="sistema")
                    self.db.add(ot)
                
                # Actualizar conceptos de TODAS las OTs asociadas
                for ot in todas_las_ots:
                    for concepto in ot.conceptos:
                        if concepto.estado == EstadoConceptoOT.PENDIENTE.value:
                            concepto.estado = EstadoConceptoOT.CANCELADO.value
                            concepto.fecha_completado = datetime.now()
                            concepto.completado_por = "sistema (cascada)"
                            self.db.add(concepto)
                
                for v in viaticos_pendientes:
                    v.cancelar(usuario="sistema")
                    self.db.add(v)
            else:
                for ot in ots_pendientes:
                    ot.finalizar(usuario="sistema")
                    self.db.add(ot)
                
                # Actualizar conceptos de TODAS las OTs asociadas
                for ot in todas_las_ots:
                    for concepto in ot.conceptos:
                        if concepto.estado == EstadoConceptoOT.PENDIENTE.value:
                            concepto.estado = EstadoConceptoOT.COMPLETADO.value
                            concepto.fecha_completado = datetime.now()
                            concepto.completado_por = "sistema (cascada)"
                            self.db.add(concepto)
                
                for v in viaticos_pendientes:
                    v.finalizar(usuario="sistema")
                    self.db.add(v)
        
        if es_cancelacion:
            cotizacion.cancelar(motivo, "sistema")
        else:
            cotizacion.finalizar(motivo, "sistema")
        
        self.db.add(cotizacion)
        self.db.commit()
        self.db.refresh(cotizacion)
        return cotizacion


