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
    [data-testid="stToolbar"] {display: none;}
    #MainMenu, footer {visibility: hidden;}
    .block-container {padding: 0 !important; max-width: 100% !important;}
    .stApp {background: #f5f7fa;}
    iframe {border: 0 !important; display: block;}
    </style>
    """,
    unsafe_allow_html=True,
)

base_dir = Path(__file__).parent
html_path = base_dir / "index.html"
admin_patch_path = base_dir / "patches" / "admin_users.html"

if not html_path.exists():
    st.error("No se encontró el archivo index.html en el repositorio.")
    st.stop()

html = html_path.read_text(encoding="utf-8")
admin_patch = admin_patch_path.read_text(encoding="utf-8") if admin_patch_path.exists() else ""

# Activa los tres botones visibles de la sección Reportes.
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

runtime_patch = r'''
<style>
.developer-credit{
  font-size:11px;
  line-height:1.4;
  color:rgba(255,255,255,.84);
  margin:10px 0 12px;
  padding-top:10px;
  border-top:1px solid rgba(255,255,255,.15);
}
.developer-credit strong{display:block;color:#fff;font-size:12px}
.login-developer{
  margin-top:16px;
  padding-top:13px;
  border-top:1px solid #dfe6ee;
  text-align:center;
  color:#6f7e91;
  font-size:11px;
}
.login-developer strong{color:#063c70}
.system-developer-badge{
  display:inline-flex;
  align-items:center;
  gap:7px;
  margin-top:10px;
  padding:7px 11px;
  border:1px solid #dfe6ee;
  border-radius:999px;
  background:#fff;
  color:#063c70;
  font-size:11px;
  font-weight:800;
  box-shadow:0 5px 14px rgba(18,55,88,.06);
}
.system-toast{
  position:fixed;right:22px;bottom:22px;z-index:150;
  padding:12px 16px;border-radius:10px;background:#063c70;color:#fff;
  box-shadow:0 10px 28px rgba(0,0,0,.22);font-size:12px;font-weight:800;
}
</style>
<script>
(function(){
  const AUTHOR='Bayron Retamal González';

  function installDeveloperIdentity(){
    const loginCard=document.querySelector('.login-card');
    if(loginCard&&!loginCard.querySelector('.login-developer')){
      loginCard.insertAdjacentHTML('beforeend',`<div class="login-developer">Diseño y desarrollo<br><strong>${AUTHOR}</strong></div>`);
    }

    const sidebarFoot=document.querySelector('.sidebar-foot');
    if(sidebarFoot&&!sidebarFoot.querySelector('.developer-credit')){
      sidebarFoot.insertAdjacentHTML('afterbegin',`<div class="developer-credit">Desarrollado por<strong>${AUTHOR}</strong></div>`);
    }

    const subtitle=document.querySelector('#dashboard .system-subtitle');
    if(subtitle&&!document.querySelector('.system-developer-badge')){
      subtitle.insertAdjacentHTML('afterend',`<div class="system-developer-badge">◈ Desarrollo interno · ${AUTHOR}</div>`);
    }
  }

  function csvEscape(value){return `"${String(value??'').replaceAll('"','""')}"`}
  function downloadCsv(filename,headers,rows){
    const text=[headers,...rows].map(row=>row.map(csvEscape).join(';')).join('\n');
    const blob=new Blob(['\ufeff'+text],{type:'text/csv;charset=utf-8;'});
    const url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
  }
  function toast(message){const node=document.createElement('div');node.className='system-toast';node.textContent=message;document.body.appendChild(node);setTimeout(()=>node.remove(),2600)}

  window.exportWorkloadCsv=function(){
    if(typeof isManager==='function'&&!isManager())return alert('Disponible solo para perfiles de gestión.');
    const rows=executives().map(user=>[
      user.n,
      req.filter(item=>item.exec===user.u).length,
      active(user.u).length,
      req.filter(item=>item.exec===user.u&&item.estado==='Pendiente').length,
      req.filter(item=>item.exec===user.u&&item.estado==='En ejecución').length,
      score(user.u),
      load(user.u).label
    ]);
    downloadCsv(`carga_ejecutivos_${new Date().toISOString().slice(0,10)}.csv`,['Ejecutivo','Total','Activos','Pendientes','En ejecución','Puntaje','Carga'],rows);
    toast('Reporte de carga descargado.');
  };

  window.exportTraceCsv=function(){
    const data=typeof visible==='function'?visible():req;
    const rows=data.flatMap(item=>item.hist.map(event=>[
      `REQ-${String(item.id).padStart(3,'0')}`,item.t,name(item.exec),item.estado,item.prio,event.f,name(event.u),event.estado||item.estado,event.d
    ]));
    downloadCsv(`trazabilidad_${new Date().toISOString().slice(0,10)}.csv`,['ID','Requerimiento','Responsable','Estado actual','Prioridad','Fecha evento','Usuario','Estado evento','Detalle'],rows);
    toast('Trazabilidad descargada.');
  };

  window.generateWeeklyReport=function(){
    if(typeof isManager==='function'&&!isManager())return alert('Disponible solo para perfiles de gestión.');
    const activeItems=req.filter(item=>item.estado!=='Terminado');
    const rows=executives().map(user=>`<tr><td>${user.n}</td><td>${active(user.u).length}</td><td>${score(user.u)}</td><td>${load(user.u).label}</td></tr>`).join('');
    const report=window.open('','_blank','width=1000,height=800');
    if(!report)return alert('Habilite las ventanas emergentes para generar el reporte.');
    report.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Reporte Ejecutivo</title><style>body{font-family:Arial;padding:28px;color:#132b49}h1,h2{color:#063c70}table{width:100%;border-collapse:collapse}th,td{border:1px solid #dfe6ee;padding:8px;text-align:left}th{background:#edf4f9}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.kpi{border:1px solid #dfe6ee;border-radius:9px;padding:12px}.kpi b{font-size:23px;display:block}@media print{body{padding:0}}</style></head><body><h1>Sistema de Gestión y Trazabilidad para Compras Públicas</h1><p>Departamento de Abastecimiento · SSMOCC</p><p>Generado por ${current?.n||'Sistema'} · ${new Date().toLocaleString('es-CL')}</p><div class="kpis"><div class="kpi">Activos<b>${activeItems.length}</b></div><div class="kpi">En ejecución<b>${activeItems.filter(x=>x.estado==='En ejecución').length}</b></div><div class="kpi">Vencidos<b>${activeItems.filter(x=>x.vencido).length}</b></div><div class="kpi">Terminados<b>${req.filter(x=>x.estado==='Terminado').length}</b></div></div><h2>Carga por ejecutivo</h2><table><thead><tr><th>Ejecutivo</th><th>Activos</th><th>Puntaje</th><th>Clasificación</th></tr></thead><tbody>${rows}</tbody></table><p style="margin-top:30px;font-size:11px;color:#6f7e91">Diseñado y desarrollado por ${AUTHOR}</p><script>setTimeout(()=>window.print(),400)<\/script></body></html>`);
    report.document.close();
  };

  const observer=new MutationObserver(installDeveloperIdentity);
  observer.observe(document.body,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',installDeveloperIdentity);
  installDeveloperIdentity();
})();
</script>
'''

# Inserta módulos antes del cierre del documento.
html = html.replace("</body>", admin_patch + runtime_patch + "\n</body>")

components.html(html, height=1700, scrolling=True)
