/* SGTCP 3.2 · Estabilización UX, seguridad y renderizado seguro */
(function(){
'use strict';
if(typeof state==='undefined')return;
const pendingUpdates=new Map();

/* ---------- Seguridad de salida ---------- */
window.esc=function(v=''){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));};
const escAttr=window.esc;
const safePct=v=>Math.max(0,Math.min(100,Number(v)||0));
const safeId=v=>Number.isFinite(Number(v))?Number(v):0;

function safeBadge(v){const value=String(v||'Sin estado'),k=value==='Terminado'?'green':value==='En ejecución'?'blue':value==='En espera'?'purple':'orange';return `<span class="badge ${k}">${esc(value)}</span>`;}
window.badge=safeBadge;

/* ---------- Diálogo interno único ---------- */
function ensureActionDialog(){
 if(document.getElementById('sgtcpActionDialog'))return;
 const d=document.createElement('dialog');d.id='sgtcpActionDialog';d.innerHTML='<div class="dialog-shell"><div class="dialog-head"><div><p class="eyebrow">Confirmación</p><h3 id="sgtcpActionTitle">Confirmar acción</h3></div></div><div id="sgtcpActionMessage" style="white-space:pre-line;line-height:1.55;margin:12px 0 18px"></div><label id="sgtcpPromptWrap" class="hidden">Información<input id="sgtcpPromptInput" autocomplete="off"></label><div class="dialog-actions"><button id="sgtcpActionCancel" class="btn ghost" type="button">Cancelar</button><button id="sgtcpActionOk" class="btn primary" type="button">Confirmar</button></div></div>';
 document.body.appendChild(d);
}
function actionDialog({title='Confirmar acción',message='',prompt=false,initial='',ok='Confirmar',danger=false,inputType='text'}={}){
 ensureActionDialog();const d=document.getElementById('sgtcpActionDialog'),t=document.getElementById('sgtcpActionTitle'),m=document.getElementById('sgtcpActionMessage'),w=document.getElementById('sgtcpPromptWrap'),i=document.getElementById('sgtcpPromptInput'),yes=document.getElementById('sgtcpActionOk'),no=document.getElementById('sgtcpActionCancel');
 t.textContent=title;m.textContent=message;w.classList.toggle('hidden',!prompt);i.value=initial;i.type=inputType;yes.textContent=ok;yes.className=danger?'btn danger':'btn primary';
 return new Promise(resolve=>{const done=v=>{yes.onclick=null;no.onclick=null;d.oncancel=null;d.close();resolve(v)};yes.onclick=()=>done(prompt?i.value:true);no.onclick=()=>done(prompt?null:false);d.oncancel=e=>{e.preventDefault();done(prompt?null:false)};d.showModal();if(prompt)setTimeout(()=>i.focus(),30)});
}
window.sgtcpConfirm=(message,title='Confirmar acción',ok='Confirmar',danger=false)=>actionDialog({title,message,ok,danger});
window.sgtcpPrompt=(message,initial='',title='Información requerida',inputType='text')=>actionDialog({title,message,prompt:true,initial,ok:'Continuar',inputType});

/* ---------- Login seguro: elimina prompt() del primer ingreso ---------- */
window.login=async function(e){
 e.preventDefault();document.getElementById('loginError').textContent='';const b=e.submitter;if(b)b.disabled=true;
 try{
  const password=document.getElementById('loginPassword').value;
  const d=await call('login',{usuario:document.getElementById('loginUser').value.trim(),password});
  state.session=d.session;state.user=d.usuario;localStorage.setItem('sgtcp_session',state.session);
  if(d.cambiar_password){
   const n=await sgtcpPrompt('Primer ingreso: cree una nueva contraseña de al menos 10 caracteres.','','Crear nueva contraseña','password');
   if(!n||n.length<10)throw new Error('Debe definir una contraseña de al menos 10 caracteres.');
   await call('cambiar_password',{actual:password,nueva:n});
  }
  await loadAll();showApp();
 }catch(err){document.getElementById('loginError').textContent=err.message}finally{if(b)b.disabled=false}
};

