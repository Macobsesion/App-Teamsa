from app.web.jinja import register_jinja_filters
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Mock de templates
root = Path(__file__).resolve().parents[1]
templates_dir = root / "web" / "templates"
tpl = Jinja2Templates(directory=str(templates_dir))
register_jinja_filters(tpl)

getv = tpl.env.globals["getv"]

class Obj:
    def __init__(self):
        self.a = 1
        self.b = None

o = Obj()
d = {"a": 2, "b": None}

print(f"Obj attr exist: {getv(o, 'a')} (expect 1)")
print(f"Obj attr None: '{getv(o, 'b')}' (expect '')")
print(f"Obj attr non-exist: '{getv(o, 'c')}' (expect '')")
print(f"Dict key exist: {getv(d, 'a')} (expect 2)")
print(f"Dict key None: '{getv(d, 'b')}' (expect '')")
print(f"Dict key non-exist: '{getv(d, 'c')}' (expect '')")
print(f"None obj: '{getv(None, 'a')}' (expect '')")
