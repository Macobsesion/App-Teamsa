"""Enumeraciones compartidas de la aplicación."""
from enum import Enum


class TipoPeticion(str, Enum):
    """Tipo de petición de cotización."""
    CORREO = "correo"
    WHATSAPP = "whatsapp"
    TELEFONO = "telefono"
    PRESENCIAL = "presencial"
    OTRO = "otro"


class EstadoCotizacion(str, Enum):
    """Estados del flujo de una cotización."""
    BORRADOR = "borrador"
    EMITIDA = "emitida"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    COBRADO = "cobrado"


class MetodoPago(str, Enum):
    """Métodos de pago disponibles."""
    POR_CONFIRMAR = "Por confirmar"
    TRANSFERENCIA_SPEI = "Transferencia SPEI"
    EFECTIVO = "Efectivo"
    CHEQUE = "Cheque"
    TARJETA = "Tarjeta"


class FormaPagoSAT(str, Enum):
    """Formas de pago según catálogo del SAT."""
    EFECTIVO = "01"
    CHEQUE_NOMINATIVO = "02"
    TRANSFERENCIA_ELECTRONICA = "03"
    TARJETA_CREDITO = "04"
    MONEDERO_ELECTRONICO = "05"
    DINERO_ELECTRONICO = "06"
    VALES_DESPENSA = "08"
    TARJETA_DEBITO = "28"
    TARJETA_SERVICIOS = "29"
    POR_DEFINIR = "99"


class UnidadSAT(str, Enum):
    """Códigos de unidad de medida según catálogo del SAT."""
    PIEZA = "H87"  # Pieza
    SERVICIO = "E48"  # Unidad de servicio
    ACTIVIDAD = "ACT"  # Actividad
    KILOGRAMO = "KGM"  # Kilogramo
    LITRO = "LTR"  # Litro
    METRO = "MTR"  # Metro
    METRO_CUADRADO = "MTK"  # Metro cuadrado
    METRO_CUBICO = "MTQ"  # Metro cúbico
    HORA = "HUR"  # Hora
    DIA = "DAY"  # Día
    SEMANA = "WEE"  # Semana
    MES = "MON"  # Mes
    LOTE = "LOT"  # Lote
    JUEGO = "SET"  # Juego
    PAR = "PR"  # Par


class CategoriaGasto(str, Enum):
    """Categorías de gastos en viáticos."""
    TRANSPORTE = "Transporte"
    ALOJAMIENTO = "Alojamiento"
    ALIMENTOS = "Alimentos"
    OTROS = "Otros"


class EstadoViatico(str, Enum):
    """Estados del ciclo de vida de un viático."""
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    PAGADO = "pagado"


class AreaUsuario(str, Enum):
    """Áreas organizacionales de la empresa."""
    ADMINISTRACION = "Administración"
    DIRECCION = "Dirección"
    ECO = "ECO"
    HI = "HI"
    HIDRO = "HIDRO"
    IND = "IND"
    MED = "MED"
    TI = "TI"
