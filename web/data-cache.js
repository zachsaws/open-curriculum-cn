// Open Curriculum CN — graph.json 共享缓存 (V3.6.9 → V4.1.3 加 lite)
// 用 localStorage + gzip 压缩缓存图谱数据, 避免每次访问都重下 1.5MB
// 用法: const data = await loadGraphData();   // 自动用缓存或下载
//       const lite = await loadGraphLite();   // 3D 球用, 80KB gz
//       const full = await loadGraphFull();   // detail panel 用, 1.9MB gz
//       try { localStorage.removeItem('occ_graph_v3_3_5_gz'); } catch(e){}   // 手动清缓存

'use strict';

const CACHE_KEY = 'occ_graph_v3_3_5_gz';   // v3.3.5 数据版本, 数据升级时改名让缓存失效
const CACHE_VERSION = '3.3.5';
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;  // 7 天

let _lastSource = null;  // 'cache' | 'network' | null
let _fullLoaded = false;
let _fullPromise = null;  // 全图 promise (用于 detail panel 异步 fetch)

async function _decompressGzip(uint8) {
  const ds = new DecompressionStream('gzip');
  const stream = new Blob([uint8]).stream().pipeThrough(ds);
  return await new Response(stream).text();
}

async function _compressGzip(text) {
  const ds = new CompressionStream('gzip');
  const stream = new Blob([text]).stream().pipeThrough(ds);
  const ab = await new Response(stream).arrayBuffer();
  return new Uint8Array(ab);
}

async function _fromCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { ts, v, b64 } = JSON.parse(raw);
    if (v !== CACHE_VERSION) {
      console.log('[data-cache] 版本不匹配, 失效', v, '!=', CACHE_VERSION);
      return null;
    }
    if (Date.now() - ts > CACHE_MAX_AGE_MS) {
      console.log('[data-cache] 缓存过期');
      return null;
    }
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const text = await _decompressGzip(bytes);
    const data = JSON.parse(text);
    console.log('[data-cache] 命中缓存, ts', new Date(ts).toLocaleString(), '大小', Math.round(bytes.length / 1024) + 'KB');
    return data;
  } catch (e) {
    console.warn('[data-cache] 读缓存失败', e.message);
    return null;
  }
}

async function _toCache(data) {
  try {
    const text = JSON.stringify(data);
    const bytes = await _compressGzip(text);
    let bin = '';
    const CHUNK = 0x8000;
    for (let i = 0; i < bytes.length; i += CHUNK) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    const b64 = btoa(bin);
    const payload = JSON.stringify({ ts: Date.now(), v: CACHE_VERSION, b64 });
    try {
      localStorage.setItem(CACHE_KEY, payload);
      console.log('[data-cache] 写入缓存, 压缩后', Math.round(bytes.length / 1024) + 'KB');
    } catch (e) {
      console.warn('[data-cache] 写入缓存失败 (quota?):', e.message);
      try { localStorage.removeItem(CACHE_KEY); } catch {}
    }
  } catch (e) {
    console.warn('[data-cache] 压缩失败', e.message);
  }
}

async function _fetchVariant(jsonPath, gzPath) {
  let text;
  try {
    const gzRes = await fetch(gzPath);
    if (gzRes.ok) {
      const ds = new DecompressionStream('gzip');
      text = await new Response(gzRes.body.pipeThrough(ds)).text();
    } else throw new Error('gz ' + gzRes.status);
  } catch (e1) {
    console.warn('[data-cache] gz 失败, fallback json:', e1.message);
    const res = await fetch(jsonPath);
    if (!res.ok) throw new Error(jsonPath + ' HTTP ' + res.status);
    text = await res.text();
  }
  return JSON.parse(text);
}

// V4.1.3: 3D 球用 lite 版 (80KB gz, ~1s 加载)
async function loadGraphLite() {
  const cached = await _fromCache();
  if (cached) {
    _lastSource = 'cache';
    // 缓存的是 full graph, 提取 lite 字段
    return _extractLite(cached);
  }
  const data = await _fetchVariant('./data/graph_lite.json', './data/graph_lite.json.gz');
  _lastSource = 'network';
  _toCache(data).catch(() => {});  // 缓存 lite 本身
  return data;
}

// V4.1.3: full graph (按需 fetch, 1.9MB gz)
async function loadGraphFull() {
  if (_fullLoaded) {
    return await _fullPromise;
  }
  if (_fullPromise) return _fullPromise;
  _fullPromise = (async () => {
    const data = await _fetchVariant('./data/graph.json', './data/graph.json.gz');
    _fullLoaded = true;
    return data;
  })();
  return _fullPromise;
}

// 兼容旧 API: loadGraphData 默认返 full
async function loadGraphData() {
  return await loadGraphFull();
}

// 提取 lite 字段 (从 full graph)
function _extractLite(full) {
  const LITE_FIELDS = [
    'id', 'subject', 'title', 'grade_start', 'grade_end', 'centrality',
    'difficulty', 'bloom', 'type', 'estimated_minutes', 'subdomain', 'domain',
  ];
  const EDGE_FIELDS = ['id', 'from', 'to', 'rel', 'weight'];
  return {
    version: full.version,
    nodes: full.nodes.map(n => {
      const lite = {};
      LITE_FIELDS.forEach(k => { if (k in n) lite[k] = n[k]; });
      return lite;
    }),
    edges: full.edges.map(e => {
      const lite = {};
      EDGE_FIELDS.forEach(k => { if (k in e) lite[k] = e[k]; });
      return lite;
    }),
  };
}

// V4.1.3: 后台预取 full graph (网络空闲时)
function prefetchFull() {
  if (_fullLoaded || _fullPromise) return;
  setTimeout(() => {
    loadGraphFull().catch(() => {});
  }, 3000);  // 3s 后网络空闲触发
}

function getLastSource() { return _lastSource; }

function clearCache() {
  try { localStorage.removeItem(CACHE_KEY); return true; } catch (e) { return false; }
}

if (typeof window !== 'undefined') {
  window.loadGraphData = loadGraphData;
  window.loadGraphLite = loadGraphLite;
  window.loadGraphFull = loadGraphFull;
  window.prefetchFull = prefetchFull;
  window.getDataSource = getLastSource;
  window.clearGraphCache = clearCache;
}
