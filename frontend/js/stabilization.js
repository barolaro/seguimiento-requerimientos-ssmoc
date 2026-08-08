/* SGTCP 3.2 · Capa de estabilización
 * Objetivo: que una actualización se vea inmediatamente y la persistencia
 * en Google Apps Script ocurra sin bloquear la experiencia del ejecutivo.
 */
(function () {
  'use strict';
  if (typeof state === 'undefined') return;

  const pendingUpdates = new Map();

  function localEvent(r, detail, changes) {
    const oldState = r.estado;
    const oldAdvance = Number(r.avance || 0);
    const newState = changes.estado ?? oldState;
    const newAdvance = Number(changes.avance ?? oldAdvance);
    return {
      fecha: new Date().toISOString(),
      tipo: oldState !== newState ? 'estado' : (oldAdvance !== newAdvance ? 'avance' : 'actualizacion'),
      autor: state.user?.usuario,
      detalle: detail,
      estado_anterior: oldState,
      estado_nuevo: newState,
      responsable_anterior: r.responsable,
      responsable_nuevo: r.responsable,
      avance_anterior: oldAdvance,
      avance_nuevo: newAdvance,
      _pending: true
    };
  }

  function renderPendingTimeline(ev, r) {
    const box = document.createElement('div');
    box.className = 'event event-pending';
    const title = document.createElement('b');
    title.textContent = `${ev.tipo || 'Actualización'} · ${ev.estado_nuevo || r.estado} · Sincronizando…`;
    const p = document.createElement('p');
    p.textContent = ev.detalle || '';
    const small = document.createElement('small');
    small.textContent = `${fmt(ev.fecha)} · ${userName(ev.autor)}`;
    box.append(title, p, small);
    return box;
  }

  async function refreshDetailInBackground(id) {
    try {
      const d = await call('detalle', { id });
      const payload = d.data || {};
      if (state.detailCache) state.detailCache[id] = { payload, ts: Date.now() };
      try { sessionStorage.setItem(`sgtcp_detail_${id}`, JSON.stringify({ payload, ts: Date.now() })); } catch (_) {}
      if (Number(state.selectedId) === Number(id) && document.getElementById('detailDialog')?.open) {
        // Reabrir utiliza la caché recién actualizada y evita una segunda espera visible.
        await openDetail(Number(id));
      }
    } catch (_) {
      // La actualización principal ya fue confirmada; un fallo de refresco no debe
      // convertir un guardado correcto en un error para el usuario.
    }
  }

  window.saveUpdate = async function saveUpdateFast() {
    const r = state.requirements.find(x => Number(x.id) === Number(state.selectedId));
    if (!r) return toast('Requerimiento no encontrado.', 'error');

    const detail = document.getElementById('detailUpdate')?.value.trim() || '';
    if (!detail) return toast('Ingrese una actualización para dejar trazabilidad.', 'error');
    if (pendingUpdates.has(Number(r.id))) return toast('Este requerimiento ya se está sincronizando.', 'info');

    const changes = {
      estado: document.getElementById('detailStatus').value,
      avance: Number(document.getElementById('detailProgress').value) || 0
    };
    if (typeof manager === 'function' && manager()) {
      changes.prioridad = document.getElementById('detailPriority').value;
      changes.descripcion = document.getElementById('detailDescription').value.trim();
    }
    if (changes.estado === 'Terminado') changes.avance = 100;

    const snapshot = { ...r };
    const ev = localEvent(r, detail, changes);
    const now = ev.fecha;

    // OPTIMISTIC UI: reflejar el cambio antes de esperar Google Apps Script.
    Object.assign(r, changes, { actualizado: now });
    const timeline = document.getElementById('timeline');
    if (timeline) timeline.prepend(renderPendingTimeline(ev, r));
    document.getElementById('detailUpdate').value = '';
    if (typeof renderRequirements === 'function') renderRequirements();
    if (typeof renderDashboard === 'function') renderDashboard();
    if (typeof renderAlerts === 'function') renderAlerts();

    const btn = document.getElementById('saveUpdateBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Sincronizando…'; }
    toast('Actualización registrada en pantalla · sincronizando…', 'success');

    const task = call('actualizar_req', { id: r.id, cambios: changes, detalle: detail });
    pendingUpdates.set(Number(r.id), task);

    try {
      await task;
      ev._pending = false;
      toast('✓ Actualización guardada y trazabilidad sincronizada.', 'success');
      await refreshDetailInBackground(r.id);
    } catch (err) {
      Object.keys(r).forEach(k => delete r[k]);
      Object.assign(r, snapshot);
      if (typeof renderAll === 'function') renderAll();
      toast(`No se pudo guardar. El cambio visual fue revertido: ${err.message}`, 'error');
    } finally {
      pendingUpdates.delete(Number(r.id));
      if (btn) { btn.disabled = false; btn.textContent = 'Guardar actualización'; }
    }
  };

  // El listener original de app.js invoca la variable global saveUpdate;
  // esta asignación garantiza que use la versión optimizada anterior.
  const saveBtn = document.getElementById('saveUpdateBtn');
  if (saveBtn) saveBtn.onclick = window.saveUpdate;

  // Refresco liviano cuando el usuario vuelve a la pestaña después de trabajar
  // en otra ventana. Evita mantener datos antiguos durante toda la sesión.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && state.session && typeof loadAll === 'function') {
      const last = Number(window.__sgtcpLastVisibilityRefresh || 0);
      if (Date.now() - last > 60000) {
        window.__sgtcpLastVisibilityRefresh = Date.now();
        loadAll().catch(() => {});
      }
    }
  });
})();