// Open Curriculum CN — 漏斗学习路径视图 (V3.4 B)
// Canvas 2D · 1:1 复刻 Marble (withmarble.com/curriculum) 的"倒漏斗 + lineage trace"模式
// 复用 web/data/graph.json / 14 学科 PALETTE / 卡片结构

'use strict';

// ============== 常量 (Marble 同款) ==============
const H = 1780;            // 漏斗世界高度
const W = 1500;            // 漏斗世界最大半宽 (影响 x 散布)
const Z_RANGE = 220;       // ±z 深度
const FOV = 1400;          // 透视强度 (Marble 原值)
const NODE_BASE_SIZE = 2.3;
const NODE_CENT_GAIN = 7.5;
const GROW_DURATION = 2800; // 入场动画时长 ms
const GROW_PEAK = 1.02;    // 略过 1.0 让最终状态稳定

// ============== 14 学科配色 — 跟 web/3d.js 完全一致 ==============
const PALETTE = {
  math: '#5b8def', chinese: '#ef6b5b', english: '#7bc96f',
  science: '#f9a825', physics: '#ba68c8', chemistry: '#26a69a',
  biology: '#66bb6a', history: '#8d6e63', geography: '#42a5f5',
  morality_law: '#ec407a', info_tech: '#26c6da', art: '#ab47bc',
  pe_health: '#ff7043', labor: '#9ccc65', integrated: '#78909c',
};

// ============== 全局状态 ==============
let DATA = null;
let NODES = [];            // 计算布局后的节点: { x, y, z, py, c, g, col, dm, a, t, q, raw, id }
let EDGES = [];            // 紧凑数组 [fromIdx, toIdx, rel, reason, weight]
let H_HALF = H / 2;
let GROUPS = [];           // subject 字符串列表 (索引 = g)
let GCOL = [];             // 每个 group 的 hex 颜色
let RGB = [];              // 每个节点的 "r,g,b" (省 hex 解析)
let activeGroups = new Set();
let titleOrig = new Map(); // nodeId -> 原始 title (繁简切换回退用)

// 邻接
let incident = null;       // incident[u] = [edgeIdx, ...]
let directPre = null;      // directPre[u] = [prereqNodeIdx, ...]  (rel 过滤)
let directNext = null;     // directNext[u] = [dependentNodeIdx, ...]

// 相机
let rotY = 0.6, tilt = -0.32, zoom = 1;
let rotYTarget = null, tiltTarget = null, zoomTarget = null;

// 入场
let grow = 0;
let growStart = 0;

// 选择 / 谱系
let selected = -1;
let lineage = null;
let hist = [];
let hover = -1;

// 投影缓存
let P = null;              // Float32Array(N*3)  sx, sy, depth-scale
let order = null;          // Int32Array(N)  depth-sorted 顺序

// Canvas
let wrap, cv, ctx;
let DPR = 1, VW = 0, VH = 0;
let isMobile = false;

// FPS
let fpsFrames = 0, fpsLastTime = 0;

