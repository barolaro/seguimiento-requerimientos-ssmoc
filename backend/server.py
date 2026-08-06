from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from main import app

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"

if not INDEX_FILE.exists():
    raise RuntimeError(f"No se encontró el frontend en {INDEX_FILE}")

# La API ya está registrada en main.py. Los recursos visuales se montan después
# para que /api/* mantenga prioridad y frontend/backend compartan el mismo dominio.
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/", include_in_schema=False)
def frontend_home() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.get("/{path:path}", include_in_schema=False)
def frontend_fallback(path: str) -> FileResponse:
    """Permite recargar rutas visuales sin devolver un error 404."""
    candidate = FRONTEND_DIR / path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(INDEX_FILE)
