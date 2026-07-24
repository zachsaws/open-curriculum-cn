// Open Curriculum CN — 3D 球面可视化 (V3.3.3)
// Three.js r160 · 球面 Fibonacci 分布 · 大圆弧 (great circle arc) 边
// 复用 graph.json / 学科配色 / 卡片结构

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ============== 常量 ==============
const SPHERE_RADIUS = 100;
const NODE_BASE_SIZE = 4.0;        // 最小节点 size (无 centrality 时的像素缩放)
const CENTRALITY_SIZE_GAIN = 14.0; // centrality 0.5 时的最大 size 加成
const EDGE_SEGMENTS = 32;          // 每条边采样段数 (用户 spec: 32 → 151K 段)
const EDGE_BASE_OPACITY = 0.07;    // 常态边透明度 (球面不能太糊)
const EDGE_NEIGHBOR_OPACITY = 0.55; // 邻居边透明度 (选中节点时)
const POINT_RAYCAST_THRESHOLD = 1.5; // 鼠标点击命中半径 (世界单位, 经 OrbitControls 后会按缩放调整)

// 14 学科配色 — 与 web/app.js PALETTE 完全一致
const PALETTE = {
  math: '#5b8def', chinese: '#ef6b5b', english: '#7bc96f',
  science: '#f9a825', physics: '#ba68c8', chemistry: '#26a69a',
  biology: '#66bb6a', history: '#8d6e63', geography: '#42a5f5',
  morality_law: '#ec407a', info_tech: '#26c6da', art: '#ab47bc',
  pe_health: '#ff7043', labor: '#9ccc65', integrated: '#78909c',
};

// ============== 全局状态 ==============
let DATA = null;
let GROUPS = [];
let activeGroups = new Set();
window._currentNode = null;

let scene, camera, renderer, controls;
let pointsMesh, linesMesh, linesHighlightMesh;
let nodePositions = [];         // flat [x,y,z, ...]
let nodeBaseColors = [];        // THREE.Color per node
let nodeIdToIndex = new Map();
let edgesData = [];             // [{fromIdx, toIdx, rel, reason}]
let edgesFromTo = new Map();    // fromIdx -> [{toIdx, rel, reason, edgeIdx}, ...]
let edgesToFrom = new Map();
let neighborMap = new Map();    // idx -> Set
let edgeBaseColor = new THREE.Color(0xb8c0d8);

let selectedNodeIdx = null;
let hoveredNodeIdx = null;
let isMobile = false;
let fpsFrames = 0;
let fpsLastTime = performance.now();

// 标题翻译 (复制自 2D app.js 的概念渲染逻辑)
const titleOrig = new Map(); // nodeId -> 原始 title (用于繁简切换)

// ============== 启动 ==============
async function init() {
  isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
  document.getElementById('loadingMsg').textContent = '加载 3D 球面知识图谱...';

  // 1) 加载数据
  await loadData();
  if (!DATA) return;

  // 2) 搭建场景
  setupScene();
  buildGraph();
  setupInteraction();

  // 3) UI
      buildLegend();
  setupSearch();
  setupCardClose();
  setupAutoRotateToggle();

  // 4) FPS 计数 + 渲染循环
  document.getElementById('loading').classList.add('done');
  animate();
}

// 标题副标题: 硬编码中文, 不依赖 i18n
function set3DHeader() {
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'zh-CN';
  const titles = {
    'zh-CN': '2022 新课标知识图谱 · 3D 球面视图',
    'zh-TW': '2022 新課標知識圖譜 · 3D 球面視圖',
    'en':    '2022 New Curriculum KG · 3D Sphere View',
  };
  const subs = {
    'zh-CN': '1906 概念按 Fibonacci 黄金角 (137.5°) 分布 · 4736 关系按 great circle arc 渲染',
    'zh-TW': '1906 概念按 Fibonacci 黃金角 (137.5°) 分布 · 4736 關係按 great circle arc 渲染 · <a href="./index.html" style="color:#6b8cff;text-decoration:none">切換到漏斗學習路徑 (即將上線) →</a>',
    'en':    '1906 concepts in Fibonacci golden-angle layout · 4736 relations as great circle arcs · <a href="./index.html" style="color:#6b8cff;text-decoration:none">Switch to funnel learning path (coming soon) →</a>',
  };
  const title = titles[lang] || titles['zh-CN'];
  const sub = subs[lang] || subs['zh-CN'];
  const h1 = document.getElementById('headerTitle3d');
  const subEl = document.getElementById('headerSub3d');
  if (h1) h1.textContent = title;
  if (subEl) subEl.innerHTML = sub;
  document.title = title + ' · Open Curriculum CN';
}

