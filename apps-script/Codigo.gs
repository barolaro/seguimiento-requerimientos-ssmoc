/**
 * SGTCP 3.0 · Backend Google Apps Script
 * Servicio de Salud Metropolitano Occidente
 */

const APP_VERSION = '3.0.2';
const SESSION_SECONDS = 21600;
const SH_USERS = 'usuarios';
const SH_REQ = 'requerimientos';
const SH_EVENTS = 'eventos';
const SH_AUDIT = 'auditoria';

const USERS_COLS = ['usuario','nombre','email','rol','password_hash','activo','cambiar_password','ultimo_acceso','creado'];
const REQ_COLS = ['id','titulo','descripcion','responsable','estado','prioridad','avance','creado','compromiso','creado_por','actualizado'];
const EVENT_COLS = ['evento_id','requerimiento_id','fecha','tipo','autor','detalle','estado_anterior','estado_nuevo','responsable_anterior','responsable_nuevo','avance_anterior','avance_nuevo'];
const AUDIT_COLS = ['evento_id','fecha','usuario','accion','entidad','entidad_id','detalle'];

function doGet(e) {
  ensureSchema_();
  return json_({ok:true, app:'SGTCP', version:APP_VERSION, mensaje:'Backend operativo'});
}

function doPost(e) {
  let out = {ok:false};
  try {
    ensureSchema_();
    const p = parseBody_(e);
    const action = String(p.action || '').trim();
    if (!action) throw new Error('Falta action.');

    if (action === 'login') return json_(login_(p.usuario, p.password));
    if (action === 'ping') return json_({ok:true, version:APP_VERSION});

    const ctx = requireSession_(p.session);
    switch (action) {
      case 'logout': out = logout_(p.session, ctx); break;
      case 'listar': out = listar_(ctx); break;
      case 'detalle': out = detalle_(ctx, p.id); break;
      case 'crear_req': out = crearReq_(ctx, p.req || {}); break;
      case 'actualizar_req': out = actualizarReq_(ctx, p.id, p.cambios || {}, p.detalle || ''); break;
      case 'reasignar_req': out = reasignarReq_(ctx, p.id, p.responsable, p.motivo || ''); break;
      case 'eliminar_req': out = eliminarReq_(ctx, p.id, p.motivo || ''); break;
      case 'crear_usuario': out = crearUsuario_(ctx, p.usuario || {}); break;
      case 'actualizar_usuario': out = actualizarUsuario_(ctx, p.usuario, p.cambios || {}); break;
      case 'reset_password': out = resetPassword_(ctx, p.usuario); break;
      case 'cambiar_password': out = cambiarPassword_(ctx, p.actual, p.nueva); break;
      case 'auditoria': out = obtenerAuditoria_(ctx, Number(p.limite || 200)); break;
      default: throw new Error('Acción desconocida: ' + action);
    }
  } catch (err) {
    out = {ok:false, error:String(err && err.message ? err.message : err)};
  }
  return json_(out);
}

function configurarProduccion() {
  ensureSchema_();
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('PASSWORD_PEPPER')) props.setProperty('PASSWORD_PEPPER', Utilities.getUuid() + Utilities.getUuid());
  const users = readObjects_(sheet_(SH_USERS, USERS_COLS));
  if (users.length) {
    Logger.log('SGTCP ya tiene usuarios. No se creó un administrador nuevo.');
    return;
  }
  const temp = tempPassword_();
  appendObject_(sheet_(SH_USERS, USERS_COLS), USERS_COLS, {
    usuario:'bayron.admin', nombre:'Bayron Retamal González', email:'', rol:'Administrador',
    password_hash:hashPassword_(temp), activo:'SI', cambiar_password:'SI', ultimo_acceso:'', creado:now_()
  });
  audit_('sistema','crear_administrador','usuario','bayron.admin','Administrador inicial de producción');
  Logger.log('USUARIO INICIAL: bayron.admin');
  Logger.log('CONTRASEÑA TEMPORAL: ' + temp);
}

