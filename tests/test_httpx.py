import httpx
from app.main import app

def simular_error():
    transport = httpx.ASGITransport(app=app)
    with httpx.Client(transport=transport, base_url="http://testserver") as client:
        # Intento de login en la bd viva
        login_res = client.post("/auth/validaUsuario", data={
            "txtNombre": "admin",
            "txtPassword": "password"  # Asumiendo que hay un admin
        })
        print(f"LOGIN: {login_res.status_code}")
        
        # Como no sabemos las creds del admin en BD, tal vez esto de 401.
        if login_res.status_code == 200:
            resp = client.post("/ui/usuarios/crear", data={
                "usuario": "bug_test",
                "nombres": "Bug Test",
                "contrasena": "123456",
                "confirmarContrasena": "123456",
                "rol": "operador"
            })
            print(f"POST CREAR STATUS: {resp.status_code}")
            
if __name__ == "__main__":
    simular_error()
