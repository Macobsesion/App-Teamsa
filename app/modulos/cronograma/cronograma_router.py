"""Router del Cronograma — Vista de calendario para OTs y Viáticos."""
from datetime import date, timedelta
from calendar import monthrange
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual, dp_usuario_db
from app.rutas.permisos import para_modulo
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.web.jinja import get_templates

TEMPLATES = get_templates()

router_cronograma_ui = APIRouter(prefix="/ui/cronograma", tags=["Cronograma"])
router_cronograma_api = APIRouter(prefix="/api/cronograma", tags=["Cronograma"])


@router_cronograma_ui.get("")
def vista_cronograma(
    request: Request,
    usuario: Usuario = Depends(dp_usuario_db)
):
    """Vista principal del cronograma con calendario mensual."""
    from app.base.timezone import hoy_mexico
    hoy = hoy_mexico()
    return TEMPLATES.TemplateResponse(
        "ui/cronograma/cronograma.html",
        {
            "request": request,
            "usuario": usuario,
            "anio": hoy.year,
            "mes": hoy.month,
            "hoy": hoy.isoformat(),
        }
    )


@router_cronograma_api.get("/eventos")
def obtener_eventos(
    anio: int,
    mes: int,
    db: Session = Depends(obtener_sesion_bd),
    usuario: Usuario = Depends(dp_usuario_db)
):
    """Retorna OTs y Viáticos del mes como JSON para el calendario."""
    primer_dia = date(anio, mes, 1)
    _, ultimo = monthrange(anio, mes)
    ultimo_dia = date(anio, mes, ultimo)

    # OTs del mes
    query_ot = select(OrdenTrabajo).where(
        OrdenTrabajo.fecha_programada >= primer_dia,
        OrdenTrabajo.fecha_programada <= ultimo_dia,
        OrdenTrabajo.estado.notin_(["cancelada"])
    )

    # Filtro por técnico si el usuario es técnico
    es_tecnico = getattr(usuario, "rol", "") == "tecnico"
    if es_tecnico:
        query_ot = query_ot.where(OrdenTrabajo.tecnico_id == usuario.id)

    ots = db.exec(query_ot).all()

    # Viáticos del mes (que se solapan con el rango del mes)
    query_via = select(Viatico).where(
        Viatico.fecha_salida <= ultimo_dia,
        Viatico.fecha_regreso >= primer_dia,
        Viatico.estado.notin_(["cancelado"])
    )
    if es_tecnico:
        query_via = query_via.where(Viatico.responsable_id == usuario.id)

    viaticos = db.exec(query_via).all()

    eventos = []

    for ot in ots:
        fecha_fin = ot.fecha_programada
        if ot.unidad_duracion == "dias":
            fecha_fin = ot.fecha_programada + timedelta(days=ot.duracion - 1)

        eventos.append({
            "id": f"ot-{ot.id}",
            "tipo": "ot",
            "titulo": ot.numero_ot,
            "fecha_inicio": ot.fecha_programada.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "hora": ot.hora_programada,
            "duracion": ot.duracion,
            "unidad": ot.unidad_duracion or "horas",
            "estado": ot.estado_visual,
            "tecnico": ot.tecnico_nombre or "Sin asignar",
            "cliente": ot.cliente_nombre,
            "url": f"/ui/ordenes-trabajo/{ot.id}/detalle",
        })

    for v in viaticos:
        eventos.append({
            "id": f"via-{v.id}",
            "tipo": "viatico",
            "titulo": v.folio,
            "fecha_inicio": v.fecha_salida.isoformat() if v.fecha_salida else "",
            "fecha_fin": v.fecha_regreso.isoformat() if v.fecha_regreso else "",
            "estado": v.estado_visual,
            "proyecto": v.proyecto or "Viaje",
            "ruta": f"{v.origen or '?'} → {v.destino or '?'}",
            "url": f"/ui/viaticos/{v.id}/detalle",
        })

    return eventos