// ============== 工具函数 ==============
// Mulberry32 — 固定种子让布局每次启动完全一致
function mulberry32(seed) {
  let s = seed >>> 0;
  return function() {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hex2rgb(h) {
  const n = parseInt(h.slice(1), 16);
  return (n >> 16) + ',' + ((n >> 8) & 255) + ',' + (n & 255);
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// ============== 启动 ==============
async function init() {
  isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
  document.getElementById('loadingMsg').textContent = '加载漏斗学习路径...';

  // 1) 加载数据
  try {
    // V3.5g: 优先 .gz 压缩版 (1.4MB) + 客户端解压
    let text;
    try {
      const gzRes = await fetch('./data/graph.json.gz');
      if (gzRes.ok) {
        const ds = new DecompressionStream('gzip');
        text = await new Response(gzRes.body.pipeThrough(ds)).text();
      } else throw new Error('gz 404');
    } catch (e1) {
      console.warn('gz 加载失败, fallback json:', e1.message);
      const res = await fetch('./data/graph.json');
      if (!res.ok) throw new Error('graph.json 不存在 (HTTP ' + res.status + ')');
      text = await res.text();
    }
    DATA = JSON.parse(text);
  } catch (e) {
    const msg = document.getElementById('loadingMsg');
    msg.innerHTML = `<div class="err">${'未找到图谱数据 (graph.json)'}<br><br>${e.message}</div>`;
    console.error(e);
    return;
  }

  // 2) 算布局 + 邻接
  computeLayout();
  setupAdjacency();

  // 3) UI
  setupCanvas();
  setupInteraction();
  setFunnelHeader();
  buildLegend();
  setupSearch();
    setupCardClose();
  setupHistoryKeys();

  // 4) Stats
  document.getElementById('nCount').textContent = NODES.length.toLocaleString();
  document.getElementById('eCount').textContent = EDGES.length.toLocaleString();
  document.getElementById('gCount').textContent = GROUPS.length;

  // 5) 启动渲染
  document.getElementById('loading').classList.add('done');
  growStart = performance.now();
  fpsLastTime = growStart;

// V3.6.8: 支持 ?grade=N query, 自动选该年级中心度最高的概念展开 lineage
// V3.6.9 优化: 优先选年级跨度更小的概念 (G5 概念比 G1-6 跨学段概念更对家长直觉)
const urlGrade = parseInt(new URLSearchParams(location.search).get('grade'), 10);
if (urlGrade >= 1 && urlGrade <= 9) {
  setTimeout(() => {
    let bestIdx = -1, bestC = -1, bestSpan = 999;
    for (let i = 0; i < NODES.length; i++) {
      const n = NODES[i];
      const gs = n.raw.grade_start || 0;
      const ge = n.raw.grade_end || 0;
      if (gs > urlGrade || ge < urlGrade) continue;
      const span = ge - gs;
      if (span < bestSpan || (span === bestSpan && (n.c || 0) > bestC)) {
        bestSpan = span;
        bestC = n.c || 0;
        bestIdx = i;
      }
    }
    if (bestIdx >= 0) {
      selectNode(bestIdx, false);
    }
  }, 800);  // 等入场动画完成
}

// V3.6.9: 支持 ?subject=xxx query, 自动只显示该学科
const urlSubject = new URLSearchParams(location.search).get('subject');
if (urlSubject && GROUPS && GROUPS.includes(urlSubject)) {
  setTimeout(() => {
    // 找到目标学科在 GROUPS 里的 idx
    const subIdx = GROUPS.indexOf(urlSubject);
    // 禁用其他学科的 chip + 节点
    for (let i = 0; i < GROUPS.length; i++) {
      const s = GROUPS[i];
      if (i === subIdx) {
        if (!activeGroups.has(s)) activeGroups.add(s);
      } else {
        activeGroups.delete(s);
      }
    }
    // 同步图例 chip 视觉
    document.querySelectorAll('.chip').forEach((el) => {
      const sub = el.dataset.subject;
      const isOff = sub !== urlSubject;
      el.classList.toggle('off', isOff);
      el.setAttribute('aria-pressed', isOff ? 'false' : 'true');
    });
    // 重画
    requestAnimationFrame(frame);
  }, 400);  // 等 buildLegend() 渲染 chip
}

requestAnimationFrame(frame);
}

// ============== 布局: 按年级升序展开成倒漏斗 ==============
function computeLayout() {
  // 1) 学科列表 (按字母排序, 跟 3D 球保持稳定顺序)
  const subjects = [...new Set(DATA.nodes.map(n => n.subject))].sort();
  GROUPS = subjects;
  GCOL = subjects.map(s => PALETTE[s] || '#888888');
  activeGroups = new Set(subjects);

  // 2) 排序: grade_start ↑ → age_range_start ↑ → difficulty ↑ → id
  const sorted = [...DATA.nodes].sort((a, b) => {
    if ((a.grade_start || 0) !== (b.grade_start || 0)) return (a.grade_start || 0) - (b.grade_start || 0);
    if ((a.age_range_start || 0) !== (b.age_range_start || 0)) return (a.age_range_start || 0) - (b.age_range_start || 0);
    if ((a.difficulty || 0) !== (b.difficulty || 0)) return (a.difficulty || 0) - (b.difficulty || 0);
    return String(a.id).localeCompare(String(b.id));
  });

  // 3) 给每个节点算 (x, y, z) + 缓存派生字段
  const N = sorted.length;
  const rng = mulberry32(0x42F00D);  // 固定种子 → 每次启动布局一致
  for (let i = 0; i < N; i++) {
    const raw = sorted[i];
    const t = i / Math.max(1, N - 1);     // 0..1
    const y = t * H;                        // 0 入门 → H 进阶
    // 漏斗形 x: 中间最宽, 上下窄 (sin 曲线, 跟 spec 一致)
    const widthFactor = 0.5 + 0.5 * Math.sin(t * Math.PI);
    const x = (rng() - 0.5) * W * widthFactor;
    // z 深度 (前/后) — 给视角一点纵深
    const z = (rng() - 0.5) * Z_RANGE;

    const g = subjects.indexOf(raw.subject);
    const col = PALETTE[raw.subject] || '#888888';
    const c = raw.centrality || 0;
    const a = raw.age_range_start || raw.grade_start || 0;

    NODES.push({
      id: raw.id,
      x, y, z,
      py: y - H_HALF,
      c, g, subject: raw.subject, col,  // 缓存 subject 字符串, 避免 activeGroups 检查时再 groupByIdx
      dm: `${raw.subject} · G${raw.grade_start || ''}-${raw.grade_end || ''} · ${raw.domain || ''}`,
      a,
      t: raw.title,
      q: raw.assessment_prompt || '',
      raw,
    });
  }

  // 4) title 缓存 (繁简切换)
  NODES.forEach(n => titleOrig.set(n.id, n.t));

  // 5) RGB 字符串缓存
  RGB = NODES.map(n => hex2rgb(n.col));

  // 6) 边: 紧凑数组 + id 映射
  const idToIdx = new Map();
  NODES.forEach((n, i) => idToIdx.set(n.id, i));
  for (const e of DATA.edges) {
    const fi = idToIdx.get(e.from);
    const ti = idToIdx.get(e.to);
    if (fi === undefined || ti === undefined) continue;
    EDGES.push([fi, ti, e.rel || 'prerequisite', e.reason || '', e.weight || 1.0]);
  }
}

function setupAdjacency() {
  const N = NODES.length;
  incident = new Array(N);
  directPre = new Array(N);
  directNext = new Array(N);
  for (let i = 0; i < N; i++) {
    incident[i] = [];
    directPre[i] = [];
    directNext[i] = [];
  }
  for (let i = 0; i < EDGES.length; i++) {
    const [from, to, rel] = EDGES[i];
    incident[from].push(i);
    incident[to].push(i);
    if (rel !== 'relates_to') {
      directPre[from].push(to);   // from 依赖 to
      directNext[to].push(from);  // to 解锁 from
    }
  }
}

// ============== Canvas / 尺寸 ==============
function setupCanvas() {
  wrap = document.getElementById('wrap');
  cv = document.createElement('canvas');
  cv.setAttribute('aria-hidden', 'true');
  wrap.appendChild(cv);
  ctx = cv.getContext('2d', { alpha: false });
  resize();
  window.addEventListener('resize', resize);
}

function resize() {
  DPR = Math.min(window.devicePixelRatio || 1, isMobile ? 1.5 : 2);
  VW = wrap.clientWidth;
  VH = wrap.clientHeight;
  cv.width = Math.max(1, Math.floor(VW * DPR));
  cv.height = Math.max(1, Math.floor(VH * DPR));
  cv.style.width = VW + 'px';
  cv.style.height = VH + 'px';
  if (NODES.length) {
    P = new Float32Array(NODES.length * 3);
    order = new Int32Array(NODES.length);
    for (let i = 0; i < NODES.length; i++) order[i] = i;
  }
}

// ============== 投影 (跟 Marble 完全一致) ==============
function project() {
  const cy = Math.cos(rotY), sy = Math.sin(rotY);
  const ct = Math.cos(tilt), st = Math.sin(tilt);
  const cx = VW * 0.52, cyy = VH * 0.52;
  const sc = Math.min(VW / 1500, VH / 1780) * zoom;
  for (let i = 0; i < NODES.length; i++) {
    const n = NODES[i];
    let x = n.x * cy + n.z * sy;
    let z = -n.x * sy + n.z * cy;
    let y = n.py;
    const y2 = y * ct - z * st;
    const z2 = y * st + z * ct;
    const pf = FOV / (FOV + z2 * sc * 1.6);
    P[i * 3]     = cx + x * sc * pf;
    P[i * 3 + 1] = cyy - y2 * sc * pf;
    P[i * 3 + 2] = pf;
  }
}

// ============== 节点大小 (像素) — Marble 公式 ==============
function nodeR(i) {
  const pf = P[i * 3 + 2];
  if (!(pf > 0)) return 0;  // 节点在相机后方, 不画
  return (NODE_BASE_SIZE + Math.sqrt(NODES[i].c) * NODE_CENT_GAIN)
    * pf
    * clamp(zoom, 0.9, 1.6);
}

// ============== 谱系 (BFS 反向追溯所有先决) ==============
function buildLineage(i) {
  const nodes = new Set([i]);
  const edges = new Set();
  const q = [i];
  while (q.length) {
    const u = q.shift();
    for (let k = 0; k < incident[u].length; k++) {
      const ei = incident[u][k];
      const e = EDGES[ei];
      // e[0] (from) 依赖 e[1] (to). u 作为依赖方 → 找 u 的先决
      if (e[0] === u) {
        edges.add(ei);
        if (!nodes.has(e[1])) { nodes.add(e[1]); q.push(e[1]); }
      }
    }
  }
  lineage = { nodes, edges };
}

// ============== 选择 / 导航 / 相机 ==============
function focusNode(i) {
  // 旋转相机让节点 i 朝向屏幕中央. 选 z'' 较大的那个候选 (更靠前)
  const n = NODES[i];
  let best = null, bestZ = -Infinity;
  for (const cand of [Math.atan2(-n.x, n.z), Math.atan2(-n.x, n.z) + Math.PI]) {
    const z2 = -n.x * Math.sin(cand) + n.z * Math.cos(cand);
    if (z2 > bestZ) { bestZ = z2; best = cand; }
  }
  rotYTarget = best;
  tiltTarget = -0.18;
  zoomTarget = Math.max(zoom, 1.5);
}

function selectNode(i, push) {
  if (push && selected >= 0 && selected !== i) hist.push(selected);
  selected = i;
  buildLineage(i);
  showCard(i);
  focusNode(i);
  hideTip();
}

function goBack() {
  if (!hist.length) return;
  selectNode(hist.pop(), false);
}

function clearSel() {
  if (selected < 0) return;
  selected = -1;
  lineage = null;
  hist.length = 0;
  rotYTarget = null; tiltTarget = null; zoomTarget = null;
  document.getElementById('card').classList.remove('on');
  document.getElementById('card').setAttribute('aria-hidden', 'true');
}

// ============== 渲染 (画边 → 深度排序 → 画点) ==============
function draw() {
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.clearRect(0, 0, VW, VH);
  project();

  const hasSel = !!lineage;
  const M = EDGES.length;
  const N = NODES.length;

  // ----- 1. 边 -----
  for (let k = 0; k < M; k++) {
    const e = EDGES[k];
    const a = e[0], b = e[1];
    if (!activeGroups.has(NODES[a].subject) || !activeGroups.has(NODES[b].subject)) continue;
    if (NODES[a].y / H > grow || NODES[b].y / H > grow) continue;
    // 跳过至少一端在相机后方的边
    if (!(P[a*3+2] > 0) || !(P[b*3+2] > 0)) continue;
    let alpha, col = null, lw = 1;
    if (hasSel) {
      if (lineage.edges.has(k)) { alpha = 0.75; col = RGB[b]; lw = 1.6; }
      else { alpha = 0.04; }
    } else {
      alpha = 0.06;
    }
    const depth = (P[a * 3 + 2] + P[b * 3 + 2]) * 0.5;
    if (col) {
      ctx.strokeStyle = `rgba(${col},${alpha})`;
    } else {
      ctx.strokeStyle = `rgba(150,165,205,${alpha * depth})`;
    }
    ctx.lineWidth = lw;
    ctx.beginPath();
    ctx.moveTo(P[a * 3], P[a * 3 + 1]);
    ctx.lineTo(P[b * 3], P[b * 3 + 1]);
    ctx.stroke();
  }

  // ----- 2. 节点 (painter's algorithm: 远→近) -----
  // 稳定地按 pf 升序排 (小 pf = 远, 大 pf = 近)
  const sortedOrder = Array.from(order);
  sortedOrder.sort((a, b) => P[a * 3 + 2] - P[b * 3 + 2]);

  for (let k = 0; k < N; k++) {
    const i = sortedOrder[k];
    const n = NODES[i];
    if (!activeGroups.has(n.subject)) continue;
    if (n.y / H > grow) continue;
    const inLin = hasSel ? lineage.nodes.has(i) : true;
    const isFocus = (i === selected) || (i === hover);
    let dim = 1;
    if (hasSel && !inLin) dim = 0.10;
    const sx = P[i * 3], sy = P[i * 3 + 1], pf = P[i * 3 + 2];
    const r0 = nodeR(i);  // 已经检查 pf > 0
    if (r0 <= 0) continue;
    const r = r0 * (isFocus ? 1.6 : 1);
    const rgb = RGB[i];
    const a = dim * (0.55 + 0.45 * Math.min(1, pf * pf));

    if (isFocus || (hasSel && inLin)) {
      ctx.shadowColor = `rgb(${rgb})`;
      ctx.shadowBlur = isFocus ? 18 : 9;
    } else {
      ctx.shadowBlur = 0;
    }
    ctx.fillStyle = `rgba(${rgb},${a})`;
    ctx.beginPath();
    ctx.arc(sx, sy, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    // 暗色环 — 让同色相邻节点可分辨
    ctx.strokeStyle = `rgba(8,10,18,${0.5 * dim})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(sx, sy, r, 0, Math.PI * 2);
    ctx.stroke();

    // 选中 / 悬停 — 加白色高亮环
    if (isFocus) {
      ctx.strokeStyle = 'rgba(255,255,255,0.95)';
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.arc(sx, sy, r + 2.5, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

// ============== 帧循环 ==============
function frame(ts) {
  grow = Math.min(GROW_PEAK, (ts - growStart) / GROW_DURATION * GROW_PEAK);

  if (rotYTarget !== null) {
    let d = ((rotYTarget - rotY + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
    rotY += d * 0.12;
    if (tiltTarget !== null) tilt += (tiltTarget - tilt) * 0.12;
    if (zoomTarget !== null) zoom += (zoomTarget - zoom) * 0.12;
    if (Math.abs(d) < 0.008) { rotYTarget = null; tiltTarget = null; zoomTarget = null; }
  }

  draw();
  updateFPS();

  requestAnimationFrame(frame);
}

function updateFPS() {
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

// ============== 交互 (拖动 / 滚轮 / 点击 / 悬停 / 双指) ==============
function setupInteraction() {
  let dragging = false, moved = false, lx = 0, ly = 0;
  const pts = new Map();
  let pinchD = 0;

  wrap.addEventListener('pointerdown', e => {
    if (e.target !== wrap && e.target !== cv) return;
    wrap.setPointerCapture(e.pointerId);
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 1) {
      dragging = true; moved = false; lx = e.clientX; ly = e.clientY;
      wrap.classList.add('drag');
    } else if (pts.size === 2) {
      dragging = false; pinchD = 0;
    }
  });

  wrap.addEventListener('pointermove', e => {
    if (pts.has(e.pointerId)) pts.set(e.pointerId, [e.clientX, e.clientY]);

    if (pts.size === 1 && dragging) {
      const dx = e.clientX - lx, dy = e.clientY - ly;
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      rotY += dx * 0.0055;
      tilt = clamp(tilt - dy * 0.003, -1.1, 0.15);
      lx = e.clientX; ly = e.clientY;
    } else if (pts.size === 2) {
      const v = [...pts.values()];
      const dx = v[0][0] - v[1][0], dy = v[0][1] - v[1][1];
      const dd = Math.hypot(dx, dy);
      if (pinchD) zoom = clamp(zoom * dd / pinchD, 0.5, 4);
      pinchD = dd;
    } else if (pts.size === 0) {
      onHover(e);
    }
  });

  wrap.addEventListener('pointerup', e => {
    pts.delete(e.pointerId);
    if (pts.size === 0) {
      if (dragging) {
        dragging = false;
        wrap.classList.remove('drag');
        if (!moved) onClick(e);
      }
    }
    if (pts.size < 2) pinchD = 0;
  });

  wrap.addEventListener('pointercancel', e => {
    pts.delete(e.pointerId);
    if (pts.size === 0) { dragging = false; wrap.classList.remove('drag'); }
    if (pts.size < 2) pinchD = 0;
  });

  wrap.addEventListener('pointerleave', () => { hideTip(); hover = -1; });

  wrap.addEventListener('wheel', e => {
    e.preventDefault();
    zoom = clamp(zoom * Math.exp(-e.deltaY * 0.0016), 0.5, 4);
  }, { passive: false });
}

function pick(mx, my) {
  let best = -1, bd = 20 * 20;
  const N = NODES.length;
  for (let i = 0; i < N; i++) {
    if (!activeGroups.has(NODES[i].subject)) continue;
    if (NODES[i].y / H > grow) continue;
    if (!(P[i * 3 + 2] > 0)) continue;  // 在相机后方
    const dx = P[i * 3] - mx, dy = P[i * 3 + 1] - my;
    const d = dx * dx + dy * dy;
    const rr = Math.max(11, nodeR(i) + 6);
    if (d < rr * rr && d < bd) { bd = d; best = i; }
  }
  return best;
}

function onClick(e) {
  const r = cv.getBoundingClientRect();
  const i = pick(e.clientX - r.left, e.clientY - r.top);
  if (i < 0) { clearSel(); return; }
  selectNode(i, true);
}

function onHover(e) {
  const r = cv.getBoundingClientRect();
  const i = pick(e.clientX - r.left, e.clientY - r.top);
  if (i !== hover) {
    hover = i;
    if (i >= 0) showTip(i, e);
    else hideTip();
  } else if (i >= 0) {
    placeTip(e);
  }
}

// ============== Tooltip ==============
function showTip(i, e) {
  const n = NODES[i];
  document.getElementById('tip-sw').style.background = n.col;
  document.getElementById('tip-ts').textContent = n.dm;
  document.getElementById('tip-ttl').textContent = n.t;
  const qEl = document.getElementById('tip-q');
  qEl.innerHTML = n.q ? esc(n.q).slice(0, 220) : '';
  document.getElementById('tip').classList.add('on');
  placeTip(e);
}

function placeTip(e) {
  const tip = document.getElementById('tip');
  const r = wrap.getBoundingClientRect();
  let x = e.clientX - r.left + 16, y = e.clientY - r.top + 16;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  if (x + w > VW - 8) x = e.clientX - r.left - w - 16;
  if (y + h > VH - 8) y = e.clientY - r.top - h - 16;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

function hideTip() {
  document.getElementById('tip').classList.remove('on');
}

// ============== Card ==============
function fillRows(container, idxs) {
  container.innerHTML = '';
  if (!idxs.length) {
    const d = document.createElement('div');
    d.className = 'empty';
    d.textContent = '— 暂无 —';
    container.appendChild(d);
    return;
  }
  idxs.slice().sort((a, b) => NODES[a].a - NODES[b].a).forEach(j => {
    const m = NODES[j];
    const b = document.createElement('button');
    b.className = 'row';
    b.innerHTML = `<span class="rdot" style="background:${m.col}"></span><span class="rt">${esc(m.t)}</span><span class="ra">G${m.raw.grade_start || ''}</span>`;
    b.addEventListener('click', () => selectNode(j, true));
    container.appendChild(b);
  });
}

function showCard(i) {
  const n = NODES[i];
  const r = n.raw;
  const cnt = lineage.nodes.size - 1;  // 排除自身

  document.getElementById('card-sw').style.background = n.col;
  document.getElementById('card-cs').textContent = n.dm;
  document.getElementById('card-ctl').textContent = n.t;

  // tags
  const tagRow = document.getElementById('card-tags');
  tagRow.innerHTML = '';
  (r.bloom || []).forEach(b => {
    const t = document.createElement('span');
    t.className = 'tag bloom';
    t.textContent = '✦ ' + b;
    tagRow.appendChild(t);
  });
  if (r.difficulty) {
    const t = document.createElement('span');
    t.className = 'tag diff-' + r.difficulty;
    t.textContent = ('难度') + ' ' + '●'.repeat(r.difficulty) + '○'.repeat(5 - r.difficulty);
    tagRow.appendChild(t);
  }
  if (r.estimated_minutes) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = '⏱ ' + r.estimated_minutes + ' ' + ('分钟');
    tagRow.appendChild(t);
  }
  if (r.subdomain) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = r.subdomain;
    tagRow.appendChild(t);
  }

  // 谱系统计 (漏斗专属)
  const linStats = document.getElementById('card-lin-stats');
  const linN = document.getElementById('card-lin-n');
  const linU = document.getElementById('card-lin-u');
  const linSub = document.getElementById('card-lin-sub');
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
    linSub.textContent = `从起点到此概念, 共需掌握 ${cnt} 个前置 (含直接 + 间接). 谱系已高亮显示在漏斗中.`;
  }

  // 内容块 (复用 3D 球)
  const cr = document.getElementById('card-content-req');
  const crBlock = document.getElementById('card-content-req-block');
  if (r.content_req) { cr.textContent = r.content_req; crBlock.style.display = ''; }
  else { crBlock.style.display = 'none'; }

  const pageLink = document.getElementById('card-page-link');
  if (r.src_page) {
    const srcText = '课标原文';
    pageLink.innerHTML = ` · <a class="src-link" href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">P${r.src_page} ${srcText}</a>`;
  } else pageLink.textContent = '';

  const ar = document.getElementById('card-academic-req');

  // V3.3.4 深度内容增强
  ['real-examples', 'common-mistakes', 'teaching-activity'].forEach(k => {
    const block = document.getElementById('card-' + k + '-block');
    const body = document.getElementById('card-' + k);
    const key = k.replace(/-/g, '_');
    if (r[key]) {
      if (block) block.style.display = '';
      if (body) body.textContent = r[key];
    } else {
      if (block) block.style.display = 'none';
    }
  });

  // V3.6.9 教学话术 (用 description 字段, 老师口吻 3 句话)
  const tvBlock = document.getElementById('card-teaching-voice-block');
  const tvBody = document.getElementById('card-teaching-voice');
  if (r.description) {
    tvBody.textContent = r.description;
    tvBlock.style.display = '';
  } else {
    tvBlock.style.display = 'none';
  }

  // V3.6.9 打印版按钮 → 新窗口打开 print.html?id=xxx
  const printBtn = document.getElementById('card-print-btn');
  if (printBtn) printBtn.href = './print.html?id=' + encodeURIComponent(r.id);

  const arBlock = document.getElementById('card-academic-req-block');
  if (r.academic_req) { ar.textContent = r.academic_req; arBlock.style.display = ''; }
  else { arBlock.style.display = 'none'; }

  const kp = document.getElementById('card-key-points');
  const kpBlock = document.getElementById('card-key-points-block');
  kp.innerHTML = '';
  if (r.key_points && r.key_points.length) {
    r.key_points.forEach(p => {
      const d = document.createElement('div');
      d.className = 'kp';
      d.textContent = p;
      kp.appendChild(d);
    });
    kpBlock.style.display = '';
  } else kpBlock.style.display = 'none';

  const exRow = document.getElementById('card-examples');
  const exBlock = document.getElementById('card-examples-block');
  exRow.innerHTML = '';
  if (r.examples && r.examples.length) {
    r.examples.forEach(ex => {
      const t = document.createElement('span');
      t.className = 'ex';
      t.textContent = ex;
      exRow.appendChild(t);
    });
    exBlock.style.display = '';
  } else exBlock.style.display = 'none';

  const assBlock = document.getElementById('card-assessment-block');
  const ass = document.getElementById('card-assessment');
  if (r.assessment_prompt) { ass.textContent = r.assessment_prompt; assBlock.style.display = ''; }
  else { assBlock.style.display = 'none'; }

  const metaBlock = document.getElementById('card-meta-block');
  const meta = document.getElementById('card-meta');
  const metaItems = [];
  if (r.type) metaItems.push(`<span class="meta-tag type-${r.type.toLowerCase()}">${r.type}</span>`);
  if (r.age_range_start) metaItems.push(`<span class="meta-tag">🎂 ${r.age_range_start}-${r.age_range_end || r.age_range_start} 岁</span>`);
  if (r.centrality !== undefined) {
    const centPct = Math.round(r.centrality * 100);
    metaItems.push(`<span class="meta-tag" title="中心度 (被需要 + 能学)">⭐ 中心度 ${centPct}%</span>`);
  }
  if (metaItems.length) { meta.innerHTML = metaItems.join(' '); metaBlock.style.display = ''; }
  else metaBlock.style.display = 'none';

  // 直接先决 / 解锁后继 (rel 过滤后)
  const pre = directPre[i];
  const nxt = directNext[i];
  const preK = document.getElementById('card-pre-k');
  const nextK = document.getElementById('card-next-k');
  preK.textContent = pre.length;
  nextK.textContent = nxt.length;
  preK.classList.toggle('zero', pre.length === 0);
  nextK.classList.toggle('zero', nxt.length === 0);
  fillRows(document.getElementById('card-pre-rows'), pre);
  fillRows(document.getElementById('card-next-rows'), nxt);

  // back 按钮
  document.getElementById('card-back').classList.toggle('on', hist.length > 0);

  document.getElementById('card').classList.add('on');
  document.getElementById('card').setAttribute('aria-hidden', 'false');
  document.getElementById('card').scrollTop = 0;
}

function setupCardClose() {
  document.querySelector('#card .close').addEventListener('click', clearSel);
  document.getElementById('card-back').addEventListener('click', goBack);
  // 防止卡片/图例的指针事件传到 canvas (避免点击行时触发 onClick)
  ['pointerdown', 'pointerup', 'click', 'wheel'].forEach(ev => {
    document.getElementById('card').addEventListener(ev, e => e.stopPropagation());
    document.getElementById('legend').addEventListener(ev, e => e.stopPropagation());
  });
}

function setupHistoryKeys() {
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const results = document.getElementById('searchResults');
      if (results.classList.contains('on')) { results.classList.remove('on'); return; }
      const si = document.getElementById('searchInput');
      if (si && document.activeElement === si) { si.blur(); return; }
      clearSel();
    } else if (e.key === 'Backspace' && selected >= 0) {
      const tag = document.activeElement && document.activeElement.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      e.preventDefault();
      goBack();
    }
  });
}

// ============== 图例 ==============
function buildLegend() {
  const legend = document.getElementById('legend');
  legend.innerHTML = '';
  const counts = GROUPS.map(() => 0);
  NODES.forEach(n => counts[n.g]++);
  GROUPS.forEach((s, i) => {
    const el = document.createElement('div');
    el.className = 'chip';
    el.dataset.subject = s;
    el.tabIndex = 0;
    el.setAttribute('role', 'button');
    el.setAttribute('aria-pressed', 'true');
    el.setAttribute('aria-label', `切换 ${s} ${counts[i]} 个概念`);
    el.innerHTML = `<span class="sw" style="background:${GCOL[i]}"></span><span class="nm">${esc(s)}</span><span class="ct">${counts[i]}</span>`;
    el.addEventListener('click', () => {
      el.classList.toggle('off');
      el.setAttribute('aria-pressed', el.classList.contains('off') ? 'false' : 'true');
      if (el.classList.contains('off')) activeGroups.delete(s);
      else activeGroups.add(s);
    });
    el.addEventListener('keydown', ev => {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); el.click(); }
    });
    legend.appendChild(el);
  });
}

