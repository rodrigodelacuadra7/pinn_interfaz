/**
 * Building3D — Edificio 3D con Three.js.
 * Deforma pisos usando las formas modales Phi reales del PINN.
 */
(function (global) {
  'use strict';

  let renderer, scene, camera, floorMeshes = [], animId;
  let currentMode = 0;
  let currentPhi = null;   // shape: [N_pisos][18] (Phi_x)
  let currentPhiY = null;  // shape: [N_pisos][18] (Phi_y)
  let currentGeom = null;  // {Lx, Ly, H, h_story_m, N_pisos}
  let playing = true;
  let time = 0;
  let lastNow = null;
  let currentView = 'iso';

  const ANIM_DUR = 12.0;
  const SCALE_FACTOR = 0.6; // amplitud visual de la deformada en metros

  function init(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(35, container.clientWidth / container.clientHeight, 0.1, 5000);

    // Luz ambiente
    scene.add(new THREE.AmbientLight(0x8aa8c8, 0.9));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.4);
    dirLight.position.set(1, 2, 2);
    scene.add(dirLight);

    loop();
  }

  function loop() {
    animId = requestAnimationFrame(loop);
    const now = performance.now();
    if (lastNow !== null && playing) {
      time += (now - lastNow) / 1000;
    }
    lastNow = now;

    const t = time % ANIM_DUR;
    _applyDeformation(t);

    // Actualizar UI de tiempo
    const pct = (t / ANIM_DUR) * 100;
    const fillEl = document.getElementById('scrub-fill');
    const headEl = document.getElementById('scrub-head');
    const dispEl = document.getElementById('time-display');
    const statusT = document.getElementById('status-t');
    if (fillEl) fillEl.style.width = pct + '%';
    if (headEl) headEl.style.left = pct + '%';
    if (dispEl) dispEl.textContent = t.toFixed(2);
    if (statusT) statusT.textContent = t.toFixed(2);

    renderer.render(scene, camera);
  }

  function _applyDeformation(t) {
    if (!floorMeshes.length || !currentPhi || !currentGeom) return;
    const phi_x = currentPhi.map(row => row[currentMode] || 0);
    const phi_y = currentPhiY ? currentPhiY.map(row => row[currentMode] || 0) : phi_x.map(() => 0);
    const T1 = window._pinn_state && window._pinn_state.modal ? window._pinn_state.modal.T[currentMode] : 0.7;
    const omega = (2 * Math.PI) / Math.max(T1, 0.05);
    const amp = Math.sin(omega * t) * SCALE_FACTOR;

    floorMeshes.forEach((mesh, i) => {
      const basePos = mesh.userData.basePos;
      mesh.position.x = basePos.x + phi_x[i] * amp;
      mesh.position.z = basePos.z + phi_y[i] * amp;
    });
  }

  function buildBuilding(geom, N_pisos, h_story_m) {
    // Limpiar edificio anterior
    floorMeshes.forEach(m => scene.remove(m));
    floorMeshes = [];

    const { Lx, Ly } = geom;
    const floorH = 0.15; // espesor losa visual en metros
    const gap = h_story_m - floorH;

    // Material losa
    const matSlab = new THREE.MeshLambertMaterial({
      color: 0x1e4d6b,
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide,
    });
    const matEdge = new THREE.LineBasicMaterial({ color: 0x3a9e7a, linewidth: 1 });

    for (let i = 0; i < N_pisos; i++) {
      const y = (i + 1) * h_story_m;
      const geo = new THREE.BoxGeometry(Lx, floorH, Ly);
      const mesh = new THREE.Mesh(geo, matSlab);
      mesh.position.set(0, y, 0);
      mesh.userData.basePos = { x: 0, y, z: 0 };
      mesh.userData.floorIndex = i;
      scene.add(mesh);
      floorMeshes.push(mesh);

      // Edges
      const edges = new THREE.EdgesGeometry(geo);
      const line = new THREE.LineSegments(edges, matEdge);
      mesh.add(line);
    }

    // Núcleo (caja en el centro, de suelo a techo)
    const nGeom = new THREE.BoxGeometry(
      geom.Lx * 0.35, geom.H, geom.Ly * 0.35
    );
    const nMat = new THREE.MeshLambertMaterial({
      color: 0x4b2d8c,
      transparent: true,
      opacity: 0.30,
    });
    const core = new THREE.Mesh(nGeom, nMat);
    core.position.set(0, geom.H / 2, 0);
    scene.add(core);

    // Base ground line
    const glGeo = new THREE.PlaneGeometry(Lx * 2, Ly * 2);
    const glMat = new THREE.MeshBasicMaterial({
      color: 0x1e2a3a,
      transparent: true,
      opacity: 0.5,
      side: THREE.DoubleSide,
    });
    const ground = new THREE.Mesh(glGeo, glMat);
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    _setCamera(geom, N_pisos, h_story_m, currentView);
  }

  function _setCamera(geom, N_pisos, h_story_m, view) {
    const H = N_pisos * h_story_m;
    const maxDim = Math.max(geom.Lx, geom.Ly, H);
    const dist = maxDim * 2.5;

    if (view === 'iso') {
      camera.position.set(dist, H * 0.8, dist);
    } else if (view === 'front') {
      camera.position.set(0, H * 0.5, dist * 1.2);
    } else {
      camera.position.set(0, dist * 1.8, 0);
    }
    camera.lookAt(0, H * 0.4, 0);
    camera.updateProjectionMatrix();
  }

  function update(modal, geometria, params) {
    currentPhi  = modal.Phi_x;
    currentPhiY = modal.Phi_y;
    currentGeom = geometria;
    window._pinn_state = { modal };
    buildBuilding(geometria, params.N_pisos, params.h_story_m);
    _highlightFloor(null);
  }

  function setMode(modeIdx) {
    currentMode = modeIdx;
  }

  function setView(view) {
    currentView = view;
    if (currentGeom && window._pinn_state) {
      const p = window._pinn_state.modal;
      _setCamera(currentGeom, floorMeshes.length, currentGeom.H / floorMeshes.length, view);
    }
  }

  function setPlaying(val) { playing = val; }
  function resetTime() { time = 0; }
  function getTime() { return time; }
  function scrubTo(pct) { time = pct * ANIM_DUR; }

  function _highlightFloor(idx) {
    floorMeshes.forEach((m, i) => {
      m.material.color.set(i === idx ? 0x2a8a5f : 0x1e4d6b);
      m.material.opacity = i === idx ? 0.85 : 0.55;
    });
  }

  global.Building3D = {
    init,
    update,
    setMode,
    setView,
    setPlaying,
    resetTime,
    getTime,
    scrubTo,
  };

}(window));
