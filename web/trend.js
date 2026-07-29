// V4.0.4 完整 canvas 进度趋势图 — 独立文件, 避开 V4.0.3 内嵌 syntax 坑
// 用法: window.TrendChart.render(canvasId, historyArray, weakThreshold, consolidateThreshold)
'use strict';

(function () {
  const STATUS_COLOR = {
    '薄弱': '#ef6b5b',      // 红
    '巩固': '#e0c97f',      // 黄
    '已掌握': '#7bc96f',    // 绿
  };
  const STATUS_GLYPH = {
    '薄弱': '😟',
    '巩固': '🙂',
    '已掌握': '🎉',
  };

  // 每个 canvas 保存自己的 state (history/threshold/dpr)
  const STATE = new WeakMap();

  function fmtDate(iso) {
    const d = new Date(iso);
    const m = d.getMonth() + 1;
    const day = d.getDate();
    const h = d.getHours();
    const min = String(d.getMinutes()).padStart(2, '0');
    return m + '/' + day + ' ' + h + ':' + min;
  }

  function render(canvasId, history, weakThreshold, consolidateThreshold) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const data = (history || []).slice().sort((a, b) => a.date.localeCompare(b.date));

    // 适配 retina
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 800;
    const cssH = canvas.clientHeight || 280;
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);

    STATE.set(canvas, { data, weakThreshold, consolidateThreshold, dpr, cssW, cssH });

    if (data.length < 2) {
      drawPlaceholder(canvas, data.length);
      return;
    }

    // hover 状态
    if (!canvas._trendHoverInited) {
      canvas._trendHoverInited = true;
      canvas.addEventListener('mousemove', e => onHover(canvas, e));
      canvas.addEventListener('mouseleave', () => { canvas._hoverIdx = -1; paint(canvas); });
    }
    paint(canvas);
  }

  function paint(canvas) {
    const st = STATE.get(canvas);
    if (!st) return;
    const { data, weakThreshold, consolidateThreshold, dpr, cssW, cssH } = st;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    if (data.length < 2) {
      drawPlaceholder(canvas, data.length);
      return;
    }

    const padL = 44, padR = 16, padT = 20, padB = 36;
    const W = cssW - padL - padR;
    const H = cssH - padT - padB;

    // 背景
    ctx.fillStyle = 'rgba(255,255,255,0.02)';
    ctx.fillRect(0, 0, cssW, cssH);

    // 网格 + Y 轴
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.font = '11px "SF Mono", monospace';
    ctx.fillStyle = '#5a6278';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (let v = 0; v <= 100; v += 25) {
      const y = padT + H - (v / 100) * H;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + W, y);
      ctx.stroke();
      ctx.fillText(v + '%', padL - 6, y);
    }

    // 阈值线
    drawDashedLine(ctx, padL + W, padT + H - (consolidateThreshold / 100) * H, padL, padT + H - (consolidateThreshold / 100) * H,
      'rgba(123,201,111,0.45)', '巩固 ' + consolidateThreshold + '%');
    drawDashedLine(ctx, padL + W, padT + H - (weakThreshold / 100) * H, padL, padT + H - (weakThreshold / 100) * H,
      'rgba(239,107,91,0.45)', '薄弱 ' + weakThreshold + '%');

    const xAt = i => padL + (data.length === 1 ? W / 2 : (i / (data.length - 1)) * W);
    const yAt = score => padT + H - (score / 100) * H;

    // X 轴时间
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = '#8a92a8';
    const labelStep = Math.max(1, Math.ceil(data.length / 6));
    for (let i = 0; i < data.length; i += labelStep) {
      const x = xAt(i);
      ctx.fillText(fmtDate(data[i].date), x, padT + H + 6);
    }

    // 折线
    ctx.strokeStyle = '#6b8cff';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = xAt(i);
      const y = yAt(data[i].score_pct);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // 数据点
    const hoverIdx = canvas._hoverIdx;
    for (let i = 0; i < data.length; i++) {
      const x = xAt(i);
      const y = yAt(data[i].score_pct);
      const color = STATUS_COLOR[data[i].status] || '#8a92a8';
      const r = i === hoverIdx ? 9 : 6;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#0d1120';
      ctx.beginPath();
      ctx.arc(x, y, r - 3, 0, Math.PI * 2);
      ctx.fill();
    }

    // tooltip
    if (hoverIdx >= 0 && hoverIdx < data.length) {
      const d = data[hoverIdx];
      const x = xAt(hoverIdx);
      const y = yAt(d.score_pct);
      const color = STATUS_COLOR[d.status] || '#8a92a8';
      const tipText = fmtDate(d.date) + '  ' + (STATUS_GLYPH[d.status] || '') + ' ' + d.score_pct + '%  ' + (d.status || '');
      ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
      const tw = ctx.measureText(tipText).width + 16;
      let tx = x + 12;
      if (tx + tw > padL + W) tx = x - tw - 12;
      const ty = Math.max(padT + 4, y - 28);
      ctx.fillStyle = 'rgba(13,17,32,0.95)';
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 1;
      roundRect(ctx, tx, ty, tw, 22, 4);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(tipText, tx + 8, ty + 11);
    }
  }

  function onHover(canvas, e) {
    const st = STATE.get(canvas);
    if (!st) return;
    const { data, dpr, cssW, cssH } = st;
    if (data.length < 2) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left);
    const my = (e.clientY - rect.top);
    const padL = 44, padR = 16, padT = 20, padB = 36;
    const W = cssW - padL - padR;
    const H = cssH - padT - padB;
    const xAt = i => padL + (data.length === 1 ? W / 2 : (i / (data.length - 1)) * W);
    const yAt = score => padT + H - (score / 100) * H;
    let nearest = -1, distMin = Infinity;
    for (let i = 0; i < data.length; i++) {
      const dx = xAt(i) - mx;
      const dy = yAt(data[i].score_pct) - my;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d < distMin) { distMin = d; nearest = i; }
    }
    const newIdx = distMin < 20 ? nearest : -1;
    if (newIdx !== canvas._hoverIdx) {
      canvas._hoverIdx = newIdx;
      paint(canvas);
    }
  }

  function drawDashedLine(ctx, x1, y1, x2, y2, color, label) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = color;
    ctx.font = '10px "SF Mono", monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'bottom';
    ctx.fillText(label, x1 - 4, y1 - 2);
    ctx.restore();
  }

  function roundRect(ctx, x, y, w, h, r) {
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

  function drawPlaceholder(canvas, count) {
    const st = STATE.get(canvas);
    if (!st) return;
    const { dpr, cssW, cssH } = st;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = 'rgba(255,255,255,0.02)';
    ctx.fillRect(0, 0, cssW, cssH);
    ctx.fillStyle = '#5a6278';
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const need = Math.max(0, 2 - count);
    ctx.fillText(need > 0 ? '再测 ' + need + ' 次开启进度趋势图' : '暂无数据', cssW / 2, cssH / 2);
  }

  window.TrendChart = { render };
})();
