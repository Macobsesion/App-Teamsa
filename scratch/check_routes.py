from app.main import app

for route in app.routes:
    methods = ", ".join(route.methods) if hasattr(route, 'methods') else "N/A"
    path = route.path if hasattr(route, 'path') else "N/A"
    name = route.name if hasattr(route, 'name') else "N/A"
    print(f"{methods:20} | {path:40} | {name}")
