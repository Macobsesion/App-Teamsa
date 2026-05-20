from app.base.logs_servicio import ServicioLogs

print("Registrando log de prueba...")
ServicioLogs.registrar(
    usuario="Antigravity",
    accion="TEST",
    modulo="sistema",
    detalles="Log de prueba generado para verificar la persistencia en la base de datos."
)
print("Log registrado exitosamente.")
