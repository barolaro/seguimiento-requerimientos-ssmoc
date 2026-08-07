/* SGTCP 3.0 · Performance + UX layer
 * Reduce viajes repetidos a Apps Script, mejora velocidad percibida
 * y refuerza confirmaciones/alertas operacionales.
 */
(function(){
  if(typeof state==='undefined') return;

  state.detailCache=state.detailCache||{};
  state.detailLoading=state.detailLoading||{};
  const CACHE_PREFIX='sgtcp_detail_';
  const CACHE_TTL=10*60*1000;

  function cacheKey(id){return CACHE_PREFIX+id}
  function saveCache(id,payload){
    state.detailCache[id]={payload,ts:Date.now()};
    try{sessionStorage.setItem(cacheKey(id),JSON.stringify(state.detailCache[id]))}catch{}
  }
  function getCache(id){
    let c=state.detailCache[id];
    if(!c){try{c=JSON.parse(sessionStorage.getItem(cacheKey(id))||'null')}catch{c=null}}
    if(!c||Date.now()-Number(c.ts||0)>CACHE_TTL)return null;
    state.detailCache[id]=c;
    return c.payload;
  }

  function timelineHtml(events,r){
    if(!events||!events.length){
      return `<div class="event"><b>Asignación inicial · ${r.estado||'Pendiente'}</b><p>Requerimiento registrado y asignado a ${userName(r.responsable)}.</p><small>${fmt(r.creado)} · ${userName(r.creado_por)}</small></div>`;
    }
    return events.slice().reverse().map(x=>`<div class="event"><b>${x.tipo||'Actualización'} · ${x.estado_nuevo||r.estado}</b><p>${x.detalle||''}</p><small>${fmt(x.fecha)} · ${userName(x.autor)}</small></div>`).join('');
  }

  function isNewAssignment(r){
    if(!r||r.estado==='Terminado') return false;
    const created=new Date(r.creado).getTime(),updated=new Date(r.actualizado).getTime();
    if(!created||!updated) return Number(r.avance||0)===0 && r.estado==='Pendiente';
    return Number(r.avance||0)===0 && r.estado==='Pendiente' && Math.abs(updated-created)<120000;
  }
  function alertReason(r){
    const reasons=[];
    if(isNewAssignment(r)) reasons.push('Nueva asignación');
    if(overdue(r)) reasons.push('Vencido');
    if(r.estado!=='Terminado'&&daysSince(r.actualizado)>7) reasons.push('Sin actualización > 7 días');
    if(r.estado!=='Terminado'&&r.prioridad==='Alta'&&Number(r.avance||0)<25) reasons.push('Alta prioridad con bajo avance');
    return reasons;
  }
  function alertItems(){return state.requirements.filter(r=>alertReason(r).length>0)}

  async function fetchDetail(id,force=false){
    if(!force){const cached=getCache(id);if(cached)return cached}
    if(state.detailLoading[id])return state.detailLoading[id];
    state.detailLoading[id]=call('detalle',{id}).then(d=>{
      const payload=d.data||{};saveCache(id,payload);return payload;
    }).finally(()=>delete state.detailLoading[id]);
    return state.detailLoading[id];
  }
  async function prefetchRecent(){
    const ids=state.requirements.slice().sort((a,b)=>new Date(b.actualizado)-new Date(a.actualizado)).slice(0,12).map(r=>Number(r.id));
    for(const id of ids){if(getCache(id))continue;try{await fetchDetail(id)}catch{}await new Promise(r=>setTimeout(r,80))}
  }
  function schedulePrefetch(){const fn=()=>prefetchRecent();if('requestIdleCallback' in window)requestIdleCallback(fn,{timeout:1800});else setTimeout(fn,700)}

  const originalLoadAll=window.loadAll||loadAll;
  window.loadAll=loadAll=async function(){const out=await originalLoadAll();schedulePrefetch();return out};

  window.openDetail=openDetail=async function(id){
    state.selectedId=Number(id);
    const r=state.requirements.find(x=>Number(x.id)===Number(id));
    if(!r)return toast('Requerimiento no encontrado.','error');
    $('detailTitle').textContent=r.titulo;
    $('detailMeta').textContent=`REQ-${String(r.id).padStart(3,'0')} · Creado ${fmt(r.creado)}`;
    $('detailResponsible').value=userName(r.responsable);
    $('detailPriority').value=r.prioridad;$('detailStatus').value=r.estado;$('detailProgress').value=r.avance||0;
    $('detailDescription').value=r.descripcion||'';$('detailUpdate').value='';
    $('detailPriority').disabled=!manager();$('detailDescription').disabled=!manager();
    document.querySelectorAll('#detailDialog .manager-only').forEach(x=>x.classList.toggle('hidden',!manager()));
    const cached=getCache(id);
    $('timeline').innerHTML=cached?timelineHtml(cached.eventos||[],r):timelineHtml([],r)+`<div class="timeline-sync"><span class="sync-dot"></span> Sincronizando historial…</div>`;
    $('detailDialog').showModal();
    try{const payload=await fetchDetail(id,!!cached);if(Number(state.selectedId)===Number(id))$('timeline').innerHTML=timelineHtml(payload.eventos||[],r)}
    catch(e){if(!cached&&Number(state.selectedId)===Number(id))$('timeline').innerHTML=timelineHtml([],r)+`<p class="error">No se pudo refrescar el historial: ${e.message}</p>`}
  };

  window.saveUpdate=saveUpdate=async function(){
    const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));
    const detail=$('detailUpdate').value.trim();
    if(!r)return;
    if(!detail)return toast('Ingrese una actualización para dejar trazabilidad.','error');
    const cambios={estado:$('detailStatus').value,avance:Number($('detailProgress').value)||0};
    if(manager()){cambios.prioridad=$('detailPriority').value;cambios.descripcion=$('detailDescription').value.trim()}
    if(cambios.estado==='Terminado')cambios.avance=100;

    const confirmText=`¿Está seguro de guardar esta actualización?\n\nREQ-${String(r.id).padStart(3,'0')} · ${r.titulo}\nEstado: ${r.estado} → ${cambios.estado}\nAvance: ${r.avance||0}% → ${cambios.avance}%\n\nActualización:\n${detail}\n\nLa acción quedará registrada en la trazabilidad.`;
    if(!window.confirm(confirmText))return;

    const btn=$('saveUpdateBtn'),old=btn.textContent,oldState=r.estado,oldAdvance=Number(r.avance||0);
    btn.disabled=true;btn.textContent='Guardando en Google Sheets…';
    try{
      await call('actualizar_req',{id:r.id,cambios,detalle:detail});
      const now=new Date().toISOString();
      Object.assign(r,cambios,{actualizado:now});
      const cached=getCache(r.id)||{eventos:[]};
      cached.eventos=(cached.eventos||[]).concat([{fecha:now,tipo:oldState!==cambios.estado?'estado':oldAdvance!==cambios.avance?'avance':'actualizacion',autor:state.user?.usuario,detalle,estado_anterior:oldState,estado_nuevo:cambios.estado,responsable_anterior:r.responsable,responsable_nuevo:r.responsable,avance_anterior:oldAdvance,avance_nuevo:cambios.avance}]);
      cached.requerimiento={...r};saveCache(r.id,cached);
      $('detailDialog').close();renderAll();
      toast(`✓ REQ-${String(r.id).padStart(3,'0')} guardado correctamente en Google Sheets y trazabilidad.`,'success');
    }catch(e){toast(`No se guardó la actualización: ${e.message}`,'error')}
    finally{btn.disabled=false;btn.textContent=old}
  };

  window.createRequirement=createRequirement=async function(e){
    e.preventDefault();
    const req={titulo:$('reqTitle').value.trim(),descripcion:$('reqDescription').value.trim(),responsable:$('reqResponsible').value,prioridad:$('reqPriority').value,compromiso:$('reqDue').value};
    if(!req.responsable)return toast('Seleccione un responsable.','error');
    if(!confirm(`¿Está seguro de registrar este requerimiento?\n\nTítulo: ${req.titulo}\nResponsable: ${userName(req.responsable)}\nPrioridad: ${req.prioridad}\n\nAl confirmar se creará una alerta de nueva asignación.`))return;
    const b=e.submitter||e.target.querySelector('button[type="submit"]'),old=b.textContent;b.disabled=true;b.textContent='Guardando…';
    try{
      const d=await call('crear_req',{req}),now=new Date().toISOString();
      const item={id:d.id,titulo:req.titulo,descripcion:req.descripcion,responsable:req.responsable,estado:'Pendiente',prioridad:req.prioridad,avance:0,creado:now,compromiso:req.compromiso,creado_por:state.user?.usuario,actualizado:now};
      state.requirements.unshift(item);
      saveCache(d.id,{requerimiento:item,eventos:[{fecha:now,tipo:'asignacion',autor:state.user?.usuario,detalle:'Requerimiento creado y asignado.',estado_nuevo:'Pendiente',responsable_nuevo:req.responsable,avance_nuevo:0}]});
      $('requirementDialog').close();e.target.reset();renderAll();
      toast(`✓ REQ-${String(d.id).padStart(3,'0')} registrado. Nueva asignación agregada a Alertas.`,'success');
    }catch(err){toast(`No se creó el requerimiento: ${err.message}`,'error')}
    finally{b.disabled=false;b.textContent=old}
  };

  window.renderAlerts=renderAlerts=function(){
    const rows=alertItems();
    const nav=$('navAlertCount');
    if(nav){nav.textContent=rows.length;nav.classList.toggle('hidden',rows.length===0)}
    $('alertsPage').innerHTML=rows.length?rows.map(r=>{
      const reasons=alertReason(r),isNew=reasons.includes('Nueva asignación');
      return `<article class="panel alert-card ${isNew?'alert-new':''}"><div class="alert-card-main"><div class="attention-icon">${isNew?'🔔':overdue(r)?'⏰':'⚠'}</div><div><div class="alert-card-top"><b>REQ-${String(r.id).padStart(3,'0')} · ${r.titulo}</b>${isNew?'<span class="badge blue">NUEVA ASIGNACIÓN</span>':''}</div><p>${reasons.join(' · ')}</p><small>Responsable: ${userName(r.responsable)} · ${r.prioridad} · Actualizado ${fmt(r.actualizado)}</small></div></div><button class="btn ghost alert-open" data-id="${r.id}">Abrir ficha</button></article>`
    }).join(''):'<article class="panel"><b>Sin alertas pendientes.</b><p class="muted">No existen requerimientos que requieran atención en este momento.</p></article>';
    document.querySelectorAll('.alert-open').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)));
  };

  const originalRenderAttention=window.renderAttention||renderAttention;
  window.renderAttention=renderAttention=function(){
    originalRenderAttention();
    const newCount=state.requirements.filter(isNewAssignment).length;
    if(newCount>0){
      const list=$('attentionList');
      const row=document.createElement('div');row.className='attention-item blue';
      row.innerHTML=`<div class="attention-icon">🔔</div><div><b>Nuevas asignaciones</b><span>${newCount} requerimiento${newCount===1?'':'s'} pendiente${newCount===1?'':'s'} de primera gestión</span></div><button class="link">Ver →</button>`;
      row.querySelector('button').onclick=()=>setView('alerts');list.prepend(row);
    }
  };

  if(window.Chart){Chart.defaults.animation.duration=120;Chart.defaults.responsive=true}
  document.addEventListener('DOMContentLoaded',schedulePrefetch);
})();