function ensureSchema_() {
  sheet_(SH_USERS, USERS_COLS); sheet_(SH_REQ, REQ_COLS); sheet_(SH_EVENTS, EVENT_COLS); sheet_(SH_AUDIT, AUDIT_COLS);
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('PASSWORD_PEPPER')) props.setProperty('PASSWORD_PEPPER', Utilities.getUuid() + Utilities.getUuid());
}

function login_(username, password) {
  const user = getUser_(username);
  if (!user || !bool_(user.activo) || hashPassword_(password) !== String(user.password_hash)) {
    audit_(String(username || '').toLowerCase(),'login_fallido','sesion','', 'Credenciales inválidas');
    return {ok:false, error:'Usuario o contraseña incorrectos.'};
  }
  const token = Utilities.getUuid() + Utilities.getUuid();
  CacheService.getScriptCache().put('sess:' + token, JSON.stringify({usuario:user.usuario}), SESSION_SECONDS);
  updateRowByKey_(sheet_(SH_USERS, USERS_COLS), USERS_COLS, 'usuario', user.usuario, {ultimo_acceso:now_()});
  audit_(user.usuario,'login','sesion','', 'Inicio de sesión');
  return {ok:true,session:token,cambiar_password:bool_(user.cambiar_password),usuario:publicUser_(user)};
}
function logout_(token, ctx) {CacheService.getScriptCache().remove('sess:' + token);audit_(ctx.user.usuario,'logout','sesion','', 'Cierre de sesión');return {ok:true};}
function requireSession_(token) {
  if (!token) throw new Error('Sesión requerida.');
  const raw = CacheService.getScriptCache().get('sess:' + token);
  if (!raw) throw new Error('La sesión expiró. Ingrese nuevamente.');
  const payload = JSON.parse(raw), user = getUser_(payload.usuario);
  if (!user || !bool_(user.activo)) throw new Error('Usuario inactivo o inexistente.');
  CacheService.getScriptCache().put('sess:' + token, raw, SESSION_SECONDS);
  return {user:user};
}
function cambiarPassword_(ctx, actual, nueva) {
  if (String(nueva || '').length < 10) throw new Error('La nueva contraseña debe tener al menos 10 caracteres.');
  if (hashPassword_(actual) !== String(ctx.user.password_hash)) throw new Error('La contraseña actual no es correcta.');
  updateRowByKey_(sheet_(SH_USERS, USERS_COLS), USERS_COLS, 'usuario', ctx.user.usuario, {password_hash:hashPassword_(nueva), cambiar_password:'NO'});
  audit_(ctx.user.usuario,'cambiar_password','usuario',ctx.user.usuario,'Contraseña modificada'); return {ok:true};
}

function listar_(ctx) {
  const allReq = readObjects_(sheet_(SH_REQ, REQ_COLS)).map(normalizeReq_);
  const visible = isExecutive_(ctx.user) ? allReq.filter(r => String(r.responsable) === String(ctx.user.usuario)) : allReq;
  const users = isExecutive_(ctx.user) ? [publicUser_(ctx.user)] : readObjects_(sheet_(SH_USERS, USERS_COLS)).map(publicUser_);
  return {ok:true, data:{usuario:publicUser_(ctx.user), usuarios:users, requerimientos:visible}};
}
function detalle_(ctx, id) {
  const req = getReq_(id); authorizeReq_(ctx.user, req);
  const events = readObjects_(sheet_(SH_EVENTS, EVENT_COLS)).filter(e => Number(e.requerimiento_id) === Number(id)).sort((a,b) => String(a.fecha).localeCompare(String(b.fecha)));
  return {ok:true, data:{requerimiento:normalizeReq_(req), eventos:events}};
}
function obtenerAuditoria_(ctx, limit) {requireAdmin_(ctx.user);const rows = readObjects_(sheet_(SH_AUDIT, AUDIT_COLS));return {ok:true, data:rows.slice(-Math.min(Math.max(limit,1),1000)).reverse()};}

