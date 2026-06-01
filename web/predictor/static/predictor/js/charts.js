/**
 * Charts — SVG puros sin dependencias externas.
 * Patrón inspirado en el charts.jsx del diseño handoff.
 */
(function (global) {
  'use strict';

  const C = {
    accent:  'oklch(0.82 0.16 155)',
    danger:  'oklch(0.7 0.18 25)',
    warn:    'oklch(0.78 0.16 75)',
    info:    'oklch(0.78 0.13 230)',
    mute:    '#5b6776',
    border:  '#1e2a3a',
    border2: '#28384c',
    text2:   '#8a96a5',
  };

  function _svgEl(tag, attrs) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
    return el;
  }

  function _linePath(pts, xFn, yFn) {
    return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${xFn(p).toFixed(1)} ${yFn(p).toFixed(1)}`).join(' ');
  }

  // ---- Derivas vs piso ----
  function drawDriftProfile(svgId, dx, dy, limit) {
    const svg = document.getElementById(svgId);
    if (!svg) return;
    svg.innerHTML = '';
    const W = 420, H = 160;
    const pL = 40, pR = 14, pT = 10, pB = 22;
    const iW = W - pL - pR, iH = H - pT - pB;
    const N = dx.length;
    const maxVal = Math.max(Math.max(...dx), Math.max(...dy), limit * 1.2);
    const x = v => pL + (v / maxVal) * iW;
    const y = i => pT + iH - ((i + 1) / N) * iH;

    // Ejes
    svg.appendChild(_svgEl('line', { x1: pL, y1: pT, x2: pL, y2: H - pB, stroke: C.border2 }));
    svg.appendChild(_svgEl('line', { x1: pL, y1: H - pB, x2: W - pR, y2: H - pB, stroke: C.border2 }));

    // Grid vertical
    [0, 0.5, 1].forEach(f => {
      const xp = x(maxVal * f);
      svg.appendChild(_svgEl('line', { x1: xp, y1: pT, x2: xp, y2: H - pB, stroke: C.border, 'stroke-dasharray': '2 3' }));
      const t = _svgEl('text', { x: xp, y: H - 6, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono', 'text-anchor': 'middle' });
      t.textContent = (maxVal * f).toFixed(4);
      svg.appendChild(t);
    });

    // Etiquetas eje Y (pisos)
    [0, Math.floor(N / 2), N - 1].forEach(i => {
      const t = _svgEl('text', { x: pL - 4, y: y(i) + 3, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono', 'text-anchor': 'end' });
      t.textContent = i + 1;
      svg.appendChild(t);
    });

    // Límite NCh433
    const xl = x(limit);
    svg.appendChild(_svgEl('line', { x1: xl, y1: pT, x2: xl, y2: H - pB, stroke: C.danger, 'stroke-dasharray': '3 2', 'stroke-width': 1.2 }));

    // Curvas
    const pts = dx.map((v, i) => [v, i]);
    const path_dx = _linePath(pts, p => x(p[0]), p => y(p[1]));
    svg.appendChild(_svgEl('path', { d: path_dx, stroke: C.accent, 'stroke-width': 1.5, fill: 'none' }));

    const pts_dy = dy.map((v, i) => [v, i]);
    const path_dy = _linePath(pts_dy, p => x(p[0]), p => y(p[1]));
    svg.appendChild(_svgEl('path', { d: path_dy, stroke: C.danger, 'stroke-width': 1.5, fill: 'none', 'stroke-dasharray': '4 2' }));

    // Puntos
    dx.forEach((v, i) => svg.appendChild(_svgEl('circle', { cx: x(v), cy: y(i), r: 2.5, fill: C.accent })));
    dy.forEach((v, i) => svg.appendChild(_svgEl('circle', { cx: x(v), cy: y(i), r: 2.5, fill: C.danger })));

    // Label
    const lb = _svgEl('text', { x: pL + 4, y: pT + 10, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono' });
    lb.textContent = 'δ [-]';
    svg.appendChild(lb);
  }

  // ── Espectro NCh433 Mod.Of2012 + DS61 (cliente, traducción 1:1 del backend) ──
  // Útil para calcular sin necesidad de llamar al API.
  const _SOIL_PARAMS_JS = {
    A: { S: 0.90, T0: 0.15, Tp: 0.20, n: 1.00 },
    B: { S: 1.00, T0: 0.30, Tp: 0.35, n: 1.33 },
    C: { S: 1.05, T0: 0.40, Tp: 0.45, n: 1.40 },
    D: { S: 1.20, T0: 0.75, Tp: 0.85, n: 1.80 },
  };
  const _A0_ZONE = { 1: 0.20, 2: 0.30, 3: 0.40 };

  function espectro_nch433(zona, suelo, T_star, T_max, n_pts) {
    T_max = T_max || 4.0; n_pts = n_pts || 200;
    const sp   = _SOIL_PARAMS_JS[String(suelo).toUpperCase()] || _SOIL_PARAMS_JS.C;
    const A0   = _A0_ZONE[parseInt(zona)] || 0.30;
    const { S, T0, Tp, n } = sp;
    const Tstar = (T_star && T_star > 0) ? T_star : 0.5;
    const den   = 0.10 * T0 + Tstar / (11.0 - 1.0);
    const Rstar = 1.0 + Tstar / Math.max(den, 1e-9);
    const Sa_min = S * A0 / 6.0, Sa_max = 0.35 * S * A0;
    const Ts = [], Sa_e = [], Sa_d = [];
    for (let i = 0; i < n_pts; i++) {
      const T = 0.02 + (i / (n_pts - 1)) * (T_max - 0.02);
      const x_  = Math.max(T, 0) / Tp;
      const alpha = (1.0 + 4.5 * Math.pow(x_, n)) / (1.0 + Math.pow(x_, 3));
      Ts.push(T);
      Sa_e.push(S * A0 * alpha);
      Sa_d.push(Math.max(Sa_min, Math.min(Sa_max, S * A0 * alpha / Rstar)));
    }
    return { T: Ts, Sa_elastic_g: Sa_e, Sa_design_g: Sa_d,
             Sa_min_g: Sa_min, Sa_max_g: Sa_max, Rstar, A0_g: A0, S, T0, Tp };
  }

  // ---- Espectro NCh433 — dos curvas, límites y marcadores modales ----
  function drawSpectrum(svgId, spec, periods) {
    const svg = document.getElementById(svgId);
    if (!svg) return;
    svg.innerHTML = '';
    const W = 320, H = 160;
    const pL = 36, pR = 10, pT = 8, pB = 22;
    const iW = W - pL - pR, iH = H - pT - pB;
    const Ts   = spec.T;
    const Tmax = Ts[Ts.length - 1] || 4.0;

    // Escala Y basada en la curva elástica (mayor que la de diseño)
    const yMax = Math.max(...spec.Sa_elastic_g) * 1.15;
    const x = T => pL + (T / Tmax) * iW;
    const y = v => pT + iH - (v / yMax) * iH;

    // Ejes
    svg.appendChild(_svgEl('line', { x1: pL, y1: pT, x2: pL, y2: H - pB, stroke: C.border2 }));
    svg.appendChild(_svgEl('line', { x1: pL, y1: H - pB, x2: W - pR, y2: H - pB, stroke: C.border2 }));

    // Grid T
    [0, 1, 2, 3, 4].forEach(T => {
      const xp = x(T);
      svg.appendChild(_svgEl('line', { x1: xp, y1: pT, x2: xp, y2: H - pB, stroke: C.border, 'stroke-dasharray': '2 3' }));
      const t = _svgEl('text', { x: xp, y: H - 6, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono', 'text-anchor': 'middle' });
      t.textContent = T.toFixed(1);
      svg.appendChild(t);
    });

    // Fill bajo curva de diseño
    const designPts   = Ts.map((T, i) => [T, spec.Sa_design_g[i]]);
    const designPath  = _linePath(designPts, p => x(p[0]), p => y(p[1]));
    const fillPath    = `${designPath} L ${x(Ts[Ts.length - 1])} ${y(0)} L ${x(Ts[0])} ${y(0)} Z`;
    svg.appendChild(_svgEl('path', { d: fillPath, fill: 'oklch(0.82 0.16 155 / 0.06)' }));

    // Curva elástica — delgada, punteada, semitransparente
    const elasticPts = Ts.map((T, i) => [T, spec.Sa_elastic_g[i]]);
    svg.appendChild(_svgEl('path', {
      d: _linePath(elasticPts, p => x(p[0]), p => y(p[1])),
      stroke: C.info, 'stroke-width': 1.0, fill: 'none', 'stroke-dasharray': '3 2', opacity: 0.55,
    }));

    // Línea horizontal Sa_max
    const yMax_line = y(spec.Sa_max_g);
    if (yMax_line >= pT) {
      svg.appendChild(_svgEl('line', { x1: pL, y1: yMax_line, x2: W - pR, y2: yMax_line, stroke: C.danger, 'stroke-dasharray': '2 3', 'stroke-width': 1, opacity: 0.65 }));
      const tm = _svgEl('text', { x: W - pR - 2, y: yMax_line - 2, fill: C.danger, 'font-size': 7.5, 'font-family': 'IBM Plex Mono', 'text-anchor': 'end' });
      tm.textContent = 'Saₘₐˣ';
      svg.appendChild(tm);
    }

    // Línea horizontal Sa_min
    const yMin_line = y(spec.Sa_min_g);
    if (yMin_line <= H - pB) {
      svg.appendChild(_svgEl('line', { x1: pL, y1: yMin_line, x2: W - pR, y2: yMin_line, stroke: C.warn, 'stroke-dasharray': '2 3', 'stroke-width': 1, opacity: 0.65 }));
      const tm2 = _svgEl('text', { x: W - pR - 2, y: yMin_line + 9, fill: C.warn, 'font-size': 7.5, 'font-family': 'IBM Plex Mono', 'text-anchor': 'end' });
      tm2.textContent = 'Saₘᴵⁿ';
      svg.appendChild(tm2);
    }

    // Curva de diseño — principal
    svg.appendChild(_svgEl('path', {
      d: designPath, stroke: C.accent, 'stroke-width': 1.5, fill: 'none',
    }));

    // Marcadores de períodos sobre curva de diseño
    const modeColors = [C.accent, C.info, C.warn, '#6b7785', '#6b7785', '#6b7785'];
    (periods || []).slice(0, 6).forEach((T, i) => {
      if (T > Tmax) return;
      const idx = Ts.findIndex(t => t >= T);
      const saD = idx >= 0 ? spec.Sa_design_g[idx] : spec.Sa_min_g;
      svg.appendChild(_svgEl('line', { x1: x(T), y1: pT, x2: x(T), y2: H - pB, stroke: modeColors[i], 'stroke-dasharray': '1 2', opacity: 0.7 }));
      svg.appendChild(_svgEl('circle', { cx: x(T), cy: y(saD), r: 2.5, fill: modeColors[i] }));
    });

    // Labels
    const la = _svgEl('text', { x: pL + 4, y: pT + 10, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono' });
    la.textContent = 'Sa/g';
    svg.appendChild(la);
    const lb = _svgEl('text', { x: W - pR - 4, y: H - pB - 4, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono', 'text-anchor': 'end' });
    lb.textContent = 'T [s]';
    svg.appendChild(lb);
  }

  // ---- Desplazamientos vs piso ----
  function drawDisplacementProfile(svgId, Ux, Uy) {
    const svg = document.getElementById(svgId);
    if (!svg) return;
    svg.innerHTML = '';
    const W = 310, H = 130;
    const pL = 40, pR = 10, pT = 8, pB = 22;
    const iW = W - pL - pR, iH = H - pT - pB;
    const N = Ux.length;
    const maxU = Math.max(Math.max(...Ux), Math.max(...Uy), 1e-6) * 1.15;
    const x = v => pL + (v / maxU) * iW;
    const y = i => pT + iH - ((i + 1) / N) * iH;

    // Ejes
    svg.appendChild(_svgEl('line', { x1: pL, y1: pT, x2: pL, y2: H - pB, stroke: C.border2 }));
    svg.appendChild(_svgEl('line', { x1: pL, y1: H - pB, x2: W - pR, y2: H - pB, stroke: C.border2 }));

    // Curvas
    const path_ux = _linePath(Ux.map((v, i) => [v, i]), p => x(p[0]), p => y(p[1]));
    svg.appendChild(_svgEl('path', { d: path_ux, stroke: C.accent, 'stroke-width': 1.5, fill: 'none' }));
    const path_uy = _linePath(Uy.map((v, i) => [v, i]), p => x(p[0]), p => y(p[1]));
    svg.appendChild(_svgEl('path', { d: path_uy, stroke: C.danger, 'stroke-width': 1.5, fill: 'none', 'stroke-dasharray': '4 2' }));

    Ux.forEach((v, i) => svg.appendChild(_svgEl('circle', { cx: x(v), cy: y(i), r: 2, fill: C.accent })));
    Uy.forEach((v, i) => svg.appendChild(_svgEl('circle', { cx: x(v), cy: y(i), r: 2, fill: C.danger })));

    // Etiqueta
    const lb = _svgEl('text', { x: pL + 4, y: pT + 10, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono' });
    lb.textContent = 'U [m]';
    svg.appendChild(lb);
    const lb2 = _svgEl('text', { x: W - pR - 4, y: H - pB - 4, fill: C.mute, 'font-size': 9, 'font-family': 'IBM Plex Mono', 'text-anchor': 'end' });
    lb2.textContent = 'piso';
    svg.appendChild(lb2);
  }

  // ---- Mini forma modal SVG ----
  function drawModeShapeMini(svgEl, phi, active) {
    svgEl.innerHTML = '';
    const W = 44, H = 80;
    const pX = 10, pY = 6;
    const iW = W - 2 * pX, iH = H - 2 * pY;
    const N = phi.length;
    const maxAbs = Math.max(Math.max(...phi.map(Math.abs)), 1e-6);
    const x = v => pX + iW / 2 + (v / maxAbs) * (iW / 2);
    const y = i => pY + iH - ((i + 1) / N) * iH;

    // Baseline y eje base
    svgEl.appendChild(_svgEl('line', {
      x1: pX + iW / 2, y1: pY,
      x2: pX + iW / 2, y2: pY + iH,
      stroke: C.border, 'stroke-dasharray': '2 2',
    }));
    svgEl.appendChild(_svgEl('line', {
      x1: pX, y1: pY + iH, x2: pX + iW, y2: pY + iH, stroke: C.border2,
    }));

    // Forma
    const pts = phi.map((v, i) => [x(v), y(i)]);
    // Añadir punto base (0, suelo)
    const allPts = [[pX + iW / 2, pY + iH], ...pts];
    const pathStr = allPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
    const stroke = active ? C.accent : '#6b7785';
    svgEl.appendChild(_svgEl('path', { d: pathStr, stroke, 'stroke-width': active ? 1.6 : 1.2, fill: 'none' }));
    pts.forEach(([cx, cy]) => svgEl.appendChild(_svgEl('circle', { cx, cy, r: 1.5, fill: stroke })));
  }

  global.Charts = { drawDriftProfile, drawSpectrum, drawDisplacementProfile, drawModeShapeMini, espectro_nch433 };

}(window));