/* ---------- Renderizadores seguros ---------- */
window.renderWorkload=function(){
 const box=document.getElementById('workloadTable');
 if(!manager()){box.innerHTML='<p class="muted">La distribución global de carga está disponible para perfiles de jefatura.</p>';return;}
 const ex=executives();
 box.innerHTML=`<div style="overflow:auto"><table class="work-table"><thead><tr><th>Ejecutivo</th><th>Activos</th><th>Carga ponderada</th><th>Estado</th></tr></thead><tbody>${ex.map(u=>{const l=load(u.usuario),s=score(u.usuario);return `<tr class="work-row" data-exec="${escAttr(u.usuario)}"><td><div class="person"><span class="mini-avatar">${esc(initials(u.nombre))}</span><b>${esc(u.nombre)}</b></div></td><td>${activeFor(u.usuario).length}</td><td>${s} / 30 pts<div class="load-bar"><i style="width:${safePct(l.pct)}%;background:${escAttr(l.color)}"></i></div></td><td><span class="load-pill ${escAttr(l.cls)}">${esc(l.label)}</span></td></tr>`}).join('')}</tbody></table></div>`;
 document.querySelectorAll('.work-row').forEach(x=>x.onclick=()=>openExecutive(x.dataset.exec));
};

window.renderRecent=function(){
 const rows=state.requirements.slice().sort((a,b)=>new Date(b.actualizado)-new Date(a.actualizado)).slice(0,7);
 document.getElementById('recentActivity').innerHTML=rows.length?rows.map(x=>`<div class="activity-item"><span class="activity-dot"></span><div><b>REQ-${String(safeId(x.id)).padStart(3,'0')} · ${esc(x.titulo)}</b><p>${esc(x.estado)} · ${safePct(x.avance)}% · ${esc(userName(x.responsable))}</p><small>Actualizado ${esc(fmt(x.actualizado))}</small></div></div>`).join(''):'<p class="muted">Sin actividad reciente.</p>';
};

window.fillSelects=function(){
 const opts=executives().map(u=>`<option value="${escAttr(u.usuario)}">${esc(u.nombre)}</option>`).join('');
 document.getElementById('reqResponsible').innerHTML=opts;
 document.getElementById('execFilter').innerHTML='<option value="">Todos los ejecutivos</option>'+opts;
 renderAssignLoad();
};

window.renderRequirements=function(){
 const q=(document.getElementById('searchInput')?.value||'').toLowerCase(),e=document.getElementById('execFilter')?.value||'',s=document.getElementById('stateFilter')?.value||'',p=document.getElementById('priorityFilter')?.value||'';
 const rows=state.requirements.filter(r=>(!q||`${r.id} ${r.titulo} ${r.descripcion} ${userName(r.responsable)}`.toLowerCase().includes(q))&&(!e||r.responsable===e)&&(!s||r.estado===s)&&(!p||r.prioridad===p));
 document.getElementById('requirementsBody').innerHTML=rows.map(r=>{const id=safeId(r.id),pct=safePct(r.avance);return `<tr><td>REQ-${String(id).padStart(3,'0')}</td><td><b>${esc(r.titulo)}</b><br><span class="muted">${esc(r.descripcion||'')}</span></td><td>${esc(userName(r.responsable))}</td><td>${safeBadge(r.estado)}</td><td>${esc(r.prioridad)}</td><td><div class="progress"><i style="width:${pct}%"></i></div><small>${pct}%</small></td><td>${esc(fmt(r.actualizado))}</td><td><button class="btn ghost open-detail" data-id="${id}">Abrir</button></td></tr>`}).join('');
 document.querySelectorAll('.open-detail').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)));
};

window.openDetail=async function(id){
 state.selectedId=Number(id);const r=state.requirements.find(x=>Number(x.id)===Number(id));if(!r)return toast('Requerimiento no encontrado.','error');
 document.getElementById('detailTitle').textContent=r.titulo;document.getElementById('detailMeta').textContent=`REQ-${String(safeId(r.id)).padStart(3,'0')} · Creado ${fmt(r.creado)}`;document.getElementById('detailResponsible').value=userName(r.responsable);document.getElementById('detailPriority').value=r.prioridad;document.getElementById('detailStatus').value=r.estado;document.getElementById('detailProgress').value=safePct(r.avance);document.getElementById('detailDescription').value=r.descripcion||'';document.getElementById('detailUpdate').value='';document.getElementById('detailPriority').disabled=!manager();document.getElementById('detailDescription').disabled=!manager();document.querySelectorAll('#detailDialog .manager-only').forEach(x=>x.classList.toggle('hidden',!manager()));
 const tl=document.getElementById('timeline');tl.innerHTML='<p class="muted">Cargando trazabilidad…</p>';document.getElementById('detailDialog').showModal();
 try{const d=await call('detalle',{id:Number(id)}),ev=d.data.eventos||[];tl.innerHTML=ev.length?ev.slice().reverse().map(x=>`<div class="event"><b>${esc(x.tipo||'Actualización')} · ${esc(x.estado_nuevo||r.estado)}</b><p>${esc(x.detalle||'')}</p><small>${esc(fmt(x.fecha))} · ${esc(userName(x.autor))}</small></div>`).join(''):'<p class="muted">Sin eventos registrados.</p>'}catch(err){tl.textContent=`No se pudo cargar la trazabilidad: ${err.message}`;tl.classList.add('error')}
};

