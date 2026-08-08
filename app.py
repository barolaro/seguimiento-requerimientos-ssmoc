from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Sistema de Gestión y Trazabilidad para Compras Públicas · SSMOCC",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"] {display:none!important;}
    #MainMenu, footer {visibility:hidden!important;}
    html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{margin:0!important;padding:0!important;overflow-x:hidden!important;}
    [data-testid="stAppViewContainer"]{overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;}
    .block-container{padding:0!important;margin:0!important;max-width:100%!important;}
    iframe{display:block;width:100%!important;border:0!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

base_dir = Path(__file__).resolve().parent
frontend_dir = base_dir / "frontend"
html_path = frontend_dir / "index.html"
css_path = frontend_dir / "css" / "style.css"
mobile_css_path = frontend_dir / "css" / "mobile.css"
js_path = frontend_dir / "js" / "app.js"
performance_path = frontend_dir / "js" / "performance.js"

required = (html_path, css_path, mobile_css_path, js_path, performance_path)
missing = [str(p.relative_to(base_dir)) for p in required if not p.exists()]
if missing:
    st.error("La interfaz está incompleta. Faltan: " + ", ".join(missing))
    st.stop()

html = html_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")
mobile_css = mobile_css_path.read_text(encoding="utf-8")
javascript = js_path.read_text(encoding="utf-8")
performance_js = performance_path.read_text(encoding="utf-8")

universal_css = r"""
html,body{width:100%;max-width:100%;overflow-x:hidden!important}body{min-height:100%;}
@media (min-width:821px){
  .login-shell{min-height:880px;height:880px;padding:24px;display:flex;align-items:center;justify-content:center;}
  .login-card{width:min(460px,calc(100vw - 56px));max-width:460px;padding:34px;border-radius:24px;}
  .login-card .logo{width:145px;height:145px;margin-bottom:15px}.login-card h1{font-size:26px;line-height:1.12}.login-card>.muted{font-size:12px}.login-card form{gap:13px;margin:22px 0 14px}.login-card input{min-height:44px}.login-card .btn{min-height:44px}
  .topbar{grid-template-columns:minmax(210px,260px) minmax(0,1fr) auto;gap:10px;padding:0 20px}.brand{min-width:0}.brand img{width:42px;height:42px}.brand strong{font-size:17px}.brand span{font-size:8px}
  .topbar nav{min-width:0;overflow:visible!important;flex-wrap:wrap;justify-content:center;align-content:center;gap:2px 3px;scrollbar-width:none}.topbar nav::-webkit-scrollbar{display:none!important}.topbar nav button{padding:8px 9px;font-size:9px;line-height:1.1}
  .account{min-width:max-content}.account b{font-size:10px}.account span{font-size:8px}.account .btn{padding:10px 13px}main{width:min(1480px,calc(100% - 40px));padding:28px 0 56px}.topbar,.topbar nav,.brand,.account{max-width:100%}
}
@media (min-width:821px) and (max-width:1500px){.topbar{grid-template-columns:1fr auto;grid-template-rows:auto auto;padding:8px 18px 6px}.topbar nav{grid-column:1/-1;order:3;justify-content:flex-start;padding:2px 0 0}.topbar nav button{padding:7px 9px;font-size:9px}}
@media (min-width:1900px){main{width:min(1720px,calc(100% - 72px))}.page-head h2{font-size:34px}.kpi strong{font-size:31px}.panel-head h3{font-size:15px}}
.event-pending{opacity:.78;border-style:dashed!important}.event-pending b{color:#087dcc}
"""

DEFAULT_APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbzmYGqzfBTgjcyXtoB7rA6j1uvZ7XGSm_WHAuXWZSD8RLIOiQJd0krdQ_xfOSfJClsKiw/exec"
)
apps_script_url = str(st.secrets.get("apps_script_url", DEFAULT_APPS_SCRIPT_URL)).strip()
config_script = "<script>window.SGTCP_CONFIG=" + json.dumps({"appsScriptUrl": apps_script_url, "version": "3.1.3"}, ensure_ascii=False) + ";</script>"

