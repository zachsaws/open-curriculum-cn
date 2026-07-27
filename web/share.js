// Open Curriculum CN — 概念学习卡分享 (V3.6.9)
// 1080×1440 SVG → PNG (无外部库, 用 foreignObject + canvas 转换)
// 用法: showShareCard(node) → 弹出模态, 提供"下载 PNG"和"复制到剪贴板"

'use strict';

const SHARE_W = 1080;
const SHARE_H = 1440;
// V3.6.10b: SUBJECT_CN 抽到 subject-cn.js 共享, 4 个文件统一用
// (原 const 声明在多 script 共存时冲突, 已迁移)

function escHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function escText(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function wrapText(text, max) {
  if (!text) return '';
  const words = String(text).split(/(\s+|[，。！？；、,!?;])/);
  let line = '';
  let result = '';
  for (const w of words) {
    if ((line + w).length > max) {
      result += line.trim() + '\n';
      line = w.trim() ? w : '';
    } else {
      line += w;
    }
  }
  if (line.trim()) result += line.trim();
  return result;
}

function generateShareSVG(node) {
  const r = node.raw || node;
  const col = (typeof PALETTE !== 'undefined' && PALETTE[r.subject]) || '#5b8def';
  const subjectCn = SUBJECT_CN[r.subject] || r.subject || '';
  const gradeRange = (r.grade_start || 0) === (r.grade_end || 0)
    ? `G${r.grade_start}`
    : `G${r.grade_start || 0}-${r.grade_end || 0}`;
  const difficultyDots = r.difficulty
    ? '●'.repeat(r.difficulty) + '○'.repeat(5 - r.difficulty)
    : '';
  const minutes = r.estimated_minutes || '';
  const title = escHtml(r.title || '');
  const summary = escHtml(r.summary || '');
  const description = escHtml(r.description || '');
  const siteUrl = 'zachsaws.github.io/open-curriculum-cn';
  const conceptId = escHtml(r.id || '');

  // 取前置 + 后继节点
  const preNames = (node._pre || []).slice(0, 4).map(n => escHtml(n.t || n.id || ''));
  const nxtNames = (node._nxt || []).slice(0, 4).map(n => escHtml(n.t || n.id || ''));

  // 标题自动换行 (按字符数, 中英文按 18 字宽)
  const titleLines = wrapText(r.title || '', 14).split('\n').slice(0, 3);

  // 教学话术截断 (200 字以内)
  let voiceText = r.description || '';
  if (voiceText.length > 200) voiceText = voiceText.slice(0, 197) + '...';
  const voiceLines = wrapText(voiceText, 32).split('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${SHARE_W}" height="${SHARE_H}" viewBox="0 0 ${SHARE_W} ${SHARE_H}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0d18"/>
      <stop offset="100%" stop-color="#1a2040"/>
    </linearGradient>
  </defs>
  <rect width="${SHARE_W}" height="${SHARE_H}" fill="url(#bg)"/>
  <foreignObject x="0" y="0" width="${SHARE_W}" height="${SHARE_H}">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; color:#e6e9f2; padding:64px 72px; box-sizing:border-box; height:100%; display:flex; flex-direction:column;">
      <!-- 顶部 logo + 学科 tag -->
      <div style="display:flex; align-items:center; gap:14px; margin-bottom:32px;">
        <div style="display:inline-flex; align-items:center; gap:10px; padding:10px 20px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:24px; font-size:20px; font-weight:700; color:#fff;">
          <span style="display:inline-block; width:28px; height:28px; border-radius:6px; background:${col};"></span>
          <span>${escHtml(subjectCn)}</span>
        </div>
        <div style="display:inline-flex; align-items:center; gap:8px; padding:10px 18px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:18px; font-family:'SF Mono', monospace; font-size:18px; color:#a5b8f5;">
          ${gradeRange}
        </div>
        ${minutes ? `<div style="display:inline-flex; align-items:center; gap:6px; padding:8px 14px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:18px; font-size:18px; color:#a5b8f5;">⏱ ${minutes} 分钟</div>` : ''}
        ${difficultyDots ? `<div style="display:inline-flex; align-items:center; gap:6px; padding:8px 14px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:18px; font-size:18px; color:#a5b8f5;">${difficultyDots}</div>` : ''}
      </div>

      <!-- 标题 -->
      <div style="margin-bottom:24px;">
        ${titleLines.map(line => `<div style="font-size:88px; font-weight:900; line-height:1.1; color:#fff; letter-spacing:-0.02em;">${escHtml(line)}</div>`).join('')}
      </div>

      ${summary ? `<div style="font-size:26px; color:#8a92a8; margin-bottom:36px; line-height:1.5;">${escHtml(summary)}</div>` : ''}

      <!-- 教学话术 -->
      ${voiceText ? `
        <div style="background:rgba(107,140,255,0.08); border-left:5px solid ${col}; border-radius:8px; padding:24px 28px; margin-bottom:32px;">
          <div style="font-size:20px; color:${col}; font-weight:700; margin-bottom:10px;">🎓 这步怎么教</div>
          <div style="font-size:26px; color:#dde4f5; line-height:1.7;">
            ${voiceLines.slice(0, 5).map(l => `<div>${escHtml(l)}</div>`).join('')}
          </div>
        </div>
      ` : ''}

      <!-- 之前要学 + 之后能学 -->
      <div style="display:flex; gap:24px; flex:1; min-height:0;">
        ${preNames.length ? `
          <div style="flex:1; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:24px;">
            <div style="font-size:20px; color:#6b8cff; font-weight:700; margin-bottom:14px;">⬅ 之前要学</div>
            ${preNames.map(t => `<div style="font-size:22px; color:#e6e9f2; line-height:1.6; padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.05);">• ${t}</div>`).join('')}
          </div>
        ` : ''}
        ${nxtNames.length ? `
          <div style="flex:1; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:24px;">
            <div style="font-size:20px; color:#7bc96f; font-weight:700; margin-bottom:14px;">➡ 之后能学</div>
            ${nxtNames.map(t => `<div style="font-size:22px; color:#e6e9f2; line-height:1.6; padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.05);">• ${t}</div>`).join('')}
          </div>
        ` : ''}
      </div>

      <!-- 底部 -->
      <div style="margin-top:32px; padding-top:20px; border-top:1px solid rgba(255,255,255,0.08); display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size:20px; color:#8a92a8; font-family:'SF Mono', monospace;">${siteUrl}</div>
        <div style="font-size:18px; color:#5a6278; font-family:'SF Mono', monospace;">${conceptId}</div>
      </div>
    </div>
  </foreignObject>
</svg>`;
}

async function svgToPngBlob(svgString) {
  // 加 xmlns
  if (!svgString.includes('xmlns=')) {
    svgString = svgString.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
  }
  return new Promise((resolve, reject) => {
    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = SHARE_W;
      canvas.height = SHARE_H;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#0a0d18';
      ctx.fillRect(0, 0, SHARE_W, SHARE_H);
      try {
        ctx.drawImage(img, 0, 0, SHARE_W, SHARE_H);
        URL.revokeObjectURL(url);
        canvas.toBlob(b => b ? resolve(b) : reject(new Error('toBlob 失败')), 'image/png');
      } catch (e) {
        // SVG foreignObject 会让 canvas 被污染, 走 fallback
        URL.revokeObjectURL(url);
        reject(new Error('CANVAS_TAINTED:' + e.message));
      }
    };
    img.onerror = (e) => {
      URL.revokeObjectURL(url);
      reject(new Error('SVG 加载失败: ' + (e.message || e)));
    };
    img.src = url;
  });
}

// Fallback: 直接用 Canvas 2D 渲染 (避免 foreignObject taint 问题)
function renderToCanvas(node, canvas) {
  const r = node.raw || node;
  const col = (typeof PALETTE !== 'undefined' && PALETTE[r.subject]) || '#5b8def';
  const subjectCn = SUBJECT_CN[r.subject] || r.subject || '';
  const gradeRange = (r.grade_start || 0) === (r.grade_end || 0)
    ? `G${r.grade_start}`
    : `G${r.grade_start || 0}-${r.grade_end || 0}`;
  const difficultyDots = r.difficulty
    ? '●'.repeat(r.difficulty) + '○'.repeat(5 - r.difficulty)
    : '';
  const minutes = r.estimated_minutes || '';

  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

  // 背景
  const grad = ctx.createLinearGradient(0, 0, W, H);
  grad.addColorStop(0, '#0a0d18');
  grad.addColorStop(1, '#1a2040');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  // 字体
  const FONT_FAMILY = '-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif';
  const FONT_MONO = '"SF Mono", monospace';

  // 顶部 tag row
  let y = 100;
  let x = 80;
  // 学科 tag
  ctx.fillStyle = 'rgba(255,255,255,0.06)';
  ctx.strokeStyle = 'rgba(255,255,255,0.1)';
  ctx.lineWidth = 1;
  const tag1W = ctx.measureText(subjectCn).width + 80;
  drawRoundRect(ctx, x, y, tag1W, 56, 28);
  ctx.fill();
  ctx.stroke();
  // 学科色圆
  ctx.fillStyle = col;
  ctx.beginPath();
  ctx.arc(x + 24, y + 28, 14, 0, Math.PI * 2);
  ctx.fill();
  // 学科名
  ctx.fillStyle = '#fff';
  ctx.font = `600 24px ${FONT_FAMILY}`;
  ctx.textBaseline = 'middle';
  ctx.fillText(subjectCn, x + 48, y + 28);
  x += tag1W + 14;

  // 学科段
  ctx.fillStyle = 'rgba(255,255,255,0.04)';
  const tag2W = ctx.measureText(gradeRange).width + 36;
  drawRoundRect(ctx, x, y, tag2W, 56, 28);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#a5b8f5';
  ctx.font = `400 22px ${FONT_MONO}`;
  ctx.fillText(gradeRange, x + 18, y + 28);
  x += tag2W + 14;

  // 时间 + 难度
  if (minutes) {
    ctx.fillStyle = 'rgba(255,255,255,0.04)';
    const minLabel = '⏱ ' + minutes + ' 分钟';
    const tag3W = ctx.measureText(minLabel).width + 36;
    drawRoundRect(ctx, x, y, tag3W, 56, 28);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#a5b8f5';
    ctx.font = `400 22px ${FONT_FAMILY}`;
    ctx.fillText(minLabel, x + 18, y + 28);
    x += tag3W + 14;
  }
  if (difficultyDots) {
    ctx.fillStyle = 'rgba(255,255,255,0.04)';
    const tag4W = ctx.measureText(difficultyDots).width + 36;
    drawRoundRect(ctx, x, y, tag4W, 56, 28);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#a5b8f5';
    ctx.font = `400 22px ${FONT_FAMILY}`;
    ctx.fillText(difficultyDots, x + 18, y + 28);
  }

  // 标题 (大, 多行)
  y = 220;
  ctx.fillStyle = '#fff';
  ctx.font = `900 88px ${FONT_FAMILY}`;
  const titleText = r.title || '';
  const titleLines = wrapText(titleText, 14).split('\n').slice(0, 3);
  const lh = 96;
  for (const line of titleLines) {
    ctx.fillText(line, 80, y);
    y += lh;
  }

  // summary
  y += 10;
  if (r.summary) {
    ctx.fillStyle = '#8a92a8';
    ctx.font = `400 26px ${FONT_FAMILY}`;
    const summaryLines = wrapText(r.summary, 28).split('\n').slice(0, 2);
    for (const line of summaryLines) {
      ctx.fillText(line, 80, y);
      y += 38;
    }
  }

  // 教学话术
  y += 20;
  let voiceText = r.description || '';
  if (voiceText.length > 200) voiceText = voiceText.slice(0, 197) + '...';
  if (voiceText) {
    const vh = 220;
    ctx.fillStyle = 'rgba(107,140,255,0.08)';
    drawRoundRect(ctx, 80, y, W - 160, vh, 12);
    ctx.fill();
    // 左边框
    ctx.fillStyle = col;
    ctx.fillRect(80, y, 8, vh);
    // 标题
    ctx.fillStyle = col;
    ctx.font = `700 22px ${FONT_FAMILY}`;
    ctx.textBaseline = 'top';
    ctx.fillText('🎓 这步怎么教', 112, y + 24);
    // 内容
    ctx.fillStyle = '#dde4f5';
    ctx.font = `400 26px ${FONT_FAMILY}`;
    const voiceLines = wrapText(voiceText, 32).split('\n').slice(0, 5);
    let vy = y + 60;
    for (const line of voiceLines) {
      ctx.fillText(line, 112, vy);
      vy += 36;
    }
    y += vh + 20;
  }

  // 之前要学 + 之后能学
  const preNames = (node._pre || []).slice(0, 4);
  const nxtNames = (node._nxt || []).slice(0, 4);
  const colW = (W - 160 - 24) / 2;
  if (preNames.length || nxtNames.length) {
    const boxH = 220;
    let bx = 80;
    if (preNames.length) {
      drawCardBox(ctx, bx, y, colW, boxH, '⬅ 之前要学', '#6b8cff');
      let by = y + 60;
      for (const item of preNames) {
        ctx.fillStyle = '#e6e9f2';
        ctx.font = `500 22px ${FONT_FAMILY}`;
        ctx.textBaseline = 'top';
        const name = (item.t || item.id || '').slice(0, 18);
        ctx.fillText('• ' + name, bx + 20, by);
        // 底边线
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.beginPath();
        ctx.moveTo(bx + 20, by + 32);
        ctx.lineTo(bx + colW - 20, by + 32);
        ctx.stroke();
        by += 40;
      }
      bx += colW + 24;
    }
    if (nxtNames.length) {
      drawCardBox(ctx, bx, y, colW, boxH, '➡ 之后能学', '#7bc96f');
      let by = y + 60;
      for (const item of nxtNames) {
        ctx.fillStyle = '#e6e9f2';
        ctx.font = `500 22px ${FONT_FAMILY}`;
        ctx.textBaseline = 'top';
        const name = (item.t || item.id || '').slice(0, 18);
        ctx.fillText('• ' + name, bx + 20, by);
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.beginPath();
        ctx.moveTo(bx + 20, by + 32);
        ctx.lineTo(bx + colW - 20, by + 32);
        ctx.stroke();
        by += 40;
      }
    }
    y += boxH + 20;
  }

  // 底部
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.beginPath();
  ctx.moveTo(80, H - 80);
  ctx.lineTo(W - 80, H - 80);
  ctx.stroke();
  ctx.fillStyle = '#8a92a8';
  ctx.font = `400 22px ${FONT_MONO}`;
  ctx.textBaseline = 'top';
  ctx.fillText('zachsaws.github.io/open-curriculum-cn', 80, H - 60);
  ctx.fillStyle = '#5a6278';
  ctx.font = `400 20px ${FONT_MONO}`;
  const idText = r.id || '';
  const idW = ctx.measureText(idText).width;
  ctx.fillText(idText, W - 80 - idW, H - 60);
}

function drawRoundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function drawCardBox(ctx, x, y, w, h, title, titleColor) {
  ctx.fillStyle = 'rgba(255,255,255,0.03)';
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth = 1;
  drawRoundRect(ctx, x, y, w, h, 12);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = titleColor;
  ctx.font = `700 22px -apple-system, "PingFang SC", sans-serif`;
  ctx.textBaseline = 'top';
  ctx.fillText(title, x + 24, y + 20);
}

async function downloadShareImage(node) {
  let blob;
  try {
    const svg = generateShareSVG(node);
    blob = await svgToPngBlob(svg);
  } catch (e) {
    // fallback: canvas 直接渲染
    if (e.message && e.message.startsWith('CANVAS_TAINTED')) {
      const canvas = document.createElement('canvas');
      canvas.width = SHARE_W;
      canvas.height = SHARE_H;
      renderToCanvas(node, canvas);
      blob = await new Promise((res, rej) => canvas.toBlob(b => b ? res(b) : rej(new Error('canvas toBlob 失败')), 'image/png'));
    } else throw e;
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeTitle = (node.raw?.title || node.id || 'concept').replace(/[\\/:*?"<>|]/g, '_');
  a.download = `学习卡-${safeTitle}.png`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function copyShareImage(node) {
  if (!navigator.clipboard || !window.ClipboardItem) {
    throw new Error('当前浏览器不支持剪贴板图片');
  }
  // 直接用 canvas 渲染 (避免 SVG taint)
  const canvas = document.createElement('canvas');
  canvas.width = SHARE_W;
  canvas.height = SHARE_H;
  renderToCanvas(node, canvas);
  const blob = await new Promise((res, rej) => canvas.toBlob(b => b ? res(b) : rej(new Error('toBlob 失败')), 'image/png'));
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
}

function getPreNxtForNode(idx, n, NODES) {
  if (typeof n === 'undefined' || typeof NODES === 'undefined') return { pre: [], nxt: [] };
  const r = n.raw || n;
  const id = r.id || n.id;
  // 从全局 EDGES 找直接 pre/nxt (funnel.js 的 directPre 是 let 局部, 不可访问)
  // 注意: funnel.js 的 EDGES 是 [fromIdx, toIdx, rel, reason, weight]
  // share.js 调用时, EDGES 可能没暴露在 window, 所以尝试多种获取方式
  let EDGES;
  if (typeof window !== 'undefined' && window.EDGES) {
    EDGES = window.EDGES;
  } else if (typeof EDGES !== 'undefined') {
    EDGES = EDGES;
  } else {
    // 兜底: 从 NODES 里通过 reverse BFS 找 (慢, 但保底)
    return getPreNxtViaBFS(id, NODES);
  }

  const pre = [];
  const nxt = [];
  for (let i = 0; i < EDGES.length; i++) {
    const e = EDGES[i];
    if (e.length < 3) continue;
    if (e[2] === 'relates_to') continue;
    // e[0] = fromIdx, e[1] = toIdx, e[2] = rel
    if (e[1] === idx) pre.push(e[0]);
    if (e[0] === idx) nxt.push(e[1]);
  }
  return {
    pre: pre.slice(0, 4).map(i => ({ t: NODES[i]?.t, id: NODES[i]?.id })),
    nxt: nxt.slice(0, 4).map(i => ({ t: NODES[i]?.t, id: NODES[i]?.id })),
  };
}

function getPreNxtViaBFS(targetId, NODES) {
  // 兜底: 用 NODES 的 raw 字段找
  const pre = [];
  const nxt = [];
  for (const n of NODES) {
    if (n.raw?.id === targetId) continue;
    const fromId = n.raw?.id;
    // 简单判断: 名字中包含关系 (不可靠, 兜底用)
  }
  return { pre, nxt };
}

function showShareModal(node, NODES) {
  // 关闭已有
  document.getElementById('share-modal')?.remove();
  // 准备数据
  let idx = -1;
  if (typeof NODES !== 'undefined') {
    idx = NODES.findIndex(n => (n.raw?.id || n.id) === (node.raw?.id || node.id));
  }
  const nodeWithRel = { ...node };
  if (idx >= 0) {
    const rels = getPreNxtForNode(idx, node, NODES);
    nodeWithRel._pre = rels.pre;
    nodeWithRel._nxt = rels.nxt;
  }

  const modal = document.createElement('div');
  modal.id = 'share-modal';
  modal.style.cssText = 'position:fixed; inset:0; z-index:100; background:rgba(0,0,0,0.85); backdrop-filter:blur(8px); display:flex; align-items:center; justify-content:center; padding:24px;';
  modal.innerHTML = `
    <div style="background:#0a0d18; border:1px solid rgba(255,255,255,0.1); border-radius:16px; max-width:90vw; max-height:90vh; display:flex; flex-direction:column; overflow:hidden;">
      <div style="padding:16px 20px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.08);">
        <div style="font-size:14px; font-weight:700; color:#fff;">📤 分享学习卡 (1080×1440)</div>
        <button id="share-close" style="background:transparent; border:none; color:#8a92a8; font-size:18px; cursor:pointer; padding:4px 8px;">×</button>
      </div>
      <div style="padding:20px; overflow:auto; flex:1; display:flex; align-items:center; justify-content:center;">
        <div id="share-preview" style="width:360px; height:480px; background:#1a2040; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#8a92a8; font-size:13px;">生成中...</div>
      </div>
      <div style="padding:16px 20px; display:flex; gap:10px; border-top:1px solid rgba(255,255,255,0.08); flex-wrap:wrap;">
        <button id="share-download" style="flex:1; min-width:120px; padding:10px 16px; background:#6b8cff; color:#fff; border:none; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer;">⬇ 下载 PNG</button>
        <button id="share-copy" style="flex:1; min-width:120px; padding:10px 16px; background:rgba(255,255,255,0.06); color:#fff; border:1px solid rgba(255,255,255,0.1); border-radius:8px; font-size:13px; font-weight:600; cursor:pointer;">📋 复制图片</button>
        <div id="share-status" style="font-size:12px; color:#8a92a8; padding:10px 0;"></div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });
  document.getElementById('share-close').addEventListener('click', () => modal.remove());
  document.getElementById('share-download').addEventListener('click', async () => {
    const status = document.getElementById('share-status');
    status.textContent = '下载中...';
    try {
      await downloadShareImage(nodeWithRel);
      status.textContent = '✅ 已下载';
      setTimeout(() => status.textContent = '', 2000);
    } catch (e) {
      status.textContent = '❌ ' + e.message;
    }
  });
  document.getElementById('share-copy').addEventListener('click', async () => {
    const status = document.getElementById('share-status');
    status.textContent = '复制中...';
    try {
      await copyShareImage(nodeWithRel);
      status.textContent = '✅ 已复制到剪贴板';
      setTimeout(() => status.textContent = '', 2000);
    } catch (e) {
      status.textContent = '❌ ' + e.message;
    }
  });

  // 异步生成预览 (用 canvas 渲染, 避免 SVG taint)
  (async () => {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = SHARE_W;
      canvas.height = SHARE_H;
      renderToCanvas(nodeWithRel, canvas);
      const preview = document.getElementById('share-preview');
      if (preview) {
        preview.innerHTML = '';
        preview.style.background = 'transparent';
        // 显示缩小版预览
        canvas.style.cssText = 'width:100%; height:100%; object-fit:contain; border-radius:6px;';
        preview.appendChild(canvas);
      }
    } catch (e) {
      const preview = document.getElementById('share-preview');
      if (preview) preview.textContent = '预览生成失败: ' + e.message;
    }
  })();
}

// 暴露给外部
if (typeof window !== 'undefined') {
  window.showShareCard = (node, NODES) => {
    if (typeof PALETTE === 'undefined') {
      // 如果没定义 PALETTE, 用默认配色
      window.PALETTE = window.PALETTE || {
        math: '#5b8def', chinese: '#ef6b5b', english: '#7bc96f',
        science: '#f9a825', physics: '#ba68c8', chemistry: '#26a69a',
        biology: '#66bb6a', history: '#8d6e63', geography: '#42a5f5',
        morality_law: '#ec407a', info_tech: '#26c6da', art: '#ab47bc',
        pe_health: '#ff7043', labor: '#9ccc65', integrated: '#78909c',
      };
    }
    showShareModal(node, NODES);
  };
}