window.renderAssignLoad=function(){const u=document.getElementById('reqResponsible')?.value,box=document.getElementById('assignLoad');if(!u||!manager()||!state.users.length){if(box)box.textContent='';return}const l=load(u);box.innerHTML=`<b>Carga actual:</b> ${esc(l.label)} · ${activeFor(u).length} activos · ${score(u)} puntos`;};

window.renderTeam=function(){
 if(!manager())return;const ex=executives(),over=ex.filter(u=>load(u.usuario).label==='SOBRECARGA').length;
 document.getElementById('teamSummary').innerHTML=[['Ejecutivos',ex.length],['Activos',state.requirements.filter(r=>r.estado!=='Terminado').length],['Carga alta',ex.filter(u=>load(u.usuario).label==='ALTA').length],['Sobrecarga',over]].map(x=>`<article class="kpi"><span>${esc(x[0])}</span><strong>${Number(x[1])||0}</strong></article>`).join('');
 document.getElementById('teamTable').innerHTML=document.getElementById('workloadTable').innerHTML;document.querySelectorAll('#teamTable .work-row').forEach(x=>x.onclick=()=>openExecutive(x.dataset.exec));
};

window.openExecutive=function(u){
 state.selectedExecutive=u;const person=state.users.find(x=>x.usuario===u);if(!person)return;const rs=state.requirements.filter(r=>r.responsable===u),l=load(u);document.getElementById('executiveName').textContent=person.nombre;
 document.getElementById('executiveKpis').innerHTML=[['Total',rs.length],['Activos',activeFor(u).length],['Pendientes',rs.filter(r=>r.estado==='Pendiente').length],['Alta prioridad',rs.filter(r=>r.prioridad==='Alta'&&r.estado!=='Terminado').length],['Carga',score(u)+' pts']].map(x=>`<div class="exec-kpi"><span>${esc(x[0])}</span><strong>${esc(x[1])}</strong></div>`).join('');
 document.getElementById('executiveRequirements').innerHTML=`<p><span class="load-pill ${escAttr(l.cls)}">${esc(l.label)}</span></p>`+rs.map(r=>{const id=safeId(r.id);return `<div class="exec-req"><div><h4>REQ-${String(id).padStart(3,'0')} · ${esc(r.titulo)}</h4><p>${esc(r.estado)} · ${esc(r.prioridad)} · ${safePct(r.avance)}%</p></div><div><button class="btn ghost exec-open" data-id="${id}">Trazabilidad</button>${r.estado!=='Terminado'?` <button class="btn primary exec-reassign" data-id="${id}">Reasignar</button>`:''}</div></div>`}).join('');
 document.getElementById('executiveDialog').showModal();document.querySelectorAll('.exec-open').forEach(b=>b.onclick=()=>{document.getElementById('executiveDialog').close();openDetail(Number(b.dataset.id))});document.querySelectorAll('.exec-reassign').forEach(b=>b.onclick=()=>{document.getElementById('executiveDialog').close();openReassign(Number(b.dataset.id))});
};

window.openReassign=function(id=state.selectedId){const r=state.requirements.find(x=>Number(x.id)===Number(id));if(!r)return;state.selectedId=r.id;if(document.getElementById('detailDialog').open)document.getElementById('detailDialog').close();document.getElementById('reassignMeta').textContent=`REQ-${String(safeId(r.id)).padStart(3,'0')}`;document.getElementById('reassignTitle').value=r.titulo;document.getElementById('reassignCurrent').value=userName(r.responsable);document.getElementById('reassignReason').value='';document.getElementById('reassignNote').value='';document.getElementById('reassignExec').innerHTML=executives().filter(u=>u.usuario!==r.responsable).map(u=>`<option value="${escAttr(u.usuario)}">${esc(u.nombre)}</option>`).join('');renderReassignLoad();document.getElementById('reassignDialog').showModal();};

