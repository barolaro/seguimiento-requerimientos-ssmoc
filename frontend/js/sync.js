/* SGTCP 3.2 · Sincronización inteligente y alertas de asignación */
(function(){
'use strict';
if(typeof state==='undefined'||typeof call!=='function')return;

const SYNC_INTERVAL=45000;
const RESUME_DEBOUNCE=3500;
let timer=null;
let syncing=false;
let initialized=false;
let resumeTimer=null;
state.syncAlerts=Array.isArray(state.syncAlerts)?state.syncAlerts:[];

const isExecutive=()=>state.user?.rol==='Ejecutivo';
const isBusy=()=>document.hidden||!state.session||!!document.querySelector('dialog[open]');
const idOf=r=>Number(r?.id)||0;
const reqSignature=r=>[
 idOf(r),String(r?.responsable||''),String(r?.estado||''),Number(r?.avance)||0,
 String(r?.prioridad||''),String(r?.actualizado||''),String(r?.titulo||'')
].join('|');

function mapById(rows){const m=new Map();(rows||[]).forEach(r=>m.set(idOf(r),r));return m;}
function changed(oldRows,newRows){
 if((oldRows||[]).length!==(newRows||[]).length)return true;
 const old=mapById(oldRows);
 return (newRows||[]).some(r=>reqSignature(old.get(idOf(r)))!==reqSignature(r));
}

function addSyncAlert(r,type='Nueva asignación'){
 const id=idOf(r);if(!id)return;
 const key=`${type}:${id}`;
 if(state.syncAlerts.some(a=>a.key===key))return;
 state.syncAlerts.unshift({key,id,type,titulo:String(r.titulo||''),fecha:new Date().toISOString()});
 if(state.syncAlerts.length>30)state.syncAlerts.length=30;
 try{sessionStorage.setItem('sgtcp_sync_alerts',JSON.stringify(state.syncAlerts))}catch(_){}
}
function restoreAlerts(){
 try{const raw=sessionStorage.getItem('sgtcp_sync_alerts');const rows=raw?JSON.parse(raw):[];if(Array.isArray(rows))state.syncAlerts=rows}catch(_){}
}
function removeAlertsFor(id){
 const n=idOf({id});state.syncAlerts=state.syncAlerts.filter(a=>Number(a.id)!==n);
 try{sessionStorage.setItem('sgtcp_sync_alerts',JSON.stringify(state.syncAlerts))}catch(_){}
}

const baseRenderAlerts=window.renderAlerts;
window.renderAlerts=function(){
 if(typeof baseRenderAlerts==='function')baseRenderAlerts();
 const page=document.getElementById('alertsPage'),count=document.getElementById('navAlertCount');
 if(!page)return;
 const pending=(state.syncAlerts||[]).filter(a=>state.requirements.some(r=>idOf(r)===Number(a.id)&&r.estado!=='Terminado'));
 if(pending.length){
  const html=pending.map(a=>`<article class="panel alert-card alert-new" style="margin-bottom:10px"><div class="alert-card-main"><div class="attention-icon">${a.type==='Reasignación'?'🔁':'🔔'}</div><div><div class="alert-card-top"><b>REQ-${String(Number(a.id)).padStart(3,'0')} · ${esc(a.titulo)}</b><span class="badge ${a.type==='Reasignación'?'purple':'blue'}">${a.type==='Reasignación'?'REASIGNADO':'NUEVA ASIGNACIÓN'}</span></div><p>${esc(a.type==='Reasignación'?'Este requerimiento fue reasignado a usted y requiere revisión.':'Tiene un nuevo requerimiento asignado y requiere revisión.')}</p></div></div><button class="btn ghost sync-alert-open" data-id="${Number(a.id)}">Revisar ahora</button></article>`).join('');
  page.insertAdjacentHTML('afterbegin',html);
  page.querySelectorAll('.sync-alert-open').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)));
 }
 if(count){
  const operational=Number(count.textContent)||0;
  const total=Math.max(operational,pending.length+operational);
  count.textContent=total;count.classList.toggle('hidden',total===0);
 }
};

const baseOpenDetail=window.openDetail;
window.openDetail=async function(id){
 removeAlertsFor(id);renderAlerts();
 return baseOpenDetail(id);
};

function detectExecutiveAssignments(oldRows,newRows){
 if(!isExecutive()||!initialized)return [];
 const old=mapById(oldRows),notices=[];
 for(const r of newRows){
  const id=idOf(r),prev=old.get(id);
  if(!prev){addSyncAlert(r,'Nueva asignación');notices.push({r,type:'Nueva asignación'});continue;}
  if(String(prev.responsable)!==String(r.responsable)&&String(r.responsable)===String(state.user?.usuario)){
   addSyncAlert(r,'Reasignación');notices.push({r,type:'Reasignación'});
  }
 }
 return notices;
}

function renderDifferential(){
 try{fillSelects();renderDashboard();renderRequirements();renderUsers();renderTeam();renderAlerts();renderIndicators()}catch(e){console.warn('SGTCP sync render:',e)}
}

async function syncNow(reason='interval'){
 if(syncing||isBusy())return false;
 syncing=true;
 try{
  const previous=state.requirements.slice();
  const d=await call('listar');
  const nextUser=d.data?.usuario||state.user;
  const nextUsers=d.data?.usuarios||[];
  const nextReq=d.data?.requerimientos||[];
  const notices=detectExecutiveAssignments(previous,nextReq);
  const hasChanges=changed(previous,nextReq)||JSON.stringify(state.users)!==JSON.stringify(nextUsers);
  state.user=nextUser;state.users=nextUsers;state.requirements=nextReq;
  if(hasChanges)renderDifferential();
  if(notices.length){
   const n=notices.length;
   toast(n===1?`${notices[0].type}: REQ-${String(idOf(notices[0].r)).padStart(3,'0')} · ${notices[0].r.titulo}`:`Tiene ${n} nuevas asignaciones por revisar.`,'success');
   renderAlerts();
  }
  initialized=true;
  return hasChanges;
 }catch(e){
  if(String(e.message||'').toLowerCase().includes('sesión expiró')){try{clearSession()}catch(_){}}
  console.warn(`SGTCP sync (${reason}):`,e);
  return false;
 }finally{syncing=false}
}

function schedule(){
 clearInterval(timer);
 timer=setInterval(()=>syncNow('interval'),SYNC_INTERVAL);
}
function resumeSoon(){
 clearTimeout(resumeTimer);
 resumeTimer=setTimeout(()=>syncNow('resume'),RESUME_DEBOUNCE);
}

restoreAlerts();
document.addEventListener('visibilitychange',()=>{if(!document.hidden)resumeSoon()});
window.addEventListener('focus',resumeSoon);
document.addEventListener('DOMContentLoaded',()=>{
 initialized=false;
 setTimeout(()=>{if(state.session){initialized=true;renderAlerts()}},2500);
 schedule();
});

window.SGTCP_SYNC={syncNow,interval:SYNC_INTERVAL};
})();