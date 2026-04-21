"""
# Configuración de la aplicación usando pydantic-settings.
#
# - Lee variables de entorno (o .env en desarrollo) para DB y JWT.
# - Construye el DSN de PostgreSQL leyendo la contraseña desde un secret file
#   (campo POSTGRES_PASSWORD_FILE) para no exponer secretos en variables.
# - Define opciones de CORS y cookies para la sesión.
"""
from pydantic_settings import BaseSettings # type: ignore
from pydantic import PostgresDsn, computed_field # type: ignore
from pydantic_core import MultiHostUrl # type: ignore

class Settings(BaseSettings):
    PROJECT_NAME: str = "App-Teamsa"
    DEBUG: bool = True
    
    # Configuración de la Base de Datos
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    POSTGRES_PASSWORD_FILE: str | None = None
    POSTGRES_PORT: int = 5432

    # Configuración de Autenticación/JWT
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ACCESS_COOKIE_NAME: str = "sesion_teamsa"

    # CORS (lista separada por comas o "*")
    CORS_ALLOW_ORIGINS: str = "*"
    
    # Entorno de ejecución (development o production)
    # Controla configuraciones de seguridad como cookies seguras
    ENVIRONMENT: str = "development"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        # # Lee el password desde archivo si se indicó (útil con Docker secrets)
        password = None
        if self.POSTGRES_PASSWORD_FILE:
            with open(self.POSTGRES_PASSWORD_FILE) as f:
                password = f.read().strip()

        return PostgresDsn(
            MultiHostUrl.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=password,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

settings = Settings()