window.renderReassignLoad=function(){const u=document.getElementById('reassignExec').value;if(!u)return;const l=load(u),box=document.getElementById('reassignLoad');box.innerHTML=`<b>${esc(userName(u))}</b><br>${esc(l.label)} · ${activeFor(u).length} activos · ${score(u)} puntos`;document.getElementById('reassignWarning').classList.toggle('hidden',l.label!=='SOBRECARGA');document.getElementById('reassignWarning').textContent=l.label==='SOBRECARGA'?'El ejecutivo seleccionado presenta sobrecarga. Revise la distribución antes de confirmar.':'';};

window.renderTrace=function(){const rs=state.requirements.slice().sort((a,b)=>new Date(b.actualizado)-new Date(a.actualizado));document.getElementById('globalTrace').innerHTML=rs.map(r=>{const id=safeId(r.id);return `<div class="event"><b>REQ-${String(id).padStart(3,'0')} · ${esc(r.titulo)}</b><p>${esc(r.estado)} · ${safePct(r.avance)}% · ${esc(userName(r.responsable))}</p><small>Último movimiento: ${esc(fmt(r.actualizado))}</small><br><button class="link trace-open" data-id="${id}">Ver historial completo →</button></div>`}).join('');document.querySelectorAll('.trace-open').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)));};

window.renderAlerts=function(){const active=state.requirements.filter(r=>r.estado!=='Terminado'),alerts=[];active.filter(overdue).forEach(r=>alerts.push({r,t:'Requerimiento vencido',c:'red'}));active.filter(r=>daysSince(r.actualizado)>7).forEach(r=>alerts.push({r,t:'Sin actualización por más de 7 días',c:'orange'}));active.filter(r=>r.prioridad==='Alta'&&Number(r.avance)<25).forEach(r=>alerts.push({r,t:'Alta prioridad con bajo avance',c:'orange'}));document.getElementById('navAlertCount').textContent=alerts.length;document.getElementById('navAlertCount').classList.toggle('hidden',!alerts.length);document.getElementById('alertsPage').innerHTML=alerts.length?alerts.map(a=>{const id=safeId(a.r.id);return `<article class="panel" style="margin-bottom:10px"><div class="attention-item ${a.c==='orange'?'orange':''}"><div class="attention-icon">⚠</div><div><b>${esc(a.t)}</b><span>REQ-${String(id).padStart(3,'0')} · ${esc(a.r.titulo)} · ${esc(userName(a.r.responsable))}</span></div><button class="btn ghost alert-open" data-id="${id}">Revisar</button></div></article>`}).join(''):'<article class="panel"><p class="muted">No existen alertas operacionales pendientes.</p></article>';document.querySelectorAll('.alert-open').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)));};

window.renderUsers=function(){if(!document.getElementById('usersBody'))return;const us=state.users;document.getElementById('userStats').innerHTML=`<div class="admin-stat"><span>Usuarios</span><strong>${us.length}</strong></div><div class="admin-stat"><span>Activos</span><strong>${us.filter(u=>u.activo).length}</strong></div><div class="admin-stat"><span>Ejecutivos activos</span><strong>${us.filter(u=>u.activo&&u.rol==='Ejecutivo').length}</strong></div>`;document.getElementById('usersBody').innerHTML=us.map(u=>`<tr><td><b>${esc(u.nombre)}</b></td><td>${esc(u.usuario)}</td><td>${esc(u.rol)}</td><td>${esc(u.email||'—')}</td><td>${u.activo?'<span class="badge green">Activo</span>':'<span class="badge red">Inactivo</span>'}</td><td>${admin()?`<div class="user-actions"><button class="btn ghost reset-user" data-user="${escAttr(u.usuario)}">Restablecer clave</button>${u.usuario!==state.user?.usuario?`<button class="btn ${u.activo?'danger-soft':'ghost'} toggle-user" data-user="${escAttr(u.usuario)}" data-active="${u.activo?'0':'1'}">${u.activo?'Desactivar':'Activar'}</button>`:''}</div>`:'—'}</td></tr>`).join('');document.querySelectorAll('.reset-user').forEach(b=>b.onclick=()=>resetPassword(b.dataset.user));document.querySelectorAll('.toggle-user').forEach(b=>b.onclick=()=>toggleUser(b.dataset.user,b.dataset.active==='1'));};

