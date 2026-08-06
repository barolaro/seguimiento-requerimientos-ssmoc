from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

import gspread
from google.oauth2.service_account import Credentials


class SheetsStore:
    USERS = "usuarios"
    REQUIREMENTS = "requerimientos"
    HISTORY = "historial"
    AUDIT = "auditoria"

    USER_COLS = ["usuario", "nombre", "email", "rol", "password_hash", "activo"]
    REQ_COLS = ["id", "titulo", "descripcion", "responsable", "estado", "prioridad", "avance", "creado", "compromiso", "creado_por", "actualizado"]
    HISTORY_COLS = ["evento_id", "requerimiento_id", "fecha", "tipo", "autor", "detalle", "estado_anterior", "estado_nuevo"]
    AUDIT_COLS = ["evento_id", "fecha", "usuario", "accion", "entidad_id", "detalle"]

    def __init__(self, credentials: dict[str, Any], spreadsheet_id: str) -> None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(credentials, scopes=scopes)
        self.client = gspread.authorize(creds)
        self.book = self.client.open_by_key(spreadsheet_id)
        self._lock = threading.Lock()
        self._ensure_sheets()

    @classmethod
    def from_environment(cls) -> "SheetsStore":
        raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        spreadsheet_id = os.environ.get("SPREADSHEET_ID", "")
        if not raw or not spreadsheet_id:
            raise RuntimeError("Faltan GOOGLE_SERVICE_ACCOUNT_JSON o SPREADSHEET_ID")
        return cls(json.loads(raw), spreadsheet_id)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()

    def _ensure_sheet(self, name: str, headers: list[str], rows: int = 1000) -> None:
        try:
            ws = self.book.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = self.book.add_worksheet(name, rows=rows, cols=len(headers))
        first = ws.row_values(1)
        if first != headers:
            ws.update([headers], "A1")

    def _ensure_sheets(self) -> None:
        self._ensure_sheet(self.USERS, self.USER_COLS, 200)
        self._ensure_sheet(self.REQUIREMENTS, self.REQ_COLS, 3000)
        self._ensure_sheet(self.HISTORY, self.HISTORY_COLS, 10000)
        self._ensure_sheet(self.AUDIT, self.AUDIT_COLS, 10000)

    def list_users(self) -> list[dict[str, Any]]:
        rows = self.book.worksheet(self.USERS).get_all_records()
        for row in rows:
            row["activo"] = str(row.get("activo", "")).strip().upper() in {"SI", "TRUE", "1", "VERDADERO"}
        return rows

    def get_user(self, username: str) -> dict[str, Any] | None:
        username = username.strip().lower()
        return next((u for u in self.list_users() if str(u.get("usuario", "")).lower() == username), None)

    def append_user(self, item: dict[str, Any]) -> None:
        self.book.worksheet(self.USERS).append_row([
            item.get("usuario", ""), item.get("nombre", ""), item.get("email", ""),
            item.get("rol", ""), item.get("password_hash", ""), "SI" if item.get("activo", True) else "NO",
        ], value_input_option="USER_ENTERED")

    def list_requirements(self) -> list[dict[str, Any]]:
        rows = self.book.worksheet(self.REQUIREMENTS).get_all_records()
        for row in rows:
            row["id"] = int(row.get("id") or 0)
            row["avance"] = int(row.get("avance") or 0)
        rows.sort(key=lambda x: x.get("id", 0), reverse=True)
        return rows

    def get_requirement(self, requirement_id: int) -> dict[str, Any] | None:
        return next((r for r in self.list_requirements() if r.get("id") == requirement_id), None)

    def next_requirement_id(self) -> int:
        with self._lock:
            return max((r.get("id", 0) for r in self.list_requirements()), default=0) + 1

    def append_requirement(self, item: dict[str, Any]) -> None:
        self.book.worksheet(self.REQUIREMENTS).append_row(
            [item.get(k, "") for k in self.REQ_COLS], value_input_option="USER_ENTERED"
        )

    def update_requirement(self, item: dict[str, Any]) -> None:
        ws = self.book.worksheet(self.REQUIREMENTS)
        cell = ws.find(str(item["id"]), in_column=1)
        if not cell:
            raise KeyError(f"No existe REQ-{item['id']:03d}")
        ws.update([item.get(k, "") for k in self.REQ_COLS], f"A{cell.row}:K{cell.row}", value_input_option="USER_ENTERED")

    def append_history(self, requirement_id: int, event_type: str, author: str, detail: str, previous_state: str = "", new_state: str = "") -> None:
        event_id = f"H-{int(datetime.now().timestamp() * 1000)}"
        self.book.worksheet(self.HISTORY).append_row(
            [event_id, requirement_id, self._now(), event_type, author, detail, previous_state, new_state],
            value_input_option="USER_ENTERED",
        )

    def append_audit(self, user: str, action: str, entity_id: str, detail: str) -> None:
        event_id = f"A-{int(datetime.now().timestamp() * 1000)}"
        self.book.worksheet(self.AUDIT).append_row(
            [event_id, self._now(), user, action, entity_id, detail], value_input_option="USER_ENTERED"
        )
