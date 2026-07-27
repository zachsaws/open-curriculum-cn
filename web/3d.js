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

// ============== 谱系 (lineage) — BFS 反向追溯所有直接+间接先决 (V3.6.2) ==============
let lineageNodes = new Set();    // idx set
let lineageEdgeIdxs = new Set(); // edgesData 索引 set
let lineageHighRisk = new Set(); // V3.6.9: lineage 中中心度 Top 3 (高危标识)
let lineageMesh = null;          // 高亮 lineage 边的 Line mesh

// ============== 选中节点放大 + camera tween (V3.6.3) ==============
let focusGain = null;            // Float32Array, per node 0..1
let focusGainTarget = new Float32Array(0);  // 目标值 (选中=1, 其他=0)
let cameraTween = null;          // {startPos, endPos, startTime, duration}

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

  // V3.6.9 fix debug: ?debug=1 暴露内部变量 (验证 + 自动化测试)
  if (location.search.includes('debug=1') && typeof window !== 'undefined') {
    window.__occ3d = { DATA, GROUPS, selectNode, showCard, clearSelection, camera, controls, renderer, pointsMesh, scene, edgesFromTo, edgesToFrom };
    console.log('[debug] window.__occ3d 已暴露, 用 __occ3d.selectNode(idx) 测试');
  }
}

// V3.6.10b: 删掉 set3DHeader 死代码 (没被调用, 标题/副标已集成在 HTML 里)
// 之前它会覆盖 HTML 里的 K12 logo + 教育部副标, 造成回退到 "Fibonacci 黄金角" 这种开发者话