/* ---------- Guardado optimista ---------- */
function localEvent(r,detail,changes){const oldState=r.estado,oldAdvance=Number(r.avance||0),newState=changes.estado??oldState,newAdvance=safePct(changes.avance??oldAdvance);return{fecha:new Date().toISOString(),tipo:oldState!==newState?'estado':oldAdvance!==newAdvance?'avance':'actualizacion',autor:state.user?.usuario,detalle,estado_anterior:oldState,estado_nuevo:newState,responsable_anterior:r.responsable,responsable_nuevo:r.responsable,avance_anterior:oldAdvance,avance_nuevo:newAdvance,_pending:true};}
function renderPendingTimeline(ev,r){const box=document.createElement('div');box.className='event event-pending';const b=document.createElement('b');b.textContent=`${ev.tipo||'Actualización'} · ${ev.estado_nuevo||r.estado} · Sincronizando…`;const p=document.createElement('p');p.textContent=ev.detalle||'';const s=document.createElement('small');s.textContent=`${fmt(ev.fecha)} · ${userName(ev.autor)}`;box.append(b,p,s);return box;}
async function refreshDetail(id){try{const d=await call('detalle',{id}),payload=d.data||{};if(state.detailCache)state.detailCache[id]={payload,ts:Date.now()};try{sessionStorage.setItem(`sgtcp_detail_${id}`,JSON.stringify({payload,ts:Date.now()}))}catch(_){}}catch(_){}}

window.saveUpdate=async function(){const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));if(!r)return toast('Requerimiento no encontrado.','error');if(String(r.estado)==='Terminado')return toast('El requerimiento terminado está bloqueado.','error');const detail=document.getElementById('detailUpdate')?.value.trim()||'';if(!detail)return toast('Ingrese una actualización para dejar trazabilidad.','error');if(pendingUpdates.has(Number(r.id)))return toast('Este requerimiento ya se está sincronizando.','info');const changes={estado:document.getElementById('detailStatus').value,avance:safePct(document.getElementById('detailProgress').value)};if(manager()){changes.prioridad=document.getElementById('detailPriority').value;changes.descripcion=document.getElementById('detailDescription').value.trim()}if(changes.estado==='Terminado')changes.avance=100;const ok=await sgtcpConfirm(`REQ-${String(safeId(r.id)).padStart(3,'0')} · ${r.titulo}\n\nEstado: ${r.estado} → ${changes.estado}\nAvance: ${safePct(r.avance)}% → ${changes.avance}%\n\nLa actualización quedará registrada permanentemente en la trazabilidad.`,'Guardar actualización','Guardar');if(!ok)return;const snapshot={...r},ev=localEvent(r,detail,changes);Object.assign(r,changes,{actualizado:ev.fecha});const timeline=document.getElementById('timeline');if(timeline)timeline.prepend(renderPendingTimeline(ev,r));document.getElementById('detailUpdate').value='';renderRequirements();renderRecent();renderAlerts();renderAttention?.();const dlg=document.getElementById('detailDialog');if(dlg?.open)dlg.close();toast('Actualización visible · sincronizando con Google Sheets…','success');const task=call('actualizar_req',{id:r.id,cambios:changes,detalle:detail});pendingUpdates.set(Number(r.id),task);try{await task;ev._pending=false;await refreshDetail(r.id);toast('✓ Actualización guardada y trazabilidad sincronizada.','success')}catch(err){Object.keys(r).forEach(k=>delete r[k]);Object.assign(r,snapshot);renderAll();toast(`No se pudo guardar. El cambio fue revertido: ${err.message}`,'error')}finally{pendingUpdates.delete(Number(r.id));}};