// ============== 数据加载 ==============
async function loadData() {
  try {
    // V3.5g: 优先 fetch .gz 压缩版 (1.4MB vs 5.9MB), 客户端解压
    let text;
    try {
      const gzRes = await fetch('./data/graph.json.gz');
      if (gzRes.ok) {
        const ds = new DecompressionStream('gzip');
        const stream = gzRes.body.pipeThrough(ds);
        text = await new Response(stream).text();
      } else throw new Error('gz 404');
    } catch (e1) {
      console.warn('gz 加载失败, fallback json:', e1.message);
      const res = await fetch('./data/graph.json');
      if (!res.ok) throw new Error('graph.json 不存在');
      text = await res.text();
    }
    DATA = JSON.parse(text);
  } catch (e) {
    const msg = document.getElementById('loadingMsg');
    msg.innerHTML = `<div class="err">${window.t ? "..." : '未找到图谱数据 (graph.json)'}<br><br>${e.message}</div>`;
    console.error(e);
    return;
  }
  GROUPS = [...new Set(DATA.nodes.map(n => n.subject))].sort();
  activeGroups = new Set(GROUPS);
  // 缓存原始 title (用于繁简切换)
  DATA.nodes.forEach(n => { titleOrig.set(n.id, n.title); });

  document.getElementById('nCount').textContent = DATA.nodes.length.toLocaleString();
  document.getElementById('eCount').textContent = DATA.edges.length.toLocaleString();
  document.getElementById('gCount').textContent = GROUPS.length;
}

// ============== 场景 ==============
function setupScene() {
  const container = document.getElementById('three-canvas');
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0d18);

  const w = window.innerWidth;
  const h = window.innerHeight;
  camera = new THREE.PerspectiveCamera(50, w / h, 1, 2000);
  camera.position.set(50, 80, 260);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({
    antialias: !isMobile,
    powerPreference: 'high-performance',
  });
  const dpr = Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2);
  renderer.setPixelRatio(dpr);
  renderer.setSize(w, h);
  container.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.enablePan = false;
  controls.minDistance = 130;
  controls.maxDistance = 600;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.4;
  controls.rotateSpeed = 0.5;
  controls.zoomSpeed = 0.7;

  // 视觉参考: 赤道 + 一条经线 (subtle)
  scene.add(makeReferenceLines());

  window.addEventListener('resize', onResize);
}

function makeReferenceLines() {
  const group = new THREE.Group();
  const r = SPHERE_RADIUS * 1.02;
  // 赤道 (y=0 平面)
  const eqPts = [];
  for (let i = 0; i <= 96; i++) {
    const a = (i / 96) * Math.PI * 2;
    eqPts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
  }
  const eqGeo = new THREE.BufferGeometry().setFromPoints(eqPts);
  const eqMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.06 });
  group.add(new THREE.Line(eqGeo, eqMat));

  // 一条经线 (x=0 平面)
  const mePts = [];
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * Math.PI;
    mePts.push(new THREE.Vector3(0, Math.cos(a) * r, Math.sin(a) * r));
  }
  const meGeo = new THREE.BufferGeometry().setFromPoints(mePts);
  const meMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.05 });
  group.add(new THREE.Line(meGeo, meMat));
  return group;
}

