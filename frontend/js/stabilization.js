/* SGTCP 3.2 · Estabilización UX y seguridad */
(function(){
'use strict';
if(typeof state==='undefined')return;
const pendingUpdates=new Map();

// Escape central para todo contenido que en etapas siguientes deba entrar a innerHTML.
window.esc=function(v=''){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));};

function ensureActionDialog(){
 if(document.getElementById('sgtcpActionDialog'))return;
 const d=document.createElement('dialog');d.id='sgtcpActionDialog';d.innerHTML='<div class="dialog-shell"><div class="dialog-head"><div><p class="eyebrow">Confirmación</p><h3 id="sgtcpActionTitle">Confirmar acción</h3></div></div><div id="sgtcpActionMessage" style="white-space:pre-line;line-height:1.55;margin:12px 0 18px"></div><label id="sgtcpPromptWrap" class="hidden">Motivo<input id="sgtcpPromptInput" autocomplete="off"></label><div class="dialog-actions"><button id="sgtcpActionCancel" class="btn ghost" type="button">Cancelar</button><button id="sgtcpActionOk" class="btn primary" type="button">Confirmar</button></div></div>';
 document.body.appendChild(d);
}
function actionDialog({title='Confirmar acción',message='',prompt=false,initial='',ok='Confirmar',danger=false}={}){
 ensureActionDialog();const d=document.getElementById('sgtcpActionDialog'),t=document.getElementById('sgtcpActionTitle'),m=document.getElementById('sgtcpActionMessage'),w=document.getElementById('sgtcpPromptWrap'),i=document.getElementById('sgtcpPromptInput'),yes=document.getElementById('sgtcpActionOk'),no=document.getElementById('sgtcpActionCancel');
 t.textContent=title;m.textContent=message;w.classList.toggle('hidden',!prompt);i.value=initial;yes.textContent=ok;yes.className=danger?'btn danger':'btn primary';
 return new Promise(resolve=>{const done=v=>{yes.onclick=null;no.onclick=null;d.oncancel=null;d.close();resolve(v)};yes.onclick=()=>done(prompt?i.value:true);no.onclick=()=>done(prompt?null:false);d.oncancel=e=>{e.preventDefault();done(prompt?null:false)};d.showModal();if(prompt)setTimeout(()=>i.focus(),30)});
}
window.sgtcpConfirm=(message,title='Confirmar acción',ok='Confirmar',danger=false)=>actionDialog({title,message,ok,danger});
window.sgtcpPrompt=(message,initial='',title='Información requerida')=>actionDialog({title,message,prompt:true,initial,ok:'Continuar'});

function localEvent(r,detail,changes){const oldState=r.estado,oldAdvance=Number(r.avance||0),newState=changes.estado??oldState,newAdvance=Number(changes.avance??oldAdvance);return{fecha:new Date().toISOString(),tipo:oldState!==newState?'estado':oldAdvance!==newAdvance?'avance':'actualizacion',autor:state.user?.usuario,detalle,estado_anterior:oldState,estado_nuevo:newState,responsable_anterior:r.responsable,responsable_nuevo:r.responsable,avance_anterior:oldAdvance,avance_nuevo:newAdvance,_pending:true};}
function renderPendingTimeline(ev,r){const box=document.createElement('div');box.className='event event-pending';const b=document.createElement('b');b.textContent=`${ev.tipo||'Actualización'} · ${ev.estado_nuevo||r.estado} · Sincronizando…`;const p=document.createElement('p');p.textContent=ev.detalle||'';const s=document.createElement('small');s.textContent=`${fmt(ev.fecha)} · ${userName(ev.autor)}`;box.append(b,p,s);return box;}
async function refreshDetail(id){try{const d=await call('detalle',{id}),payload=d.data||{};if(state.detailCache)state.detailCache[id]={payload,ts:Date.now()};try{sessionStorage.setItem(`sgtcp_detail_${id}`,JSON.stringify({payload,ts:Date.now()}))}catch(_){}}catch(_){}}

window.saveUpdate=async function(){
 const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));if(!r)return toast('Requerimiento no encontrado.','error');if(String(r.estado)==='Terminado')return toast('El requerimiento terminado está bloqueado.','error');
 const detail=document.getElementById('detailUpdate')?.value.trim()||'';if(!detail)return toast('Ingrese una actualización para dejar trazabilidad.','error');if(pendingUpdates.has(Number(r.id)))return toast('Este requerimiento ya se está sincronizando.','info');
 const changes={estado:document.getElementById('detailStatus').value,avance:Number(document.getElementById('detailProgress').value)||0};if(manager()){changes.prioridad=document.getElementById('detailPriority').value;changes.descripcion=document.getElementById('detailDescription').value.trim()}if(changes.estado==='Terminado')changes.avance=100;
 const ok=await sgtcpConfirm(`REQ-${String(r.id).padStart(3,'0')} · ${r.titulo}\n\nEstado: ${r.estado} → ${changes.estado}\nAvance: ${r.avance||0}% → ${changes.avance}%\n\nLa actualización quedará registrada permanentemente en la trazabilidad.`,'Guardar actualización','Guardar');if(!ok)return;
 const snapshot={...r},ev=localEvent(r,detail,changes);Object.assign(r,changes,{actualizado:ev.fecha});const timeline=document.getElementById('timeline');if(timeline)timeline.prepend(renderPendingTimeline(ev,r));document.getElementById('detailUpdate').value='';renderRequirements();renderRecent?.();renderAlerts();renderAttention?.();
 const dlg=document.getElementById('detailDialog');if(dlg?.open)dlg.close();toast('Actualización visible · sincronizando con Google Sheets…','success');
 const task=call('actualizar_req',{id:r.id,cambios:changes,detalle:detail});pendingUpdates.set(Number(r.id),task);try{await task;ev._pending=false;await refreshDetail(r.id);toast('✓ Actualización guardada y trazabilidad sincronizada.','success')}catch(err){Object.keys(r).forEach(k=>delete r[k]);Object.assign(r,snapshot);renderAll();toast(`No se pudo guardar. El cambio fue revertido: ${err.message}`,'error')}finally{pendingUpdates.delete(Number(r.id));}
};

