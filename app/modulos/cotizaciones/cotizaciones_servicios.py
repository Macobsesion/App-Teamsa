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

    def _hacer_snapshot_cliente(self, cotizacion: Cotizacion, cliente_id: int):
        """Copia los datos actuales del cliente a la cotización para persistencia histórica."""
        cliente = self.db.get(Cliente, cliente_id)
        if not cliente:
            return
        
        cotizacion.cliente_id = cliente.id
        cotizacion.cliente_nombre = cliente.nombre
        cotizacion.cliente_rfc = cliente.rfc
        cotizacion.cliente_direccion = cliente.direccion
        cotizacion.cliente_ciudad = cliente.ciudad
        cotizacion.cliente_cp = cliente.cp
        cotizacion.cliente_telefono = cliente.telefono
        cotizacion.cliente_email = cliente.email

    def _procesar_conceptos_y_viaticos(self, cotizacion: Cotizacion, data: Dict[str, Any], usuario: str):
        """
        Lógica unificada para procesar viáticos nuevos del wizard y vincular conceptos.
        Maneja el mapeo de viatico_temp_id -> viatico_id real.
        """
        from app.modulos.viaticos.viaticos_servicios import ServicioViaticos
        from app.modulos.viaticos.viaticos_modelo import Viatico
        from sqlmodel import select

        items_data = data.get('servicios', [])
        viaticos_nuevos_data = data.get('viaticos_nuevos', [])

        # 1. Obtener viaticos previos para conciliación (si es actualización)
        viaticos_previos = self.db.exec(select(Viatico).where(
            Viatico.cotizacion_id == cotizacion.id,
            Viatico.estado != "cancelado"
        )).all()
        viaticos_en_uso = set()

        # 2. Procesar viáticos nuevos del Wizard
        viatico_mapping = {}
        if viaticos_nuevos_data:
            srv_v = ServicioViaticos(self.db)
            viatico_mapping = srv_v.procesar_viaticos_wizard(cotizacion.id, cotizacion.cliente_id, viaticos_nuevos_data, usuario)
            # Los IDs reales resultantes del mapeo se consideran "en uso"
            for real_id in viatico_mapping.values():
                viaticos_en_uso.add(real_id)

        # 3. Estrategia de Fusión para Conceptos (Merge)
        conceptos_db = {c.id: c for c in self.repo.obtener_conceptos(cotizacion.id)}
        nuevos_conceptos_ids = set()
        
        repo_concepto = RepositorioConcepto(self.db)

        # 4. Procesar nuevos y actualizaciones
        for s_row in items_data:
            c_id = s_row.get('id')
            v_temp_id = s_row.get('viatico_temp_id')
            v_id_final = s_row.get('viatico_id')

            # Resolver mapping si es un viático recién creado en el wizard
            if v_temp_id is not None:
                try:
                    idx_map = int(v_temp_id)
                    if idx_map in viatico_mapping:
                        v_id_final = viatico_mapping[idx_map]
                except (ValueError, TypeError):
                    pass

            if c_id and c_id in conceptos_db:
                # ACTUALIZAR EXISTENTE
                c_obj = conceptos_db[c_id]
                c_obj.cantidad = Decimal(str(s_row.get('cantidad', 1)))
                c_obj.precio_unitario = Decimal(str(s_row.get('precio_unitario', 0)))
                c_obj.descuento_porcentaje = Decimal(str(s_row.get('descuento_porcentaje', 0)))
                # Snapshot: solo actualizar si viene descripción nueva
                if s_row.get('descripcion'):
                    c_obj.descripcion = s_row['descripcion']
                c_obj.viatico_id = v_id_final
                self.db.add(c_obj)
                nuevos_conceptos_ids.add(c_id)
            else:
                # CREAR NUEVO
                nuevo_c = repo_concepto.crear_concepto(
                    cotizacion_id=cotizacion.id,
                    servicio_id=s_row.get('servicio_id'),
                    viatico_id=v_id_final,
                    codigo_sat=s_row.get('codigo_sat', ''),
                    descripcion=s_row.get('descripcion', ''),
                    unidad=s_row.get('unidad', 'pieza'),
                    cantidad=Decimal(str(s_row.get('cantidad', 1))),
                    precio_unitario=Decimal(str(s_row.get('precio_unitario', 0))),
                    descuento_porcentaje=Decimal(str(s_row.get('descuento_porcentaje', 0))),
                )
                self.db.add(nuevo_c)
            
            if v_id_final:
                viaticos_en_uso.add(int(v_id_final))
                v_obj = self.db.get(Viatico, v_id_final)
                if v_obj and v_obj.cotizacion_id != cotizacion.id:
                    v_obj.cotizacion_id = cotizacion.id
                    self.db.add(v_obj)

        # 5. Eliminar conceptos que ya no están en el request
        for old_id, old_obj in conceptos_db.items():
            if old_id not in nuevos_conceptos_ids:
                self.db.delete(old_obj)

        # 5. Cancelar viáticos que ya no están en la lista (Conciliación)
        for v_old in viaticos_previos:
            if v_old.id not in viaticos_en_uso:
                v_old.estado = "cancelado"
                self.db.add(v_old)

        self.repo.recalcular_totales(cotizacion.id)
        self.db.flush() # Sincronizar cambios financieros antes de continuar

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

        # Procesar detalles y viáticos
        self._procesar_conceptos_y_viaticos(cotizacion, data, usuario)
        
        # Generar número definitivo (atómico)
        self.repo._post_guardar(cotizacion, es_nuevo=True)

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
        self._hacer_snapshot_cliente(cotizacion, cotizacion.cliente_id)
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
        cotizacion_anterior.estado = "modificada"
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
            estado='borrador',
            folio=folio_temp,
            numero=folio_temp, # Temporal
            numero_version=folio_temp, # Temporal
            creado_por=usuario,
            modificado_por=usuario,
            fecha_emision=date.today()
        )
        self._hacer_snapshot_cliente(nueva, cotizacion_anterior.cliente_id)
        nueva.actualizar_vigencia()
        
        self.db.add(nueva)
        self.db.flush()

        # 4. Procesar conceptos y transferir viáticos
        self._procesar_conceptos_y_viaticos(nueva, data, usuario)

        # Generar número definitivo (ej. COT-240101-B)
        self.repo._post_guardar(nueva, es_nuevo=True)

        self.db.commit()
        self.db.refresh(nueva)
        return nueva

    def cerrar_cotizacion(self, cotizacion_id: int, motivo: str, forzar: bool = False, estado_final: str = "cancelada") -> Cotizacion:
        """
        Cierra una cotización (estado 'cancelada' o 'finalizada').
        Valida dependencias y ofrece cierre en cascada.
        """
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Cotización no encontrada")
        
        # 1. Definir estados de exclusión según el destino
        from app.modulos.ordenes_trabajo.enums import EstadoOrden
        from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
        from app.modulos.viaticos.viaticos_modelo import Viatico
        from app.modulos.viaticos.enums import EstadoViatico
        from sqlalchemy import select

        es_cancelacion = estado_final == "cancelada"
        
        if es_cancelacion:
            excluir_ot = [EstadoOrden.CANCELADA.value]
            excluir_via = [EstadoViatico.CANCELADO.value]
        else:
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
            from app.modulos.ordenes_trabajo.ordenes_trabajo_servicios import ServicioOrdenes
            from app.base.folios import EstrategiaFolioMensual
            # Usamos EstrategiaFolioMensual por ser la estándar actual de COTs/OTs
            servicio_ot = ServicioOrdenes(self.db, EstrategiaFolioMensual())
            
            if es_cancelacion:
                for ot in ots_pendientes:
                    servicio_ot.cancelar_orden(ot.id)
                for v in viaticos_pendientes:
                    v.estado = EstadoViatico.CANCELADO.value
                    self.db.add(v)
            else:
                for ot in ots_pendientes:
                    servicio_ot.finalizar_orden(ot.id)
                for v in viaticos_pendientes:
                    v.estado = EstadoViatico.FINALIZADO.value
                    self.db.add(v)
        
        cotizacion.estado = estado_final
        cotizacion.notas = f"{cotizacion.notas or ''}\nEstado cambiado a {estado_final}: {motivo}".strip()
        
        self.db.add(cotizacion)
        self.db.commit()
        self.db.refresh(cotizacion)
        return cotizacion

    def obtener_estado_conceptos(self, cotizacion_id: int) -> Dict[int, Dict[str, Any]]:
        """Obtiene el estado de ejecución de cada concepto consultando las OTs."""
        from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import ConceptoOrdenTrabajo, OrdenTrabajo
        from sqlalchemy import select
        
        query = (
            select(ConceptoOrdenTrabajo, OrdenTrabajo.numero_ot, OrdenTrabajo.id.label("orden_id"))
            .join(OrdenTrabajo, ConceptoOrdenTrabajo.orden_id == OrdenTrabajo.id)
            .where(ConceptoOrdenTrabajo.concepto_cotizacion_id.in_(
                select(ConceptoCotizacion.id).where(ConceptoCotizacion.cotizacion_id == cotizacion_id)
            ))
        )
        
        resultados = self.db.exec(query).all()
        estado_map = {}
        for concepto_ot, numero_ot, orden_id in resultados:
            estado_map[concepto_ot.concepto_cotizacion_id] = {
                "estado": concepto_ot.estado,
                "numero_ot": numero_ot,
                "orden_id": orden_id
            }
        return estado_map

    def generar_ot_desde_cotizacion(self, cotizacion_id: int, usuario: str, concepto_ids: List[int] = None) -> Any:
        """
        Genera una o varias OTs desde la cotización.
        CORRECCIÓN: Delega correctamente en ServicioOrdenes para permitir Multi-OT.
        """
        from app.modulos.ordenes_trabajo.ordenes_trabajo_servicios import ServicioOrdenes
        from app.base.folios import EstrategiaFolioMensual
        from datetime import date
        
        servicio_ot = ServicioOrdenes(self.db, EstrategiaFolioMensual())
        
        # Si no se pasan IDs, se asumen todos los conceptos libres (comportamiento por defecto)
        if not concepto_ids:
            conceptos = self.repo.obtener_conceptos(cotizacion_id)
            # Filtrar solo los que aún no tienen OT (obtener_estado_conceptos ayuda aquí)
            est_map = self.obtener_estado_conceptos(cotizacion_id)
            concepto_ids = [c.id for c in conceptos if c.id not in est_map]

        if not concepto_ids:
            from app.base.excepciones import ReglaNegocioError
            raise ReglaNegocioError("No hay conceptos disponibles para generar una nueva OT.")

        # Por defecto programamos para hoy a las 09:00 AM si es una generación rápida
        # En la realidad el UI llama directamente al API de órdenes con estos datos.
        return servicio_ot.crear_desde_cotizacion(
            cotizacion_id=cotizacion_id,
            fecha_programada=date.today(),
            hora_programada="09:00",
            duracion=1,
            usuario=usuario,
            concepto_ids=concepto_ids
        )
