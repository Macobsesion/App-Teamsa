from sqlmodel import Session, select
from datetime import date, datetime, timedelta
from typing import Any
from app.base.repositorio import RepositorioCRUD
from app.base.eventos import BusEventos
from app.base.folios import EstrategiaFolioFechaId, GeneradorFolio
from app.base.excepciones import RecursoNoEncontradoError

from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.modulos.ordenes.enums import EstadoConceptoOT
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.ordenes.eventos import EVENTO_ORDEN_CREADA, EVENTO_ORDEN_FINALIZADA, EVENTO_ORDEN_CANCELADA
from app.nucleo.base_datos import obtener_motor


class EmpalmeError(Exception):
    """Se lanza cuando un técnico tiene un empalme de horario."""
    pass


class ConceptoYaAsignadoError(Exception):
    """Se lanza cuando un concepto ya está asignado a otra OT."""
    pass


class ConceptoCompletadoError(Exception):
    """Se lanza al intentar modificar un concepto ya completado."""
    pass


class RepositorioOrden(RepositorioCRUD[OrdenTrabajo]):
    def __init__(self, db: Session, generador_folio: GeneradorFolio | None = None):
        super().__init__(db)
        self.modelo = OrdenTrabajo
        self.campos_filtrables = {'estado', 'usuario_id'}
        self.generador_folio = generador_folio or EstrategiaFolioFechaId()

    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        return datos

    def _post_guardar(self, entidad: OrdenTrabajo, es_nuevo: bool) -> None:
        if es_nuevo:
            BusEventos.publicar(EVENTO_ORDEN_CREADA, {
                "orden_id": entidad.id,
                "cotizacion_id": entidad.cotizacion_id,
                "session_actual": self.db
            })

    def eliminar(self, entidad_id: int) -> None:
        """
        La eliminación física está desactivada para preservar historial.
        """
        raise ValueError("La eliminación física está deshabilitada. Por favor, cambie el estado a 'Cancelada'.")

    # ---- Validación de empalme ----

    def verificar_empalme_tecnico(
        self,
        tecnico_id: int,
        fecha: date,
        hora: str,
        duracion: int,
        excluir_orden_id: int | None = None
    ) -> OrdenTrabajo | None:
        """
        Verifica si el técnico tiene otra OT activa que se empalme con el horario dado.
        
        Dos OTs se empalman si comparten la misma fecha y sus rangos horarios se solapan.
        Rango = [hora_inicio, hora_inicio + duracion_horas)
        
        Returns:
            La OT conflictiva o None si no hay empalme.
        """
        consulta = select(OrdenTrabajo).where(
            OrdenTrabajo.tecnico_id == tecnico_id,
            OrdenTrabajo.fecha_programada == fecha,
            OrdenTrabajo.estado.notin_(["cancelada", "finalizada"]),
        )
        if excluir_orden_id:
            consulta = consulta.where(OrdenTrabajo.id != excluir_orden_id)

        ots_mismo_dia = self.db.exec(consulta).all()

        # Convertir hora "HH:MM" a minutos desde medianoche para comparar rangos
        def a_minutos(h: str) -> int:
            partes = h.split(":")
            return int(partes[0]) * 60 + int(partes[1])

        inicio_nuevo = a_minutos(hora)
        fin_nuevo = inicio_nuevo + (duracion * 60)

        for ot in ots_mismo_dia:
            inicio_ot = a_minutos(ot.hora_programada)
            fin_ot = inicio_ot + (ot.duracion * 60)
            # Solapamiento: los rangos se cruzan si inicio_A < fin_B y fin_A > inicio_B
            if inicio_nuevo < fin_ot and fin_nuevo > inicio_ot:
                return ot

        return None

    # ---- Técnicos ----

    def listar_tecnicos(self) -> list[Usuario]:
        """Lista usuarios con rol 'tecnico' para el dropdown de asignación."""
        return list(self.db.exec(
            select(Usuario).where(Usuario.rol == "tecnico")
        ).all())

    # ---- Creación con conceptos ----

    def crear_desde_cotizacion(
        self,
        cotizacion_id: int,
        fecha_programada: date,
        hora_programada: str,
        duracion: int,
        usuario: str,
        concepto_ids: list[int],
        tecnico_id: int | None = None,
    ) -> OrdenTrabajo:
        """
        Orquesta la creación de una Orden a partir de una Cotización.
        
        - Valida que la cotización exista
        - Si hay técnico, valida que no tenga empalme
        - [ANTES del flush] Valida que los conceptos no estén ya asignados
        - Crea la OT con snapshot de técnico
        - Crea los ConceptoOrdenTrabajo seleccionados (con snapshot)
        Todo en una sola transacción.
        """
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise RecursoNoEncontradoError(f"Cotización {cotizacion_id} no encontrada")

        # Snapshot del técnico si se asigna
        tecnico_nombre = None
        if tecnico_id:
            tecnico = self.db.get(Usuario, tecnico_id)
            if not tecnico:
                raise RecursoNoEncontradoError(f"Técnico {tecnico_id} no encontrado")
            if tecnico.rol != "tecnico":
                raise ValueError(f"El usuario '{tecnico.usuario}' no tiene rol 'tecnico'")
            # Validar empalme
            conflicto = self.verificar_empalme_tecnico(tecnico_id, fecha_programada, hora_programada, duracion)
            if conflicto:
                raise EmpalmeError(
                    f"El técnico '{tecnico.nombres}' ya tiene la OT {conflicto.numero_ot} "
                    f"asignada ese día de {conflicto.hora_programada} "
                    f"({conflicto.duracion}h). Hay empalme de horario."
                )
            tecnico_nombre = tecnico.nombres

        # ── Validar conceptos ANTES de tocar la BD ──────────────────────────
        conceptos_cot: list[ConceptoCotizacion] = []
        if concepto_ids:
            conceptos_cot = self.db.exec(
                select(ConceptoCotizacion).where(
                    ConceptoCotizacion.id.in_(concepto_ids),
                    ConceptoCotizacion.cotizacion_id == cotizacion_id,
                )
            ).all()

            ids_encontrados = {c.id for c in conceptos_cot}
            for cid in concepto_ids:
                if cid not in ids_encontrados:
                    raise RecursoNoEncontradoError(
                        f"Concepto {cid} no pertenece a la cotización {cotizacion_id}"
                    )

            for concepto in conceptos_cot:
                existente = self.db.exec(
                    select(ConceptoOrdenTrabajo).where(
                        ConceptoOrdenTrabajo.concepto_cotizacion_id == concepto.id
                    )
                ).first()
                if existente:
                    raise ConceptoYaAsignadoError(
                        f"El concepto '{concepto.descripcion}' (#{concepto.id}) "
                        f"ya está asignado a otra OT."
                    )
        # ────────────────────────────────────────────────────────────────────

        # Crear instancia de OT con Factory Method
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
        self.db.flush()  # El ID de la OT queda disponible aquí

        # Asignar folio definitivo usando el ID de la OT (garantiza unicidad)
        orden.asignar_folio(self.generador_folio)

        # Crear snapshots de los ConceptoOrdenTrabajo (ya validados)
        for concepto in conceptos_cot:
            snapshot = ConceptoOrdenTrabajo(
                orden_id=orden.id,
                concepto_cotizacion_id=concepto.id,
                descripcion=concepto.descripcion,
                cantidad=concepto.cantidad,
                precio_unitario=concepto.precio_unitario,
                importe=concepto.importe,
                unidad=concepto.unidad,
            )
            self.db.add(snapshot)

        self.db.commit()
        self.db.refresh(orden)
        self._post_guardar(orden, es_nuevo=True)

        return orden

    # ---- Conceptos ----

    def completar_concepto(
        self,
        orden_id: int,
        concepto_id: int,
        usuario: str
    ) -> ConceptoOrdenTrabajo:
        """
        Marca un concepto de OT como completado (irreversible: pendiente → completado).
        """
        concepto = self.db.exec(
            select(ConceptoOrdenTrabajo).where(
                ConceptoOrdenTrabajo.id == concepto_id,
                ConceptoOrdenTrabajo.orden_id == orden_id,
            )
        ).first()

        if not concepto:
            raise RecursoNoEncontradoError(
                f"Concepto {concepto_id} no encontrado en la OT {orden_id}"
            )
        if concepto.estado == EstadoConceptoOT.COMPLETADO.value:
            raise ConceptoCompletadoError(
                f"El concepto '{concepto.descripcion}' ya está completado (irreversible)."
            )

        concepto.estado = EstadoConceptoOT.COMPLETADO.value
        concepto.fecha_completado = datetime.utcnow()
        concepto.completado_por = usuario

        self.db.add(concepto)
        self.db.commit()
        self.db.refresh(concepto)

        # Verificacion de finalizacion automatica de la OT
        pendientes = self.db.exec(
            select(ConceptoOrdenTrabajo).where(
                ConceptoOrdenTrabajo.orden_id == orden_id,
                ConceptoOrdenTrabajo.estado == EstadoConceptoOT.PENDIENTE.value
            )
        ).all()

        if not pendientes:
            # Todos los conceptos están completados, finalizar automáticamente la OT
            orden = self.db.get(OrdenTrabajo, orden_id)
            from app.modulos.ordenes.enums import EstadoOrden
            if orden and orden.estado != EstadoOrden.FINALIZADA.value:
                orden.estado = EstadoOrden.FINALIZADA.value
                self.db.add(orden)
                self.db.commit()
                # Disparar evento para actualizar cotización
                BusEventos.publicar(EVENTO_ORDEN_FINALIZADA, {
                    "orden_id": orden.id,
                    "cotizacion_id": orden.cotizacion_id,
                    "session_actual": self.db
                })

        return concepto

    # ---- Cambios de Estado Manuales ----

    def finalizar_orden(self, orden_id: int) -> OrdenTrabajo:
        """Finaliza manualmente una OT (ej. si no tiene conceptos y se terminó)."""
        orden = self.db.get(OrdenTrabajo, orden_id)
        if not orden:
            raise RecursoNoEncontradoError(f"Orden {orden_id} no encontrada")
        
        from app.modulos.ordenes.enums import EstadoOrden
        if orden.estado != EstadoOrden.FINALIZADA.value:
            orden.estado = EstadoOrden.FINALIZADA.value
            self.db.add(orden)
            self.db.commit()
            BusEventos.publicar(EVENTO_ORDEN_FINALIZADA, {
                "orden_id": orden.id,
                "cotizacion_id": orden.cotizacion_id,
                "session_actual": self.db
            })
        return orden

    def cancelar_orden(self, orden_id: int) -> OrdenTrabajo:
        """Cancela una OT. Retorna a estado anterior la cotización si era la única activa."""
        orden = self.db.get(OrdenTrabajo, orden_id)
        if not orden:
            raise RecursoNoEncontradoError(f"Orden {orden_id} no encontrada")
        
        from app.modulos.ordenes.enums import EstadoOrden
        if not orden.es_cancelable:
            raise ValueError("La orden ya está finalizada o cancelada.")

        if orden.estado != EstadoOrden.CANCELADA.value:
            orden.estado = EstadoOrden.CANCELADA.value
            self.db.add(orden)
            self.db.commit()
            BusEventos.publicar(EVENTO_ORDEN_CANCELADA, {
                "orden_id": orden.id,
                "cotizacion_id": orden.cotizacion_id,
                "session_actual": self.db
            })
        return orden

    # ---- Reasignación de técnico ----


    def reasignar_tecnico(
        self,
        orden_id: int,
        tecnico_id: int | None,
        usuario: str
    ) -> OrdenTrabajo:
        """
        Reasigna o quita el técnico de una OT.
        Valida empalme excluyendo la OT actual.
        """
        orden = self.db.get(OrdenTrabajo, orden_id)
        if not orden:
            raise RecursoNoEncontradoError(f"Orden {orden_id} no encontrada")
        if not orden.es_editable:
            raise ValueError("Solo se puede reasignar técnico en OTs programadas o en curso")

        if tecnico_id is None:
            # Quitar asignación
            orden.tecnico_id = None
            orden.tecnico_nombre = None
        else:
            tecnico = self.db.get(Usuario, tecnico_id)
            if not tecnico:
                raise RecursoNoEncontradoError(f"Técnico {tecnico_id} no encontrado")
            if tecnico.rol != "tecnico":
                raise ValueError(f"El usuario '{tecnico.usuario}' no tiene rol 'tecnico'")

            conflicto = self.verificar_empalme_tecnico(
                tecnico_id,
                orden.fecha_programada,
                orden.hora_programada,
                orden.duracion,
                excluir_orden_id=orden_id,
            )
            if conflicto:
                raise EmpalmeError(
                    f"El técnico '{tecnico.nombres}' ya tiene la OT {conflicto.numero_ot} "
                    f"ese día de {conflicto.hora_programada} ({conflicto.duracion}h)."
                )

            orden.tecnico_id = tecnico_id
            orden.tecnico_nombre = tecnico.nombres
            orden.modificado_por = usuario

        self.db.add(orden)
        self.db.commit()
        self.db.refresh(orden)
        return orden
