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
    html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{margin:0!important;padding:0!important;overflow-x:hidden!important;}
    [data-testid="stAppViewContainer"]{overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;}
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
mobile_css_path = frontend_dir / "css" / "mobile.css"
js_path = frontend_dir / "js" / "app.js"
stabilization_path = frontend_dir / "js" / "stabilization.js"

required = (html_path, css_path, mobile_css_path, js_path, stabilization_path)
missing = [str(p.relative_to(base_dir)) for p in required if not p.exists()]
if missing:
    st.error("La interfaz está incompleta. Faltan: " + ", ".join(missing))
    st.stop()

html = html_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")
mobile_css = mobile_css_path.read_text(encoding="utf-8")
javascript = js_path.read_text(encoding="utf-8")
stabilization_js = stabilization_path.read_text(encoding="utf-8")

universal_css = r"""
html,body{width:100%;max-width:100%;overflow-x:hidden!important}body{min-height:100%;}
@media (min-width:821px){
  .login-shell{min-height:880px;height:880px;padding:24px;display:flex;align-items:center;justify-content:center;}
  .login-card{width:min(460px,calc(100vw - 56px));max-width:460px;padding:34px;border-radius:24px;}
  .login-card .logo{width:145px;height:145px;margin-bottom:15px}.login-card h1{font-size:26px;line-height:1.12}.login-card>.muted{font-size:12px}.login-card form{gap:13px;margin:22px 0 14px}.login-card input{min-height:44px}.login-card .btn{min-height:44px}
  .topbar{grid-template-columns:minmax(210px,260px) minmax(0,1fr) auto;gap:10px;padding:0 20px}.brand{min-width:0}.brand img{width:42px;height:42px}.brand strong{font-size:17px}.brand span{font-size:8px}
  .topbar nav{min-width:0;overflow:visible!important;flex-wrap:wrap;justify-content:center;align-content:center;gap:2px 3px;scrollbar-width:none}.topbar nav::-webkit-scrollbar{display:none!important}.topbar nav button{padding:8px 9px;font-size:9px;line-height:1.1}
  .account{min-width:max-content}.account b{font-size:10px}.account span{font-size:8px}.account .btn{padding:10px 13px}main{width:min(1480px,calc(100% - 40px));padding:28px 0 56px}.topbar,.topbar nav,.brand,.account{max-width:100%}
}
@media (min-width:821px) and (max-width:1500px){.topbar{grid-template-columns:1fr auto;grid-template-rows:auto auto;padding:8px 18px 6px}.topbar nav{grid-column:1/-1;order:3;justify-content:flex-start;padding:2px 0 0}.topbar nav button{padding:7px 9px;font-size:9px}}
@media (min-width:1900px){main{width:min(1720px,calc(100% - 72px))}.page-head h2{font-size:34px}.kpi strong{font-size:31px}.panel-head h3{font-size:15px}}
.event-pending{opacity:.78;border-style:dashed!important}.event-pending b{color:#087dcc}
"""

DEFAULT_APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbzmYGqzfBTgjcyXtoB7rA6j1uvZ7XGSm_WHAuXWZSD8RLIOiQJd0krdQ_xfOSfJClsKiw/exec"
)
apps_script_url = str(st.secrets.get("apps_script_url", DEFAULT_APPS_SCRIPT_URL)).strip()
config_script = "<script>window.SGTCP_CONFIG=" + json.dumps(
    {"appsScriptUrl": apps_script_url, "version": "3.2.0"}, ensure_ascii=False
) + ";</script>"

# Streamlit no sirve los archivos relativos del iframe. Se incrustan una sola vez,
# respetando el orden: configuración -> app base -> estabilización.
html = html.replace('<link rel="stylesheet" href="css/style.css">', f"<style>{css}\n{mobile_css}\n{universal_css}</style>")
html = html.replace('<script src="js/config.js"></script>', config_script)
html = html.replace('<script src="js/app.js"></script>', f"<script>{javascript}</script>")
html = html.replace('<script src="js/performance.js?v=3.0.2"></script>', '')
html = html.replace('<script src="js/performance.js"></script>', '')
html = html.replace('<script src="js/stabilization.js?v=3.2.0"></script>', f"<script>{stabilization_js}</script>")
html = html.replace('<script src="js/stabilization.js"></script>', f"<script>{stabilization_js}</script>")

html = html.replace(
    'Diseñado y desarrollado por <strong>Bayron Retamal González</strong></small>',
    'SGTCP 3.2.0 · Estabilización<br>Diseñado y desarrollado por <strong>Bayron Retamal González</strong></small>'
)
html = html.replace(
    'Servicio de Salud Metropolitano Occidente · SGTCP 3.0 · Diseñado y desarrollado',
    'Servicio de Salud Metropolitano Occidente · SGTCP 3.2.0 · Diseñado y desarrollado'
)

components.html(html, height=900, scrolling=True)
