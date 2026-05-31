/**
 * Building3D — Visor Three.js con tres modos de visualización:
 *   'iso'    — losas apiladas con deformada modal animada (vista original)
 *   '3d'     — geometría real del edificio (muros coloreados por grupo B1-B4)
 *   'planta' — misma geometría real, cámara ortográfica top-down
 *
 * Orbit controls: drag para rotar, scroll para zoom.
 */
(function (global) {
  'use strict';

  // ── Renderer y escena ────────────────────────────────────────────────────
  let renderer, scene;
  let cameraPersp, cameraOrtho;
  let animId;

  // ── Estado de animación ─────────────────────────────────────────────────
  let playing  = true;
  let time     = 0;
  let lastNow  = null;
  const ANIM_DUR    = 12.0;
  const SCALE_FACTOR = 0.6;

  // ── Estado modal ────────────────────────────────────────────────────────
  let currentMode  = 0;
  let currentPhi   = null;   // [N_pisos][18]
  let currentPhiY  = null;

  // ── Geometrías (3 conjuntos de meshes) ──────────────────────────────────
  let isoMeshes  = [];   // losas apiladas (vista ISO)
  let realMeshes = [];   // muros reales (vistas 3D y PLANTA)

  // ── Modo activo ─────────────────────────────────────────────────────────
  let currentViewMode = 'iso';

  // ── Datos de geometría guardados para recalcular cámara ─────────────────
  let _geomISO  = null;   // {Lx, Ly, H}
  let _geomReal = null;   // {walls, corridor}
  let _paramsSaved = null;

  // ── Orbit controls ──────────────────────────────────────────────────────
  const _orbit = {
    theta: Math.PI / 4, phi: Math.PI / 3.2,
    radius: 50, isDragging: false, prevX: 0, prevY: 0,
  };
  let _orbitTarget = { x: 0, y: 0, z: 0 };

  // ── Paleta de grupos ────────────────────────────────────────────────────
  const GROUP_COLOR = {
    B1: 0x3498db,   // azul
    B2: 0xdc3545,   // rojo
    B3: 0xfd7e14,   // naranja
    B4: 0x28a745,   // verde
  };
  const GROUP_EDGE = {
    B1: 0x5dade2,
    B2: 0xe74c3c,
    B3: 0xff9f43,
    B4: 0x2ecc71,
  };

  // ════════════════════════════════════════════════════════════════════════
  // INIT
  // ════════════════════════════════════════════════════════════════════════
  function init(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(el.clientWidth, el.clientHeight);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);

    scene = new THREE.Scene();

    const w = el.clientWidth, h = el.clientHeight;
    cameraPersp = new THREE.PerspectiveCamera(35, w / h, 0.1, 5000);
    cameraOrtho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 5000);

    scene.add(new THREE.AmbientLight(0x8aa8c8, 0.9));
    const dir = new THREE.DirectionalLight(0xffffff, 0.4);
    dir.position.set(1, 2, 2);
    scene.add(dir);

    _initOrbitControls(el);
    loop();
  }

  // ════════════════════════════════════════════════════════════════════════
  // ORBIT CONTROLS
  // ════════════════════════════════════════════════════════════════════════
  function _initOrbitControls(el) {
    el.style.cursor = 'grab';

    el.addEventListener('mousedown', function (e) {
      _orbit.isDragging = true;
      _orbit.prevX = e.clientX;
      _orbit.prevY = e.clientY;
      el.style.cursor = 'grabbing';
      e.preventDefault();
    });

    window.addEventListener('mousemove', function (e) {
      if (!_orbit.isDragging) return;
      const dx = e.clientX - _orbit.prevX;
      const dy = e.clientY - _orbit.prevY;
      _orbit.theta -= dx * 0.008;
      // En PLANTA bloqueamos la rotación vertical para mantener la vista cenital
      if (currentViewMode !== 'planta') {
        _orbit.phi = Math.max(0.05, Math.min(Math.PI / 2 - 0.05, _orbit.phi - dy * 0.008));
      }
      _orbit.prevX = e.clientX;
      _orbit.prevY = e.clientY;
      _positionCamera();
    });

    window.addEventListener('mouseup', function () {
      _orbit.isDragging = false;
      el.style.cursor = 'grab';
    });

    el.addEventListener('wheel', function (e) {
      e.preventDefault();
      _orbit.radius = Math.max(5, Math.min(600, _orbit.radius * (1 + e.deltaY * 0.001)));
      _positionCamera();
    }, { passive: false });
  }

  function _positionCamera() {
    const { theta, phi, radius } = _orbit;
    const tx = _orbitTarget.x, ty = _orbitTarget.y, tz = _orbitTarget.z;

    if (currentViewMode === 'planta') {
      // Cámara ortográfica directamente encima
      cameraOrtho.position.set(tx, radius * 2, tz);
      cameraOrtho.lookAt(tx, 0, tz);
      cameraOrtho.updateProjectionMatrix();
    } else {
      // Cámara perspectiva esférica (ISO y 3D)
      cameraPersp.position.set(
        tx + radius * Math.sin(phi) * Math.sin(theta),
        ty + radius * Math.cos(phi),
        tz + radius * Math.sin(phi) * Math.cos(theta)
      );
      cameraPersp.lookAt(tx, ty, tz);
      cameraPersp.updateProjectionMatrix();
    }
  }

  // ════════════════════════════════════════════════════════════════════════
  // LOOP
  // ════════════════════════════════════════════════════════════════════════
  function loop() {
    animId = requestAnimationFrame(loop);
    const now = performance.now();
    if (lastNow !== null && playing) time += (now - lastNow) / 1000;
    lastNow = now;

    if (currentViewMode === 'iso') _applyDeformation(time % ANIM_DUR);

    const cam = currentViewMode === 'planta' ? cameraOrtho : cameraPersp;
    renderer.render(scene, cam);
  }

  // ════════════════════════════════════════════════════════════════════════
  // GEOMETRÍA ISO — losas apiladas
  // ════════════════════════════════════════════════════════════════════════
  function _buildIsoGeometry(geom, N_pisos, h_story_m) {
    isoMeshes.forEach(m => scene.remove(m));
    isoMeshes = [];

    const { Lx, Ly } = geom;
    const floorH = 0.15;
    const matSlab = new THREE.MeshLambertMaterial({
      color: 0x1e4d6b, transparent: true, opacity: 0.55, side: THREE.DoubleSide,
    });
    const matEdge = new THREE.LineBasicMaterial({ color: 0x3a9e7a });

    for (let i = 0; i < N_pisos; i++) {
      const y = (i + 1) * h_story_m;
      const geo = new THREE.BoxGeometry(Lx, floorH, Ly);
      const mesh = new THREE.Mesh(geo, matSlab);
      mesh.position.set(0, y, 0);
      mesh.userData.basePos = { x: 0, y, z: 0 };
      mesh.userData.floorIndex = i;
      scene.add(mesh);
      isoMeshes.push(mesh);
      mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), matEdge));
    }

    // Núcleo
    const nGeom = new THREE.BoxGeometry(Lx * 0.35, geom.H, Ly * 0.35);
    const nMat  = new THREE.MeshLambertMaterial({ color: 0x4b2d8c, transparent: true, opacity: 0.30 });
    const core  = new THREE.Mesh(nGeom, nMat);
    core.position.set(0, geom.H / 2, 0);
    scene.add(core);
    isoMeshes.push(core);

    // Suelo
    const gGeo = new THREE.PlaneGeometry(Lx * 2, Ly * 2);
    const gMat = new THREE.MeshBasicMaterial({ color: 0x1e2a3a, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
    const ground = new THREE.Mesh(gGeo, gMat);
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);
    isoMeshes.push(ground);
  }

  function _applyDeformation(t) {
    if (!isoMeshes.length || !currentPhi || !_geomISO) return;
    const phi_x = currentPhi.map(row => row[currentMode] || 0);
    const phi_y = currentPhiY ? currentPhiY.map(row => row[currentMode] || 0) : phi_x.map(() => 0);
    const T1 = window._pinn_state && window._pinn_state.modal ? window._pinn_state.modal.T[currentMode] : 0.7;
    const omega = (2 * Math.PI) / Math.max(T1, 0.05);
    const amp = Math.sin(omega * t) * SCALE_FACTOR;

    // Solo las losas (no el core ni el suelo)
    const N_pisos = currentPhi.length;
    isoMeshes.slice(0, N_pisos).forEach((mesh, i) => {
      const b = mesh.userData.basePos;
      if (!b) return;
      mesh.position.x = b.x + phi_x[i] * amp;
      mesh.position.z = b.z + phi_y[i] * amp;
    });
  }

  // ════════════════════════════════════════════════════════════════════════
  // GEOMETRÍA REAL — muros de familia_B_core
  // ════════════════════════════════════════════════════════════════════════
  function _buildRealGeometry(geomReal, H_total) {
    realMeshes.forEach(m => scene.remove(m));
    realMeshes = [];

    if (!geomReal || !geomReal.walls || !geomReal.walls.length) return;

    const { walls, corridor } = geomReal;

    // Muros extruidos de suelo a techo
    walls.forEach(function (w) {
      const color = GROUP_COLOR[w.group] || 0x888888;
      const edge  = GROUP_EDGE[w.group]  || 0xaaaaaa;
      const geo = new THREE.BoxGeometry(w.w, H_total, w.h);
      const mat = new THREE.MeshLambertMaterial({
        color, transparent: true, opacity: 0.75,
      });
      const mesh = new THREE.Mesh(geo, mat);
      // plan: x→Three.x, y→Three.z, elevación→Three.y
      mesh.position.set(w.cx, H_total / 2, w.cy);
      scene.add(mesh);
      realMeshes.push(mesh);

      const eMat = new THREE.LineBasicMaterial({ color: edge });
      mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), eMat));
    });

    // Corredor — plano horizontal a y=0 semitransparente
    if (corridor && corridor.w && corridor.h) {
      const cgeo = new THREE.PlaneGeometry(corridor.w, corridor.h);
      const cmat = new THREE.MeshBasicMaterial({
        color: 0x1a5c2a, transparent: true, opacity: 0.25, side: THREE.DoubleSide,
      });
      const cm = new THREE.Mesh(cgeo, cmat);
      cm.rotation.x = -Math.PI / 2;
      cm.position.set(corridor.x + corridor.w / 2, 0.01, corridor.y + corridor.h / 2);
      scene.add(cm);
      realMeshes.push(cm);
    }

    // Plano de suelo
    const allLx = walls.reduce((m, w) => Math.max(m, w.cx + w.w / 2), 0);
    const allLy = walls.reduce((m, w) => Math.max(m, w.cy + w.h / 2), 0);
    const gGeo = new THREE.PlaneGeometry(allLx * 1.1, allLy * 1.1);
    const gMat = new THREE.MeshBasicMaterial({ color: 0x0f1620, transparent: true, opacity: 0.6, side: THREE.DoubleSide });
    const ground = new THREE.Mesh(gGeo, gMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(allLx / 2, 0, allLy / 2);
    scene.add(ground);
    realMeshes.push(ground);
  }

  // ════════════════════════════════════════════════════════════════════════
  // CAMBIO DE MODO
  // ════════════════════════════════════════════════════════════════════════
  function setViewMode(mode) {
    currentViewMode = mode;

    const showIso  = mode === 'iso';
    const showReal = mode === '3d' || mode === 'planta';
    isoMeshes.forEach(m => { m.visible = showIso; });
    realMeshes.forEach(m => { m.visible = showReal; });

    if (!_geomISO && !_geomReal) return;

    if (mode === 'iso') {
      _orbit.phi = Math.PI / 3.2;
      if (_geomISO && _paramsSaved) {
        const H   = _geomISO.H;
        const max = Math.max(_geomISO.Lx, _geomISO.Ly, H);
        _orbitTarget = { x: 0, y: H * 0.4, z: 0 };
        _orbit.radius = max * 2.5;
      }

    } else if (mode === '3d') {
      _orbit.phi = Math.PI / 3.2;
      _setRealCameraTarget();

    } else if (mode === 'planta') {
      _orbit.phi = 0.02;  // casi desde arriba
      _setRealCameraTarget();
      _updateOrthoCamera();
    }

    _positionCamera();
  }

  function _setRealCameraTarget() {
    if (!_geomReal || !_geomReal.walls || !_geomReal.walls.length) return;
    const walls = _geomReal.walls;
    const maxX = walls.reduce((m, w) => Math.max(m, w.cx + w.w / 2), 0);
    const maxZ = walls.reduce((m, w) => Math.max(m, w.cy + w.h / 2), 0);
    const H    = _paramsSaved ? int(_paramsSaved.N_pisos) * float(_paramsSaved.h_story_m) : 30;
    _orbitTarget = { x: maxX / 2, y: H * 0.3, z: maxZ / 2 };
    _orbit.radius = Math.max(maxX, maxZ, H) * 1.6;
  }

  function _updateOrthoCamera() {
    if (!_geomReal || !_geomReal.walls || !_geomReal.walls.length) return;
    const walls = _geomReal.walls;
    const maxX = walls.reduce((m, w) => Math.max(m, w.cx + w.w / 2), 0);
    const maxZ = walls.reduce((m, w) => Math.max(m, w.cy + w.h / 2), 0);
    const half  = Math.max(maxX, maxZ) * 0.65;
    const ar    = renderer ? renderer.domElement.width / renderer.domElement.height : 1;
    cameraOrtho.left   = -half * ar;
    cameraOrtho.right  =  half * ar;
    cameraOrtho.top    =  half;
    cameraOrtho.bottom = -half;
    cameraOrtho.updateProjectionMatrix();
  }

  // ════════════════════════════════════════════════════════════════════════
  // API PÚBLICA
  // ════════════════════════════════════════════════════════════════════════
  function update(modal, geometria, geometriaReal, params) {
    currentPhi   = modal.Phi_x;
    currentPhiY  = modal.Phi_y;
    _geomISO     = geometria;
    _geomReal    = geometriaReal;
    _paramsSaved = params;
    window._pinn_state = { modal };

    // Construir ambas geometrías
    _buildIsoGeometry(geometria, params.N_pisos, params.h_story_m);
    const H_total = params.N_pisos * params.h_story_m;
    _buildRealGeometry(geometriaReal, H_total);

    // Mostrar solo la geometría del modo activo
    setViewMode(currentViewMode);
  }

  function setMode(modeIdx) { currentMode = modeIdx; }

  function setPlaying(val) { playing = val; }
  function resetTime()     { time = 0; }
  function getTime()       { return time; }
  function scrubTo(pct)    { time = pct * ANIM_DUR; }

  // helpers para conversión de tipo en _setRealCameraTarget
  function int(v) { return parseInt(v, 10); }
  function float(v) { return parseFloat(v); }

  global.Building3D = { init, update, setMode, setViewMode, setPlaying, resetTime, getTime, scrubTo };

}(window));
