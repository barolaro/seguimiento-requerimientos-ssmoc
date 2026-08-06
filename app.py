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

html = html.replace('alt="Logo SSMOCCC"', 'alt="Logo SSMOCC"')

# Refuerza la separación de información por perfil.
# El Ejecutivo no puede ver carga, nombres ni actividad de otros integrantes.
profile_guard = r'''
<script>
(function () {
  const originalDashboard = window.dashboard;

  window.dashboard = function () {
    if (typeof current === "undefined" || !current) return;

    const executivePanel = document.getElementById("execSummary")?.closest(".panel");
    const recentPanel = document.getElementById("recent")?.closest(".panel");
    const dashboardGrid = executivePanel?.parentElement;

    if (typeof manager === "function" && manager()) {
      if (executivePanel) executivePanel.classList.remove("hidden");
      if (recentPanel) recentPanel.classList.remove("hidden");
      if (dashboardGrid) dashboardGrid.style.gridTemplateColumns = "1.2fr .8fr";
      if (typeof originalDashboard === "function") originalDashboard();
      return;
    }

    // Perfil Ejecutivo: elimina completamente la información del resto del equipo.
    if (executivePanel) executivePanel.classList.add("hidden");
    if (dashboardGrid) dashboardGrid.style.gridTemplateColumns = "1fr";

    if (recentPanel) {
      recentPanel.classList.remove("hidden");
      const heading = recentPanel.querySelector("h2");
      if (heading) heading.textContent = "Mis últimas actualizaciones";
    }

    const personalRequirements = req.filter(item => item.exec === current.u);
    const personalHistory = personalRequirements
      .flatMap(item => item.hist.map(event => ({...event, title: item.t})))
      .slice()
      .reverse()
      .slice(0, 8);

    recent.innerHTML = personalHistory.length
      ? personalHistory.map(event => `
          <div class="item">
            <b>${event.title}</b>
            <div>${event.d}</div>
            <small>${event.f} · ${name(event.u)}</small>
          </div>
        `).join("")
      : '<div class="item">Todavía no registra actualizaciones.</div>';
  };

  // Evita que una navegación o nuevo render vuelva a mostrar datos globales.
  const originalRenderAll = window.renderAll;
  window.renderAll = function () {
    if (typeof originalRenderAll === "function") originalRenderAll();
    window.dashboard();
  };
})();
</script>
'''

html = html.replace("</body>", profile_guard + "\n</body>")

components.html(
    html,
    height=1200,
    scrolling=True,
)
