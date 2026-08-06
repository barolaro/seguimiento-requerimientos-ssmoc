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

    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    .stApp {
        background: #f5f7fa;
    }

    iframe {
        border: 0 !important;
        display: block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

html_path = Path(__file__).with_name("index.html")

if not html_path.exists():
    st.error("No se encontró el archivo index.html en el repositorio.")
    st.stop()

html = html_path.read_text(encoding="utf-8")

# Activa los botones visibles de la sección Reportes.
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

reports_patch = r'''
<style>
.report-toolbar{
  display:flex;
  gap:9px;
  flex-wrap:wrap;
  justify-content:flex-end;
  margin-top:16px;
}
.report-document{
  font-family:Arial,sans-serif;
  color:#132b49;
}
.report-document h1{
  color:#063c70;
  font-size:24px;
  margin-bottom:4px;
}
.report-document h2{
  color:#063c70;
  font-size:17px;
  border-bottom:2px solid #0877c9;
  padding-bottom:6px;
  margin-top:22px;
}
.report-meta{
  color:#6f7e91;
  font-size:12px;
  margin-bottom:18px;
}
.report-kpis{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:10px;
  margin:14px 0;
}
.report-kpi{
  border:1px solid #dfe6ee;
  border-radius:10px;
  padding:11px;
  background:#f8fafc;
}
.report-kpi span{display:block;font-size:11px;color:#6f7e91}
.report-kpi strong{display:block;font-size:22px;margin-top:4px}
.report-table{width:100%;border-collapse:collapse;font-size:12px}
.report-table th,.report-table td{border:1px solid #dfe6ee;padding:7px;text-align:left}
.report-table th{background:#edf4f9;color:#063c70}
.report-alert{border-left:4px solid #ed1c2e;padding:9px 11px;background:#fff4f4;margin-bottom:8px;border-radius:0 8px 8px 0}
.report-success{border-left-color:#22a447;background:#f1fbf4}
.report-toast{
  position:fixed;
  right:22px;
  bottom:22px;
  z-index:120;
  background:#063c70;
  color:#fff;
  padding:12px 16px;
  border-radius:10px;
  box-shadow:0 10px 28px rgba(0,0,0,.22);
  font-size:13px;
  font-weight:800;
}
@media(max-width:760px){.report-kpis{grid-template-columns:1fr 1fr}}
</style>

<div id="weeklyReportModal" class="modal hidden">
  <div class="modal-box" style="width:min(1000px,100%)">
    <div class="modal-head">
      <div>
        <h2 style="margin:0">Reporte Ejecutivo Semanal</h2>
        <div class="small">Vista previa lista para imprimir o guardar como PDF</div>
      </div>
      <button class="close" onclick="weeklyReportModal.classList.add('hidden')">✕</button>
    </div>
    <div id="weeklyReportContent" class="report-document"></div>
    <div class="report-toolbar">
      <button class="btn btn-secondary" onclick="weeklyReportModal.classList.add('hidden')">Cerrar</button>
      <button class="btn btn-primary" onclick="printWeeklyReport()">Imprimir / Guardar PDF</button>
    </div>
  </div>
</div>

<script>
(function(){
  const escapeCsv = value => {
    const text = String(value ?? '');
    return `"${text.replaceAll('"','""')}"`;
  };

  const downloadCsv = (filename, headers, rows) => {
    const separator = ';';
    const content = [
      headers.map(escapeCsv).join(separator),
      ...rows.map(row => row.map(escapeCsv).join(separator))
    ].join('\n');
    const blob = new Blob(['\ufeff' + content], {type:'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const toast = message => {
    const node = document.createElement('div');
    node.className = 'report-toast';
    node.textContent = message;
    document.body.appendChild(node);
    setTimeout(() => node.remove(), 2800);
  };

  const todayLabel = () => new Date().toLocaleDateString('es-CL', {
    day:'2-digit', month:'2-digit', year:'numeric'
  });

  window.exportWorkloadCsv = function(){
    if (typeof isManager !== 'function' || !isManager()) {
      alert('Este reporte está disponible solo para perfiles de gestión.');
      return;
    }
    const rows = executives().map(user => {
      const assigned = req.filter(item => item.exec === user.u);
      const activeItems = assigned.filter(item => item.estado !== 'Terminado');
      const workload = load(user.u);
      return [
        user.n,
        assigned.length,
        activeItems.length,
        assigned.filter(item => item.estado === 'Pendiente').length,
        assigned.filter(item => item.estado === 'En ejecución').length,
        assigned.filter(item => item.prio === 'Alta' && item.estado !== 'Terminado').length,
        score(user.u),
        workload.label
      ];
    });
    downloadCsv(
      `carga_ejecutivos_${new Date().toISOString().slice(0,10)}.csv`,
      ['Ejecutivo','Total','Activos','Pendientes','En ejecución','Alta prioridad','Carga ponderada','Clasificación'],
      rows
    );
    toast('Reporte de carga descargado correctamente.');
  };

  window.exportTraceCsv = function(){
    const data = typeof visible === 'function' ? visible() : req;
    const rows = data.flatMap(item => item.hist.map(event => [
      `REQ-${String(item.id).padStart(3,'0')}`,
      item.t,
      name(item.exec),
      item.estado,
      item.prio,
      event.f,
      name(event.u),
      event.estado || item.estado,
      event.d
    ]));
    downloadCsv(
      `trazabilidad_${new Date().toISOString().slice(0,10)}.csv`,
      ['ID','Requerimiento','Responsable actual','Estado actual','Prioridad','Fecha evento','Usuario evento','Estado evento','Detalle'],
      rows
    );
    toast('Trazabilidad descargada correctamente.');
  };

  window.generateWeeklyReport = function(){
    if (typeof isManager !== 'function' || !isManager()) {
      alert('Este reporte está disponible solo para perfiles de gestión.');
      return;
    }

    const activeItems = req.filter(item => item.estado !== 'Terminado');
    const overdue = activeItems.filter(item => item.vencido);
    const stale = activeItems.filter(item => item.dias > 7);
    const done = req.filter(item => item.estado === 'Terminado');
    const high = activeItems.filter(item => item.prio === 'Alta');
    const overloaded = executives().filter(user => load(user.u).label === 'SOBRECARGA');

    const workloadRows = executives().map(user => {
      const assigned = req.filter(item => item.exec === user.u);
      const workload = load(user.u);
      return `<tr>
        <td>${user.n}</td>
        <td>${assigned.filter(item => item.estado !== 'Terminado').length}</td>
        <td>${assigned.filter(item => item.prio === 'Alta' && item.estado !== 'Terminado').length}</td>
        <td>${score(user.u)}</td>
        <td>${workload.label}</td>
      </tr>`;
    }).join('');

    const alertsHtml = [
      overdue.length ? `<div class="report-alert"><b>${overdue.length} requerimiento(s) vencido(s)</b><br>Requieren revisión prioritaria.</div>` : '',
      stale.length ? `<div class="report-alert"><b>${stale.length} requerimiento(s) sin actualización por más de 7 días</b></div>` : '',
      overloaded.length ? `<div class="report-alert"><b>${overloaded.length} ejecutivo(s) con sobrecarga</b><br>${overloaded.map(user => user.n).join(', ')}</div>` : '',
      (!overdue.length && !stale.length && !overloaded.length) ? '<div class="report-alert report-success"><b>No se detectan alertas críticas.</b></div>' : ''
    ].join('');

    weeklyReportContent.innerHTML = `
      <h1>Sistema de Gestión y Trazabilidad para Compras Públicas</h1>
      <div class="report-meta">
        Departamento de Abastecimiento · Servicio de Salud Metropolitano Occidente<br>
        Reporte emitido el ${todayLabel()} · Generado por ${current?.n || 'Sistema'}
      </div>
      <div class="report-kpis">
        <div class="report-kpi"><span>Activos</span><strong>${activeItems.length}</strong></div>
        <div class="report-kpi"><span>En ejecución</span><strong>${activeItems.filter(item => item.estado === 'En ejecución').length}</strong></div>
        <div class="report-kpi"><span>Terminados</span><strong>${done.length}</strong></div>
        <div class="report-kpi"><span>Vencidos</span><strong>${overdue.length}</strong></div>
        <div class="report-kpi"><span>Alta prioridad</span><strong>${high.length}</strong></div>
        <div class="report-kpi"><span>Sin actualizar</span><strong>${stale.length}</strong></div>
        <div class="report-kpi"><span>Sobrecarga</span><strong>${overloaded.length}</strong></div>
        <div class="report-kpi"><span>Total histórico</span><strong>${req.length}</strong></div>
      </div>
      <h2>Alertas de gestión</h2>
      ${alertsHtml}
      <h2>Carga por ejecutivo</h2>
      <table class="report-table">
        <thead><tr><th>Ejecutivo</th><th>Activos</th><th>Alta prioridad</th><th>Puntaje</th><th>Carga</th></tr></thead>
        <tbody>${workloadRows}</tbody>
      </table>
      <h2>Requerimientos que requieren atención</h2>
      <table class="report-table">
        <thead><tr><th>ID</th><th>Requerimiento</th><th>Responsable</th><th>Estado</th><th>Prioridad</th><th>Avance</th></tr></thead>
        <tbody>${activeItems.filter(item => item.vencido || item.dias > 7 || item.prio === 'Alta').map(item => `<tr>
          <td>REQ-${String(item.id).padStart(3,'0')}</td><td>${item.t}</td><td>${name(item.exec)}</td><td>${item.estado}</td><td>${item.prio}</td><td>${item.avance}%</td>
        </tr>`).join('') || '<tr><td colspan="6">Sin requerimientos críticos.</td></tr>'}</tbody>
      </table>
      <p style="margin-top:24px;font-size:10px;color:#6f7e91">Desarrollado por Bayron Retamal González · Versión de demostración</p>
    `;
    weeklyReportModal.classList.remove('hidden');
  };

  window.printWeeklyReport = function(){
    const content = weeklyReportContent.innerHTML;
    const printWindow = window.open('', '_blank', 'width=1000,height=800');
    if (!printWindow) {
      alert('El navegador bloqueó la ventana de impresión. Habilite las ventanas emergentes para esta aplicación.');
      return;
    }
    printWindow.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Reporte Ejecutivo Semanal</title><style>
      body{font-family:Arial,sans-serif;color:#132b49;padding:24px}h1,h2{color:#063c70}h2{border-bottom:2px solid #0877c9;padding-bottom:6px}.report-meta{color:#6f7e91;font-size:12px}.report-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}.report-kpi{border:1px solid #dfe6ee;border-radius:8px;padding:10px}.report-kpi span{display:block;font-size:11px;color:#6f7e91}.report-kpi strong{font-size:21px}.report-table{width:100%;border-collapse:collapse;font-size:11px}.report-table th,.report-table td{border:1px solid #dfe6ee;padding:6px;text-align:left}.report-table th{background:#edf4f9}.report-alert{border-left:4px solid #ed1c2e;padding:8px;background:#fff4f4;margin-bottom:7px}.report-success{border-left-color:#22a447;background:#f1fbf4}@media print{body{padding:0}}
    </style></head><body>${content}</body></html>`);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 350);
  };
})();
</script>
'''

html = html.replace("</body>", reports_patch + "\n</body>")

components.html(
    html,
    height=1500,
    scrolling=True,
)
