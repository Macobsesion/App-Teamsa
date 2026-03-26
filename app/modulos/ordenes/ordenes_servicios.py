"""Capa de Servicios de Dominio para Órdenes de Trabajo."""
from datetime import date, datetime
from typing import Optional
from sqlmodel import Session, select

from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError
from app.base.eventos import BusEventos
from app.base.folios import GeneradorFolio
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.ordenes.enums import EstadoConceptoOT
from app.modulos.ordenes.eventos import EVENTO_ORDEN_CREADA, EVENTO_ORDEN_FINALIZADA, EVENTO_ORDEN_CANCELADA

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

    def verificar_empalme_tecnico(self, tecnico_id: int, fecha: date, hora: str, duracion: int, excluir_orden_id: int | None = None) -> OrdenTrabajo | None:
        consulta = select(OrdenTrabajo).where(
            OrdenTrabajo.tecnico_id == tecnico_id,
            OrdenTrabajo.fecha_programada == fecha,
            OrdenTrabajo.estado.notin_(["cancelada", "finalizada"]),
        )
        if excluir_orden_id:
            consulta = consulta.where(OrdenTrabajo.id != excluir_orden_id)
        ots_mismo_dia = self.db.exec(consulta).all()

        def a_minutos(h: str) -> int:
            partes = h.split(":")
            return int(partes[0]) * 60 + int(partes[1])

        inicio_nuevo = a_minutos(hora)
        fin_nuevo = inicio_nuevo + (duracion * 60)

        for ot in ots_mismo_dia:
            inicio_ot = a_minutos(ot.hora_programada)
            fin_ot = inicio_ot + (ot.duracion * 60)
            if inicio_nuevo < fin_ot and fin_nuevo > inicio_ot:
                return ot
        return None

    def listar_tecnicos(self) -> list[Usuario]:
        return list(self.db.exec(select(Usuario).where(Usuario.rol == "tecnico")).all())

    def crear_desde_cotizacion(self, cotizacion_id: int, fecha_programada: date, hora_programada: str, duracion: int, usuario: str, concepto_ids: list[int], tecnico_id: int | None = None) -> OrdenTrabajo:
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
            conflicto = self.verificar_empalme_tecnico(tecnico_id, fecha_programada, hora_programada, duracion)
            if conflicto:
                raise EmpalmeError(
                    f"El técnico '{tecnico.nombres}' ya tiene la OT {conflicto.numero_ot} "
                    f"asignada ese día de {conflicto.hora_programada} ({conflicto.duracion}h). Hay empalme de horario."
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

        self.db.add(orden)
        self.db.flush()
        orden.asignar_folio(self.generador_folio)

        for concepto in conceptos_cot:
            snapshot = ConceptoOrdenTrabajo(
                orden_id=orden.id,
                concepto_cotizacion_id=concepto.id,
                descripcion=concepto.descripcion,
                cantidad=concepto.cantidad,
                precio_unitario=concepto.precio_unitario,
                descuento_porcentaje=concepto.descuento_porcentaje,
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
            from app.modulos.ordenes.enums import EstadoOrden
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
        from app.modulos.ordenes.enums import EstadoOrden
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
        from app.modulos.ordenes.enums import EstadoOrden
        if not orden.es_cancelable:
            raise ReglaNegocioError("La orden ya está finalizada o cancelada.")
        if orden.estado != EstadoOrden.CANCELADA.value:
            orden.estado = EstadoOrden.CANCELADA.value
            self.db.add(orden)
            self.db.commit()
            BusEventos.publicar(EVENTO_ORDEN_CANCELADA, {"orden_id": orden.id, "cotizacion_id": orden.cotizacion_id, "session_actual": self.db})
        return orden

    def reasignar_tecnico(self, orden_id: int, tecnico_id: int | None, usuario: str) -> OrdenTrabajo:
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