// ============== 搜索 ==============
function setupSearch() {
  const input = document.getElementById('searchInput');
  const results = document.getElementById('searchResults');
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { results.classList.remove('on'); return; }
    const matches = [];
    for (let i = 0; i < NODES.length; i++) {
      const n = NODES[i];
      const titleLc = n.t ? n.t.toLowerCase() : '';
      const idLc = n.id.toLowerCase();
      const sd = (n.raw.subdomain || '').toLowerCase();
      if (idLc.includes(q) || titleLc.includes(q) || sd.includes(q)) {
        matches.push({ idx: i, n });
      }
    }
    results.innerHTML = '';
    const count = document.createElement('div');
    count.className = 'r-count';
    count.textContent = `${matches.length} 匹配 (按 ESC 关闭)`;
    results.appendChild(count);
    if (matches.length === 0) {
      const e = document.createElement('div');
      e.className = 'r-empty';
      e.textContent = '无匹配概念';
      results.appendChild(e);
    } else {
      matches.slice(0, 50).forEach(m => {
        const it = document.createElement('div');
        it.className = 'r-item';
        it.innerHTML = `<span class="r-dot" style="background:${m.n.col}"></span><span class="r-t">${esc(m.n.t)}</span><span class="r-m">G${m.n.raw.grade_start || ''}</span>`;
        it.addEventListener('click', () => {
          selectNode(m.idx, true);
          results.classList.remove('on');
          input.value = '';
        });
        results.appendChild(it);
      });
    }
    results.classList.add('on');
  });
  document.addEventListener('click', e => {
    if (!e.target.closest('.search')) results.classList.remove('on');
  });
}