// ============== 构建图 ==============
function buildGraph() {
  const N = DATA.nodes.length;
  const golden_angle = Math.PI * (1 + Math.sqrt(5));

  // ---- 节点位置 (Fibonacci 球分布) ----
  for (let i = 0; i < N; i++) {
    const phi = Math.acos(1 - 2 * (i + 0.5) / N);
    const theta = golden_angle * i;
    // 球面坐标: y 是极轴 (Three.js 默认 y-up)
    const x = SPHERE_RADIUS * Math.sin(phi) * Math.cos(theta);
    const y = SPHERE_RADIUS * Math.cos(phi);
    const z = SPHERE_RADIUS * Math.sin(phi) * Math.sin(theta);
    nodePositions.push(x, y, z);

    const subject = DATA.nodes[i].subject;
    const hex = PALETTE[subject] || '#888888';
    nodeBaseColors.push(new THREE.Color(hex));
    nodeIdToIndex.set(DATA.nodes[i].id, i);
  }

  // ---- 边 + 邻接索引 ----
  DATA.edges.forEach((e, ei) => {
    const fi = nodeIdToIndex.get(e.from);
    const ti = nodeIdToIndex.get(e.to);
    if (fi === undefined || ti === undefined) return;
    const rel = e.rel || 'prerequisite';
    const reason = e.reason || '';
    const rec = { fromIdx: fi, toIdx: ti, rel, reason, edgeIdx: ei };
    edgesData.push(rec);
    if (!edgesFromTo.has(fi)) edgesFromTo.set(fi, []);
    if (!edgesToFrom.has(ti)) edgesToFrom.set(ti, []);
    edgesFromTo.get(fi).push(rec);
    edgesToFrom.get(ti).push(rec);
    if (!neighborMap.has(fi)) neighborMap.set(fi, new Set());
    if (!neighborMap.has(ti)) neighborMap.set(ti, new Set());
    neighborMap.get(fi).add(ti);
    neighborMap.get(ti).add(fi);
  });

  buildNodeMesh();
  buildEdgeMesh();
  buildHighlightEdgeMesh();
}

function makeNodeSprite() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.4, 'rgba(255,255,255,0.92)');
  g.addColorStop(0.75, 'rgba(255,255,255,0.32)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(32, 32, 32, 0, Math.PI * 2);
  ctx.fill();
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

function buildNodeMesh() {
  const N = DATA.nodes.length;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(nodePositions, 3));

  // 初始颜色 (按学科)
  const initColors = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const c = nodeBaseColors[i];
    initColors[i*3] = c.r; initColors[i*3+1] = c.g; initColors[i*3+2] = c.b;
  }
  geo.setAttribute('color', new THREE.Float32BufferAttribute(initColors, 3));

  // size 按 centrality (0-0.51) 线性插值
  const sizes = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const cent = DATA.nodes[i].centrality || 0;
    sizes[i] = NODE_BASE_SIZE + CENTRALITY_SIZE_GAIN * (cent / 0.5);
  }
  geo.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));

  const sprite = makeNodeSprite();
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      pointTexture: { value: sprite },
    },
    vertexShader: `
      attribute float size;
      varying vec3 vColor;
      void main() {
        vColor = color;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = size * (380.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      uniform sampler2D pointTexture;
      varying vec3 vColor;
      void main() {
        vec4 tex = texture2D(pointTexture, gl_PointCoord);
        if (tex.a < 0.1) discard;
        gl_FragColor = vec4(vColor, tex.a);
      }
    `,
    vertexColors: true,
    transparent: true,
    depthWrite: false,
  });

  pointsMesh = new THREE.Points(geo, mat);
  pointsMesh.frustumCulled = false; // 球面节点都在原点周围, 不需要剔除
  scene.add(pointsMesh);
}

// 大圆弧 slerp 插值 (精确公式, 不用 user 提供的近似)
function slerpArc(A, B, segments) {
  const omega = Math.acos(Math.max(-1, Math.min(1, A.dot(B))));
  if (omega < 1e-5) {
    // 几乎重合 — 直接返回
    return [A.clone(), B.clone()];
  }
  const sinOmega = Math.sin(omega);
  const out = new Array(segments + 1);
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const a = Math.sin((1 - t) * omega) / sinOmega;
    const b = Math.sin(t * omega) / sinOmega;
    out[i] = A.clone().multiplyScalar(a).add(B.clone().multiplyScalar(b));
  }
  return out;
}

