/* SGTCP 3.0 · Performance layer
 * Reduce viajes repetidos a Apps Script y mejora velocidad percibida.
 */
(function(){
  if(typeof state==='undefined') return;

  state.detailCache=state.detailCache||{};
  state.detailLoading=state.detailLoading||{};
  const CACHE_PREFIX='sgtcp_detail_';
  const CACHE_TTL=10*60*1000; // 10 min

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
  function invalidate(id){delete state.detailCache[id];try{sessionStorage.removeItem(cacheKey(id))}catch{}}

  function timelineHtml(events,r){
    if(!events||!events.length){
      return `<div class="event"><b>Asignación inicial · ${r.estado||'Pendiente'}</b><p>Requerimiento registrado y asignado a ${userName(r.responsable)}.</p><small>${fmt(r.creado)} · ${userName(r.creado_por)}</small></div>`;
    }
    return events.slice().reverse().map(x=>`<div class="event"><b>${x.tipo||'Actualización'} · ${x.estado_nuevo||r.estado}</b><p>${x.detalle||''}</p><small>${fmt(x.fecha)} · ${userName(x.autor)}</small></div>`).join('');
  }

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
    for(const id of ids){
      if(getCache(id))continue;
      try{await fetchDetail(id)}catch{}
      await new Promise(r=>setTimeout(r,80));
    }
  }
  function schedulePrefetch(){
    const fn=()=>prefetchRecent();
    if('requestIdleCallback' in window)requestIdleCallback(fn,{timeout:1800});else setTimeout(fn,700);
  }

  const originalLoadAll=window.loadAll||loadAll;
  window.loadAll=loadAll=async function(){
    const out=await originalLoadAll();
    schedulePrefetch();
    return out;
  };

  window.openDetail=openDetail=async function(id){
    state.selectedId=Number(id);
    const r=state.requirements.find(x=>Number(x.id)===Number(id));
    if(!r)return toast('Requerimiento no encontrado.','error');

    $('detailTitle').textContent=r.titulo;
    $('detailMeta').textContent=`REQ-${String(r.id).padStart(3,'0')} · Creado ${fmt(r.creado)}`;
    $('detailResponsible').value=userName(r.responsable);
    $('detailPriority').value=r.prioridad;
    $('detailStatus').value=r.estado;
    $('detailProgress').value=r.avance||0;
    $('detailDescription').value=r.descripcion||'';
    $('detailUpdate').value='';
    $('detailPriority').disabled=!manager();
    $('detailDescription').disabled=!manager();
    document.querySelectorAll('#detailDialog .manager-only').forEach(x=>x.classList.toggle('hidden',!manager()));

    const cached=getCache(id);
    $('timeline').innerHTML=cached?timelineHtml(cached.eventos||[],r):timelineHtml([],r)+`<div class="timeline-sync"><span class="sync-dot"></span> Sincronizando historial…</div>`;
    $('detailDialog').showModal();

    // Si ya hay cache, refresca en segundo plano sin bloquear al usuario.
    try{
      const payload=await fetchDetail(id,!!cached);
      if(Number(state.selectedId)===Number(id))$('timeline').innerHTML=timelineHtml(payload.eventos||[],r);
    }catch(e){
      if(!cached&&Number(state.selectedId)===Number(id))$('timeline').innerHTML=timelineHtml([],r)+`<p class="error">No se pudo refrescar el historial: ${e.message}</p>`;
    }
  };

  window.saveUpdate=saveUpdate=async function(){
    const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));
    const detail=$('detailUpdate').value.trim();
    if(!r)return;
    if(!detail)return toast('Ingrese una actualización para dejar trazabilidad.','error');

    const cambios={estado:$('detailStatus').value,avance:Number($('detailProgress').value)||0};
    if(manager()){cambios.prioridad=$('detailPriority').value;cambios.descripcion=$('detailDescription').value.trim()}
    if(cambios.estado==='Terminado')cambios.avance=100;
    const btn=$('saveUpdateBtn');const old=btn.textContent;btn.disabled=true;btn.textContent='Guardando…';
    try{
      await call('actualizar_req',{id:r.id,cambios,detalle:detail});
      Object.assign(r,cambios,{actualizado:new Date().toISOString()});
      const cached=getCache(r.id)||{eventos:[]};
      cached.eventos=(cached.eventos||[]).concat([{fecha:new Date().toISOString(),tipo:'actualizacion',autor:state.user?.usuario,detalle,estado_anterior:r.estado,estado_nuevo:cambios.estado,responsable_anterior:r.responsable,responsable_nuevo:r.responsable,avance_nuevo:cambios.avance}]);
      saveCache(r.id,cached);
      $('detailDialog').close();
      renderAll();
      toast('Actualización guardada y registrada en trazabilidad.','success');
    }catch(e){toast(e.message,'error')}
    finally{btn.disabled=false;btn.textContent=old}
  };

  window.createRequirement=createRequirement=async function(e){
    e.preventDefault();
    const req={titulo:$('reqTitle').value.trim(),descripcion:$('reqDescription').value.trim(),responsable:$('reqResponsible').value,prioridad:$('reqPriority').value,compromiso:$('reqDue').value};
    if(!req.responsable)return toast('Seleccione un responsable.','error');
    if(!confirm(`¿Registrar y asignar este requerimiento a ${userName(req.responsable)}?`))return;
    const b=e.submitter||e.target.querySelector('button[type="submit"]');const old=b.textContent;b.disabled=true;b.textContent='Guardando…';
    try{
      const d=await call('crear_req',{req});
      const now=new Date().toISOString();
      const item={id:d.id,titulo:req.titulo,descripcion:req.descripcion,responsable:req.responsable,estado:'Pendiente',prioridad:req.prioridad,avance:0,creado:now,compromiso:req.compromiso,creado_por:state.user?.usuario,actualizado:now};
      state.requirements.unshift(item);
      saveCache(d.id,{requerimiento:item,eventos:[{fecha:now,tipo:'asignacion',autor:state.user?.usuario,detalle:'Requerimiento creado y asignado.',estado_nuevo:'Pendiente',responsable_nuevo:req.responsable,avance_nuevo:0}]});
      $('requirementDialog').close();e.target.reset();renderAll();toast(`REQ-${String(d.id).padStart(3,'0')} registrado correctamente.`,'success');
    }catch(err){toast(err.message,'error')}
    finally{b.disabled=false;b.textContent=old}
  };

  // Desactivar animaciones largas de Chart.js: el dashboard responde antes.
  if(window.Chart){Chart.defaults.animation.duration=120;Chart.defaults.responsive=true;}

  document.addEventListener('DOMContentLoaded',schedulePrefetch);
})();
