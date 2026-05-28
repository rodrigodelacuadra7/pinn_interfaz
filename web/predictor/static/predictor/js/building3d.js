/**
 * Building3D — Edificio 3D con Three.js.
 * Deforma pisos usando las formas modales Phi reales del PINN.
 * Orbit controls manuales: drag para rotar, scroll para zoom.
 */
(function (global) {
  'use strict';

  let renderer, scene, camera, floorMeshes = [], animId;
  let currentMode = 0;
  let currentPhi  = null;   // [N_pisos][18]
  let currentPhiY = null;   // [N_pisos][18]
  let currentGeom = null;
  let playing = true;
  let time = 0;
  let lastNow = null;

  const ANIM_DUR   = 12.0;
  const SCALE_FACTOR = 0.6;

  // Orbit controls state
  const _orbit = { theta: Math.PI / 4, phi: Math.PI / 3.2, radius: 50, isDragging: false, prevX: 0, prevY: 0 };
  let _orbitTarget = { x: 0, y: 0, z: 0 };

  // ---- Init ----
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

    scene.add(new THREE.AmbientLight(0x8aa8c8, 0.9));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.4);
    dirLight.position.set(1, 2, 2);
    scene.add(dirLight);

    _initOrbitControls(container);
    loop();
  }

  // ---- Orbit controls ----
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
      _orbit.phi = Math.max(0.05, Math.min(Math.PI / 2 - 0.05, _orbit.phi - dy * 0.008));
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
    camera.position.set(
      _orbitTarget.x + radius * Math.sin(phi) * Math.sin(theta),
      _orbitTarget.y + radius * Math.cos(phi),
      _orbitTarget.z + radius * Math.sin(phi) * Math.cos(theta)
    );
    camera.lookAt(_orbitTarget.x, _orbitTarget.y, _orbitTarget.z);
    camera.updateProjectionMatrix();
  }

  // ---- Animation loop ----
  function loop() {
    animId = requestAnimationFrame(loop);
    const now = performance.now();
    if (lastNow !== null && playing) {
      time += (now - lastNow) / 1000;
    }
    lastNow = now;
    _applyDeformation(time % ANIM_DUR);
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
      const b = mesh.userData.basePos;
      mesh.position.x = b.x + phi_x[i] * amp;
      mesh.position.z = b.z + phi_y[i] * amp;
    });
  }

  // ---- Build ----
  function buildBuilding(geom, N_pisos, h_story_m) {
    floorMeshes.forEach(m => scene.remove(m));
    floorMeshes = [];

    const { Lx, Ly } = geom;
    const floorH = 0.15;

    const matSlab = new THREE.MeshLambertMaterial({
      color: 0x1e4d6b, transparent: true, opacity: 0.55, side: THREE.DoubleSide,
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

      const edges = new THREE.EdgesGeometry(geo);
      mesh.add(new THREE.LineSegments(edges, matEdge));
    }

    // Núcleo
    const nGeom = new THREE.BoxGeometry(Lx * 0.35, geom.H, Ly * 0.35);
    const nMat  = new THREE.MeshLambertMaterial({ color: 0x4b2d8c, transparent: true, opacity: 0.30 });
    const core  = new THREE.Mesh(nGeom, nMat);
    core.position.set(0, geom.H / 2, 0);
    scene.add(core);

    // Plano de suelo
    const glGeo = new THREE.PlaneGeometry(Lx * 2, Ly * 2);
    const glMat = new THREE.MeshBasicMaterial({ color: 0x1e2a3a, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
    const ground = new THREE.Mesh(glGeo, glMat);
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    // Centrar la cámara en el edificio
    const H = N_pisos * h_story_m;
    const maxDim = Math.max(Lx, Ly, H);
    _orbitTarget = { x: 0, y: H * 0.4, z: 0 };
    _orbit.radius = maxDim * 2.5;
    _positionCamera();
  }

  // ---- API pública ----
  function update(modal, geometria, params) {
    currentPhi  = modal.Phi_x;
    currentPhiY = modal.Phi_y;
    currentGeom = geometria;
    window._pinn_state = { modal };
    buildBuilding(geometria, params.N_pisos, params.h_story_m);
  }

  function setMode(modeIdx) { currentMode = modeIdx; }

  // setView se mantiene para compatibilidad; resetea a ISO
  function setView() {
    _orbit.theta = Math.PI / 4;
    _orbit.phi   = Math.PI / 3.2;
    _positionCamera();
  }

  function setPlaying(val) { playing = val; }
  function resetTime()     { time = 0; }
  function getTime()       { return time; }
  function scrubTo(pct)    { time = pct * ANIM_DUR; }

  global.Building3D = { init, update, setMode, setView, setPlaying, resetTime, getTime, scrubTo };

}(window));
