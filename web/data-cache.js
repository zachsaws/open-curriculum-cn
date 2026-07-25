// Open Curriculum CN — graph.json 共享缓存 (V3.6.9)
// 用 localStorage + gzip 压缩缓存图谱数据, 避免每次访问都重下 1.5MB
// 用法: const data = await loadGraphData();   // 自动用缓存或下载
//       try { localStorage.removeItem('occ_graph_v3_3_5_gz'); } catch(e){}   // 手动清缓存

'use strict';

const CACHE_KEY = 'occ_graph_v3_3_5_gz';   // v3.3.5 数据版本, 数据升级时改名让缓存失效
const CACHE_VERSION = '3.3.5';
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;  // 7 天

let _lastSource = null;  // 'cache' | 'network' | null

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
    // b64 → Uint8Array → 解压
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
    // 编码 base64 (分块, 处理大字符串)
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
      // QuotaExceededError: localStorage 满了 (5-10MB)
      console.warn('[data-cache] 写入缓存失败 (quota?):', e.message);
      // 清掉老缓存再试一次
      try { localStorage.removeItem(CACHE_KEY); } catch {}
    }
  } catch (e) {
    console.warn('[data-cache] 压缩失败', e.message);
  }
}

async function loadGraphData() {
  // 1) 试缓存
  const cached = await _fromCache();
  if (cached) {
    _lastSource = 'cache';
    return cached;
  }
  // 2) 下载 (优先 .gz, 失败 fallback .json)
  let text;
  try {
    const gzRes = await fetch('./data/graph.json.gz');
    if (gzRes.ok) {
      const ds = new DecompressionStream('gzip');
      text = await new Response(gzRes.body.pipeThrough(ds)).text();
    } else throw new Error('gz ' + gzRes.status);
  } catch (e1) {
    console.warn('[data-cache] gz 失败, fallback json:', e1.message);
    const res = await fetch('./data/graph.json');
    if (!res.ok) throw new Error('graph.json HTTP ' + res.status);
    text = await res.text();
  }
  const data = JSON.parse(text);
  _lastSource = 'network';
  // 3) 后台写缓存 (不阻塞当前)
  _toCache(data).catch(() => {});
  return data;
}

function getLastSource() { return _lastSource; }

function clearCache() {
  try { localStorage.removeItem(CACHE_KEY); return true; } catch (e) { return false; }
}

if (typeof window !== 'undefined') {
  window.loadGraphData = loadGraphData;
  window.getDataSource = getLastSource;
  window.clearGraphCache = clearCache;
}
