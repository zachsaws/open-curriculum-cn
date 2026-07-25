// Open Curriculum CN — 概念学习卡分享 (V3.6.9)
// 1080×1440 SVG → PNG (无外部库, 用 foreignObject + canvas 转换)
// 用法: showShareCard(node) → 弹出模态, 提供"下载 PNG"和"复制到剪贴板"

'use strict';

const SHARE_W = 1080;
const SHARE_H = 1440;
const SUBJECT_CN = {
  math: '数学', chinese: '语文', english: '英语',
  science: '科学', physics: '物理', chemistry: '化学',
  biology: '生物', history: '历史', geography: '地理',
  morality_law: '道德与法治', info_tech: '信息科技', art: '艺术',
  pe_health: '体育与健康', labor: '劳动', integrated: '综合',
};

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

function wrap(text, max) {
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
  const titleLines = wrap(r.title || '', 14).split('\n').slice(0, 3);

  // 教学话术截断 (200 字以内)
  let voiceText = r.description || '';
  if (voiceText.length > 200) voiceText = voiceText.slice(0, 197) + '...';
  const voiceLines = wrap(voiceText, 32).split('\n');

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
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = SHARE_W;
      canvas.height = SHARE_H;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#0a0d18';
      ctx.fillRect(0, 0, SHARE_W, SHARE_H);
      ctx.drawImage(img, 0, 0, SHARE_W, SHARE_H);
      URL.revokeObjectURL(url);
      canvas.toBlob(b => b ? resolve(b) : reject(new Error('toBlob 失败')), 'image/png');
    };
    img.onerror = (e) => {
      URL.revokeObjectURL(url);
      reject(new Error('SVG 加载失败: ' + (e.message || e)));
    };
    img.src = url;
  });
}

async function downloadShareImage(node) {
  const svg = generateShareSVG(node);
  const blob = await svgToPngBlob(svg);
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
  const svg = generateShareSVG(node);
  const blob = await svgToPngBlob(svg);
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
}

function getPreNxtForNode(idx, n, NODES) {
  if (typeof n === 'undefined' || typeof NODES === 'undefined') return { pre: [], nxt: [] };
  const r = n.raw || n;
  // 用 prebuilt directPre / directNext 数组
  const pre = (window.directPre && window.directPre[idx]) || [];
  const nxt = (window.directNext && window.directNext[idx]) || [];
  // 排除 self
  const preFiltered = pre.filter(i => i !== idx);
  const nxtFiltered = nxt.filter(i => i !== idx);
  return {
    pre: preFiltered.slice(0, 4).map(i => ({ t: NODES[i]?.t, id: NODES[i]?.id })),
    nxt: nxtFiltered.slice(0, 4).map(i => ({ t: NODES[i]?.t, id: NODES[i]?.id })),
  };
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

  // 异步生成预览
  (async () => {
    try {
      const svg = generateShareSVG(nodeWithRel);
      const blob = await svgToPngBlob(svg);
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.style.cssText = 'width:100%; height:100%; object-fit:contain; border-radius:6px;';
      img.onload = () => URL.revokeObjectURL(url);
      img.src = url;
      const preview = document.getElementById('share-preview');
      if (preview) {
        preview.innerHTML = '';
        preview.style.background = 'transparent';
        preview.appendChild(img);
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
