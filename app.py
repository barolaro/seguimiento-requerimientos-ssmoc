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

html = html.replace("SSMOCCC", "SSMOCC")
html = re.sub(r"\bSSMOC\b", "SSMOCC", html)

logo_url = "https://gestordocumentalhsjd.ceropapel.cl/archivos/publico//logos/logo3.jpg"
html = re.sub(
    r'(<img[^>]*class=["\'][^"\']*(?:logo-login|brand-logo)[^"\']*["\'][^>]*src=)["\'][^"\']*["\']',
    lambda match: f'{match.group(1)}"{logo_url}"',
    html,
    flags=re.IGNORECASE,
)
html = html.replace('alt="Logo SSMOCCC"', 'alt="Logo SSMOCC"')

interaction_patch = r'''
<style>
.execrow.executive-clickable{
  cursor:pointer;
  border-radius:10px;
  padding-left:10px;
  padding-right:10px;
  transition:background .18s ease,transform .18s ease,box-shadow .18s ease;
}
.execrow.executive-clickable:hover{
  background:#eef7fd;
  transform:translateY(-1px);
  box-shadow:0 5px 15px rgba(0,103,168,.10);
}
.execrow.executive-clickable .execname::after{
  content:"  Ver detalle ›";
  color:#0067a8;
  font-size:11px;
  font-weight:800;
  white-space:nowrap;
}
.executive-modal-grid{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;
  margin:14px 0 18px;
}
.executive-modal-kpi{
  background:#f6f9fc;
  border:1px solid #dce4ec;
  border-radius:11px;
  padding:12px;
}
.executive-modal-kpi span{display:block;font-size:11px;color:#718096}
.executive-modal-kpi strong{display:block;font-size:24px;margin-top:4px;color:#25364a}
.executive-requirement{
  border:1px solid #dce4ec;
  border-radius:12px;
  padding:13px;
  margin-bottom:10px;
  background:#fbfdff;
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  gap:12px;
  align-items:center;
}
.executive-requirement h4{margin:0 0 5px;font-size:15px}
.executive-requirement p{margin:0;color:#718096;font-size:12px}
@media(max-width:760px){
  .executive-modal-grid{grid-template-columns:1fr 1fr}
  .executive-requirement{grid-template-columns:1fr}
}
</style>

<div id="executiveDetailModal" class="modal hidden">
  <div class="modalbox" style="width:min(900px,100%)">
    <div class="modalhead">
      <div>
        <h2 id="executiveDetailName" style="margin:0"></h2>
        <div class="small">Resumen individual y requerimientos asignados</div>
      </div>
      <button class="close" onclick="closeExecutiveDetail()">✕</button>
    </div>
    <div id="executiveDetailKpis" class="executive-modal-grid"></div>
    <h3>Requerimientos del ejecutivo</h3>
    <div id="executiveDetailRequirements"></div>
  </div>
</div>

<script>
(function () {
  function isManagementProfile() {
    return typeof manager === "function" && manager();
  }

  function personalHistoryHtml() {
    const personalRequirements = req.filter(item => item.exec === current.u);
    const personalHistory = personalRequirements
      .flatMap(item => item.hist.map(event => ({...event, title: item.t})))
      .slice()
      .reverse()
      .slice(0, 8);

    return personalHistory.length
      ? personalHistory.map(event => `
          <div class="item">
            <b>${event.title}</b>
            <div>${event.d}</div>
            <small>${event.f} · ${name(event.u)}</small>
          </div>
        `).join("")
      : '<div class="item">Todavía no registra actualizaciones.</div>';
  }

  function configureDashboardByRole() {
    if (typeof current === "undefined" || !current) return;

    const executivePanel = document.getElementById("execSummary")?.closest(".panel");
    const recentPanel = document.getElementById("recent")?.closest(".panel");
    const dashboardGrid = executivePanel?.parentElement;

    if (!isManagementProfile()) {
      if (executivePanel) executivePanel.classList.add("hidden");
      if (dashboardGrid) dashboardGrid.style.gridTemplateColumns = "1fr";
      if (recentPanel) {
        recentPanel.classList.remove("hidden");
        const title = recentPanel.querySelector("h2");
        if (title) title.textContent = "Mis últimas actualizaciones";
      }
      if (typeof recent !== "undefined") recent.innerHTML = personalHistoryHtml();
      return;
    }

    if (executivePanel) executivePanel.classList.remove("hidden");
    if (recentPanel) recentPanel.classList.remove("hidden");
    if (dashboardGrid) dashboardGrid.style.gridTemplateColumns = "1.2fr .8fr";

    const executives = users.filter(user => user.r === "Ejecutivo");
    document.querySelectorAll("#execSummary .execrow").forEach((row, index) => {
      const executive = executives[index];
      if (!executive) return;
      row.classList.add("executive-clickable");
      row.setAttribute("role", "button");
      row.setAttribute("tabindex", "0");
      row.onclick = () => openExecutiveDetail(executive.u);
      row.onkeydown = event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openExecutiveDetail(executive.u);
        }
      };
    });
  }

  window.openExecutiveDetail = function (userId) {
    if (!isManagementProfile()) return;

    const executive = users.find(user => user.u === userId);
    if (!executive) return;

    const assigned = req.filter(item => item.exec === userId);
    const active = assigned.filter(item => item.estado !== "Terminado");
    const pending = assigned.filter(item => item.estado === "Pendiente");
    const newAssignments = assigned.filter(item => item.alerts?.[userId]);

    executiveDetailName.textContent = executive.n;
    executiveDetailKpis.innerHTML = `
      <div class="executive-modal-kpi"><span>Total</span><strong>${assigned.length}</strong></div>
      <div class="executive-modal-kpi"><span>Activos</span><strong>${active.length}</strong></div>
      <div class="executive-modal-kpi"><span>Pendientes</span><strong>${pending.length}</strong></div>
      <div class="executive-modal-kpi"><span>Nuevas asignaciones</span><strong>${newAssignments.length}</strong></div>
    `;

    executiveDetailRequirements.innerHTML = assigned.length
      ? assigned.map(item => `
          <div class="executive-requirement">
            <div>
              <h4>#${String(item.id).padStart(3, "0")} · ${item.t}</h4>
              <p>${item.desc}</p>
              <p><b>Estado:</b> ${item.estado} · <b>Prioridad:</b> ${item.prio} · <b>Avance:</b> ${item.avance}%</p>
            </div>
            <button class="btn secondary" onclick="closeExecutiveDetail(); openDetail(${item.id})">Ver trazabilidad</button>
          </div>
        `).join("")
      : '<div class="item">Este ejecutivo todavía no tiene requerimientos asignados.</div>';

    executiveDetailModal.classList.remove("hidden");
  };

  window.closeExecutiveDetail = function () {
    executiveDetailModal.classList.add("hidden");
  };

  const originalDashboard = dashboard;
  dashboard = function () {
    originalDashboard();
    configureDashboardByRole();
  };

  const originalRenderAll = renderAll;
  renderAll = function () {
    originalRenderAll();
    configureDashboardByRole();
  };
})();
</script>
'''

html = html.replace("</body>", interaction_patch + "\n</body>")

components.html(
    html,
    height=1200,
    scrolling=True,
)