// ============== 数据加载 ==============
async function loadData() {
  // V3.6.9: 用 data-cache.js 共享 localStorage 缓存 (冷启 <1s 热, 30s+ 冷)
  try {
    DATA = await loadGraphData();
  } catch (e) {
    const msg = document.getElementById('loadingMsg');
    msg.innerHTML = `<div class="err">未找到图谱数据 (graph.json / .gz)<br><br>${e.message}</div>`;
    console.error(e);
    return;
  }
  GROUPS = [...new Set(DATA.nodes.map(n => n.subject))].sort();
  activeGroups = new Set(GROUPS);
  // 缓存原始 title (用于繁简切换)
  DATA.nodes.forEach(n => { titleOrig.set(n.id, n.title); });

  // V3.6.10b: 删掉 nCount/eCount/gCount 更新 (不显示给用户)
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

  // V3.6.3: focusGain (0..1) 选中节点时 = 1.0, 其他 = 0, 缓动后节点放大 1.6x
  focusGain = new Float32Array(N);
  geo.setAttribute('focusGain', new THREE.Float32BufferAttribute(focusGain, 1));

  const sprite = makeNodeSprite();
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      pointTexture: { value: sprite },
    },
    vertexShader: `
      attribute float size;
      attribute float focusGain;
      varying vec3 vColor;
      varying float vFocusGain;
      varying float vDepth;
      void main() {
        vColor = color;
        vFocusGain = focusGain;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        // V3.6.4: depth fog 准备 — 归一化 z 到 0..1, 0=远, 1=近
        // camera 默认距原点 ~200, 球面半径 100, 所以 mvPosition.z 范围 ~-300..-100
        vDepth = clamp((-mvPosition.z - 100.0) / 200.0, 0.0, 1.0);
        gl_PointSize = size * (1.0 + focusGain * 0.6) * (380.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      uniform sampler2D pointTexture;
      varying vec3 vColor;
      varying float vFocusGain;
      varying float vDepth;
      void main() {
        vec4 tex = texture2D(pointTexture, gl_PointCoord);
        if (tex.a < 0.1) discard;
        vec3 col = vColor;
        // V3.6.4: depth fog (跟 Marble 漏斗一致: 远的点 alpha 0.55, 近的 1.0, 中间线性)
        float fog = 0.55 + 0.45 * vDepth;
        // V3.6.3: 白色高亮环 (vFocusGain > 0.5 时, 在 0.85-0.97 半径范围画白环)
        if (vFocusGain > 0.5) {
          vec2 uv = gl_PointCoord - vec2(0.5);
          float d = length(uv) * 2.0;  // 0..1
          if (d > 0.85 && d < 0.97) {
            col = mix(vColor, vec3(1.0), 0.95);
          }
        }
        gl_FragColor = vec4(col * fog, tex.a * fog);
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

// ============== 谱系 BFS (跟 funnel.js 1:1 复刻, 沿 edgesFromTo 反向走) ==============
// 沿 edgesFromTo (u 是 from) BFS, 找 u 的所有直接 + 间接先决 (e.toIdx)
function buildLineage(startIdx) {
  const nodes = new Set([startIdx]);
  const edges = new Set();
  const q = [startIdx];
  while (q.length) {
    const u = q.shift();
    const outEdges = edgesFromTo.get(u) || [];
    for (const e of outEdges) {
      edges.add(e.edgeIdx);
      if (!nodes.has(e.toIdx)) {
        nodes.add(e.toIdx);
        q.push(e.toIdx);
      }
    }
  }
  lineageNodes = nodes;
  lineageEdgeIdxs = edges;

  // V3.6.9: 高危标识 — lineage 中中心度 Top 3 (排除选中)
  const cands = [];
  for (const ni of nodes) {
    if (ni === startIdx) continue;
    cands.push({ idx: ni, c: DATA.nodes[ni].c || 0 });
  }
  cands.sort((a, b) => b.c - a.c);
  lineageHighRisk = new Set(cands.slice(0, 3).map(x => x.idx));
}

// Lineage 边 mesh — 用选中节点学科色 lerp 白 0.5, opacity 0.75 (比邻居边 0.55 更亮)
function buildLineageEdgeMesh() {
  if (lineageMesh) {
    scene.remove(lineageMesh);
    lineageMesh.geometry.dispose();
    lineageMesh.material.dispose();
  }
  if (selectedNodeIdx === null || lineageEdgeIdxs.size === 0) {
    lineageMesh = null;
    return;
  }
  const segments = EDGE_SEGMENTS;
  const totalPts = lineageEdgeIdxs.size * (segments + 1);
  const linePositions = new Float32Array(totalPts * 3);
  let pIdx = 0;
  const A = new THREE.Vector3();
  const B = new THREE.Vector3();
  for (const ei of lineageEdgeIdxs) {
    const e = edgesData[ei];
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
  const selColor = nodeBaseColors[selectedNodeIdx].clone().lerp(new THREE.Color(0xffffff), 0.5);
  const mat = new THREE.LineBasicMaterial({
    color: selColor,
    transparent: true,
    opacity: 0.75,
    depthWrite: false,
  });
  lineageMesh = new THREE.Line(geo, mat);
  lineageMesh.frustumCulled = false;
  scene.add(lineageMesh);
}

// ============== 选中节点放大 + camera tween (V3.6.3, 跟 funnel.js focusNode 思路一致) ==============
// focusGain target: 选中 = 1.0, 其他 = 0.0
function setFocusGainTarget(idx) {
  if (!focusGain || focusGainTarget.length !== DATA.nodes.length) {
    focusGainTarget = new Float32Array(DATA.nodes.length);
  } else {
    focusGainTarget.fill(0);
  }
  if (idx !== null) focusGainTarget[idx] = 1.0;
}

// focusNode: 旋转相机让节点 idx 朝向屏幕中央 (球形态: 保持距原点距离不变, 改方向)
function focusNode(idx) {
  const pos = pointsMesh.geometry.attributes.position.array;
  const tx = pos[idx*3], ty = pos[idx*3+1], tz = pos[idx*3+2];
  // 当前 camera 距原点距离 (球面切线半径)
  const R = camera.position.length();
  // 目标位置: 节点方向, 保持 R 不变
  const len = Math.sqrt(tx*tx + ty*ty + tz*tz);
  if (len < 1e-3) return;
  const endPos = new THREE.Vector3(tx / len * R, ty / len * R, tz / len * R);
  cameraTween = {
    startPos: camera.position.clone(),
    endPos,
    startTime: performance.now(),
    duration: 450,  // 0.45s
  };
  controls.enabled = false;  // 暂时禁掉 OrbitControls, 避免用户拖动冲突
}

// 在 animate() 里每帧调
function updateCameraTween() {
  if (!cameraTween) return;
  const t = (performance.now() - cameraTween.startTime) / cameraTween.duration;
  if (t >= 1) {
    camera.position.copy(cameraTween.endPos);
    camera.lookAt(0, 0, 0);
    cameraTween = null;
    controls.enabled = true;
    controls.update();  // 同步 OrbitControls 内部 spherical
    return;
  }
  // ease-out cubic
  const eased = 1 - Math.pow(1 - t, 3);
  camera.position.lerpVectors(cameraTween.startPos, cameraTween.endPos, eased);
  camera.lookAt(0, 0, 0);
}

// focusGain 缓动 (每帧 lerp, 0.15 系数)
function updateFocusGain() {
  if (!focusGain || !focusGainTarget || focusGain.length !== focusGainTarget.length) return;
  let changed = false;
  for (let i = 0; i < focusGain.length; i++) {
    const diff = focusGainTarget[i] - focusGain[i];
    if (Math.abs(diff) > 0.005) {
      focusGain[i] += diff * 0.15;
      changed = true;
    } else if (Math.abs(diff) > 0) {
      focusGain[i] = focusGainTarget[i];
      changed = true;
    }
  }
  if (changed) {
    pointsMesh.geometry.attributes.focusGain.needsUpdate = true;
  }
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
        document.getElementById('tip-ts').textContent = `${node.subject} · G${node.grade_start || ''}`;
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
  // V3.6.5: 先 highlightNode (它会 buildLineage), 后 showCard (lin-stats 用 lineageNodes)
  highlightNode(idx);
  showCard(node);
  // V3.6.3: 相机 tween + 选中节点放大
  setFocusGainTarget(idx);
  focusNode(idx);
}

function clearSelection() {
  if (selectedNodeIdx === null) return;
  selectedNodeIdx = null;
  window._currentNode = null;
  document.getElementById('card').classList.remove('on');
  document.getElementById('card').setAttribute('aria-hidden', 'true');
  // V3.6.2: 清掉 lineage 状态
  lineageNodes = new Set();
  lineageEdgeIdxs = new Set();
  lineageHighRisk = new Set();
  if (lineageMesh) { scene.remove(lineageMesh); lineageMesh.geometry.dispose(); lineageMesh.material.dispose(); lineageMesh = null; }
  // V3.6.3: focusGain 全设 0
  setFocusGainTarget(null);
  applyFilterToColors(); // 重置颜色
  buildHighlightEdgeMesh();
  buildLineageEdgeMesh();
}

function highlightNode(idx) {
  // V3.6.2: 沿 edgesFromTo BFS 反向追溯所有直接 + 间接先决
  buildLineage(idx);
  const colors = pointsMesh.geometry.attributes.color.array;
  for (let i = 0; i < DATA.nodes.length; i++) {
    const c = nodeBaseColors[i];
    if (i === idx) {
      // 选中: 提亮 + 加白
      colors[i*3] = Math.min(1, c.r * 0.5 + 0.85);
      colors[i*3+1] = Math.min(1, c.g * 0.5 + 0.85);
      colors[i*3+2] = Math.min(1, c.b * 0.5 + 0.85);
    } else if (lineageHighRisk.has(i)) {
      // V3.6.9: 高危节点 (lineage 中心度 Top 3): 偏红
      colors[i*3] = Math.min(1, c.r * 0.5 + 0.95 * 0.4);
      colors[i*3+1] = Math.min(1, c.g * 0.2);
      colors[i*3+2] = Math.min(1, c.b * 0.2);
    } else if (lineageNodes.has(i)) {
      // lineage 节点 (含直接邻居 + 间接先决): 保持原色
      colors[i*3] = c.r; colors[i*3+1] = c.g; colors[i*3+2] = c.b;
    } else {
      // 非 lineage: 压暗到 0.18
      colors[i*3] = c.r * 0.18;
      colors[i*3+1] = c.g * 0.18;
      colors[i*3+2] = c.b * 0.18;
    }
  }
  pointsMesh.geometry.attributes.color.needsUpdate = true;
  buildHighlightEdgeMesh();
  buildLineageEdgeMesh();
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
  document.getElementById('card-cs').textContent = `${node.subject} · G${node.grade_start || ''}-${node.grade_end || ''} · ${node.domain || ''}`;
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
    // V3.6.10c: 删 "..." 真字符 (之前 V3.6.2 留的占位), 改成"难度"前缀更清楚
    t.textContent = '难度 ' + '●'.repeat(node.difficulty) + '○'.repeat(5 - node.difficulty);
    tagRow.appendChild(t);
  }
  if (node.estimated_minutes) {
    const t = document.createElement('span');
    t.className = 'tag min';
    // V3.6.10c: 删 "..." 真字符, 改成"约 N 分钟"更自然
    t.textContent = '⏱ 约 ' + node.estimated_minutes + ' 分钟';
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
    pageLink.innerHTML = ` · <a class="src-link" href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">P${node.src_page} 查看</a>`;
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

  // V3.6.9 教学话术 (description 字段, 老师口吻 3 句话)
  const tvBlock = document.getElementById('card-teaching-voice-block');
  const tvBody = document.getElementById('card-teaching-voice');
  if (node.description) {
    tvBody.textContent = node.description;
    tvBlock.style.display = '';
  } else {
    tvBlock.style.display = 'none';
  }

  // V3.6.9 打印版按钮
  const printBtn = document.getElementById('card-print-btn');
  if (printBtn) printBtn.href = './print.html?id=' + encodeURIComponent(node.id);

  // V3.6.9 分享学习卡按钮
  const shareBtn = document.getElementById('card-share-btn');
  if (shareBtn) {
    shareBtn.onclick = () => {
      if (typeof showShareCard === 'function') {
        // V3.6.9 fix: 3d.js 用 DATA.nodes (跟 funnel.js 一样), 不要再用 NODES/NODES3D
        showShareCard(node, DATA.nodes);
      } else {
        alert('share.js 加载失败');
      }
    };
  }

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

  // 元信息 — V3.6.10c: 标签用户化 (FACTUAL/中心度/6-7 岁 改成中文+更直白)
  const metaBlock = document.getElementById('card-meta-block');
  const meta = document.getElementById('card-meta');
  const metaItems = [];
  const TYPE_CN = { FACTUAL: '📘 事实型', PROCEDURAL: '🔧 步骤型', CONCEPTUAL: '💡 概念型' };
  if (node.type) metaItems.push(`<span class="meta-tag type-${node.type.toLowerCase()}">${TYPE_CN[node.type] || node.type}</span>`);
  // V3.6.10c: 用 grade_start 替代 age_range (用户更熟悉年级, 不是"6-7 岁")
  if (node.grade_start && node.grade_end && node.grade_start === node.grade_end) {
    metaItems.push(`<span class="meta-tag">📅 ${node.grade_start} 年级</span>`);
  } else if (node.grade_start && node.grade_end) {
    metaItems.push(`<span class="meta-tag">📅 ${node.grade_start}-${node.grade_end} 年级</span>`);
  }
  // V3.6.10c: 中心度 7% 改成"重要度 7%" (更直白, tooltip 解释)
  if (node.centrality !== undefined) {
    const centPct = Math.round(node.centrality * 100);
    metaItems.push(`<span class="meta-tag" title="重要度: 这个概念被多少个其他概念依赖 + 能解锁多少新概念。越高越关键。">📊 重要度 ${centPct}%</span>`);
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
  preLabel.innerHTML = `<span >先要会</span> · <span class="k" id="card-pre-k">${preEdges.length}</span>${softPre.length ? ` <span class="soft-hint">(+${softPre.length} 软关联)</span>` : ''}`;
  const nextLabel = document.querySelector('.sec-next .label');
  nextLabel.innerHTML = `<span >之后能学</span> · <span class="k" id="card-next-k">${nextEdges.length}</span>${softNext.length ? ` <span class="soft-hint">(+${softNext.length} 软关联)</span>` : ''}`;

  // 边 reason — V3.6.10c: relLabels 按 side 区分 (pre 边 = "需要先会", next 边 = "之后能学")
  // 不再共用一张表, 避免"之后能学"区显示"前置"字样的矛盾
  const fillReasons = (container, edges, side) => {
    container.innerHTML = '';
    const withReason = edges.filter(e => e.reason);
    const relLabels = {
      pre:  { prerequisite: '需要先会', progresses_to: '需要先会', relates_to: '相关' },
      next: { prerequisite: '之后能学', progresses_to: '之后能学', relates_to: '相关' }
    };
    withReason.slice(0, 3).forEach(e => {
      const otherIdx = side === 'pre' ? e.fromIdx : e.toIdx;
      const d = document.createElement('div');
      d.className = 'reason-row';
      const tag = relLabels[side][e.rel] || e.rel;
      d.innerHTML = `<span class="rel-tag rel-${e.rel}">${tag}</span><span class="reason-txt">${e.reason}</span>`;
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
      // V3.6.10c: 删 "..." 真字符, 改成"无直接先要会" / "无之后能学"
      d.textContent = side === 'pre' ? '没有先要会的概念 (起点或独立概念)' : '暂无之后能学的概念';
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

  // V3.6.2: lineage 统计 (跟 funnel.js 一致, V3.6.5 改成用 highlightNode 已算的 lineageNodes)
  const linStats = document.getElementById('card-lin-stats');
  const linN = document.getElementById('card-lin-n');
  const linU = document.getElementById('card-lin-u');
  const linSub = document.getElementById('card-lin-sub');
  if (linStats && linN && linU && linSub) {
    const cnt = lineageNodes.size - 1;  // 减去自己
    linN.textContent = cnt;
    if (cnt === 0) {
      linU.textContent = '起点节点';
      linStats.classList.add('empty');
      linSub.textContent = '之前没有要学的概念 — 这是可学起的入口, 单击反向追溯会立刻回到这里.';
    } else if (cnt === 1) {
      linU.textContent = '之前要学的 (全部)';
      linStats.classList.remove('empty');
      linSub.textContent = '只需掌握 1 个前置 (含直接 + 间接), 即可学这个概念.';
    } else {
      linU.textContent = '之前要学的 (全部)';
      linStats.classList.remove('empty');
      linSub.textContent = `从起点到此概念, 共需掌握 ${cnt} 个前置 (含直接 + 间接). 已高亮显示在球中.`;
    }
  }

  card.classList.add('on');
  card.setAttribute('aria-hidden', 'false');
}

function setupCardClose() {
  document.querySelector('#card .close').onclick = () => clearSelection();
}

// ============== UI: 图例 ==============
// V3.6.10b: SUBJECT_CN 抽到 subject-cn.js 共享 (从 window 拿)

function buildLegend() {
  const legend = document.getElementById('legend');
  legend.innerHTML = '';
  // V3.6.10: legend 前面加一句引导 (从开发者话改人话)
  const hint = document.createElement('div');
  hint.className = 'legend-hint';
  hint.textContent = '想看哪个学科? 点节点开卡片';
  legend.appendChild(hint);
  const counts = GROUPS.map(s => DATA.nodes.filter(n => n.subject === s).length);
  GROUPS.forEach((s, i) => {
    const el = document.createElement('div');
    el.className = 'chip';
    el.dataset.subject = s;
    el.setAttribute('role', 'button');
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-pressed', 'true');
    const nameCn = SUBJECT_CN[s] || s;
    el.setAttribute('aria-label', `切换 ${nameCn} ${counts[i]} 个概念`);
    el.innerHTML = `<span class="sw" style="background:${PALETTE[s]}"></span><span class="nm">${nameCn}</span><span class="ct">${counts[i]}</span>`;
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
  // V3.6.3: camera tween + focusGain 缓动
  updateCameraTween();
  updateFocusGain();
  controls.update();
  renderer.render(scene, camera);

  // FPS — V3.6.10b: 不再算/不再显示 (用户视角不关心, 删掉 DOM 更新)
  fpsFrames++;
  const now = performance.now();
  const elapsed = now - fpsLastTime;
  if (elapsed >= 500) {
    fpsFrames = 0;
    fpsLastTime = now;
  }
}

// 启动
init();
