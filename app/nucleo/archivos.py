from __future__ import annotations

from pathlib import Path
from typing import IO
from uuid import uuid4

from fastapi import UploadFile  # type: ignore

from .configuracion import settings


def get_upload_root() -> Path:
    """Directorio base para subir archivos. Usa settings o `uploads/`.

    Crea el directorio si no existe.
    """
    root = Path(getattr(settings, "UPLOAD_DIR", "uploads")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_stream_to_path(src: IO[bytes], dst: Path, *, max_bytes: int) -> int:
    total = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as f:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("Archivo excede el tamaño máximo permitido")
            f.write(chunk)
    return total


def _validate_pdf_file(file: UploadFile) -> None:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    if not filename.endswith(".pdf"):
        raise ValueError("El archivo debe tener extensión .pdf")
    if content_type not in {"application/pdf", "application/octet-stream"}:
        # `octet-stream` se acepta por compatibilidad de algunos navegadores
        raise ValueError("Tipo de contenido no permitido; sólo PDF")



def save_pdf_temp(file: UploadFile, *, max_mb: int = 10) -> str:
    """Guarda un PDF a `uploads/tmp/<uuid>.pdf` y devuelve la ruta relativa."""
    _validate_pdf_file(file)
    upload_root = get_upload_root()
    rel = Path("tmp") / f"{uuid4().hex}.pdf"
    dst = upload_root / rel
    _ = _write_stream_to_path(file.file, dst, max_bytes=max_mb * 1024 * 1024)
    return str(Path("uploads") / rel)



def move_pdf_to_entity(temp_rel_path: str, *, entity_plural: str, entity_id: int) -> str:
    """Mueve un PDF desde `uploads/tmp/...` a `uploads/<plural>/<id>/identificacion.pdf`.

    Devuelve la ruta relativa final.
    """
    upload_root = get_upload_root()
    temp_abs = (Path.cwd() / temp_rel_path).resolve() if not temp_rel_path.startswith("/") else Path(temp_rel_path)
    if not temp_abs.exists():
        # Si ya no existe, retornamos una ruta calculada pero sin mover
        pass
    final_rel = Path("uploads") / entity_plural / str(entity_id) / "identificacion.pdf"
    final_abs = upload_root / entity_plural / str(entity_id) / "identificacion.pdf"
    final_abs.parent.mkdir(parents=True, exist_ok=True)
    if temp_abs.exists():
        temp_abs.replace(final_abs)
    return str(final_rel)


    


def delete_upload_rel_path(rel_path: str) -> bool:
    """Elimina físicamente un archivo bajo /uploads. Devuelve True si se borró."""
    try:
        root = get_upload_root()
        p = rel_path
        if rel_path.startswith("uploads/"):
            p = rel_path[len("uploads/"):]
        abs_path = root / p
        if abs_path.exists() and abs_path.is_file():
            abs_path.unlink()
            return True
    except Exception:
        return False
    return False


def save_pdf_for_entity(file: UploadFile, *, entity_plural: str, entity_id: int, max_mb: int = 10) -> str:
    """Guarda un PDF directamente en `uploads/<plural>/<id>/identificacion.pdf`."""
    _validate_pdf_file(file)
    upload_root = get_upload_root()
    final_rel = Path("uploads") / entity_plural / str(entity_id) / "identificacion.pdf"
    final_abs = upload_root / entity_plural / str(entity_id) / "identificacion.pdf"
    _ = _write_stream_to_path(file.file, final_abs, max_bytes=max_mb * 1024 * 1024)
    return str(final_rel)
