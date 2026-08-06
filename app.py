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
.execrow.executive-clickable{cursor:pointer;border-radius:10px;padding-left:10px;padding-right:10px;transition:background .18s ease,transform .18s ease,box-shadow .18s ease}
.execrow.executive-clickable:hover{background:#eef7fd;transform:translateY(-1px);box-shadow:0 5px 15px rgba(0,103,168,.10)}
.execrow.executive-clickable .execname::after{content:"  Ver detalle ›";color:#0067a8;font-size:11px;font-weight:800;white-space:nowrap}
.executive-modal-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:14px 0 18px}
.executive-modal-kpi{background:#f6f9fc;border:1px solid #dce4ec;border-radius:11px;padding:12px}
.executive-modal-kpi span{display:block;font-size:11px;color:#718096}
.executive-modal-kpi strong{display:block;font-size:24px;margin-top:4px;color:#25364a}
.load-low{border-left:5px solid #2ca25f}.load-medium{border-left:5px solid #e0a100}.load-high{border-left:5px solid #e2771b}.load-overload{border-left:5px solid #d92d20}
.executive-requirement{border:1px solid #dce4ec;border-radius:12px;padding:13px;margin-bottom:10px;background:#fbfdff;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center}
.executive-requirement h4{margin:0 0 5px;font-size:15px}.executive-requirement p{margin:0;color:#718096;font-size:12px}
.reassign-load-box{background:#f6f9fc;border:1px solid #dce4ec;border-radius:12px;padding:13px;margin-top:12px}
.reassign-load-box strong{font-size:20px}.reassign-warning{background:#fff4e5;border:1px solid #f4c47b;border-radius:10px;padding:11px;margin-top:10px;color:#774a00}
.requirement-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
@media(max-width:900px){.executive-modal-grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:760px){.executive-modal-grid{grid-template-columns:1fr 1fr}.executive-requirement{grid-template-columns:1fr}.requirement-actions{justify-content:flex-start}}
</style>

<div id="executiveDetailModal" class="modal hidden">
  <div class="modalbox" style="width:min(940px,100%)">
    <div class="modalhead">
      <div><h2 id="executiveDetailName" style="margin:0"></h2><div class="small">Resumen individual, carga y requerimientos asignados</div></div>
      <button class="close" onclick="closeExecutiveDetail()">✕</button>
    </div>
    <div id="executiveDetailKpis" class="executive-modal-grid"></div>
    <h3>Requerimientos del ejecutivo</h3>
    <div id="executiveDetailRequirements"></div>
  </div>
</div>

<div id="reassignModal" class="modal hidden">
  <div class="modalbox" style="width:min(720px,100%)">
    <div class="modalhead">
      <div><h2 style="margin:0">Reasignar requerimiento</h2><div id="reassignMeta" class="small"></div></div>
      <button class="close" onclick="closeReassign()">✕</button>
    </div>
    <div class="formgrid">
      <div class="full"><label>Requerimiento</label><input id="reassignTitle" disabled></div>
      <div><label>Responsable actual</label><input id="reassignCurrent" disabled></div>
      <div><label>Nuevo responsable</label><select id="reassignNew" onchange="renderNewAssigneeLoad()"></select></div>
      <div class="full"><label>Motivo de la reasignación</label><select id="reassignReason"><option value="">Seleccione un motivo</option><option>Redistribución de carga de trabajo</option><option>Ausencia del ejecutivo</option><option>Especialidad técnica</option><option>Continuidad operacional</option><option>Instrucción de jefatura</option><option>Otro</option></select></div>
      <div class="full"><label>Observación complementaria</label><textarea id="reassignNote" placeholder="Explique brevemente la razón o contexto"></textarea></div>
    </div>
    <div id="newAssigneeLoad" class="reassign-load-box"></div>
    <div id="reassignWarning" class="reassign-warning hidden"></div>
    <div class="modalactions"><button class="btn secondary" onclick="closeReassign()">Cancelar</button><button class="btn primary" onclick="confirmReassign()">Confirmar reasignación</button></div>
  </div>
</div>

<script>
(function () {
  let reassignRequirementId = null;
  let lastExecutiveDetailUser = null;

  function isManagementProfile(){return typeof manager === "function" && manager()}
  function activeRequirements(userId){return req.filter(item=>item.exec===userId && item.estado!=="Terminado")}
  function priorityWeight(priority){return priority==="Alta"?3:priority==="Media"?2:1}
  function workloadScore(userId){return activeRequirements(userId).reduce((total,item)=>total+priorityWeight(item.prio),0)}
  function workloadInfo(userId){
    const active=activeRequirements(userId).length;
    const score=workloadScore(userId);
    if(score>=25||active>=12)return{label:"Sobrecarga",className:"load-overload",symbol:"🔴"};
    if(score>=16||active>=8)return{label:"Carga alta",className:"load-high",symbol:"🟠"};
    if(score>=8||active>=4)return{label:"Carga moderada",className:"load-medium",symbol:"🟡"};
    return{label:"Carga baja",className:"load-low",symbol:"🟢"};
  }

  function personalHistoryHtml(){
    const personal=req.filter(item=>item.exec===current.u);
    const history=personal.flatMap(item=>item.hist.map(event=>({...event,title:item.t}))).slice().reverse().slice(0,8);
    return history.length?history.map(event=>`<div class="item"><b>${event.title}</b><div>${event.d}</div><small>${event.f} · ${name(event.u)}</small></div>`).join(""):'<div class="item">Todavía no registra actualizaciones.</div>';
  }

  function configureDashboardByRole(){
    if(typeof current==="undefined"||!current)return;
    const executivePanel=document.getElementById("execSummary")?.closest(".panel");
    const recentPanel=document.getElementById("recent")?.closest(".panel");
    const dashboardGrid=executivePanel?.parentElement;
    if(!isManagementProfile()){
      if(executivePanel)executivePanel.classList.add("hidden");
      if(dashboardGrid)dashboardGrid.style.gridTemplateColumns="1fr";
      if(recentPanel){recentPanel.classList.remove("hidden");const heading=recentPanel.querySelector("h2");if(heading)heading.textContent="Mis últimas actualizaciones"}
      if(typeof recent!=="undefined")recent.innerHTML=personalHistoryHtml();
      return;
    }
    if(executivePanel)executivePanel.classList.remove("hidden");
    if(recentPanel)recentPanel.classList.remove("hidden");
    if(dashboardGrid)dashboardGrid.style.gridTemplateColumns="1.2fr .8fr";
    const executives=users.filter(user=>user.r==="Ejecutivo");
    document.querySelectorAll("#execSummary .execrow").forEach((row,index)=>{
      const executive=executives[index];if(!executive)return;
      const load=workloadInfo(executive.u);
      row.classList.add("executive-clickable",load.className);
      row.setAttribute("role","button");row.setAttribute("tabindex","0");
      row.onclick=()=>openExecutiveDetail(executive.u);
      row.onkeydown=event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();openExecutiveDetail(executive.u)}};
      const nameNode=row.querySelector(".execname");
      if(nameNode&&!nameNode.querySelector(".load-label"))nameNode.insertAdjacentHTML("beforeend",`<div class="small load-label">${load.symbol} ${load.label} · ${workloadScore(executive.u)} puntos</div>`);
    });
  }

  window.openExecutiveDetail=function(userId){
    if(!isManagementProfile())return;
    lastExecutiveDetailUser=userId;
    const executive=users.find(user=>user.u===userId);if(!executive)return;
    const assigned=req.filter(item=>item.exec===userId);
    const active=assigned.filter(item=>item.estado!=="Terminado");
    const pending=assigned.filter(item=>item.estado==="Pendiente");
    const high=active.filter(item=>item.prio==="Alta");
    const newAssignments=assigned.filter(item=>item.alerts?.[userId]);
    const load=workloadInfo(userId);
    executiveDetailName.textContent=executive.n;
    executiveDetailKpis.innerHTML=`
      <div class="executive-modal-kpi"><span>Total</span><strong>${assigned.length}</strong></div>
      <div class="executive-modal-kpi"><span>Activos</span><strong>${active.length}</strong></div>
      <div class="executive-modal-kpi"><span>Pendientes</span><strong>${pending.length}</strong></div>
      <div class="executive-modal-kpi"><span>Alta prioridad</span><strong>${high.length}</strong></div>
      <div class="executive-modal-kpi ${load.className}"><span>Carga ponderada</span><strong>${load.symbol} ${workloadScore(userId)}</strong><div class="small">${load.label}</div></div>`;
    executiveDetailRequirements.innerHTML=assigned.length?assigned.map(item=>`
      <div class="executive-requirement">
        <div><h4>#${String(item.id).padStart(3,"0")} · ${item.t}</h4><p>${item.desc}</p><p><b>Estado:</b> ${item.estado} · <b>Prioridad:</b> ${item.prio} · <b>Avance:</b> ${item.avance}%</p></div>
        <div class="requirement-actions"><button class="btn secondary" onclick="closeExecutiveDetail();openDetail(${item.id})">Ver trazabilidad</button>${item.estado!=="Terminado"?`<button class="btn primary" onclick="openReassign(${item.id})">Reasignar</button>`:""}</div>
      </div>`).join(""):'<div class="item">Este ejecutivo todavía no tiene requerimientos asignados.</div>';
    executiveDetailModal.classList.remove("hidden");
  };

  window.closeExecutiveDetail=function(){executiveDetailModal.classList.add("hidden")};

  window.openReassign=function(requirementId){
    if(!isManagementProfile())return;
    const item=req.find(requirement=>requirement.id===requirementId);if(!item)return;
    reassignRequirementId=requirementId;
    reassignMeta.textContent=`Requerimiento #${String(item.id).padStart(3,"0")}`;
    reassignTitle.value=item.t;reassignCurrent.value=name(item.exec);reassignReason.value="";reassignNote.value="";
    const executives=users.filter(user=>user.r==="Ejecutivo"&&user.u!==item.exec);
    reassignNew.innerHTML=executives.map(user=>`<option value="${user.u}">${user.n}</option>`).join("");
    closeExecutiveDetail();renderNewAssigneeLoad();reassignModal.classList.remove("hidden");
  };

  window.renderNewAssigneeLoad=function(){
    const userId=reassignNew.value;const executive=users.find(user=>user.u===userId);if(!executive)return;
    const active=activeRequirements(userId);const high=active.filter(item=>item.prio==="Alta").length;const load=workloadInfo(userId);
    newAssigneeLoad.className=`reassign-load-box ${load.className}`;
    newAssigneeLoad.innerHTML=`<div class="small">Carga del nuevo responsable</div><strong>${load.symbol} ${load.label}</strong><div>Activos: ${active.length} · Alta prioridad: ${high} · Puntaje ponderado: ${workloadScore(userId)}</div>`;
    reassignWarning.classList.toggle("hidden",load.label!=="Sobrecarga");
    reassignWarning.textContent=load.label==="Sobrecarga"?"Advertencia: el ejecutivo seleccionado ya presenta sobrecarga. Revise la distribución antes de confirmar.":"";
  };

  window.closeReassign=function(){reassignModal.classList.add("hidden");reassignRequirementId=null};

  window.confirmReassign=function(){
    if(!isManagementProfile())return;
    const item=req.find(requirement=>requirement.id===reassignRequirementId);if(!item)return;
    const newUser=reassignNew.value;const reason=reassignReason.value;const note=reassignNote.value.trim();
    if(!reason){alert("Debe seleccionar un motivo de reasignación.");return}
    const oldUser=item.exec;const stamp="Hoy "+new Date().toLocaleTimeString("es-CL",{hour:"2-digit",minute:"2-digit"});
    item.exec=newUser;item.alerts=item.alerts||{};item.alerts[newUser]=true;item.alerts[oldUser]=true;
    item.hist.push({f:stamp,u:current.u,d:`Reasignó el requerimiento desde ${name(oldUser)} a ${name(newUser)}. Motivo: ${reason}${note?`. Observación: ${note}`:""}`});
    closeReassign();renderAll();alert(`Requerimiento reasignado a ${name(newUser)}. La acción quedó registrada en la trazabilidad.`);
    if(lastExecutiveDetailUser)openExecutiveDetail(lastExecutiveDetailUser);
  };

  const originalDashboard=dashboard;
  dashboard=function(){originalDashboard();configureDashboardByRole()};
  const originalRenderAll=renderAll;
  renderAll=function(){originalRenderAll();configureDashboardByRole()};
})();
</script>
'''

html = html.replace("</body>", interaction_patch + "\n</body>")

components.html(
    html,
    height=1200,
    scrolling=True,
)
