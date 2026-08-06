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
        display: none;
    }

    #MainMenu,
    footer {
        visibility: hidden;
    }

    html,
    body,
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

    .stApp {
        background: #f5f7fa;
    }

    iframe {
        display: block;
        width: 100% !important;
        border: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

base_dir = Path(__file__).parent
html_path = base_dir / "index.html"
admin_patch_path = base_dir / "patches" / "admin_users.html"
runtime_patch_path = base_dir / "patches" / "runtime_tools.html"

if not html_path.exists():
    st.error("No se encontró el archivo index.html en el repositorio.")
    st.stop()

html = html_path.read_text(encoding="utf-8")
admin_patch = admin_patch_path.read_text(encoding="utf-8") if admin_patch_path.exists() else ""
runtime_patch = runtime_patch_path.read_text(encoding="utf-8") if runtime_patch_path.exists() else ""

# Activa los botones de reportes en el HTML principal.
html = html.replace(
    '<button class="btn btn-primary">Generar</button>',
    '<button class="btn btn-primary" onclick="generateWeeklyReport()">Generar</button>',
    1,
)
html = html.replace(
    '<button class="btn btn-primary">Generar</button>',
    '<button class="btn btn-primary" onclick="exportWorkloadCsv()">Generar</button>',
    1,
)
html = html.replace(
    '<button class="btn btn-primary">Generar</button>',
    '<button class="btn btn-primary" onclick="exportTraceCsv()">Generar</button>',
    1,
)

# Integra módulos antes del cierre del documento.
html = html.replace(
    "</body>",
    admin_patch + runtime_patch + "\n</body>",
)

# Altura cercana al área visible real. El contenido largo usa scroll dentro del visor.
components.html(
    html,
    height=900,
    scrolling=True,
)
