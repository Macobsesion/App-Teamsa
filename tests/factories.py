"""
Factories para generar datos de prueba de forma declarativa.
"""
import factory
from factory import Faker, SubFactory, LazyAttribute
from decimal import Decimal
from datetime import date

from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.servicios.servicios_modelo import Servicio
from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo

class ClienteFactory(factory.Factory):
    class Meta:
        model = Cliente

    nombre = Faker("company")
    rfc = Faker("bothify", text="????######???")
    razon_social = LazyAttribute(lambda o: o.nombre + " S.A. de C.V.")
    email = Faker("email")
    direccion = Faker("address")
    ciudad = Faker("city")
    cp = "06000" # Ejemplo fijo o Faker("postcode")
    activo = True
    
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"

class ProveedorFactory(factory.Factory):
    class Meta:
        model = Proveedor

    nombre = Faker("company")
    rfc = Faker("bothify", text="????######???")
    activo = True
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"

class ServicioProveedorFactory(factory.Factory):
    class Meta:
        model = ServicioProveedor

    proveedor = SubFactory(ProveedorFactory)
    codigo_sku = Faker("bothify", text="SKU-####")
    descripcion = Faker("sentence", nb_words=3)
    costo_unitario = Decimal("50.00")
    moneda = "MXN"
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"

class ServicioFactory(factory.Factory):
    class Meta:
        model = Servicio

    clave = Faker("bothify", text="SERV-###")
    codigo_sat = "81111500" # Servicios genericos
    descripcion = Faker("sentence")
    area = "General"
    unidad = "Servicio"
    codigo_unidad = "E48"
    precio_base = Decimal("500.00")
    activo = True
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"

class CotizacionFactory(factory.Factory):
    class Meta:
        model = Cotizacion

    cliente = SubFactory(ClienteFactory)
    estado = EstadoCotizacion.BORRADOR.value
    fecha_emision = date.today()
    fecha_vigencia = date.today() # O una fecha futura
    metodo_pago = "Por confirmar"
    forma_pago = "99" # Por definir
    numero = Faker("bothify", text="COT-????-##")
    folio = Faker("uuid4")
    numero_version = LazyAttribute(lambda o: o.numero)
    subtotal = Decimal("0.00")
    total = Decimal("0.00")
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"
    
class ConceptoCotizacionFactory(factory.Factory):
    class Meta:
        model = ConceptoCotizacion

    cotizacion = SubFactory(CotizacionFactory)
    descripcion = Faker("sentence")
    cantidad = Decimal("1.00")
    precio_unitario = Decimal("1000.00")
    descuento_porcentaje = Decimal("0.00")
    unidad = "PZA"
    codigo_sat = "81112100"
    importe = Decimal("1000.00")
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"

class OrdenCompraFactory(factory.Factory):
    class Meta:
        model = OrdenCompra

    proveedor = SubFactory(ProveedorFactory)
    fecha_emision = date.today()
    folio = Faker("bothify", text="OC-????-###")
    estado = "borrador"
    moneda = "MXN"
    subtotal = Decimal("0.00")
    total = Decimal("0.00")
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"

class DetalleOrdenCompraFactory(factory.Factory):
    class Meta:
        model = DetalleOrdenCompra

    orden = SubFactory(OrdenCompraFactory)
    servicio_original = SubFactory(ServicioProveedorFactory)
    codigo_sku = Faker("bothify", text="SKU-####")
    descripcion = Faker("sentence", nb_words=3)
    unidad = "Pieza"
    cantidad = Decimal("10.00")
    precio_unitario = Decimal("50.00")
    importe = Decimal("500.00")
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"

class OrdenTrabajoFactory(factory.Factory):
    class Meta:
        model = OrdenTrabajo

    numero_ot = Faker("bothify", text="OT-####-##")
    cotizacion_id = None          # se asigna en el test
    cliente_nombre = Faker("company")
    domicilio = Faker("address")
    contacto = Faker("name")
    fecha_programada = date.today()
    hora_programada = "09:00"
    duracion = 2
    estado = "programada"
    notas_publicas = None
    notas_privadas = None
    tecnico_id = None
    tecnico_nombre = None
    # Auditoría
    creado_por = "TEST_FACTORY"
    modificado_por = "TEST_FACTORY"


# ── Helpers de persistencia para tests de integración ────────────────────────

def crear_cotizacion_con_conceptos(
    db,
    n_conceptos: int = 2,
    *,
    usuario: str = "TEST",
) -> tuple:
    """
    Crea y persiste en BD una cotización con ``n_conceptos`` conceptos.

    Retorna: ``(cotizacion, [concepto1, concepto2, ...])``

    Ejemplo de uso::

        cot, conceptos = crear_cotizacion_con_conceptos(db, 3)
        ids = [c.id for c in conceptos]
    """
    from decimal import Decimal
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion

    # Persistir cliente
    cliente = ClienteFactory.build()
    db.add(cliente)
    db.flush()

    # Persistir cotización con número provisional vacío
    cotizacion = Cotizacion(
        cliente_id=cliente.id,
        numero="",
        numero_version="",
        fecha_emision=date.today(),
        fecha_vigencia=date.today(),
        metodo_pago="Por confirmar",
        forma_pago="99",
        subtotal=Decimal("0.00"),
        total=Decimal("0.00"),
        creado_por=usuario,
        modificado_por=usuario,
    )
    db.add(cotizacion)
    db.flush()

    # Asignar número definitivo basado en ID
    cotizacion.numero = f"COT-{date.today().strftime('%y%m%d')}-{cotizacion.id}"
    cotizacion.numero_version = cotizacion.numero
    db.add(cotizacion)
    db.flush()

    # Persistir conceptos
    conceptos = []
    for i in range(n_conceptos):
        precio = Decimal("500.00") * (i + 1)
        concepto = ConceptoCotizacion(
            cotizacion_id=cotizacion.id,
            descripcion=f"Servicio de prueba {i + 1}",
            cantidad=Decimal("1.00"),
            precio_unitario=precio,
            importe=precio,
            descuento_porcentaje=Decimal("0.00"),
            unidad="Servicio",
            codigo_sat="81111500",
            creado_por=usuario,
            modificado_por=usuario,
        )
        db.add(concepto)
        db.flush()
        conceptos.append(concepto)

    db.commit()
    db.refresh(cotizacion)
    for c in conceptos:
        db.refresh(c)

    return cotizacion, conceptos


def crear_ot_desde_cotizacion(
    db,
    cotizacion,
    concepto_ids: list[int],
    *,
    usuario: str = "TEST",
    tecnico_id: int | None = None,
):
    """
    Crea y persiste una OT usando el ``RepositorioOrden``.

    Retorna: ``OrdenTrabajo``

    Ejemplo de uso::

        cot, conceptos = crear_cotizacion_con_conceptos(db)
        ot = crear_ot_desde_cotizacion(db, cot, [conceptos[0].id])
    """
    from datetime import date
    from app.modulos.ordenes_trabajo.ordenes_trabajo_servicios import ServicioOrdenes
    from app.modulos.ordenes_trabajo.ordenes_trabajo_repositorio import RepositorioOrden

    repo = RepositorioOrden(db)
    return repo.crear_desde_cotizacion(
        cotizacion_id=cotizacion.id,
        fecha_programada=date.today(),
        hora_programada="09:00",
        duracion=1,
        usuario=usuario,
        concepto_ids=concepto_ids,
        tecnico_id=tecnico_id,
    )