function buildEdgeMesh() {
  const segments = EDGE_SEGMENTS;
  const totalPts = edgesData.length * (segments + 1);
  const linePositions = new Float32Array(totalPts * 3);

  let pIdx = 0;
  const A = new THREE.Vector3();
  const B = new THREE.Vector3();
  for (const e of edgesData) {
    A.set(nodePositions[e.fromIdx*3], nodePositions[e.fromIdx*3+1], nodePositions[e.fromIdx*3+2]);
    B.set(nodePositions[e.toIdx*3], nodePositions[e.toIdx*3+1], nodePositions[e.toIdx*3+2]);
    const arc = slerpArc(A, B, segments);
    for (const p of arc) {
      linePositions[pIdx*3] = p.x;
      linePositions[pIdx*3+1] = p.y;
      linePositions[pIdx*3+2] = p.z;
      pIdx++;
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
  const mat = new THREE.LineBasicMaterial({
    color: edgeBaseColor,
    transparent: true,
    opacity: EDGE_BASE_OPACITY,
    depthWrite: false,
  });
  linesMesh = new THREE.Line(geo, mat);
  linesMesh.frustumCulled = false;
  scene.add(linesMesh);
}

// 选中节点时高亮它的邻居边 — 单独一个 mesh, 重建
function buildHighlightEdgeMesh() {
  if (linesHighlightMesh) {
    scene.remove(linesHighlightMesh);
    linesHighlightMesh.geometry.dispose();
    linesHighlightMesh.material.dispose();
  }
  if (selectedNodeIdx === null) {
    linesHighlightMesh = null;
    return;
  }
  const neighborSet = neighborMap.get(selectedNodeIdx) || new Set();
  if (neighborSet.size === 0) {
    linesHighlightMesh = null;
    return;
  }
  const segments = EDGE_SEGMENTS;
  // 选中节点直接相邻的边
  const selEdges = edgesData.filter(e =>
    e.fromIdx === selectedNodeIdx || e.toIdx === selectedNodeIdx
  );
  const totalPts = selEdges.length * (segments + 1);
  const linePositions = new Float32Array(totalPts * 3);
  let pIdx = 0;
  const A = new THREE.Vector3();
  const B = new THREE.Vector3();
  for (const e of selEdges) {
    A.set(nodePositions[e.fromIdx*3], nodePositions[e.fromIdx*3+1], nodePositions[e.fromIdx*3+2]);
    B.set(nodePositions[e.toIdx*3], nodePositions[e.toIdx*3+1], nodePositions[e.toIdx*3+2]);
    const arc = slerpArc(A, B, segments);
    for (const p of arc) {
      linePositions[pIdx*3] = p.x;
      linePositions[pIdx*3+1] = p.y;
      linePositions[pIdx*3+2] = p.z;
      pIdx++;
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
  // 用一个亮色 (用选中节点的学科色)
  const selColor = nodeBaseColors[selectedNodeIdx].clone().lerp(new THREE.Color(0xffffff), 0.4);
  const mat = new THREE.LineBasicMaterial({
    color: selColor,
    transparent: true,
    opacity: EDGE_NEIGHBOR_OPACITY,
    depthWrite: false,
  });
  linesHighlightMesh = new THREE.Line(geo, mat);
  linesHighlightMesh.frustumCulled = false;
  scene.add(linesHighlightMesh);
}

// ============== 交互 ==============
function setupInteraction() {
  const dom = renderer.domElement;
  const raycaster = new THREE.Raycaster();
  raycaster.params.Points.threshold = POINT_RAYCAST_THRESHOLD;
  const pointer = new THREE.Vector2();

  // 区分 click vs drag — pointerdown 记位置, pointerup 看距离
  let pdownX = 0, pdownY = 0, pdownT = 0;
  dom.addEventListener('pointerdown', (e) => {
    pdownX = e.clientX; pdownY = e.clientY; pdownT = performance.now();
  });
  dom.addEventListener('pointerup', (e) => {
    const dx = e.clientX - pdownX;
    const dy = e.clientY - pdownY;
    const dt = performance.now() - pdownT;
    if (Math.sqrt(dx*dx + dy*dy) < 5 && dt < 400) {
      // click
      const rect = dom.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObject(pointsMesh);
      if (hits.length > 0) {
        const idx = hits[0].index;
        selectNode(idx);
      } else {
        clearSelection();
      }
    }
  });

  // hover tooltip
  let lastTipIdx = -1;
  dom.addEventListener('pointermove', (e) => {
    const rect = dom.getBoundingClientRect();
    pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObject(pointsMesh);
    const tip = document.getElementById('tip');
    if (hits.length > 0) {
      const idx = hits[0].index;
      if (idx !== lastTipIdx) {
        lastTipIdx = idx;
        const node = DATA.nodes[idx];
        document.getElementById('tip-sw').style.background = PALETTE[node.subject] || '#888';
        document.getElementById('tip-ts').textContent = `${window.tSubject(node.subject)} · G${node.grade_start || ''}`;
        document.getElementById('tip-ttl').textContent = node.title;
        tip.classList.add('on');
      }
      tip.style.left = (e.clientX + 14) + 'px';
      tip.style.top = (e.clientY + 14) + 'px';
    } else {
      if (lastTipIdx !== -1) {
        lastTipIdx = -1;
        tip.classList.remove('on');
      }
    }
  });
  dom.addEventListener('pointerleave', () => {
    lastTipIdx = -1;
    document.getElementById('tip').classList.remove('on');
  });

  // 用户拖动 → 关掉 auto-rotate
  controls.addEventListener('start', () => {
    if (controls.autoRotate) {
      controls.autoRotate = false;
      const btn = document.getElementById('toggleAutoRotate');
      btn.textContent = '▶ 自动旋转';
      btn.setAttribute('aria-pressed', 'false');
    }
  });

  // 键盘 ESC 关卡片
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      clearSelection();
      const si = document.getElementById('searchInput');
      if (si && document.activeElement === si) si.blur();
      document.getElementById('searchResults').classList.remove('on');
    }
  });
}

function selectNode(idx) {
  selectedNodeIdx = idx;
  const node = DATA.nodes[idx];
  showCard(node);
  highlightNode(idx);
}

function clearSelection() {
  if (selectedNodeIdx === null) return;
  selectedNodeIdx = null;
  window._currentNode = null;
  document.getElementById('card').classList.remove('on');
  document.getElementById('card').setAttribute('aria-hidden', 'true');
  applyFilterToColors(); // 重置颜色
  buildHighlightEdgeMesh();
}

function highlightNode(idx) {
  const neighborSet = neighborMap.get(idx) || new Set();
  const colors = pointsMesh.geometry.attributes.color.array;
  for (let i = 0; i < DATA.nodes.length; i++) {
    const c = nodeBaseColors[i];
    if (i === idx) {
      // 选中: 提亮 + 加白
      colors[i*3] = Math.min(1, c.r * 0.5 + 0.85);
      colors[i*3+1] = Math.min(1, c.g * 0.5 + 0.85);
      colors[i*3+2] = Math.min(1, c.b * 0.5 + 0.85);
    } else if (neighborSet.has(i)) {
      colors[i*3] = c.r; colors[i*3+1] = c.g; colors[i*3+2] = c.b;
    } else {
      // 非邻居: 压暗到 0.15
      colors[i*3] = c.r * 0.18;
      colors[i*3+1] = c.g * 0.18;
      colors[i*3+2] = c.b * 0.18;
    }
  }
  pointsMesh.geometry.attributes.color.needsUpdate = true;
  buildHighlightEdgeMesh();
}

// 学科过滤 (chip 点击) — 隐藏非选中学科
function applyFilterToColors() {
  if (selectedNodeIdx !== null) {
    highlightNode(selectedNodeIdx);
    return;
  }
  const colors = pointsMesh.geometry.attributes.color.array;
  for (let i = 0; i < DATA.nodes.length; i++) {
    const subject = DATA.nodes[i].subject;
    const c = nodeBaseColors[i];
    if (activeGroups.has(subject)) {
      colors[i*3] = c.r; colors[i*3+1] = c.g; colors[i*3+2] = c.b;
    } else {
      // 隐藏: 压暗到接近背景色
      colors[i*3] = 0.018;
      colors[i*3+1] = 0.024;
      colors[i*3+2] = 0.038;
    }
  }
  pointsMesh.geometry.attributes.color.needsUpdate = true;
}

// ============== UI: 卡片 ==============
// 复用 2D app.js 的 showCard 逻辑, 但用 3D 的邻接表
function showCard(node) {
  const card = document.getElementById('card');
  window._currentNode = node;
  document.getElementById('card-sw').style.background = PALETTE[node.subject] || '#888';
  document.getElementById('card-cs').textContent = `${window.tSubject(node.subject)} · G${node.grade_start || ''}-${node.grade_end || ''} · ${node.domain || ''}`;
  document.getElementById('card-ctl').textContent = node.title;

  // tags
  const tagRow = document.getElementById('card-tags');
  tagRow.innerHTML = '';
  (node.bloom || []).forEach(b => {
    const t = document.createElement('span');
    t.className = 'tag bloom';
    t.textContent = '✦ ' + b;
    tagRow.appendChild(t);
  });
  if (node.difficulty) {
    const t = document.createElement('span');
    t.className = 'tag diff-' + node.difficulty;
    t.textContent = "..." + ' ' + '●'.repeat(node.difficulty) + '○'.repeat(5 - node.difficulty);
    tagRow.appendChild(t);
  }
  if (node.estimated_minutes) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = '⏱ ' + node.estimated_minutes + ' ' + "...";
    tagRow.appendChild(t);
  }
  if (node.subdomain) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = node.subdomain;
    tagRow.appendChild(t);
  }

  // 内容要求
  const cr = document.getElementById('card-content-req');
  const crBlock = document.getElementById('card-content-req-block');
  if (node.content_req) { cr.textContent = node.content_req; crBlock.style.display = ''; }
  else { crBlock.style.display = 'none'; }

  // 页码
  const pageLink = document.getElementById('card-page-link');
  if (node.src_page) {
    const srcText = "...";
    pageLink.innerHTML = ` · <a class="src-link" href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">P${node.src_page} ${srcText}</a>`;
  } else pageLink.textContent = '';

  // 学业要求
  const ar = document.getElementById('card-academic-req');

  // V3.3.4 深度内容增强: 3 教师用书级字段
  ['real-examples', 'common-mistakes', 'teaching-activity'].forEach(k => {
    const block = document.getElementById('card-' + k + '-block');
    const body = document.getElementById('card-' + k);
    const key = k.replace(/-/g, '_');
    if (node[key]) {
      block.style.display = '';
      body.textContent = node[key];
    } else {
      block.style.display = 'none';
    }
  });

  const arBlock = document.getElementById('card-academic-req-block');
  if (node.academic_req) { ar.textContent = node.academic_req; arBlock.style.display = ''; }
  else { arBlock.style.display = 'none'; }

  // 知识要点
  const kp = document.getElementById('card-key-points');
  const kpBlock = document.getElementById('card-key-points-block');
  kp.innerHTML = '';
  if (node.key_points && node.key_points.length) {
    node.key_points.forEach(p => {
      const d = document.createElement('div');
      d.className = 'kp';
      d.textContent = p;
      kp.appendChild(d);
    });
    kpBlock.style.display = '';
  } else kpBlock.style.display = 'none';

  // 例题
  const exRow = document.getElementById('card-examples');
  const exBlock = document.getElementById('card-examples-block');
  exRow.innerHTML = '';
  if (node.examples && node.examples.length) {
    node.examples.forEach(ex => {
      const t = document.createElement('span');
      t.className = 'ex';
      t.textContent = ex;
      exRow.appendChild(t);
    });
    exBlock.style.display = '';
  } else exBlock.style.display = 'none';

  // 评估提示
  const assBlock = document.getElementById('card-assessment-block');
  const ass = document.getElementById('card-assessment');
  if (node.assessment_prompt) { ass.textContent = node.assessment_prompt; assBlock.style.display = ''; }
  else { assBlock.style.display = 'none'; }

  // 元信息
  const metaBlock = document.getElementById('card-meta-block');
  const meta = document.getElementById('card-meta');
  const metaItems = [];
  if (node.type) metaItems.push(`<span class="meta-tag type-${node.type.toLowerCase()}">${node.type}</span>`);
  if (node.age_range_start) metaItems.push(`<span class="meta-tag">🎂 ${node.age_range_start}-${node.age_range_end || node.age_range_start} 岁</span>`);
  if (node.centrality !== undefined) {
    const centPct = Math.round(node.centrality * 100);
    metaItems.push(`<span class="meta-tag" title="中心度 (被需要 + 能解锁)">⭐ 中心度 ${centPct}%</span>`);
  }
  if (node.bloom) metaItems.push(`<span class="meta-tag bloom-tag">${node.bloom}</span>`);
  if (metaItems.length) { meta.innerHTML = metaItems.join(' '); metaBlock.style.display = ''; }
  else metaBlock.style.display = 'none';

  // 边的 reason + rows — 用 3D 的邻接表
  const allPre = edgesToFrom.get(nodeIdToIndex.get(node.id)) || [];
  const allNext = edgesFromTo.get(nodeIdToIndex.get(node.id)) || [];
  const preEdges = allPre.filter(e => e.rel !== 'relates_to');
  const nextEdges = allNext.filter(e => e.rel !== 'relates_to');
  const softPre = allPre.filter(e => e.rel === 'relates_to');
  const softNext = allNext.filter(e => e.rel === 'relates_to');

  const preLabel = document.querySelector('.sec-pre .label');
  preLabel.innerHTML = `<span >直接先决</span> · <span class="k" id="card-pre-k">${preEdges.length}</span>${softPre.length ? ` <span class="soft-hint">(+${softPre.length} 软关联)</span>` : ''}`;
  const nextLabel = document.querySelector('.sec-next .label');
  nextLabel.innerHTML = `<span >解锁后继</span> · <span class="k" id="card-next-k">${nextEdges.length}</span>${softNext.length ? ` <span class="soft-hint">(+${softNext.length} 软关联)</span>` : ''}`;

  // 边 reason
  const fillReasons = (container, edges, side) => {
    container.innerHTML = '';
    const withReason = edges.filter(e => e.reason);
    withReason.slice(0, 3).forEach(e => {
      const otherIdx = side === 'pre' ? e.fromIdx : e.toIdx;
      const relLabels = { prerequisite: '先决', progresses_to: '进阶', relates_to: '关联' };
      const d = document.createElement('div');
      d.className = 'reason-row';
      d.innerHTML = `<span class="rel-tag rel-${e.rel}">${relLabels[e.rel] || e.rel}</span><span class="reason-txt">${e.reason}</span>`;
      container.appendChild(d);
    });
  };
  fillReasons(document.getElementById('card-pre-reasons'), preEdges, 'pre');
  fillReasons(document.getElementById('card-next-reasons'), nextEdges, 'next');

  // 邻接 rows
  const fillRows = (container, edges, side) => {
    container.innerHTML = '';
    if (!edges.length) {
      const d = document.createElement('div');
      d.className = 'empty';
      d.textContent = "...";
      container.appendChild(d);
      return;
    }
    edges.forEach(e => {
      const otherIdx = side === 'pre' ? e.fromIdx : e.toIdx;
      const data = DATA.nodes[otherIdx];
      const btn = document.createElement('button');
      btn.className = 'row';
      btn.innerHTML = `<span class="rdot" style="background:${PALETTE[data.subject] || '#888'}"></span><span class="rt">${data.title}</span><span class="ra">G${data.grade_start || ''}</span>`;
      btn.onclick = () => {
        selectNode(otherIdx);
      };
      container.appendChild(btn);
    });
  };
  fillRows(document.getElementById('card-pre-rows'), preEdges, 'pre');
  fillRows(document.getElementById('card-next-rows'), nextEdges, 'next');

  card.classList.add('on');
  card.setAttribute('aria-hidden', 'false');
}