fast_save_script = r"""
<script>
(function(){
  function writeTraceCache(r,event){
    try{
      const id=Number(r.id);
      let payload=null;
      const mem=state.detailCache && state.detailCache[id];
      if(mem && mem.payload) payload=mem.payload;
      if(!payload){
        try{
          const raw=sessionStorage.getItem('sgtcp_detail_'+id);
          const parsed=raw?JSON.parse(raw):null;
          if(parsed && parsed.payload) payload=parsed.payload;
        }catch(_){}
      }
      if(!payload) payload={requerimiento:{...r},eventos:[]};
      payload.requerimiento={...r};
      payload.eventos=Array.isArray(payload.eventos)?payload.eventos:[];
      payload.eventos.push(event);
      state.detailCache=state.detailCache||{};
      state.detailCache[id]={payload,ts:Date.now()};
      sessionStorage.setItem('sgtcp_detail_'+id,JSON.stringify(state.detailCache[id]));
      return payload;
    }catch(e){console.warn('Cache trazabilidad:',e);return null;}
  }

  function updateTraceCache(id,event){
    try{
      const entry=state.detailCache && state.detailCache[Number(id)];
      if(!entry || !entry.payload || !Array.isArray(entry.payload.eventos)) return;
      const found=entry.payload.eventos.find(x=>x._local_id===event._local_id);
      if(found) found._pending=false;
      entry.ts=Date.now();
      sessionStorage.setItem('sgtcp_detail_'+Number(id),JSON.stringify(entry));
    }catch(e){console.warn('Confirmación cache:',e);}
  }

  function removeTraceCacheEvent(id,event){
    try{
      const entry=state.detailCache && state.detailCache[Number(id)];
      if(!entry || !entry.payload || !Array.isArray(entry.payload.eventos)) return;
      entry.payload.eventos=entry.payload.eventos.filter(x=>x._local_id!==event._local_id);
      entry.ts=Date.now();
      sessionStorage.setItem('sgtcp_detail_'+Number(id),JSON.stringify(entry));
    }catch(e){console.warn('Reversión cache:',e);}
  }

  function installFastSave(){
    const btn=document.getElementById('saveUpdateBtn');
    if(!btn || typeof state==='undefined' || typeof call!=='function') return;

    window.__sgtcpFastSave = async function(){
      const r=state.requirements.find(x=>Number(x.id)===Number(state.selectedId));
      if(!r){ toast('Requerimiento no encontrado.','error'); return; }
      if(String(r.estado)==='Terminado'){ toast('Este requerimiento ya está terminado y está bloqueado.','error'); return; }

      const detail=document.getElementById('detailUpdate').value.trim();
      if(!detail){ toast('Ingrese una actualización para dejar trazabilidad.','error'); return; }

      const cambios={estado:document.getElementById('detailStatus').value,avance:Number(document.getElementById('detailProgress').value)||0};
      if(typeof manager==='function' && manager()){
        cambios.prioridad=document.getElementById('detailPriority').value;
        cambios.descripcion=document.getElementById('detailDescription').value.trim();
      }
      if(cambios.estado==='Terminado') cambios.avance=100;

      if(!window.confirm(`¿Está seguro de guardar esta actualización?\n\nREQ-${String(r.id).padStart(3,'0')} · ${r.titulo}\nEstado: ${r.estado} → ${cambios.estado}\nAvance: ${r.avance||0}% → ${cambios.avance}%\n\nLa acción quedará registrada en la trazabilidad.`)) return;

      const snapshot={...r};
      const now=new Date().toISOString();
      const oldState=r.estado;
      const oldAdvance=Number(r.avance||0);
      const event={
        _local_id:'LOCAL-'+Date.now()+'-'+Math.random().toString(36).slice(2),
        _pending:true,
        fecha:now,
        tipo:oldState!==cambios.estado?'estado':oldAdvance!==cambios.avance?'avance':'actualizacion',
        autor:state.user?.usuario,
        detalle:detail,
        estado_anterior:oldState,
        estado_nuevo:cambios.estado,
        responsable_anterior:r.responsable,
        responsable_nuevo:r.responsable,
        avance_anterior:oldAdvance,
        avance_nuevo:cambios.avance
      };

      // Estado y visualizador se actualizan ANTES de esperar Google Sheets.
      Object.assign(r,cambios,{actualizado:now});
      const tracePayload=writeTraceCache(r,event);
      const timeline=document.getElementById('timeline');
      if(timeline && tracePayload && typeof timelineHtml==='function') timeline.innerHTML=timelineHtml(tracePayload.eventos,r);

      const dialog=document.getElementById('detailDialog');
      if(dialog?.open) setTimeout(()=>dialog.close(),180);
      toast(`REQ-${String(r.id).padStart(3,'0')} actualizado · sincronizando…`,'success');

      requestAnimationFrame(()=>{
        try{
          if(typeof renderRequirements==='function') renderRequirements();
          if(typeof renderRecent==='function') renderRecent();
          if(typeof renderAlerts==='function') renderAlerts();
          if(typeof renderAttention==='function') renderAttention();
          const active=state.requirements.filter(x=>x.estado!=='Terminado');
          const over=active.filter(x=>typeof overdue==='function'&&overdue(x));
          const vals=[['Activos',active.length,'Requerimientos abiertos'],['En ejecución',state.requirements.filter(x=>x.estado==='En ejecución').length,'Gestión activa'],['Pendientes',state.requirements.filter(x=>x.estado==='Pendiente').length,'Por iniciar'],['Terminados',state.requirements.filter(x=>x.estado==='Terminado').length,'Cerrados'],['Vencidos',over.length,'Requieren atención']];
          const k=document.getElementById('kpis');
          if(k) k.innerHTML=vals.map(x=>`<article class="kpi"><span>${x[0]}</span><strong>${x[1]}</strong><small>${x[2]}</small></article>`).join('');
        }catch(e){console.warn('Render rápido:',e);}
      });

      try{
        await call('actualizar_req',{id:r.id,cambios,detalle:detail});
        updateTraceCache(r.id,event);
        toast(`✓ REQ-${String(r.id).padStart(3,'0')} guardado correctamente en Google Sheets.`,'success');
      }catch(e){
        Object.keys(r).forEach(k=>delete r[k]);Object.assign(r,snapshot);
        removeTraceCacheEvent(r.id,event);
        requestAnimationFrame(()=>{try{renderRequirements();renderRecent();renderAlerts();renderAttention();}catch(_){}});
        toast(`No se pudo guardar. El cambio fue revertido: ${e.message}`,'error');
      }
    };

    btn.onclick=null;
    btn.addEventListener('click',window.__sgtcpFastSave);
    btn.dataset.fastSave='3.1.3';
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>setTimeout(installFastSave,0));
  else setTimeout(installFastSave,0);
})();
</script>
"""

