"""Capa de Servicios de Dominio para Órdenes de Trabajo."""
from datetime import date, datetime
from typing import Optional
from sqlmodel import Session, select

from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError
from app.base.eventos import BusEventos
from app.base.folios import GeneradorFolio
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.ordenes_trabajo.enums import EstadoConceptoOT
from app.modulos.ordenes_trabajo.eventos import EVENTO_ORDEN_CREADA, EVENTO_ORDEN_FINALIZADA, EVENTO_ORDEN_CANCELADA

class EmpalmeError(ReglaNegocioError):
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo="EMPALME_HORARIO")

class ConceptoYaAsignadoError(ReglaNegocioError):
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo="CONCEPTO_YA_ASIGNADO")

class ConceptoCompletadoError(ReglaNegocioError):
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo="CONCEPTO_COMPLETADO")

class ServicioOrdenes:
    def __init__(self, db: Session, generador_folio: GeneradorFolio):
        self.db = db
        self.generador_folio = generador_folio

    def verificar_empalme_tecnico(self, tecnico_id: int, fecha: date, hora: str, duracion: int, excluir_orden_id: int | None = None, unidad_duracion: str = "horas") -> OrdenTrabajo | None:
        from datetime import timedelta
        
        # Calcular rango sugerido
        fecha_inicio_nueva = fecha
        fecha_fin_nueva = fecha
        if unidad_duracion == "dias":
            fecha_fin_nueva = fecha + timedelta(days=duracion - 1)

        # 1. Buscar OTs existentes del técnico que no estén canceladas/finalizadas
        consulta = select(OrdenTrabajo).where(
            OrdenTrabajo.tecnico_id == tecnico_id,
            OrdenTrabajo.estado.notin_(["cancelada", "finalizada"]),
        )
        if excluir_orden_id:
            consulta = consulta.where(OrdenTrabajo.id != excluir_orden_id)
            
        ots_tecnico = self.db.exec(consulta).all()

        for ot in ots_tecnico:
            # Calcular rango de la OT existente
            ot_fecha_fin = ot.fecha_programada
            if ot.unidad_duracion == "dias":
                ot_fecha_fin = ot.fecha_programada + timedelta(days=ot.duracion - 1)
            
            # Verificar solapamiento de fechas
            if max(fecha_inicio_nueva, ot.fecha_programada) <= min(fecha_fin_nueva, ot_fecha_fin):
                # Si hay solapamiento de fechas, checar si es por horas o días
                if unidad_duracion == "dias" or ot.unidad_duracion == "dias":
                    # Al menos una es por días, el solapamiento de fecha es suficiente para el empalme
                    return ot
                else:
                    # Ambas son por horas en el mismo día (ya sabemos que es el mismo día por el overlap de max/min)
                    def a_minutos(h: str) -> int:
                        partes = h.split(":")
                        return int(partes[0]) * 60 + int(partes[1])

                    inicio_nuevo = a_minutos(hora)
                    fin_nuevo = inicio_nuevo + (duracion * 60)
                    inicio_ot = a_minutos(ot.hora_programada)
                    fin_ot = inicio_ot + (ot.duracion * 60)
                    
                    if inicio_nuevo < fin_ot and fin_nuevo > inicio_ot:
                        return ot
                        
        # 2. Verificar empalmes de Viáticos directos (por si hay viáticos sin OT aún)
        from app.modulos.viaticos.viaticos_modelo import Viatico, ViaticoOrdenEnlace
        consulta_v = select(Viatico).where(
            Viatico.responsable_id == tecnico_id,
            Viatico.estado.notin_(["cancelado", "borrador"]),
        )
        viaticos_activos = self.db.exec(consulta_v).all()
        for v in viaticos_activos:
            if v.fecha_salida and v.fecha_regreso:
                if max(fecha_inicio_nueva, v.fecha_salida) <= min(fecha_fin_nueva, v.fecha_regreso):
                    # Si ya está vinculado a alguna OT que NO estamos excluyendo, el check anterior ya lo atrapó.
                    # Aquí buscamos viáticos "viviendo solos" o vinculados a otras OTs.
                    es_vinculado_a_excluida = False
                    if excluir_orden_id:
                        enlaces = self.db.exec(select(ViaticoOrdenEnlace).where(
                            ViaticoOrdenEnlace.viatico_id == v.id,
                            ViaticoOrdenEnlace.orden_id == excluir_orden_id
                        )).all()
                        if enlaces:
                            es_vinculado_a_excluida = True
                    
                    if not es_vinculado_a_excluida:
                        class SimulacionEmpalme:
                            numero_ot = f"Viaje de Viáticos '{v.proyecto or v.folio}'"
                            hora_programada = "Itinerario Completo"
                            duracion = "N/A"
                            unidad_duracion = "en el viaje"
                        return SimulacionEmpalme() # type: ignore
                
        return None

    def listar_tecnicos(self) -> list[Usuario]:
        return list(self.db.exec(select(Usuario).where(Usuario.rol == "tecnico")).all())

    def crear_desde_cotizacion(self, cotizacion_id: int, fecha_programada: date, hora_programada: str, duracion: int, usuario: str, concepto_ids: list[int], tecnico_id: int | None = None, fuerza: bool = False, unidad_duracion: str = "horas") -> OrdenTrabajo:
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise RecursoNoEncontradoError(f"Cotización {cotizacion_id} no encontrada")

        tecnico_nombre = None
        if tecnico_id:
            tecnico = self.db.get(Usuario, tecnico_id)
            if not tecnico:
                raise RecursoNoEncontradoError(f"Técnico {tecnico_id} no encontrado")
            if tecnico.rol != "tecnico":
                raise ReglaNegocioError(f"El usuario '{tecnico.usuario}' no tiene rol 'tecnico'")
            if tecnico_id and not fuerza:
                # Nota: verificar_empalme_tecnico ahora debe considerar la unidad
                conflicto = self.verificar_empalme_tecnico(tecnico_id, fecha_programada, hora_programada, duracion, unidad_duracion=unidad_duracion)
                if conflicto:
                    raise EmpalmeError(
                        f"El técnico '{tecnico.nombres}' ya tiene la OT {conflicto.numero_ot} "
                        f"asignada ese día de {conflicto.hora_programada} ({conflicto.duracion} {conflicto.unidad_duracion}). Hay empalme de horario."
                    )
            tecnico_nombre = tecnico.nombres

        conceptos_cot: list[ConceptoCotizacion] = []
        if concepto_ids:
            conceptos_cot = self.db.exec(select(ConceptoCotizacion).where(ConceptoCotizacion.id.in_(concepto_ids), ConceptoCotizacion.cotizacion_id == cotizacion_id)).all()
            ids_encontrados = {c.id for c in conceptos_cot}
            for cid in concepto_ids:
                if cid not in ids_encontrados:
                    raise RecursoNoEncontradoError(f"Concepto {cid} no pertenece a la cotización {cotizacion_id}")
            for concepto in conceptos_cot:
                existente = self.db.exec(select(ConceptoOrdenTrabajo).where(ConceptoOrdenTrabajo.concepto_cotizacion_id == concepto.id)).first()
                if existente:
                    raise ConceptoYaAsignadoError(f"El concepto '{concepto.descripcion}' (#{concepto.id}) ya está asignado a otra OT.")

        orden = OrdenTrabajo.crear_desde_cotizacion(
            cotizacion=cotizacion,
            fecha_programada=fecha_programada,
            hora_programada=hora_programada,
            duracion=duracion,
            usuario_id=usuario,
            generador_folio=self.generador_folio,
            tecnico_id=tecnico_id,
            tecnico_nombre=tecnico_nombre,
        )
        orden.unidad_duracion = unidad_duracion

        self.db.add(orden)
        self.db.flush()

        # Calcular secuencia para esta cotización
        from sqlalchemy import func
        conteo = self.db.exec(
            select(func.count(OrdenTrabajo.id))
            .where(OrdenTrabajo.cotizacion_id == cotizacion_id)
        ).first() or 0
        secuencia = conteo 

        orden.asignar_folio(cotizacion_numero=cotizacion.numero, secuencia=secuencia)

        # Importar modelos de viáticos para vinculación
        from app.modulos.viaticos.viaticos_modelo import Viatico, ViaticoOrdenEnlace
        from app.modulos.viaticos.enums import EstadoViatico
        from datetime import timedelta

        viaticos_vinculados = set()

        for concepto in conceptos_cot:
            # Si el concepto es un Viático, lo vinculamos y actualizamos fechas, pero NO creamos snapshot
            if concepto.viatico_id:
                viatico = self.db.get(Viatico, concepto.viatico_id)
                if viatico and viatico.id not in viaticos_vinculados:
                    # Crear enlace N:M
                    enlace = ViaticoOrdenEnlace(viatico_id=viatico.id, orden_id=orden.id)
                    self.db.add(enlace)
                    
                    # Sincronizar fechas basadas en la OT
                    viatico.fecha_salida = fecha_programada
                    if unidad_duracion == "dias":
                        viatico.fecha_regreso = fecha_programada + timedelta(days=duracion - 1)
                    else:
                        viatico.fecha_regreso = fecha_programada
                    
                    viatico.estado = EstadoViatico.APROBADO.value
                    self.db.add(viatico)
                    viaticos_vinculados.add(viatico.id)
                
                # Omitimos el snapshot para no duplicar en la lista del técnico
                continue

            snapshot = ConceptoOrdenTrabajo(
                orden_id=orden.id,
                concepto_cotizacion_id=concepto.id,
                descripcion=concepto.descripcion,
                cantidad=concepto.cantidad,
                precio_unitario=concepto.precio_unitario,
                importe=concepto.importe,
                unidad=concepto.unidad,
                creado_por=usuario,
            )
            self.db.add(snapshot)

        self.db.commit()
        self.db.refresh(orden)
        
        BusEventos.publicar(EVENTO_ORDEN_CREADA, {
            "orden_id": orden.id,
            "cotizacion_id": orden.cotizacion_id,
            "evento_tipo": EVENTO_ORDEN_CREADA,
            "session_actual": self.db
        })

        return orden

    def completar_concepto(self, orden_id: int, concepto_id: int, usuario: str) -> ConceptoOrdenTrabajo:
        concepto = self.db.exec(select(ConceptoOrdenTrabajo).where(ConceptoOrdenTrabajo.id == concepto_id, ConceptoOrdenTrabajo.orden_id == orden_id,)).first()
        if not concepto:
            raise RecursoNoEncontradoError(f"Concepto {concepto_id} no encontrado en la OT {orden_id}")
        if concepto.estado == EstadoConceptoOT.COMPLETADO.value:
            raise ConceptoCompletadoError(f"El concepto '{concepto.descripcion}' ya está completado (irreversible).")

        concepto.estado = EstadoConceptoOT.COMPLETADO.value
        concepto.fecha_completado = datetime.utcnow()
        concepto.completado_por = usuario

        self.db.add(concepto)
        self.db.commit()
        self.db.refresh(concepto)

        pendientes = self.db.exec(select(ConceptoOrdenTrabajo).where(ConceptoOrdenTrabajo.orden_id == orden_id, ConceptoOrdenTrabajo.estado == EstadoConceptoOT.PENDIENTE.value)).all()
        if not pendientes:
            orden = self.db.get(OrdenTrabajo, orden_id)
            from app.modulos.ordenes_trabajo.enums import EstadoOrden
            if orden and orden.estado != EstadoOrden.FINALIZADA.value:
                orden.estado = EstadoOrden.FINALIZADA.value
                self.db.add(orden)
                self.db.commit()
                BusEventos.publicar(EVENTO_ORDEN_FINALIZADA, {"orden_id": orden.id, "cotizacion_id": orden.cotizacion_id, "session_actual": self.db})

        return concepto

    def finalizar_orden(self, orden_id: int) -> OrdenTrabajo:
        orden = self.db.get(OrdenTrabajo, orden_id)
        if not orden:
            raise RecursoNoEncontradoError(f"Orden {orden_id} no encontrada")
        from app.modulos.ordenes_trabajo.enums import EstadoOrden
        if orden.estado != EstadoOrden.FINALIZADA.value:
            orden.estado = EstadoOrden.FINALIZADA.value
            self.db.add(orden)
            self.db.commit()
            BusEventos.publicar(EVENTO_ORDEN_FINALIZADA, {"orden_id": orden.id, "cotizacion_id": orden.cotizacion_id, "session_actual": self.db})
        return orden

    def cancelar_orden(self, orden_id: int) -> OrdenTrabajo:
        orden = self.db.get(OrdenTrabajo, orden_id)
        if not orden:
            raise RecursoNoEncontradoError(f"Orden {orden_id} no encontrada")
        from app.modulos.ordenes_trabajo.enums import EstadoOrden
        if not orden.es_cancelable:
            raise ReglaNegocioError("La orden ya está finalizada o cancelada.")
        if orden.estado != EstadoOrden.CANCELADA.value:
            orden.estado = EstadoOrden.CANCELADA.value
            
            self.db.add(orden)
            self.db.commit()
            BusEventos.publicar(EVENTO_ORDEN_CANCELADA, {
                "orden_id": orden.id, 
                "cotizacion_id": orden.cotizacion_id, 
                "evento_tipo": EVENTO_ORDEN_CANCELADA,
                "session_actual": self.db
            })
        return orden

    def reasignar_tecnico(self, orden_id: int, tecnico_id: int | None, usuario: str, fuerza: bool = False) -> OrdenTrabajo:
        orden = self.db.get(OrdenTrabajo, orden_id)
        if not orden:
            raise RecursoNoEncontradoError(f"Orden {orden_id} no encontrada")
        if not orden.es_editable:
            raise ReglaNegocioError("Solo se puede reasignar técnico en OTs programadas o en curso")
        if tecnico_id is None:
            orden.tecnico_id = None
            orden.tecnico_nombre = None
        else:
            tecnico = self.db.get(Usuario, tecnico_id)
            if not tecnico:
                raise RecursoNoEncontradoError(f"Técnico {tecnico_id} no encontrado")
            if tecnico.rol != "tecnico":
                raise ReglaNegocioError(f"El usuario '{tecnico.usuario}' no tiene rol 'tecnico'")
            if not fuerza:
                conflicto = self.verificar_empalme_tecnico(tecnico_id, orden.fecha_programada, orden.hora_programada, orden.duracion, excluir_orden_id=orden_id)
                if conflicto:
                    raise EmpalmeError(f"El técnico '{tecnico.nombres}' ya tiene la OT {conflicto.numero_ot} ese día de {conflicto.hora_programada} ({conflicto.duracion}h).")
            orden.tecnico_id = tecnico_id
            orden.tecnico_nombre = tecnico.nombres
            orden.modificado_por = usuario

        self.db.add(orden)
        self.db.commit()
        self.db.refresh(orden)
        return orden