function crearReq_(ctx, req) {
  requireManager_(ctx.user);
  const responsible = getUser_(req.responsable);
  if (!responsible || !bool_(responsible.activo) || String(responsible.rol) !== 'Ejecutivo') throw new Error('Responsable inválido.');
  if (!String(req.titulo || '').trim()) throw new Error('El título es obligatorio.');
  const lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    const rows = readObjects_(sheet_(SH_REQ, REQ_COLS)), id = rows.reduce((m,r) => Math.max(m, Number(r.id)||0), 0) + 1, now = now_();
    const item = {id:id,titulo:String(req.titulo).trim(),descripcion:String(req.descripcion || '').trim(),responsable:responsible.usuario,estado:'Pendiente',prioridad:String(req.prioridad || 'Media'),avance:0,creado:now,compromiso:String(req.compromiso || ''),creado_por:ctx.user.usuario,actualizado:now};
    appendObject_(sheet_(SH_REQ, REQ_COLS), REQ_COLS, item);
    event_(id,'asignacion',ctx.user.usuario,'Requerimiento creado y asignado.','','Pendiente','',responsible.usuario,'',0);
    audit_(ctx.user.usuario,'crear_requerimiento','requerimiento',String(id),item.titulo); return {ok:true, id:id};
  } finally {lock.releaseLock();}
}

function actualizarReq_(ctx, id, changes, detail) {
  const req = getReq_(id); authorizeReq_(ctx.user, req);
  if (String(req.estado) === 'Terminado') throw new Error('El requerimiento está terminado y se encuentra bloqueado para nuevas modificaciones.');
  const allowed = isExecutive_(ctx.user) ? ['estado','avance'] : ['estado','prioridad','avance','compromiso','titulo','descripcion'];
  const clean = {}; allowed.forEach(k => { if (changes[k] !== undefined) clean[k] = changes[k]; });
  if (clean.avance !== undefined) clean.avance = Math.max(0, Math.min(100, Number(clean.avance)||0));
  if (String(clean.estado) === 'Terminado') clean.avance = 100;
  clean.actualizado = now_();
  const oldState = req.estado, oldAdvance = Number(req.avance)||0;
  updateRowByKey_(sheet_(SH_REQ, REQ_COLS), REQ_COLS, 'id', Number(id), clean);
  const newState = clean.estado !== undefined ? clean.estado : req.estado, newAdvance = clean.avance !== undefined ? clean.avance : oldAdvance;
  const type = oldState !== newState ? 'estado' : (oldAdvance !== newAdvance ? 'avance' : 'actualizacion');
  event_(id,type,ctx.user.usuario,String(detail || 'Actualización de requerimiento'),oldState,newState,req.responsable,req.responsable,oldAdvance,newAdvance);
  audit_(ctx.user.usuario,'actualizar_requerimiento','requerimiento',String(id),String(detail || type)); return {ok:true};
}

function reasignarReq_(ctx, id, newResponsible, reason) {
  requireManager_(ctx.user); const req = getReq_(id);
  if (String(req.estado) === 'Terminado') throw new Error('No se puede reasignar un requerimiento terminado.');
  const target = getUser_(newResponsible);
  if (!target || !bool_(target.activo) || String(target.rol) !== 'Ejecutivo') throw new Error('Ejecutivo destino inválido.');
  const previous = req.responsable;
  if (String(previous) === String(target.usuario)) throw new Error('El requerimiento ya está asignado a ese ejecutivo.');
  updateRowByKey_(sheet_(SH_REQ, REQ_COLS), REQ_COLS, 'id', Number(id), {responsable:target.usuario, actualizado:now_()});
  event_(id,'reasignacion',ctx.user.usuario,String(reason || 'Reasignación por jefatura'),req.estado,req.estado,previous,target.usuario,req.avance,req.avance);
  audit_(ctx.user.usuario,'reasignar_requerimiento','requerimiento',String(id),previous + ' → ' + target.usuario); return {ok:true};
}

