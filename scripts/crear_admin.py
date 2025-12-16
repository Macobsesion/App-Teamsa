# Script auxiliar para crear un usuario administrador en desarrollo.
import sys
sys.path.insert(0, '/teamsa-app')

from app.modulos.usuarios.usuarios_repositorio import RepositorioUsuario
from app.nucleo.base_datos import sesion_bd
from app.nucleo.cls_autenticacion import obtener_gestor_autenticacion

ADMIN_USERNAME = "mjimenez"
# Las credenciales se usan solo en desarrollo; no exponer en producción.
ADMIN_PASSWORD = "Numanot0"
ADMIN_NOMBRES = "Marco Jimenez"


def crear_usuario_admin() -> None:
    # Crea el usuario admin si aún no existe.
    print("Iniciando script para crear usuario administrador...")

    gestor_auth = obtener_gestor_autenticacion()

    with sesion_bd() as db:
        repo = RepositorioUsuario(db)
        if repo.obtener_por_username(username=ADMIN_USERNAME):
            print(f"El usuario administrador '{ADMIN_USERNAME}' ya existe.")
            return

        contrasena_hasheada = gestor_auth.obtener_hash_contrasena(ADMIN_PASSWORD)
        repo.crear(
            usuario=ADMIN_USERNAME,
            nombres=ADMIN_NOMBRES,
            rol="admin",
            contrasena=contrasena_hasheada,
            correo="",
            area="TI",
            creado_por="sistema",
            modificado_por="sistema",
        )
        print(f"¡Usuario administrador '{ADMIN_USERNAME}' creado!")

    print("Script finalizado.")


if __name__ == "__main__":
    crear_usuario_admin()
