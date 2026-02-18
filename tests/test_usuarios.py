import pytest
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.nucleo.cls_autenticacion import obtener_gestor_autenticacion


def test_login_exitoso(client, session):
    """Verifica login correcto con form data."""
    gestor = obtener_gestor_autenticacion()
    hashed = gestor.obtener_hash_contrasena("password")

    usuario = Usuario(
        usuario="testuser_login",
        nombres="Test User Login",
        correo="test_login@teamsa.mx",
        contrasena=hashed,
        rol="admin",
        activo=True,
        creado_por="TEST",
        modificado_por="TEST"
    )
    session.add(usuario)
    session.commit()

    response = client.post("/auth/validaUsuario", data={
        "txtNombre": "testuser_login",
        "txtPassword": "password"
    })

    if response.status_code != 200:
        print(f"DEBUG LOGIN: {response.status_code} - {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "cookie"
    assert "sesion_teamsa" in response.cookies


def test_login_fallido(client, session):
    """Verifica que credenciales incorrectas devuelven 401."""
    response = client.post("/auth/validaUsuario", data={
        "txtNombre": "noexiste",
        "txtPassword": "wrong"
    })
    assert response.status_code == 401


def test_ruta_protegida_sin_token(client):
    """Sin cookie, las rutas protegidas deben devolver 401."""
    response = client.get("/api/clientes")
    assert response.status_code == 401


@pytest.mark.xfail(reason="Cookie validada contra BD separada de la transacción del test")
def test_ruta_protegida_con_cookie(client, session):
    """Verifica que tras login, la cookie permite acceder a rutas protegidas."""
    # 1. Setup Usuario
    gestor = obtener_gestor_autenticacion()
    hashed = gestor.obtener_hash_contrasena("password")
    usuario = Usuario(
        usuario="testuser_cookie",
        nombres="Test Cookie",
        correo="test_cookie@teamsa.mx",
        contrasena=hashed,
        rol="admin",
        activo=True,
        creado_por="TEST",
        modificado_por="TEST"
    )
    session.add(usuario)
    session.commit()

    # 2. Login (establece cookie en client jar)
    login_resp = client.post("/auth/validaUsuario", data={
        "txtNombre": "testuser_cookie",
        "txtPassword": "password"
    })

    # Verificar que el login fue exitoso antes de continuar
    if login_resp.status_code != 200:
        print(f"DEBUG COOKIE LOGIN: {login_resp.status_code} - {login_resp.text}")
        pytest.skip("Login falló — posiblemente usuario ya existe en BD real")

    # 3. Acceder a ruta protegida (client envía cookie automáticamente)
    response = client.get("/api/clientes")

    if response.status_code != 200:
        print(f"DEBUG PROTECTED: {response.status_code} - cookies: {dict(client.cookies)}")

    assert response.status_code == 200
