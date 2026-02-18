"""
Funciones auxiliares para versionamiento de cotizaciones.
"""
from datetime import date
from decimal import Decimal
from sqlmodel import Session
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity



def actualizar_sin_versionar(cotizacion_id: int, data: dict, db: Session, usuario: UsuarioIdentity):
    """
    Actualiza una cotización existente SIN crear nueva versión.
    Solo actualiza campos permitidos: metodo_pago, forma_pago, notas, notas_privadas.
    """
    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    
    if not cotizacion:
        raise ValueError("Cotización no encontrada")
    
    # Solo actualizar campos permitidos (NO servicios)
    cotizacion.metodo_pago = data.get('metodo_pago', cotizacion.metodo_pago)
    cotizacion.forma_pago = data.get('forma_pago', cotizacion.forma_pago)
    cotizacion.notas = data.get('notas')
    cotizacion.notas_privadas = data.get('notas_privadas')  # Campo para uso futuro
    cotizacion.modificado_por = usuario.usuario
    
    db.commit()
    db.refresh(cotizacion)
    
    return {"id": cotizacion.id, "numero": cotizacion.numero, "numero_version": cotizacion.numero_version}



def crear_nueva_version(cotizacion_id: int, data: dict, db: Session, usuario: UsuarioIdentity):
    """
    Crea una NUEVA VERSIÓN de una cotización existente.
    
    Funciona correctamente incluso si se versiona una versión (ej: COT-00001-B -> COT-00001-C).
    Siempre encuentra la cotización madre y todas sus versiones hermanas.
    """
    from app.modulos.cotizaciones.calculadora import ServicioCalculadoraCotizacion
    
    repo = RepositorioCotizacion(db)
    cotizacion_actual = db.get(Cotizacion, cotizacion_id)
    
    if not cotizacion_actual:
        raise ValueError("Cotización no encontrada")
    
    # 1. ENCONTRAR LA COTIZACIÓN MADRE (original)
    if cotizacion_actual.cotizacion_original_id:
        # Esta cotización ya es una versión, buscar la madre
        id_madre = cotizacion_actual.cotizacion_original_id
        cotizacion_madre = db.get(Cotizacion, id_madre)
        if not cotizacion_madre:
            raise ValueError("Cotización madre no encontrada")
    else:
        # Esta ES la cotización madre
        id_madre = cotizacion_actual.id
        cotizacion_madre = cotizacion_actual
    
    # 2. OBTENER TODAS LAS VERSIONES DE LA FAMILIA
    # Usar método del repositorio re-factorizado
    versiones = repo.obtener_versiones_familia(id_madre)
    letras_usadas = [v[1] for v in versiones]
    
    # 3. CALCULAR SIGUIENTE LETRA
    # Usar servicio de dominio puro
    nueva_letra = ServicioCalculadoraCotizacion.calcular_siguiente_letra(letras_usadas)
    
    # 4. EXTRAER NÚMERO BASE LIMPIO
    numero_base = ServicioCalculadoraCotizacion.extraer_numero_base(cotizacion_madre.numero)
    nuevo_numero = f"{numero_base}-{nueva_letra}"
    
    # 5. MARCAR LA COTIZACIÓN ACTUAL COMO MODIFICADA
    cotizacion_actual.estado = "modificada"
    db.add(cotizacion_actual)
    
    # 6. CREAR NUEVA VERSIÓN
    import uuid
    nueva_cotizacion = Cotizacion(
        folio=str(uuid.uuid4()),  # Temporal UUID para folio
        numero=nuevo_numero,  # COT-00001-C
        numero_version=nuevo_numero,  # Alias
        version_letra=nueva_letra,  # "C"
        cotizacion_original_id=id_madre,  # SIEMPRE apunta a la madre
        cliente_id=cotizacion_actual.cliente_id,  # Cliente no cambia
        estado='borrador',  # Nueva versión empieza como borrador
        metodo_pago=data.get('metodo_pago', cotizacion_actual.metodo_pago),
        forma_pago=data.get('forma_pago', cotizacion_actual.forma_pago),
        notas=data.get('notas'),
        notas_privadas=data.get('notas_privadas'),
        fecha_emision=date.today(),
        fecha_vigencia=date.today(), # Placeholder, se recalcula abajo
        creado_por=usuario.usuario,
        modificado_por=usuario.usuario,
    )
    
    # Recalcular vigencia con lógica encapsulada
    nueva_cotizacion.actualizar_vigencia()
    
    db.add(nueva_cotizacion)
    db.flush()  # Para obtener el ID
    
    # 7. COPIAR SERVICIOS MODIFICADOS
    repo_concepto = RepositorioConcepto(db)
    for servicio_data in data.get('servicios', []):
        repo_concepto.crear(
            cotizacion_id=nueva_cotizacion.id,
            servicio_id=servicio_data.get('servicio_id'),
            codigo_sat=servicio_data['codigo_sat'],
            descripcion=servicio_data['descripcion'],
            unidad=servicio_data['unidad'],
            cantidad=Decimal(str(servicio_data['cantidad'])),
            precio_unitario=Decimal(str(servicio_data['precio_unitario'])),
            descuento_porcentaje=Decimal(str(servicio_data.get('descuento_porcentaje', 0))),
        )
    
    db.commit()
    db.refresh(nueva_cotizacion)
    
    return {"id": nueva_cotizacion.id, "numero": nueva_cotizacion.numero, "numero_version": nueva_cotizacion.numero_version}