function eliminarReq_(ctx, id, reason) {
  requireAdmin_(ctx.user);
  const motivo = String(reason || '').trim();
  if (motivo.length < 5) throw new Error('Debe indicar un motivo de eliminación.');
  const req = getReq_(id);
  const snapshot = {id:req.id,titulo:req.titulo,descripcion:req.descripcion,responsable:req.responsable,estado:req.estado,prioridad:req.prioridad,avance:req.avance,creado:req.creado,compromiso:req.compromiso,creado_por:req.creado_por,actualizado:req.actualizado};
  audit_(ctx.user.usuario,'eliminar_requerimiento','requerimiento',String(id),JSON.stringify({motivo:motivo, snapshot:snapshot}));
  deleteRowByKey_(sheet_(SH_REQ, REQ_COLS), REQ_COLS, 'id', Number(id));
  return {ok:true};
}

function crearUsuario_(ctx, u) {
  requireAdmin_(ctx.user); const username = String(u.usuario || '').toLowerCase().trim();
  if (!username || getUser_(username)) throw new Error('El usuario ya existe o es inválido.');
  if (!['Administrador','Jefa de Unidad','Jefe de Departamento','Ejecutivo'].includes(String(u.rol))) throw new Error('Rol inválido.');
  const temp = String(u.password || tempPassword_()); if (temp.length < 10) throw new Error('La contraseña inicial debe tener al menos 10 caracteres.');
  appendObject_(sheet_(SH_USERS, USERS_COLS), USERS_COLS, {usuario:username,nombre:String(u.nombre || '').trim(),email:String(u.email || '').trim(),rol:String(u.rol),password_hash:hashPassword_(temp),activo:'SI',cambiar_password:'SI',ultimo_acceso:'',creado:now_()});
  audit_(ctx.user.usuario,'crear_usuario','usuario',username,String(u.rol)); return {ok:true, usuario:username, password_temporal:u.password ? undefined : temp};
}
function actualizarUsuario_(ctx, username, changes) {requireAdmin_(ctx.user);const user = getUser_(username);if (!user) throw new Error('Usuario no encontrado.');const clean = {};['nombre','email','rol','activo'].forEach(k => { if (changes[k] !== undefined) clean[k] = changes[k]; });if (clean.activo !== undefined) clean.activo = bool_(clean.activo) ? 'SI' : 'NO';updateRowByKey_(sheet_(SH_USERS, USERS_COLS), USERS_COLS, 'usuario', user.usuario, clean);audit_(ctx.user.usuario,'actualizar_usuario','usuario',user.usuario,JSON.stringify(clean));return {ok:true};}
function resetPassword_(ctx, username) {requireAdmin_(ctx.user);const user = getUser_(username);if (!user) throw new Error('Usuario no encontrado.');const temp = tempPassword_();updateRowByKey_(sheet_(SH_USERS, USERS_COLS), USERS_COLS, 'usuario', user.usuario, {password_hash:hashPassword_(temp), cambiar_password:'SI'});audit_(ctx.user.usuario,'reset_password','usuario',user.usuario,'Contraseña temporal generada');return {ok:true, password_temporal:temp};}