html = html.replace('<link rel="stylesheet" href="css/style.css">', f"<style>{css}\n{mobile_css}\n{universal_css}</style>")
html = html.replace('<script src="js/config.js"></script>', config_script)
html = html.replace('<script src="js/app.js"></script>', f"<script>{javascript}</script>")
for tag in ('<script src="js/performance.js?v=3.0.1"></script>','<script src="js/performance.js?v=3.0.2"></script>','<script src="js/performance.js?v=3.1.1"></script>','<script src="js/performance.js"></script>'):
    html = html.replace(tag, f"<script>{performance_js}</script>{fast_save_script}")

html = html.replace('Diseñado y desarrollado por <strong>Bayron Retamal González</strong></small>','SGTCP 3.1.3 · Trazabilidad instantánea<br>Diseñado y desarrollado por <strong>Bayron Retamal González</strong></small>')
for old in ('SGTCP 3.0 · Diseñado y desarrollado','SGTCP 3.0.3 · Diseñado y desarrollado','SGTCP 3.0.4 · Diseñado y desarrollado','SGTCP 3.0.5 · Diseñado y desarrollado','SGTCP 3.0.6 · Diseñado y desarrollado','SGTCP 3.0.7 · Diseñado y desarrollado','SGTCP 3.0.8 · Diseñado y desarrollado','SGTCP 3.0.9 · Diseñado y desarrollado','SGTCP 3.1.0 · Diseñado y desarrollado','SGTCP 3.1.1 · Diseñado y desarrollado','SGTCP 3.1.2 · Diseñado y desarrollado'):
    html = html.replace(old,'SGTCP 3.1.3 · Diseñado y desarrollado')

components.html(html, height=900, scrolling=True)