window.logout=async function(){const ok=await sgtcpConfirm('La sesión actual se cerrará y volverá a la pantalla de ingreso.','Cerrar sesión','Cerrar sesión');if(!ok)return;const b=document.getElementById('logoutBtn');if(b){b.disabled=true;b.textContent='Cerrando…'}try{if(state.session)await call('logout')}catch(_){}finally{clearSession();if(b){b.disabled=false;b.textContent='Cerrar sesión'}}};
window.createRequirement=async function(e){e.preventDefault();const req={titulo:document.getElementById('reqTitle').value.trim(),descripcion:document.getElementById('reqDescription').value.trim(),responsable:document.getElementById('reqResponsible').value,prioridad:document.getElementById('reqPriority').value,compromiso:document.getElementById('reqDue').value};if(!req.responsable)return toast('Seleccione un responsable.','error');const ok=await sgtcpConfirm(`${req.titulo}\n\nResponsable: ${userName(req.responsable)}\nPrioridad: ${req.prioridad}${req.compromiso?'\nCompromiso: '+req.compromiso:''}\n\nEl ejecutivo recibirá el requerimiento en su cartera.`,'Registrar requerimiento','Registrar');if(!ok)return;const b=e.submitter;if(b)b.disabled=true;try{await call('crear_req',{req});document.getElementById('requirementDialog').close();e.target.reset();await loadAll();toast('✓ Requerimiento creado y asignado correctamente.','success')}catch(err){toast(err.message,'error')}finally{if(b)b.disabled=false}};
window.resetPassword=async function(u){const ok=await sgtcpConfirm(`Se generará una nueva contraseña temporal para ${userName(u)}.`,'Restablecer contraseña','Restablecer',true);if(!ok)return;try{const d=await call('reset_password',{usuario:u});showTempPassword(d.password_temporal)}catch(e){toast(e.message,'error')}};
window.toggleUser=async function(u,a){const ok=await sgtcpConfirm(`${a?'Activar':'Desactivar'} a ${userName(u)}.${!a?'\n\nEl usuario no podrá ingresar mientras permanezca inactivo.':''}`,`${a?'Activar':'Desactivar'} usuario`,a?'Activar':'Desactivar',!a);if(!ok)return;try{await call('actualizar_usuario',{usuario:u,cambios:{activo:a}});await loadAll();toast(`Usuario ${a?'activado':'desactivado'}.`,'success')}catch(e){toast(e.message,'error')}};

function installSafeReassign(){const old=document.getElementById('confirmReassignBtn');if(!old)return;const btn=old.cloneNode(true);old.replaceWith(btn);btn.addEventListener('click',async()=>{if(!manager())return toast('No tiene permisos para reasignar.','error');const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));if(!r)return;if(r.estado==='Terminado')return toast('No se puede reasignar un requerimiento terminado.','error');const target=document.getElementById('reassignExec').value,reason=document.getElementById('reassignReason').value,note=document.getElementById('reassignNote').value.trim();if(!target||target===r.responsable)return toast('Seleccione un ejecutivo distinto.','error');if(!reason)return toast('Seleccione el motivo de reasignación.','error');const motivo=note?`${reason} · ${note}`:reason,targetName=userName(target);const ok=await sgtcpConfirm(`REQ-${String(safeId(r.id)).padStart(3,'0')} · ${r.titulo}\n\nResponsable actual: ${userName(r.responsable)}\nNuevo responsable: ${targetName}\nMotivo: ${motivo}\n\nEl nuevo ejecutivo recibirá una alerta y el movimiento quedará en trazabilidad.`,'Confirmar reasignación','Reasignar');if(!ok)return;try{await call('reasignar_req',{id:r.id,responsable:target,motivo});document.getElementById('reassignDialog').close();document.getElementById('detailDialog')?.close();await loadAll();toast(`✓ Reasignado a ${targetName}. El ejecutivo recibirá una alerta.`,'success')}catch(err){toast(err.message,'error')}});}

function rebind(){ensureActionDialog();const loginForm=document.getElementById('loginForm');if(loginForm)loginForm.onsubmit=window.login;const save=document.getElementById('saveUpdateBtn');if(save)save.onclick=window.saveUpdate;const logoutBtn=document.getElementById('logoutBtn');if(logoutBtn)logoutBtn.onclick=window.logout;const form=document.getElementById('requirementForm');if(form)form.onsubmit=window.createRequirement;installSafeReassign();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(rebind,0));else setTimeout(rebind,0);

document.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.session&&!document.querySelector('dialog[open]')){const last=Number(window.__sgtcpLastVisibilityRefresh||0);if(Date.now()-last>60000){window.__sgtcpLastVisibilityRefresh=Date.now();loadAll().catch(()=>{})}}});
})();