function parseBody_(e) {if (e && e.postData && e.postData.contents) return JSON.parse(e.postData.contents);return (e && e.parameter) || {};}
function ss_(){ return SpreadsheetApp.getActiveSpreadsheet(); }
function sheet_(name, cols) {let sh = ss_().getSheetByName(name);if (!sh) sh = ss_().insertSheet(name);if (sh.getLastRow() === 0) sh.appendRow(cols);else {const head = sh.getRange(1,1,1,Math.max(sh.getLastColumn(),cols.length)).getValues()[0].slice(0,cols.length);if (head.join('|') !== cols.join('|')) sh.getRange(1,1,1,cols.length).setValues([cols]);}return sh;}
function readObjects_(sh) {const values = sh.getDataRange().getValues(); if (values.length < 2) return [];const head = values[0];return values.slice(1).filter(r => r.some(v => v !== '')).map(r => { const o={}; head.forEach((h,i)=>o[h]=r[i]); return o; });}
function appendObject_(sh, cols, obj){ sh.appendRow(cols.map(c => obj[c] !== undefined ? obj[c] : '')); }
function updateRowByKey_(sh, cols, key, value, changes) {const values = sh.getDataRange().getValues(), keyIdx = cols.indexOf(key);for (let i=1;i<values.length;i++) {if (String(values[i][keyIdx]) === String(value)) {Object.keys(changes).forEach(k => { const idx=cols.indexOf(k); if(idx>=0) values[i][idx]=changes[k]; });sh.getRange(i+1,1,1,cols.length).setValues([values[i].slice(0,cols.length)]); return;}}throw new Error('Registro no encontrado: ' + value);}
function deleteRowByKey_(sh, cols, key, value) {const values = sh.getDataRange().getValues(), keyIdx = cols.indexOf(key);for (let i=1;i<values.length;i++) {if (String(values[i][keyIdx]) === String(value)) {sh.deleteRow(i+1); return;}}throw new Error('Registro no encontrado: ' + value);}
function getUser_(username){ const u=String(username||'').toLowerCase().trim(); return readObjects_(sheet_(SH_USERS,USERS_COLS)).find(x=>String(x.usuario).toLowerCase()===u) || null; }
function getReq_(id){ const r=readObjects_(sheet_(SH_REQ,REQ_COLS)).find(x=>Number(x.id)===Number(id)); if(!r) throw new Error('Requerimiento no encontrado.'); return normalizeReq_(r); }
function normalizeReq_(r){ r.id=Number(r.id)||0; r.avance=Number(r.avance)||0; return r; }
function publicUser_(u){ return {usuario:u.usuario,nombre:u.nombre,email:u.email,rol:u.rol,activo:bool_(u.activo),cambiar_password:bool_(u.cambiar_password),ultimo_acceso:u.ultimo_acceso}; }
function bool_(v){ return !(v===false || v===0 || String(v).toUpperCase()==='NO' || String(v).toUpperCase()==='FALSE' || v===''); }
function isExecutive_(u){ return String(u.rol)==='Ejecutivo'; }
function isManager_(u){ return ['Administrador','Jefa de Unidad','Jefe de Departamento'].includes(String(u.rol)); }
function requireManager_(u){ if(!isManager_(u)) throw new Error('Permiso insuficiente para esta acción.'); }
function requireAdmin_(u){ if(String(u.rol)!=='Administrador') throw new Error('Esta acción requiere perfil Administrador.'); }
function authorizeReq_(u,r){ if(isExecutive_(u) && String(r.responsable)!==String(u.usuario)) throw new Error('No tiene acceso a este requerimiento.'); }
function now_(){ return Utilities.formatDate(new Date(), Session.getScriptTimeZone() || 'America/Santiago', "yyyy-MM-dd'T'HH:mm:ssXXX"); }
function hashPassword_(p){ const pepper=PropertiesService.getScriptProperties().getProperty('PASSWORD_PEPPER') || ''; const bytes=Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,String(p||'')+'|'+pepper); return bytes.map(b=>('0'+(b&255).toString(16)).slice(-2)).join(''); }
function tempPassword_(){ return 'Sg!' + Utilities.getUuid().replace(/-/g,'').slice(0,12) + '#26'; }
function event_(reqId,type,author,detail,oldState,newState,oldResp,newResp,oldAdvance,newAdvance){appendObject_(sheet_(SH_EVENTS,EVENT_COLS),EVENT_COLS,{evento_id:'EV-'+new Date().getTime()+'-'+Math.floor(Math.random()*1000),requerimiento_id:Number(reqId),fecha:now_(),tipo:type,autor:author,detalle:detail,estado_anterior:oldState||'',estado_nuevo:newState||'',responsable_anterior:oldResp||'',responsable_nuevo:newResp||'',avance_anterior:oldAdvance===''?'':Number(oldAdvance||0),avance_nuevo:newAdvance===''?'':Number(newAdvance||0)});}
function audit_(user,action,entity,entityId,detail){ appendObject_(sheet_(SH_AUDIT,AUDIT_COLS),AUDIT_COLS,{evento_id:'AU-'+new Date().getTime()+'-'+Math.floor(Math.random()*1000),fecha:now_(),usuario:user||'',accion:action,entidad:entity,entidad_id:entityId||'',detalle:detail||''}); }
function json_(obj){ return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