window.logout=async function(){const ok=await sgtcpConfirm('La sesión actual se cerrará y volverá a la pantalla de ingreso.','Cerrar sesión','Cerrar sesión');if(!ok)return;const b=document.getElementById('logoutBtn');if(b){b.disabled=true;b.textContent='Cerrando…'}try{if(state.session)await call('logout')}catch(_){}finally{clearSession();if(b){b.disabled=false;b.textContent='Cerrar sesión'}}};

// Creación con confirmación propia; evita confirm() nativo dentro del iframe.
window.createRequirement=async function(e){e.preventDefault();const req={titulo:document.getElementById('reqTitle').value.trim(),descripcion:document.getElementById('reqDescription').value.trim(),responsable:document.getElementById('reqResponsible').value,prioridad:document.getElementById('reqPriority').value,compromiso:document.getElementById('reqDue').value};if(!req.responsable)return toast('Seleccione un responsable.','error');const ok=await sgtcpConfirm(`${req.titulo}\n\nResponsable: ${userName(req.responsable)}\nPrioridad: ${req.prioridad}${req.compromiso?'\nCompromiso: '+req.compromiso:''}\n\nEl ejecutivo recibirá el requerimiento en su cartera.`,'Registrar requerimiento','Registrar');if(!ok)return;const b=e.submitter;if(b)b.disabled=true;try{await call('crear_req',{req});document.getElementById('requirementDialog').close();e.target.reset();await loadAll();toast('✓ Requerimiento creado y asignado correctamente.','success')}catch(err){toast(err.message,'error')}finally{if(b)b.disabled=false}};

window.resetPassword=async function(u){const ok=await sgtcpConfirm(`Se generará una nueva contraseña temporal para ${userName(u)}.`,'Restablecer contraseña','Restablecer',true);if(!ok)return;try{const d=await call('reset_password',{usuario:u});showTempPassword(d.password_temporal)}catch(e){toast(e.message,'error')}};
window.toggleUser=async function(u,a){const ok=await sgtcpConfirm(`${a?'Activar':'Desactivar'} a ${userName(u)}.${!a?'\n\nEl usuario no podrá ingresar mientras permanezca inactivo.':''}`,`${a?'Activar':'Desactivar'} usuario`,a?'Activar':'Desactivar',!a);if(!ok)return;try{await call('actualizar_usuario',{usuario:u,cambios:{activo:a}});await loadAll();toast(`Usuario ${a?'activado':'desactivado'}.`,'success')}catch(e){toast(e.message,'error')}};

// Reasignación: anulamos el listener anterior antes de que llegue al confirm nativo.
function installSafeReassign(){const old=document.getElementById('confirmReassignBtn');if(!old)return;const btn=old.cloneNode(true);old.replaceWith(btn);btn.addEventListener('click',async()=>{if(!manager())return toast('No tiene permisos para reasignar.','error');const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));if(!r)return;if(r.estado==='Terminado')return toast('No se puede reasignar un requerimiento terminado.','error');const target=document.getElementById('reassignExec').value,reason=document.getElementById('reassignReason').value,note=document.getElementById('reassignNote').value.trim();if(!target||target===r.responsable)return toast('Seleccione un ejecutivo distinto.','error');if(!reason)return toast('Seleccione el motivo de reasignación.','error');const motivo=note?`${reason} · ${note}`:reason,targetName=userName(target);const ok=await sgtcpConfirm(`REQ-${String(r.id).padStart(3,'0')} · ${r.titulo}\n\nResponsable actual: ${userName(r.responsable)}\nNuevo responsable: ${targetName}\nMotivo: ${motivo}\n\nEl nuevo ejecutivo recibirá una alerta y el movimiento quedará en trazabilidad.`,'Confirmar reasignación','Reasignar');if(!ok)return;try{await call('reasignar_req',{id:r.id,responsable:target,motivo});document.getElementById('reassignDialog').close();document.getElementById('detailDialog')?.close();await loadAll();toast(`✓ Reasignado a ${targetName}. El ejecutivo recibirá una alerta.`,'success')}catch(err){toast(err.message,'error')}});}

function rebind(){ensureActionDialog();const save=document.getElementById('saveUpdateBtn');if(save)save.onclick=window.saveUpdate;const logoutBtn=document.getElementById('logoutBtn');if(logoutBtn)logoutBtn.onclick=window.logout;const form=document.getElementById('requirementForm');if(form)form.onsubmit=window.createRequirement;installSafeReassign();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(rebind,0));else setTimeout(rebind,0);

// Refresco liviano, nunca mientras hay una edición abierta.
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.session&&!document.querySelector('dialog[open]')){const last=Number(window.__sgtcpLastVisibilityRefresh||0);if(Date.now()-last>60000){window.__sgtcpLastVisibilityRefresh=Date.now();loadAll().catch(()=>{})}}});
})();