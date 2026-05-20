from typing import Any

class MixinEstadoDocumento:
    """Mixin para manejo polimórfico de estados terminales (Finalizar/Cancelar)."""
    
    def _cambiar_estado(self, nuevo_estado: str, usuario: str = "sistema") -> None:
        """Lógica base para transiciones de estado con auditoría."""
        from datetime import datetime
        self.estado = nuevo_estado
        self.modificado_por = usuario
        self.fecha_modificacion = datetime.now()

    def finalizar(self, usuario: str = "sistema", **kwargs) -> None:
        """Cambia el estado a terminal exitoso (finalizado/pagado/etc)."""
        # Obtenemos la clase del Enum (ej: EstadoCotizacion)
        clase_enum = self.estado_enum.__class__
        
        # Valores candidatos para estado final exitoso (Prioridad descendente)
        candidatos = ("finalizada", "finalizado", "pagado", "recibida", "aceptada", "aprobado")
        
        for candidato in candidatos:
            for miembro in clase_enum:
                if miembro.value == candidato:
                    self._cambiar_estado(miembro.value, usuario)
                    return
        raise NotImplementedError(f"El Enum {clase_enum.__name__} no define un estado terminal de finalización conocido")

    def cancelar(self, usuario: str = "sistema", **kwargs) -> None:
        """Cambia el estado a terminal fallido (cancelado/rechazado)."""
        clase_enum = self.estado_enum.__class__
        
        # Valores candidatos para estado final fallido
        candidatos = ("cancelada", "cancelado", "rechazada", "rechazado")
        
        for miembro in clase_enum:
            if miembro.value in candidatos:
                self._cambiar_estado(miembro.value, usuario)
                return
        raise NotImplementedError(f"El Enum {clase_enum.__name__} no define un estado terminal de cancelación conocido")
