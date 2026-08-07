const state={session:localStorage.getItem('sgtcp_session')||'',user:null,requirements:[],users:[],charts:{}};
const WEBAPP=(window.SGTCP_CONFIG?.appsScriptUrl||'').trim();
const $=id=>document.getElementById(id);
const managerRoles=new Set(['Administrador','Jefa de Unidad','Jefe de Departamento']);

async function call(action,payload={}){
  if(!WEBAPP) throw new Error('Backend de producción pendiente de configuración.');
  const res=await fetch(WEBAPP,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify({action,session:state.session,...payload}),redirect:'follow'});
  const text=await res.text();
  let data;try{data=JSON.parse(text)}catch{throw new Error('El backend respondió en un formato no válido. Revise la implementación de Apps Script.');}
  if(!data.ok) throw new Error(data.error||'No fue posible completar la operación.');
  return data;
}
function toast(message){const n=$('toast');n.textContent=message;n.classList.remove('hidden');setTimeout(()=>n.classList.add('hidden'),2800)}
function setView(name){document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));$(`${name}View`)?.classList.remove('hidden');document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===name));}
function badge(value){const key=value==='Terminado'?'green':value==='En ejecución'?'blue':value==='Pendiente'?'orange':'red';return `<span class="badge ${key}">${value||'Sin estado'}</span>`}
function formatDate(v){if(!v)return '—';const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short'})}
function isOverdue(r){return r.compromiso&&r.estado!=='Terminado'&&new Date(r.compromiso)<new Date(new Date().toDateString())}
function userName(username){return state.users.find(u=>u.usuario===username)?.nombre||username||'Sin responsable'}

async function login(e){
  e.preventDefault();$('loginError').textContent='';
  const button=e.submitter||e.target.querySelector('button[type="submit"]');const original=button?.textContent;
  if(button){button.disabled=true;button.textContent='Ingresando…';}
  try{
    const data=await call('login',{usuario:$('loginUser').value.trim(),password:$('loginPassword').value});
    state.session=data.session;state.user=data.usuario;localStorage.setItem('sgtcp_session',state.session);
    if(data.cambiar_password){
      const nueva=window.prompt('Primer ingreso: cree una nueva contraseña de al menos 10 caracteres.');
      if(nueva){await call('cambiar_password',{actual:$('loginPassword').value,nueva});toast('Contraseña actualizada correctamente');}
    }
    showApp();await loadAll();
  }catch(err){$('loginError').textContent=err.message;}
  finally{if(button){button.disabled=false;button.textContent=original;}}
}
async function restore(){if(!state.session)return;try{await loadAll();showApp();}catch{clearSession();}}
function clearSession(){state.session='';state.user=null;state.requirements=[];state.users=[];localStorage.removeItem('sgtcp_session');$('appView').classList.add('hidden');$('loginView').classList.remove('hidden');$('loginPassword').value='';}
async function logout(){try{if(state.session)await call('logout')}catch{}clearSession()}
function showApp(){
  $('loginView').classList.add('hidden');$('appView').classList.remove('hidden');
  $('accountName').textContent=state.user?.nombre||'';$('accountRole').textContent=state.user?.rol||'';
  const manager=managerRoles.has(state.user?.rol);const admin=state.user?.rol==='Administrador';
  $('usersNav').classList.toggle('hidden',!manager);
  $('newReqBtn').classList.toggle('hidden',!manager);$('newReqBtn2').classList.toggle('hidden',!manager);
  $('newUserBtn')?.classList.toggle('hidden',!admin);
}
async function loadAll(){
  const data=await call('listar');
  state.user=data.data.usuario;state.users=data.data.usuarios||[];state.requirements=data.data.requerimientos||[];
  renderUsers();fillResponsible();renderDashboard();renderRequirements();
}

function renderDashboard(){
  const rs=state.requirements,active=rs.filter(r=>r.estado!=='Terminado');
  const values=[['Activos',active.length,'Requerimientos abiertos'],['En ejecución',rs.filter(r=>r.estado==='En ejecución').length,'Gestión activa'],['Pendientes',rs.filter(r=>r.estado==='Pendiente').length,'Por iniciar'],['Terminados',rs.filter(r=>r.estado==='Terminado').length,'Cerrados'],['Vencidos',rs.filter(isOverdue).length,'Requieren atención']];
  $('kpis').innerHTML=values.map(x=>`<article class="kpi"><span>${x[0]}</span><strong>${x[1]}</strong><small>${x[2]}</small></article>`).join('');
  renderCharts();
  const attention=active.filter(r=>isOverdue(r)||r.prioridad==='Alta').slice(0,8);
  $('attentionList').innerHTML=attention.length?attention.map(r=>`<div class="attention-item"><b>REQ-${String(r.id).padStart(3,'0')}</b><div><b>${r.titulo}</b><span>${userName(r.responsable)} · ${r.prioridad}</span></div>${isOverdue(r)?'<span class="badge red">Vencido</span>':badge(r.estado)}</div>`).join(''):'<p class="muted">No existen requerimientos críticos.</p>';
}
function renderCharts(){
  const labels=['Pendiente','En ejecución','En espera','Terminado'];const data=labels.map(s=>state.requirements.filter(r=>r.estado===s).length);
  state.charts.state?.destroy();state.charts.state=new Chart($('stateChart'),{type:'doughnut',data:{labels,datasets:[{data,backgroundColor:['#ff8a1f','#087dcc','#805ad5','#20a548'],borderWidth:0}]},options:{plugins:{legend:{position:'bottom'}},cutout:'68%'}});
  const executives=state.users.filter(u=>u.rol==='Ejecutivo');const counts=executives.map(u=>state.requirements.filter(r=>r.responsable===u.usuario&&r.estado!=='Terminado').length);
  state.charts.work?.destroy();state.charts.work=new Chart($('workloadChart'),{type:'bar',data:{labels:executives.map(u=>u.nombre.split(' ').slice(0,2).join(' ')),datasets:[{label:'Activos',data:counts,backgroundColor:'#087dcc',borderRadius:8}]},options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,ticks:{precision:0}},y:{grid:{display:false}}}}});
}
function renderRequirements(){
  const q=$('searchInput')?.value.toLowerCase()||'',f=$('stateFilter')?.value||'';
  const rows=state.requirements.filter(r=>(!f||r.estado===f)&&(!q||`${r.id} ${r.titulo} ${r.descripcion} ${userName(r.responsable)}`.toLowerCase().includes(q)));
  $('requirementsBody').innerHTML=rows.map(r=>`<tr data-id="${r.id}"><td>REQ-${String(r.id).padStart(3,'0')}</td><td><b>${r.titulo}</b><br><span class="muted">${r.descripcion||''}</span></td><td>${userName(r.responsable)}</td><td>${badge(r.estado)}</td><td>${r.prioridad}</td><td><div class="progress"><i style="width:${r.avance||0}%"></i></div><small>${r.avance||0}%</small></td><td>${formatDate(r.actualizado)}</td></tr>`).join('');
}
function renderUsers(){if(!$('usersBody'))return;$('usersBody').innerHTML=state.users.map(u=>`<tr><td><b>${u.nombre}</b></td><td>${u.usuario}</td><td>${u.rol}</td><td>${u.email||'—'}</td><td>${u.activo?'<span class="badge green">Activo</span>':'<span class="badge red">Inactivo</span>'}</td></tr>`).join('')}
function fillResponsible(){const users=state.users.filter(u=>u.rol==='Ejecutivo'&&u.activo);$('reqResponsible').innerHTML=users.map(u=>`<option value="${u.usuario}">${u.nombre}</option>`).join('')}
async function createRequirement(e){
  e.preventDefault();
  try{await call('crear_req',{req:{titulo:$('reqTitle').value.trim(),descripcion:$('reqDescription').value.trim(),responsable:$('reqResponsible').value,prioridad:$('reqPriority').value,compromiso:$('reqDue').value}});$('requirementDialog').close();e.target.reset();await loadAll();toast('Requerimiento registrado y trazabilidad iniciada');}catch(err){toast(err.message)}
}
async function createUser(e){
  e.preventDefault();
  try{const data=await call('crear_usuario',{usuario:{nombre:$('userName').value.trim(),usuario:$('userLogin').value.trim(),email:$('userEmail').value.trim(),rol:$('userRole').value,password:$('userPassword').value}});$('userDialog').close();e.target.reset();await loadAll();toast(data.password_temporal?`Usuario creado. Clave temporal: ${data.password_temporal}`:'Usuario creado correctamente');}catch(err){toast(err.message)}
}

document.addEventListener('DOMContentLoaded',()=>{
  $('loginForm').addEventListener('submit',login);$('logoutBtn').addEventListener('click',logout);
  document.querySelectorAll('[data-view]').forEach(x=>x.addEventListener('click',()=>setView(x.dataset.view)));
  [$('newReqBtn'),$('newReqBtn2')].forEach(x=>x?.addEventListener('click',()=>$('requirementDialog').showModal()));
  $('newUserBtn')?.addEventListener('click',()=>$('userDialog').showModal());
  document.querySelectorAll('[data-close]').forEach(x=>x.addEventListener('click',()=>$(x.dataset.close).close()));
  $('requirementForm').addEventListener('submit',createRequirement);$('userForm').addEventListener('submit',createUser);
  $('searchInput').addEventListener('input',renderRequirements);$('stateFilter').addEventListener('change',renderRequirements);
  if(!WEBAPP)$('loginError').innerHTML='<div class="status-note"><b>SGTCP 3.0 preparado.</b> Falta configurar <b>apps_script_url</b> con la URL /exec de Google Apps Script.</div>';
  restore();
});