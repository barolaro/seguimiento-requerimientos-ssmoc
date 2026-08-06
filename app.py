from pathlib import Path
import re

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Seguimiento de Requerimientos · Abastecimiento SSMOCC",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stHeader"] {display: none;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stToolbar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    .stApp {background: #f4f6f8;}
    iframe {border: 0 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

html_path = Path(__file__).with_name("index.html")

if not html_path.exists():
    st.error("No se encontró el archivo index.html en el repositorio.")
    st.stop()

html = html_path.read_text(encoding="utf-8")

# Corrige únicamente denominaciones incorrectas, sin transformar SSMOCC nuevamente.
html = html.replace("SSMOCCC", "SSMOCC")
html = re.sub(r"\bSSMOC\b", "SSMOCC", html)

# Reemplaza cualquier logo incrustado o roto por una imagen institucional estable.
logo_url = "https://gestordocumentalhsjd.ceropapel.cl/archivos/publico//logos/logo3.jpg"
html = re.sub(
    r'(<img[^>]*class=["\'][^"\']*(?:logo-login|brand-logo)[^"\']*["\'][^>]*src=)["\'][^"\']*["\']',
    lambda match: f'{match.group(1)}"{logo_url}"',
    html,
    flags=re.IGNORECASE,
)

# Ajuste preventivo del texto alternativo.
html = html.replace('alt="Logo SSMOCCC"', 'alt="Logo SSMOCC"')

components.html(
    html,
    height=1200,
    scrolling=True,
)