function setFunnelHeader() {
  const lang = 'zh-CN';
  const titles = {
    'zh-CN': '2022 新课标知识图谱 · 漏斗学习路径视图',
    'zh-TW': '2022 新課標知識圖譜 · 漏斗學習路徑視圖',
    'en':    '2022 New Curriculum KG · Funnel Learning Path',
  };
  const subs = {
    'zh-CN': '1906 概念按年级升序展开成倒漏斗 · 4736 条学习路径可看完整前置 · <a href="./index.html" style="color:#6b8cff;text-decoration:none">切换回 3D 球面视图 →</a>',
    'zh-TW': '1906 概念按年級升序展開成倒漏斗 · 4736 關係可反向追溯全譜系先決 · <a href="./index.html" style="color:#6b8cff;text-decoration:none">切換回 3D 球面視圖 →</a>',
    'en':    '1906 concepts in an inverted funnel by grade · 4736 relations traceable backward · <a href="./index.html" style="color:#6b8cff;text-decoration:none">Switch to 3D sphere view →</a>',
  };
  const h1 = document.getElementById('headerTitleFunnel');
  const subEl = document.getElementById('headerSubFunnel');
  if (h1) h1.textContent = titles[lang] || titles['zh-CN'];
  if (subEl) subEl.innerHTML = subs[lang] || subs['zh-CN'];
  document.title = (titles[lang] || titles['zh-CN']) + ' · Open Curriculum CN';
}

// ============== 启动 ==============
init();
