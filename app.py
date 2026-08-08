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
    @media(max-width:820px){iframe{min-height:1200px!important;}}
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
performance_path = frontend_dir / "js" / "performance.js"

required = (html_path, css_path, mobile_css_path, js_path, performance_path)
missing = [str(p.relative_to(base_dir)) for p in required if not p.exists()]
if missing:
    st.error("La interfaz está incompleta. Faltan: " + ", ".join(missing))
    st.stop()

html = html_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")
mobile_css = mobile_css_path.read_text(encoding="utf-8")
javascript = js_path.read_text(encoding="utf-8")
performance_js = performance_path.read_text(encoding="utf-8")

# Ajuste específico para monitores de escritorio grandes/4K.
# Mantiene intactas las reglas móviles de mobile.css.
desktop_css = r"""
@media (min-width:821px){
  .login-shell{min-height:100vh;padding:clamp(24px,3vh,48px);}
  .login-card{width:clamp(470px,30vw,620px);padding:clamp(34px,2.6vw,54px);border-radius:28px;}
  .login-card .logo{width:clamp(135px,9vw,185px);height:clamp(135px,9vw,185px);margin-bottom:18px;}
  .login-card h1{font-size:clamp(27px,1.75vw,36px);line-height:1.12;}
  .login-card>.muted{font-size:clamp(12px,.8vw,16px);}
  .login-card form{gap:clamp(14px,1vw,20px);margin:clamp(24px,1.8vw,34px) 0 18px;}
  .login-card label{font-size:clamp(11px,.72vw,14px);}
  .login-card input{min-height:clamp(45px,3vw,58px);font-size:clamp(14px,.9vw,18px);}
  .login-card .btn{min-height:clamp(45px,3vw,58px);font-size:clamp(14px,.9vw,18px);}
  .login-card small{font-size:clamp(9px,.6vw,12px);}
}
@media (min-width:2000px){
  .topbar{min-height:88px;padding-left:clamp(28px,2vw,56px);padding-right:clamp(28px,2vw,56px);grid-template-columns:360px 1fr auto;}
  .brand img{width:54px;height:54px}.brand strong{font-size:22px}.brand span{font-size:11px}
  .topbar nav button{font-size:12px;padding:12px 14px}.account b{font-size:13px}.account span{font-size:11px}
  main{width:min(1900px,calc(100% - 80px));padding-top:38px;}
  .page-head h2{font-size:38px}.page-head p:last-child{font-size:15px}
  .kpi span{font-size:12px}.kpi strong{font-size:34px}.kpi small{font-size:11px}
  .panel-head h3{font-size:17px}th,td{font-size:12px}th{font-size:11px}
}
"""

DEFAULT_APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbzmYGqzfBTgjcyXtoB7rA6j1uvZ7XGSm_WHAuXWZSD8RLIOiQJd0krdQ_xfOSfJClsKiw/exec"
)
apps_script_url = str(st.secrets.get("apps_script_url", DEFAULT_APPS_SCRIPT_URL)).strip()

config_script = "<script>window.SGTCP_CONFIG=" + json.dumps(
    {"appsScriptUrl": apps_script_url, "version": "3.0.9"}, ensure_ascii=False
) + ";</script>"

html = html.replace('<link rel="stylesheet" href="css/style.css">', f"<style>{css}\n{mobile_css}\n{desktop_css}</style>")
html = html.replace('<script src="js/config.js"></script>', config_script)
html = html.replace('<script src="js/app.js"></script>', f"<script>{javascript}</script>")
for tag in ('<script src="js/performance.js?v=3.0.1"></script>','<script src="js/performance.js?v=3.0.2"></script>','<script src="js/performance.js"></script>'):
    html = html.replace(tag, f"<script>{performance_js}</script>")

html = html.replace('Diseñado y desarrollado por <strong>Bayron Retamal González</strong></small>','SGTCP 3.0.9 · Responsive móvil + escritorio 4K<br>Diseñado y desarrollado por <strong>Bayron Retamal González</strong></small>')
for old in ('SGTCP 3.0 · Diseñado y desarrollado','SGTCP 3.0.3 · Diseñado y desarrollado','SGTCP 3.0.4 · Diseñado y desarrollado','SGTCP 3.0.5 · Diseñado y desarrollado','SGTCP 3.0.6 · Diseñado y desarrollado','SGTCP 3.0.7 · Diseñado y desarrollado','SGTCP 3.0.8 · Diseñado y desarrollado'):
    html = html.replace(old, 'SGTCP 3.0.9 · Diseñado y desarrollado')

components.html(html, height=1200, scrolling=True)
