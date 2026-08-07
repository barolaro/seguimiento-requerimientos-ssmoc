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
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"] {display:none!important;}
    #MainMenu, footer {visibility:hidden!important;}
    html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{margin:0!important;padding:0!important;overflow:hidden!important;}
    .block-container{padding:0!important;margin:0!important;max-width:100%!important;}
    iframe{display:block;width:100%!important;border:0!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

base_dir = Path(__file__).resolve().parent
frontend_dir = base_dir / "frontend"
html_path = frontend_dir / "index.html"
css_path = frontend_dir / "css" / "style.css"
js_path = frontend_dir / "js" / "app.js"

missing = [str(p.relative_to(base_dir)) for p in (html_path, css_path, js_path) if not p.exists()]
if missing:
    st.error("La interfaz está incompleta. Faltan: " + ", ".join(missing))
    st.stop()

html = html_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")
javascript = js_path.read_text(encoding="utf-8")

# Backend SGTCP 3.0: Google Apps Script publicado como Web App (/exec).
# Si existe apps_script_url en Streamlit Secrets, tiene prioridad.
DEFAULT_APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbzmYGqzfBTgjcyXtoB7rA6j1uvZ7XGSm_WHAuXWZSD8RLIOiQJd0krdQ_xfOSfJClsKiw/exec"
)
apps_script_url = str(st.secrets.get("apps_script_url", DEFAULT_APPS_SCRIPT_URL)).strip()

config_script = "<script>window.SGTCP_CONFIG=" + json.dumps(
    {"appsScriptUrl": apps_script_url, "version": "3.0.0"}, ensure_ascii=False
) + ";</script>"

html = html.replace('<link rel="stylesheet" href="css/style.css">', f"<style>{css}</style>")
html = html.replace('<script src="js/config.js"></script>', config_script)
html = html.replace('<script src="js/app.js"></script>', f"<script>{javascript}</script>")

components.html(html, height=1050, scrolling=True)