function setupCardClose() {
  document.querySelector('#card .close').onclick = () => clearSelection();
}

// ============== UI: 图例 ==============
function buildLegend() {
  const legend = document.getElementById('legend');
  legend.innerHTML = '';
  const counts = GROUPS.map(s => DATA.nodes.filter(n => n.subject === s).length);
  GROUPS.forEach((s, i) => {
    const el = document.createElement('div');
    el.className = 'chip';
    el.dataset.subject = s;
    el.setAttribute('role', 'button');
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-pressed', 'true');
    el.setAttribute('aria-label', `${"..." || '切换'} ${window.tSubject(s)} ${counts[i]} ${"..." || '个概念'}`);
    el.innerHTML = `<span class="sw" style="background:${PALETTE[s]}"></span><span class="nm">${window.tSubject(s)}</span><span class="ct">${counts[i]}</span>`;
    el.onclick = () => {
      el.classList.toggle('off');
      el.setAttribute('aria-pressed', el.classList.contains('off') ? 'false' : 'true');
      if (el.classList.contains('off')) activeGroups.delete(s);
      else activeGroups.add(s);
      applyFilterToColors();
    };
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.click(); }
    });
    legend.appendChild(el);
  });
}

// ============== UI: 搜索 ==============
function setupSearch() {
  const input = document.getElementById('searchInput');
  const results = document.getElementById('searchResults');
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { results.classList.remove('on'); return; }
    const matches = [];
    for (let i = 0; i < DATA.nodes.length; i++) {
      const n = DATA.nodes[i];
      const titleLc = n.title ? n.title.toLowerCase() : '';
      if (n.id.toLowerCase().includes(q) || titleLc.includes(q) ||
          (n.subdomain && n.subdomain.toLowerCase().includes(q))) {
        matches.push({ idx: i, node: n });
      }
    }
    results.innerHTML = '';
    const count = document.createElement('div');
    count.className = 'r-count';
    count.textContent = `${matches.length} ${"..." || '匹配'}`;
    results.appendChild(count);
    if (matches.length === 0) {
      const e = document.createElement('div');
      e.className = 'r-empty';
      e.textContent = "..." || '无匹配概念';
      results.appendChild(e);
    } else {
      matches.slice(0, 50).forEach((m, k) => {
        const it = document.createElement('div');
        it.className = 'r-item';
        it.innerHTML = `<span class="r-dot" style="background:${PALETTE[m.node.subject] || '#888'}"></span><span class="r-t">${m.node.title}</span><span class="r-m">G${m.node.grade_start || ''}</span>`;
        it.onclick = () => {
          selectNode(m.idx);
          results.classList.remove('on');
          input.value = '';
        };
        results.appendChild(it);
      });
    }
    results.classList.add('on');
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search')) results.classList.remove('on');
  });
}

// ============== UI: 暂停旋转 ==============
function setupAutoRotateToggle() {
  const btn = document.getElementById('toggleAutoRotate');
  btn.onclick = () => {
    controls.autoRotate = !controls.autoRotate;
    btn.textContent = controls.autoRotate ? '⏸ 暂停旋转' : '▶ 自动旋转';
    btn.setAttribute('aria-pressed', controls.autoRotate ? 'true' : 'false');
  };
}

// ============== Resize / Loop ==============
function onResize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);

  // FPS — 每 500ms 算一次
  fpsFrames++;
  const now = performance.now();
  const elapsed = now - fpsLastTime;
  if (elapsed >= 500) {
    const fps = Math.round(fpsFrames * 1000 / elapsed);
    fpsFrames = 0;
    fpsLastTime = now;
    const fpsEl = document.getElementById('fps');
    fpsEl.textContent = fps;
    fpsEl.classList.remove('fps-low', 'fps-bad');
    if (fps < 30) fpsEl.classList.add('fps-bad');
    else if (fps < 50) fpsEl.classList.add('fps-low');
  }
}

// 启动
init();
