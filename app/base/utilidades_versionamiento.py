"""Utilidades para versionamiento de cotizaciones."""


def extraer_numero_base(numero: str) -> str:
    """
    Extrae el número base sin letra de versión.
    
    Examples:
        >>> extraer_numero_base("COT-00001")
        'COT-00001'
        >>> extraer_numero_base("COT-00001-B")
        'COT-00001'
        >>> extraer_numero_base("COT-00001-Z")
        'COT-00001'
        >>> extraer_numero_base("COT-00001-AA")
        'COT-00001'
    
    Args:
        numero: Número de cotización completo
    
    Returns:
        Número base sin letra de versión
    """
    partes = numero.split('-')
    if len(partes) == 2:
        # Ya es base (COT-00001)
        return numero
    elif len(partes) >= 3:
        # Tiene letra de versión (COT-00001-B)
        return f"{partes[0]}-{partes[1]}"
    return numero


def calcular_siguiente_letra(letras_usadas: list[str | None]) -> str:
    """
    Calcula la siguiente letra de versión.
    
    Secuencia: B, C, D, ..., Z, AA, AB, AC, ..., AZ, BA, BB, ...
    
    Args:
        letras_usadas: Lista de letras ya usadas (None = original, "B", "C", "AA", etc.)
    
    Returns:
        La siguiente letra en la secuencia
    
    Examples:
        >>> calcular_siguiente_letra([None])
        'B'
        >>> calcular_siguiente_letra([None, 'B', 'C'])
        'D'
        >>> calcular_siguiente_letra([None, 'B', 'C', ..., 'Z'])
        'AA'
        >>> calcular_siguiente_letra([None, ..., 'Z', 'AA', 'AB'])
        'AC'
    """
    # Filtrar None y ordenar
    letras = [l for l in letras_usadas if l is not None]
    
    # Si no hay letras, empezar con B
    if not letras:
        return "B"
    
    # Encontrar la última letra en orden alfabético
    ultima = max(letras)
    
    # Caso 1: Letra simple (B-Z)
    if len(ultima) == 1:
        if ultima == "Z":
            return "AA"  # Después de Z viene AA
        else:
            return chr(ord(ultima) + 1)  # B→C, C→D, etc.
    
    # Caso 2: Doble letra (AA, AB, ..., ZZ)
    elif len(ultima) == 2:
        primera, segunda = ultima[0], ultima[1]
        
        if segunda == "Z":
            # AZ → BA, BZ → CA, etc.
            if primera == "Z":
                return "AAA"  # Caso extremo: ZZ → AAA
            else:
                return chr(ord(primera) + 1) + "A"
        else:
            # AA → AB, AB → AC, etc.
            return primera + chr(ord(segunda) + 1)
    
    # Caso 3: Triple letra o más (AAA, AAB, etc.)
    else:
        # Por ahora solo soportamos hasta ZZ (676 versiones)
        # Si se necesita más, implementar lógica recursiva
        raise ValueError(f"Versión {ultima} excede el límite soportado (ZZ)")


def obtener_versiones_por_familia(db, id_cotizacion_madre: int):
    """
    Obtiene todas las versiones de una familia de cotizaciones.
    
    Busca la cotización madre y todas sus hijas (versiones).
    
    Args:
        db: Sesión de base de datos
        id_cotizacion_madre: ID de la cotización madre (original)
    
    Returns:
        Lista de tuplas (id, version_letra) ordenadas
    """
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from sqlmodel import select, or_
    
    # Buscar:
    # 1. La cotización madre (id = id_cotizacion_madre)
    # 2. Todas las versiones (cotizacion_original_id = id_cotizacion_madre)
    statement = select(Cotizacion).where(
        or_(
            Cotizacion.id == id_cotizacion_madre,
            Cotizacion.cotizacion_original_id == id_cotizacion_madre
        )
    )
    results = db.execute(statement).scalars().all()
    
    return [(c.id, c.version_letra) for c in results]


def obtener_versiones_existentes(db, numero_base: str):
    """
    DEPRECATED: Usar obtener_versiones_por_familia() en su lugar.
    Mantenida por compatibilidad.
    
    Obtiene todas las versiones de una cotización base por número.
    
    Args:
        db: Sesión de base de datos
        numero_base: Número base (ej: "COT-00001")
    
    Returns:
        Lista de tuplas (id, version_letra) ordenadas
    """
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from sqlmodel import select
    
    # Buscar la cotización original por número base
    statement = select(Cotizacion).where(
        Cotizacion.numero == numero_base,
        Cotizacion.version_letra == None
    )
    original = db.execute(statement).scalars().first()
    
    if not original:
        return []
    
    # Usar la nueva función
    return obtener_versiones_por_familia(db, original.id)
