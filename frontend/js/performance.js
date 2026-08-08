/* SGTCP 3.1.4 · Performance + UX + Reasignaciones */
(function(){
  if(typeof state==='undefined') return;
  state.detailCache=state.detailCache||{}; state.detailLoading=state.detailLoading||{};
  const CACHE_PREFIX='sgtcp_detail_', CACHE_TTL=10*60*1000;
  const cacheKey=id=>CACHE_PREFIX+id;
  function saveCache(id,payload){state.detailCache[id]={payload,ts:Date.now()};try{sessionStorage.setItem(cacheKey(id),JSON.stringify(state.detailCache[id]))}catch{}}
  function clearCache(id){delete state.detailCache[id];try{sessionStorage.removeItem(cacheKey(id))}catch{}}
  function getCache(id){let c=state.detailCache[id];if(!c){try{c=JSON.parse(sessionStorage.getItem(cacheKey(id))||'null')}catch{c=null}}if(!c||Date.now()-Number(c.ts||0)>CACHE_TTL)return null;state.detailCache[id]=c;return c.payload}
  function timelineHtml(events,r){if(!events||!events.length)return `<div class="event"><b>Asignación inicial · ${r.estado||'Pendiente'}</b><p>Requerimiento registrado y asignado a ${userName(r.responsable)}.</p><small>${fmt(r.creado)} · ${userName(r.creado_por)}</small></div>`;return events.slice().reverse().map(x=>`<div class="event${x._pending?' event-pending':''}"><b>${x.tipo||'Actualización'} · ${x.estado_nuevo||r.estado}${x._pending?' · Sincronizando…':''}</b><p>${x.detalle||''}</p><small>${fmt(x.fecha)} · ${userName(x.autor)}</small></div>`).join('')}
  function isExecutiveSession(){return state.user?.rol==='Ejecutivo'}
  function isNewAssignment(r){if(!r||r.estado==='Terminado')return false;const c=new Date(r.creado).getTime(),u=new Date(r.actualizado).getTime();if(!c||!u)return Number(r.avance||0)===0&&r.estado==='Pendiente';return Number(r.avance||0)===0&&r.estado==='Pendiente'&&Math.abs(u-c)<120000}
  function pendingAssignment(r){return !!r?._assignmentAlert||isNewAssignment(r)}
  function alertReason(r){const a=[];if(r?._assignmentAlert==='Reasignación')a.push('Requerimiento reasignado');else if(pendingAssignment(r))a.push('Nueva asignación');if(overdue(r))a.push('Vencido');if(r.estado!=='Terminado'&&daysSince(r.actualizado)>7)a.push('Sin actualización > 7 días');if(r.estado!=='Terminado'&&r.prioridad==='Alta'&&Number(r.avance||0)<25)a.push('Alta prioridad con bajo avance');return a}
  function alertItems(){return state.requirements.filter(r=>alertReason(r).length>0)}
  async function fetchDetail(id,force=false){if(!force){const c=getCache(id);if(c)return c}if(state.detailLoading[id])return state.detailLoading[id];state.detailLoading[id]=call('detalle',{id}).then(d=>{const p=d.data||{};saveCache(id,p);return p}).finally(()=>delete state.detailLoading[id]);return state.detailLoading[id]}
  function assignmentAlertFromEvents(events,r){
    if(!Array.isArray(events)||!events.length||!r||r.estado==='Terminado')return '';
    const ev=events.slice().sort((a,b)=>new Date(a.fecha)-new Date(b.fecha));let last=null,lastIdx=-1;
    ev.forEach((x,i)=>{const t=String(x.tipo||'').toLowerCase();if((t==='reasignacion'||t==='reasignación'||t==='asignacion'||t==='asignación')&&String(x.responsable_nuevo||r.responsable)===String(r.responsable)){last=x;lastIdx=i}});
    if(!last)return '';
    const reviewed=ev.slice(lastIdx+1).some(x=>String(x.tipo||'').toLowerCase()==='revision'||String(x.detalle||'').toLowerCase().includes('requerimiento revisado por el ejecutivo'));
    if(reviewed)return '';
    return String(last.tipo||'').toLowerCase().startsWith('reasign')?'Reasignación':'Nueva asignación';
  }
  async function hydrateExecutiveAlerts(){
    if(!isExecutiveSession())return;
    const rows=state.requirements.filter(r=>r.estado!=='Terminado').slice(0,20);
    let changed=false;
    for(const r of rows){
      try{const p=await fetchDetail(r.id,false);const a=assignmentAlertFromEvents(p.eventos||[],r);if((r._assignmentAlert||'')!==a){r._assignmentAlert=a;changed=true}}catch{}
      await new Promise(res=>setTimeout(res,70));
    }
    if(changed){renderAlerts();if(typeof renderAttention==='function')renderAttention()}
  }
  async function prefetchRecent(){const ids=state.requirements.slice().sort((a,b)=>new Date(b.actualizado)-new Date(a.actualizado)).slice(0,3).map(r=>Number(r.id));for(const id of ids){if(getCache(id))continue;try{await fetchDetail(id)}catch{}await new Promise(r=>setTimeout(r,180))}}
  function scheduleBackground(){const fn=()=>{prefetchRecent();hydrateExecutiveAlerts()};if('requestIdleCallback'in window)requestIdleCallback(fn,{timeout:2500});else setTimeout(fn,1200)}
  const originalLoadAll=window.loadAll||loadAll; window.loadAll=loadAll=async function(){const out=await originalLoadAll();scheduleBackground();return out};

  window.logout=logout=async function(){if(!window.confirm('¿Está seguro de cerrar sesión?'))return;const btn=$('logoutBtn'),old=btn?.textContent;if(btn){btn.disabled=true;btn.textContent='Cerrando…'}try{if(state.session)await call('logout')}catch{}finally{clearSession();if(btn){btn.disabled=false;btn.textContent=old||'Cerrar sesión'}}};

  async function markReviewedIfNeeded(r){
    if(!isExecutiveSession()||!pendingAssignment(r)||String(r.responsable)!==String(state.user?.usuario))return;
    const oldUpdated=r.actualizado,oldAlert=r._assignmentAlert,oldState=r.estado,oldAdvance=Number(r.avance||0),now=new Date().toISOString();r.actualizado=now;r._assignmentAlert='';renderAlerts();if(typeof renderAttention==='function')renderAttention();
    try{await call('actualizar_req',{id:r.id,cambios:{estado:r.estado,avance:oldAdvance},detalle:'Requerimiento revisado por el ejecutivo.'});const cached=getCache(r.id)||{eventos:[]};cached.eventos=(cached.eventos||[]).concat([{fecha:now,tipo:'revision',autor:state.user?.usuario,detalle:'Requerimiento revisado por el ejecutivo.',estado_anterior:oldState,estado_nuevo:oldState,responsable_anterior:r.responsable,responsable_nuevo:r.responsable,avance_anterior:oldAdvance,avance_nuevo:oldAdvance}]);cached.requerimiento={...r};saveCache(r.id,cached);if(Number(state.selectedId)===Number(r.id))$('timeline').innerHTML=timelineHtml(cached.eventos||[],r)}catch(e){r.actualizado=oldUpdated;r._assignmentAlert=oldAlert;renderAlerts()}
  }

  function setLockedUI(r){const locked=String(r.estado)==='Terminado';['detailPriority','detailStatus','detailProgress','detailDescription','detailUpdate'].forEach(id=>{const el=$(id);if(el)el.disabled=locked||(id==='detailPriority'||id==='detailDescription'?!manager():false)});const save=$('saveUpdateBtn');if(save){save.disabled=locked;save.textContent=locked?'Requerimiento terminado':'Guardar actualización'}const reas=$('openReassignBtn');if(reas)reas.classList.toggle('hidden',locked||!manager());let del=$('deleteReqBtn');if(!del&&admin()){del=document.createElement('button');del.id='deleteReqBtn';del.type='button';del.className='btn ghost';del.style.color='#b42318';del.textContent='Eliminar requerimiento';$('saveUpdateBtn')?.parentElement?.appendChild(del)}if(del){del.classList.toggle('hidden',!admin());del.onclick=()=>deleteRequirement(r.id)}}

  window.openDetail=openDetail=async function(id){state.selectedId=Number(id);const r=state.requirements.find(x=>Number(x.id)===Number(id));if(!r)return toast('Requerimiento no encontrado.','error');$('detailTitle').textContent=r.titulo;$('detailMeta').textContent=`REQ-${String(r.id).padStart(3,'0')} · Creado ${fmt(r.creado)}`;$('detailResponsible').value=userName(r.responsable);$('detailPriority').value=r.prioridad;$('detailStatus').value=r.estado;$('detailProgress').value=r.avance||0;$('detailDescription').value=r.descripcion||'';$('detailUpdate').value='';document.querySelectorAll('#detailDialog .manager-only').forEach(x=>x.classList.toggle('hidden',!manager()));setLockedUI(r);const cached=getCache(id);$('timeline').innerHTML=cached?timelineHtml(cached.eventos||[],r):timelineHtml([],r)+`<div class="timeline-sync"><span class="sync-dot"></span> Sincronizando historial…</div>`;$('detailDialog').showModal();markReviewedIfNeeded(r);try{const payload=await fetchDetail(id,false);if(Number(state.selectedId)===Number(id))$('timeline').innerHTML=timelineHtml(payload.eventos||[],r)}catch(e){if(!cached&&Number(state.selectedId)===Number(id))$('timeline').innerHTML=timelineHtml([],r)+`<p class="error">No se pudo refrescar el historial: ${e.message}</p>`}};

  /* Reasignación segura: intercepta el botón Confirmar antes del handler original. */
  document.addEventListener('click',async function(e){
    const btn=e.target?.closest?.('#confirmReassignBtn');if(!btn)return;
    e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
    if(!manager())return toast('No tiene permisos para reasignar.','error');
    const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));if(!r)return toast('Requerimiento no encontrado.','error');
    if(r.estado==='Terminado')return toast('No se puede reasignar un requerimiento terminado.','error');
    const target=$('reassignExec')?.value||'',reason=$('reassignReason')?.value||'',note=$('reassignNote')?.value.trim()||'';
    if(!target)return toast('Seleccione el nuevo responsable.','error');if(target===r.responsable)return toast('Seleccione un ejecutivo distinto al responsable actual.','error');if(!reason)return toast('Seleccione el motivo de reasignación.','error');
    const targetName=userName(target),currentName=userName(r.responsable),motivo=note?`${reason} · ${note}`:reason;
    if(!window.confirm(`¿Está seguro de reasignar este requerimiento?\n\nREQ-${String(r.id).padStart(3,'0')} · ${r.titulo}\nResponsable actual: ${currentName}\nNuevo responsable: ${targetName}\nMotivo: ${motivo}\n\nEl nuevo ejecutivo recibirá una alerta y la reasignación quedará registrada en trazabilidad.`))return;
    const previous=r.responsable,now=new Date().toISOString(),cached=getCache(r.id)||{eventos:[]};
    r.responsable=target;r.actualizado=now;r._assignmentAlert='Reasignación';
    const ev={fecha:now,tipo:'reasignacion',autor:state.user?.usuario,detalle:motivo,estado_anterior:r.estado,estado_nuevo:r.estado,responsable_anterior:previous,responsable_nuevo:target,avance_anterior:r.avance,avance_nuevo:r.avance,_pending:true};
    cached.eventos=(cached.eventos||[]).concat([ev]);cached.requerimiento={...r};saveCache(r.id,cached);
    $('reassignDialog')?.close();$('detailDialog')?.close();renderAll();toast(`REQ-${String(r.id).padStart(3,'0')} reasignado a ${targetName} · sincronizando…`,'success');
    try{await call('reasignar_req',{id:r.id,responsable:target,motivo});ev._pending=false;saveCache(r.id,cached);toast(`✓ Reasignación confirmada. ${targetName} verá una alerta al ingresar.`,'success')}
    catch(err){r.responsable=previous;r._assignmentAlert='';cached.eventos=(cached.eventos||[]).filter(x=>x!==ev);cached.requerimiento={...r};saveCache(r.id,cached);renderAll();toast(`No se pudo reasignar. Se revirtió el cambio: ${err.message}`,'error')}
  },true);

  window.deleteRequirement=async function(id){if(!admin())return toast('Solo el Administrador puede eliminar requerimientos.','error');const r=state.requirements.find(x=>Number(x.id)===Number(id));if(!r)return;if(!confirm(`¿Está seguro de eliminar REQ-${String(r.id).padStart(3,'0')} · ${r.titulo}?\n\nEsta acción quitará el requerimiento de la cartera activa y quedará registrada en Auditoría.`))return;const motivo=prompt('Indique el motivo de eliminación (obligatorio):','Creado por error');if(motivo===null)return;if(motivo.trim().length<5)return toast('Debe indicar un motivo de eliminación.','error');try{await call('eliminar_req',{id:r.id,motivo:motivo.trim()});state.requirements=state.requirements.filter(x=>Number(x.id)!==Number(r.id));clearCache(r.id);$('detailDialog').close();renderAll();toast(`✓ REQ-${String(r.id).padStart(3,'0')} eliminado de la cartera. La acción quedó auditada.`,'success')}catch(e){toast(`No se pudo eliminar: ${e.message}`,'error')}};

  window.renderAlerts=renderAlerts=function(){const rows=alertItems(),nav=$('navAlertCount');if(nav){nav.textContent=rows.length;nav.classList.toggle('hidden',rows.length===0)}$('alertsPage').innerHTML=rows.length?rows.map(r=>{const reasons=alertReason(r),reassigned=reasons.includes('Requerimiento reasignado'),isNew=reasons.includes('Nueva asignación');return `<article class="panel alert-card ${(reassigned||isNew)?'alert-new':''}"><div class="alert-card-main"><div class="attention-icon">${reassigned?'🔁':isNew?'🔔':overdue(r)?'⏰':'⚠'}</div><div><div class="alert-card-top"><b>REQ-${String(r.id).padStart(3,'0')} · ${r.titulo}</b>${reassigned?'<span class="badge purple">REASIGNADO</span>':isNew?'<span class="badge blue">NUEVA ASIGNACIÓN</span>':''}</div><p>${reasons.join(' · ')}</p><small>Responsable: ${userName(r.responsable)} · ${r.prioridad} · Actualizado ${fmt(r.actualizado)}</small></div></div><button class="btn ghost alert-open" data-id="${r.id}">Revisar ahora</button></article>`}).join(''):'<article class="panel"><b>Sin alertas pendientes.</b><p class="muted">No existen requerimientos que requieran atención en este momento.</p></article>';document.querySelectorAll('.alert-open').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)))};
  const originalRenderAttention=window.renderAttention||renderAttention;window.renderAttention=renderAttention=function(){originalRenderAttention();const n=state.requirements.filter(pendingAssignment).length;if(n>0){const list=$('attentionList'),row=document.createElement('div');row.className='attention-item blue';row.innerHTML=`<div class="attention-icon">🔔</div><div><b>Asignaciones por revisar</b><span>${n} requerimiento${n===1?'':'s'} requiere${n===1?'':'n'} revisión</span></div><button class="link">Ver →</button>`;row.querySelector('button').onclick=()=>setView('alerts');list.prepend(row)}};
  if(window.Chart){Chart.defaults.animation.duration=60;Chart.defaults.responsive=true}document.addEventListener('DOMContentLoaded',scheduleBackground);
})();