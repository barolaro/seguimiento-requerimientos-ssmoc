from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from sheets_store import SheetsStore

APP_NAME = "SGTCP API"
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
TOKEN_HOURS = 10
BOOTSTRAP_ADMIN_USER = os.environ.get("BOOTSTRAP_ADMIN_USER", "bayron.admin").strip().lower()
BOOTSTRAP_ADMIN_NAME = os.environ.get("BOOTSTRAP_ADMIN_NAME", "Bayron Retamal González").strip()
BOOTSTRAP_ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")

if not JWT_SECRET:
    raise RuntimeError("Falta la variable de entorno JWT_SECRET")

app = FastAPI(title=APP_NAME, version="3.0.0")
origins = [x.strip() for x in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

store = SheetsStore.from_environment()
security = HTTPBearer(auto_error=False)


class LoginPayload(BaseModel):
    usuario: str
    password: str


class PasswordChange(BaseModel):
    actual: str = Field(min_length=8, max_length=100)
    nueva: str = Field(min_length=10, max_length=100)


class RequirementCreate(BaseModel):
    titulo: str = Field(min_length=3, max_length=250)
    descripcion: str = Field(default="", max_length=4000)
    responsable: str
    estado: str = "Pendiente"
    prioridad: str = "Media"
    avance: int = Field(default=0, ge=0, le=100)
    compromiso: str = ""


class RequirementUpdate(BaseModel):
    estado: str | None = None
    prioridad: str | None = None
    avance: int | None = Field(default=None, ge=0, le=100)
    responsable: str | None = None
    comentario: str = ""


class UserCreate(BaseModel):
    usuario: str = Field(min_length=3, max_length=60)
    nombre: str = Field(min_length=3, max_length=180)
    email: str = ""
    rol: str = "Ejecutivo"
    password: str = Field(min_length=10, max_length=100)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def bootstrap_admin() -> None:
    if store.list_users():
        return
    if not BOOTSTRAP_ADMIN_PASSWORD:
        raise RuntimeError("No existen usuarios y falta BOOTSTRAP_ADMIN_PASSWORD")
    store.append_user({
        "usuario": BOOTSTRAP_ADMIN_USER,
        "nombre": BOOTSTRAP_ADMIN_NAME,
        "email": BOOTSTRAP_ADMIN_EMAIL,
        "rol": "Administrador",
        "password_hash": bcrypt.hashpw(BOOTSTRAP_ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode(),
        "activo": True,
        "cambiar_password": True,
        "ultimo_acceso": "",
        "creado": now_iso(),
    })
    store.append_audit("sistema", "bootstrap_administrador", BOOTSTRAP_ADMIN_USER, "Administrador inicial creado")


def make_token(user: dict[str, Any]) -> str:
    payload = {
        "sub": user["usuario"],
        "nombre": user["nombre"],
        "rol": user["rol"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión requerida")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada") from exc
    user = store.get_user(payload.get("sub", ""))
    if not user or not user.get("activo", False):
        raise HTTPException(status_code=401, detail="Usuario inactivo o inexistente")
    return user


def require_management(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user.get("rol") not in {"Administrador", "Jefa de Unidad", "Jefe de Departamento"}:
        raise HTTPException(status_code=403, detail="Permiso insuficiente")
    return user


@app.on_event("startup")
def startup() -> None:
    bootstrap_admin()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": APP_NAME, "version": "3.0.0", "time": now_iso()}


@app.post("/api/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    user = store.get_user(payload.usuario.strip().lower())
    if not user or not user.get("activo", False):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    try:
        valid = bcrypt.checkpw(payload.password.encode(), user.get("password_hash", "").encode())
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    store.update_user(user["usuario"], {"ultimo_acceso": now_iso()})
    store.append_audit(user["usuario"], "inicio_sesion", "", "Ingreso al sistema")
    return {
        "token": make_token(user),
        "requiere_cambio_password": bool(user.get("cambiar_password", False)),
        "usuario": {k: user.get(k, "") for k in ("usuario", "nombre", "email", "rol")},
    }


@app.post("/api/change-password")
def change_password(payload: PasswordChange, user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    try:
        valid = bcrypt.checkpw(payload.actual.encode(), user.get("password_hash", "").encode())
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    if payload.actual == payload.nueva:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta")
    store.update_user(user["usuario"], {
        "password_hash": bcrypt.hashpw(payload.nueva.encode(), bcrypt.gensalt()).decode(),
        "cambiar_password": False,
    })
    store.append_audit(user["usuario"], "cambio_password", user["usuario"], "Contraseña actualizada")
    return {"status": "ok"}


@app.get("/api/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {k: user.get(k, "") for k in ("usuario", "nombre", "email", "rol", "cambiar_password")}


@app.get("/api/requirements")
def list_requirements(user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    items = store.list_requirements()
    if user.get("rol") == "Ejecutivo":
        items = [item for item in items if item.get("responsable") == user["usuario"]]
    return items


@app.post("/api/requirements", status_code=201)
def create_requirement(payload: RequirementCreate, user: dict[str, Any] = Depends(require_management)) -> dict[str, Any]:
    item = payload.model_dump()
    item.update({"id": store.next_requirement_id(), "creado": now_iso(), "creado_por": user["usuario"], "actualizado": now_iso()})
    store.append_requirement(item)
    store.append_history(item["id"], "creacion", user["usuario"], "Requerimiento creado", "", item["estado"])
    store.append_audit(user["usuario"], "crear_requerimiento", str(item["id"]), item["titulo"])
    return item


@app.patch("/api/requirements/{requirement_id}")
def update_requirement(requirement_id: int, payload: RequirementUpdate, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    item = store.get_requirement(requirement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Requerimiento no encontrado")
    if user.get("rol") == "Ejecutivo" and item.get("responsable") != user["usuario"]:
        raise HTTPException(status_code=403, detail="No puede modificar este requerimiento")
    changes = payload.model_dump(exclude_none=True)
    comment = changes.pop("comentario", "").strip()
    before_state = item.get("estado", "")
    item.update(changes)
    item["actualizado"] = now_iso()
    store.update_requirement(item)
    description = comment or "Actualización de requerimiento"
    store.append_history(requirement_id, "actualizacion", user["usuario"], description, before_state, item.get("estado", ""))
    store.append_audit(user["usuario"], "actualizar_requerimiento", str(requirement_id), description)
    return item


@app.get("/api/users")
def list_users(user: dict[str, Any] = Depends(require_management)) -> list[dict[str, Any]]:
    return [{k: item.get(k, "") for k in ("usuario", "nombre", "email", "rol", "activo")} for item in store.list_users()]


@app.post("/api/users", status_code=201)
def create_user(payload: UserCreate, user: dict[str, Any] = Depends(require_management)) -> dict[str, Any]:
    username = payload.usuario.strip().lower()
    if store.get_user(username):
        raise HTTPException(status_code=409, detail="El usuario ya existe")
    item = payload.model_dump(exclude={"password"})
    item.update({
        "usuario": username,
        "password_hash": bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode(),
        "activo": True,
        "cambiar_password": True,
        "ultimo_acceso": "",
        "creado": now_iso(),
    })
    store.append_user(item)
    store.append_audit(user["usuario"], "crear_usuario", username, item["rol"])
    return {k: item.get(k, "") for k in ("usuario", "nombre", "email", "rol", "activo")}
