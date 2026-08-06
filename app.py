from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Sistema de Gestión y Trazabilidad para Compras Públicas · SSMOCC",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stHeader"],
    [data-testid="stSidebar"],
    [data-testid="stToolbar"] {
        display: none !important;
    }
    #MainMenu, footer { visibility: hidden !important; }
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }
    .stApp { background: #f3f6fa; }
    iframe {
        display: block;
        width: 100% !important;
        border: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

base_dir = Path(__file__).resolve().parent
frontend_dir = base_dir / "frontend"
html_path = frontend_dir / "index.html"
css_path = frontend_dir / "css" / "style.css"
js_path = frontend_dir / "js" / "app.js"

missing = [str(path.relative_to(base_dir)) for path in (html_path, css_path, js_path) if not path.exists()]
if missing:
    st.error("La interfaz V2 está incompleta. Faltan: " + ", ".join(missing))
    st.stop()

html = html_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")
javascript = js_path.read_text(encoding="utf-8")

# URL pública del backend FastAPI desplegado en Cloud Run, Render u otro servicio.
# En Streamlit Cloud debe configurarse en Secrets como:
# api_base_url = "https://URL-DEL-BACKEND"
api_base_url = str(st.secrets.get("api_base_url", "")).strip()
config_script = (
    "<script>window.SGTCP_CONFIG = "
    + json.dumps({"apiBaseUrl": api_base_url}, ensure_ascii=False)
    + ";</script>"
)

# Streamlit components.html no sirve archivos relativos. Por eso se insertan
# CSS, configuración y JavaScript directamente dentro del documento V2.
html = html.replace(
    '<link rel="stylesheet" href="css/style.css">',
    f"<style>{css}</style>",
)
html = html.replace(
    '<script src="js/config.js"></script>',
    config_script,
)
html = html.replace(
    '<script src="js/app.js"></script>',
    f"<script>{javascript}</script>",
)

components.html(
    html,
    height=1000,
    scrolling=True,
)
