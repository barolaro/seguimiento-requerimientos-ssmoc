/* SGTCP 3.2 · Sincronización inteligente */
(function(){
'use strict';
if(typeof state==='undefined'||typeof call!=='function')return;

const SYNC_INTERVAL=45000;
const RESUME_DEBOUNCE=3500;
let timer=null;
let syncing=false;
let lastSync=0;
let initialized=false;

function reqKey(r){return [Number(r.id)||0,String(r.responsable||''),String(r.estado||''),Number(r.avance)||0,String(r.pr