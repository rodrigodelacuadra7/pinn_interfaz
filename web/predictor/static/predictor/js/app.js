/**
 * app.js — Orquesta UI, fetch de API, actualiza paneles.
 */
(function () {
  'use strict';

  // ---- Estado global ----
  let state = null;   // resultado de la última predicción
  let activeMode = 0;
  let isPlaying = true;

  // ---- Inicialización ----
  document.addEventListener('DOMContentLoaded', function () {
    Building3D.init('building-canvas');
    _setupSegButtons();

    const zonaDesc = {
      '1': 'A₀ = 0.20g · Costa interior',
      '2': 'A₀ = 0.30g · Cordillera',
      '3': 'A₀ = 0.40g · Costa norte',
    };
    const sueloDesc = {
      'A': 'Roca · T₀=0.15s · S=0.90',
      'B': 'Suelo denso · T₀=0.30s · S=1.00',
      'C': 'Suelo firme · T₀=0.40s · S=1.05',
      'D': 'Suelo medio · T₀=0.75s · S=1.20',
    };

    document.querySelectorAll('.seg-btn[data-field="zona"]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('zona-desc').textContent = zonaDesc[btn.dataset.value] || '';
      });
    });
    document.querySelectorAll('.seg-btn[data-field="suelo"]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('suelo-desc').textContent = sueloDesc[btn.dataset.value] || '';
      });
    });
  });

  // ---- Segmented controls ----
  function _setupSegButtons() {
    document.querySelectorAll('.seg-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const field = this.dataset.field;
        // desactivar hermanos del mismo field
        document.querySelectorAll(`.seg-btn[data-field="${field}"]`).forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        // escribir hidden input
        const hiddenId = `field-${field}`;
        const hidden = document.getElementById(hiddenId);
        if (hidden) hidden.value = this.dataset.value;
      });
    });
  }

  // ---- Leer parámetros del formulario ----
  function _readParams() {
    const fields = [
      'N_pisos', 'n_unid_lado', 'activar_B2',
      'L_mod_m', 'prof_depto_m', 'ancho_corredor_m',
      'L_nucleo_m', 'B_nucleo_m', 'h_story_m',
      'fc_MPa', 'gk_kN_m2',
      't_muro_nucleo_m', 't_muro_borde_m', 't_muro_mid_m',
      'suelo', 'zona',
    ];
    const params = {};
    fields.forEach(f => {
      const el = document.getElementById(`field-${f}`);
      if (!el) return;
      const raw = el.value;
      // Detectar tipo: entero, float o string
      if (['N_pisos', 'n_unid_lado', 'activar_B2', 'fc_MPa', 'zona'].includes(f)) {
        params[f] = parseInt(raw, 10);
      } else if (['suelo'].includes(f)) {
        params[f] = raw;
      } else {
        params[f] = parseFloat(raw);
      }
    });
    return params;
  }

  // ---- CSRF token ----
  function _csrfToken() {
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    if (cookie) return cookie.split('=')[1];
    const meta = document.querySelector('[name=csrfmiddlewaretoken]');
    return meta ? meta.value : '';
  }

  // ---- Predicción principal ----
  window.runPredict = async function () {
    const btn = document.getElementById('predict-btn');
    const label = document.getElementById('predict-label');
    const spinner = document.getElementById('predict-spinner');
    const errDiv = document.getElementById('form-error');

    btn.disabled = true;
    label.style.display = 'none';
    spinner.style.display = '';
    errDiv.style.display = 'none';
    _setStatus('CALCULANDO', false);

    const params = _readParams();

    try {
      const resp = await fetch('/api/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': _csrfToken(),
        },
        body: JSON.stringify(params),
      });
      const data = await resp.json();

      if (!resp.ok) {
        const msg = typeof data.error === 'object'
          ? Object.entries(data.error).map(([k, v]) => `${k}: ${v}`).join('\n')
          : (data.error || 'Error desconocido');
        throw new Error(msg);
      }

      state = data;
      activeMode = 0;
      _updateAll(data);
      _setStatus('ACTIVO', true);
      // Habilitar botones 3D y PLANTA (requieren geometría del predict)
      document.querySelectorAll('[data-needs-predict]').forEach(function (b) { b.disabled = false; });

    } catch (err) {
      errDiv.textContent = err.message;
      errDiv.style.display = '';
      _setStatus('ERROR', false);
    } finally {
      btn.disabled = false;
      label.style.display = '';
      spinner.style.display = 'none';
    }
  };

  // ---- Actualizar toda la UI con los resultados ----
  function _updateAll(data) {
    const { modal, respuesta, normativa, spectrum, geometria, params, avisos, extrapolando } = data;

    // Three.js
    Building3D.update(modal, geometria, data.geometria_real || {walls:[], corridor:{}}, params);
    Building3D.setMode(activeMode);

    // KPIs
    _setText('kpi-T1', modal.T[0].toFixed(3));
    _setText('kpi-T2', modal.T[1].toFixed(3));
    const umax = respuesta.Ux_por_piso[respuesta.Ux_por_piso.length - 1];
    _setText('kpi-umax', (umax * 100).toFixed(2));
    const driftMax = Math.max(Math.max(...respuesta.dx_por_piso), Math.max(...respuesta.dy_por_piso));
    _setText('kpi-drift', (driftMax * 100).toFixed(3));
    _setText('kpi-vbx', (respuesta.Vb_x / 1000).toFixed(2));
    _setText('kpi-vby', (respuesta.Vb_y / 1000).toFixed(2));

    // Viewport labels
    _setText('T-label', modal.T[activeMode].toFixed(3) + 's');
    _setText('mode-label', (activeMode + 1).toString());
    _setText('umax-label', (umax * 100).toFixed(2) + ' cm');
    _setText('drift-label', (driftMax * 100).toFixed(3) + ' %');

    // Veredicto
    const verdBanner = document.getElementById('verdict-banner');
    const verdText = document.getElementById('verdict-text');
    const verdSub = document.getElementById('verdict-sub');
    const verdCorner = document.getElementById('verdict-corner');
    const verdLabel = document.getElementById('verdict-label');
    if (verdBanner) {
      verdBanner.style.display = '';
      const cumple = normativa.veredicto === 'CUMPLE';
      verdText.textContent = normativa.veredicto;
      verdText.style.color = cumple ? 'var(--accent)' : 'var(--danger)';
      let sub = `dx_max=${normativa.deriva_x_max.toFixed(5)} (piso ${normativa.piso_dx_max})  ·  dy_max=${normativa.deriva_y_max.toFixed(5)} (piso ${normativa.piso_dy_max})`;
      if (normativa.razones_fallo && normativa.razones_fallo.length) {
        sub += '\n' + normativa.razones_fallo.join('\n');
      }
      verdSub.textContent = sub;
      if (verdCorner) { verdCorner.style.display = ''; verdLabel.textContent = normativa.veredicto; verdLabel.style.color = cumple ? 'var(--accent)' : 'var(--danger)'; }
    }

    // Tabla de modos (primeros 18)
    _fillModesTable(modal.T);

    // Mini formas modales (primeras 6)
    _fillModeShapes(modal, params.N_pisos);

    // Charts
    Charts.drawDriftProfile('drift-chart', respuesta.dx_por_piso, respuesta.dy_por_piso, 0.002);
    Charts.drawSpectrum('spectrum-chart', spectrum, modal.T);
    Charts.drawDisplacementProfile('disp-chart', respuesta.Ux_por_piso, respuesta.Uy_por_piso);

    // Leyenda espectro
    const legEl = document.getElementById('spectrum-legend');
    if (legEl) {
      const rstar = spectrum && spectrum.Rstar ? ` · R*=${spectrum.Rstar.toFixed(2)}` : '';
      legEl.textContent = `Z${params.zona} · suelo ${params.suelo}${rstar}`;
    }

    // Avisos
    if (avisos && avisos.length) {
      const errDiv = document.getElementById('form-error');
      errDiv.textContent = 'Advertencia: ' + avisos.join(' | ');
      errDiv.style.display = '';
      errDiv.style.color = 'var(--warn)';
      errDiv.style.borderColor = 'var(--warn)';
    }
  }

  function _fillModesTable(T) {
    const tbody = document.getElementById('modes-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    T.forEach((t, i) => {
      const f = 1 / t;
      const omega = 2 * Math.PI * f;
      const tr = document.createElement('tr');
      if (i === activeMode) tr.classList.add('active');
      tr.innerHTML = `
        <td>φ<sub>${i + 1}</sub></td>
        <td>${t.toFixed(3)}</td>
        <td>${f.toFixed(2)}</td>
        <td class="num">${omega.toFixed(2)}</td>`;
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', () => _selectMode(i));
      tbody.appendChild(tr);
    });
  }

  function _fillModeShapes(modal, N_pisos) {
    const container = document.getElementById('mode-shapes');
    if (!container) return;
    container.innerHTML = '';
    const nShow = modal.T.length;
    for (let i = 0; i < nShow; i++) {
      const phi = modal.Phi_x.map(row => row[i]);
      const T = modal.T[i];

      const wrap = document.createElement('div');
      wrap.className = 'mode-thumb' + (i === activeMode ? ' active' : '');
      wrap.dataset.mode = i;

      const border = document.createElement('div');
      border.className = 'thumb-border';

      const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgEl.setAttribute('viewBox', '0 0 44 80');
      svgEl.setAttribute('width', '44');
      svgEl.setAttribute('height', '80');
      svgEl.style.display = 'block';
      Charts.drawModeShapeMini(svgEl, phi, i === activeMode);

      const lbl = document.createElement('div');
      lbl.className = 'thumb-lbl';
      lbl.textContent = `φ${i + 1} · ${T.toFixed(2)}s`;

      border.appendChild(svgEl);
      wrap.appendChild(border);
      wrap.appendChild(lbl);
      wrap.addEventListener('click', () => _selectMode(i));
      container.appendChild(wrap);
    }
  }

  function _selectMode(idx) {
    activeMode = idx;
    Building3D.setMode(idx);

    // Cambiar a ISO para que la animación modal sea visible
    setView('iso');

    if (state) {
      const T = state.modal.T[idx];
      _setText('T-label', T.toFixed(3) + 's');
      _setText('mode-label', (idx + 1).toString());
      const statusM = document.getElementById('status-m');
      if (statusM) { statusM.textContent = idx + 1; document.getElementById('status-modo').style.display = ''; }
    }

    // Re-render tabla y thumbnails
    if (state) {
      _fillModesTable(state.modal.T);
      _fillModeShapes(state.modal, state.params.N_pisos);
    }
  }

  // ---- Controles de animación ----
  window.togglePlay = function () {
    isPlaying = !isPlaying;
    Building3D.setPlaying(isPlaying);
    document.getElementById('icon-pause').style.display = isPlaying ? '' : 'none';
    document.getElementById('icon-play').style.display = isPlaying ? 'none' : '';
  };

  window.resetAnim = function () {
    Building3D.resetTime();
  };

  window.scrubClick = function (e) {
    const r = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - r.left) / r.width;
    Building3D.scrubTo(pct);
  };

  // ---- Cambio de vista (Three.js puro, sin fetch) ----
  window.setView = function (view) {
    if (view !== 'iso' && !state) return;
    document.querySelectorAll('.vc-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.querySelector(`.vc-btn[data-view="${view}"]`);
    if (activeBtn) activeBtn.classList.add('active');
    Building3D.setViewMode(view);
    const labels = { iso: 'ISOMÉTRICA', '3d': '3D REAL', planta: 'PLANTA' };
    _setText('view-label', labels[view] || view.toUpperCase());
  };

  // ---- Helpers ----
  function _setText(id, val) {
    const el = document.getElementById(id);
    if (el) {
      // Preservar el primer nodo de texto, reemplazar solo eso
      const first = el.firstChild;
      if (first && first.nodeType === Node.TEXT_NODE) {
        first.textContent = val;
      } else {
        el.prepend(document.createTextNode(val));
      }
    }
  }

  function _setStatus(msg, ok) {
    const el = document.getElementById('status-pinn');
    const okEl = document.getElementById('status-ok');
    const msgEl = document.getElementById('status-msg');
    if (el) el.textContent = msg;
    if (okEl) okEl.style.color = ok ? 'var(--accent)' : 'var(--warn)';
    if (msgEl) msgEl.textContent = ok ? 'SISTEMA OK' : msg;
  }

}());
