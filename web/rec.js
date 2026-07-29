// V4.0.4 个性化推荐渲染 — 独立文件, 避开 V4.0.3 内嵌 syntax 坑
// 用法: window.Recommender.render(containerId, recData, conceptId, status)
'use strict';

(function () {
  // 工具: escape HTML
  function esc(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
  }

  // 工具: 从 URL 提取 B 站 BV 号当显示文本
  function bvFromUrl(url) {
    if (!url) return '';
    const m = String(url).match(/BV[0-9A-Za-z]+/);
    return m ? m[0] : '';
  }

  // 工具: 从 URL 提取搜索关键词当显示文本 (search 链接用)
  function searchHintFromUrl(url) {
    if (!url) return '';
    try {
      const u = new URL(url);
      const kw = u.searchParams.get('keyword');
      return kw ? '🔍 搜索: ' + decodeURIComponent(kw) : '🔍 B 站搜索';
    } catch (e) {
      return '🔍 B 站搜索';
    }
  }

  // 工具: 状态决定 CTA 文案
  function ctaForStatus(status) {
    if (status === '薄弱') return { icon: '🆘', text: '薄弱? 这些资源能帮你 5 分钟补上基础' };
    if (status === '巩固') return { icon: '🎯', text: '还差一点? 这些综合题 + 视频能帮你稳到 95%' };
    return { icon: '🚀', text: '掌握得不错? 看看挑战题拔高' };
  }

  function render(containerId, recData, conceptId, status, conceptTitle) {
    const c = document.getElementById(containerId);
    if (!c) return;
    const rec = (recData && recData.recommendations) ? recData.recommendations[conceptId] : null;
    if (!rec) {
      // 19 quick pick 之外, 给 B 站搜索 fallback
      c.innerHTML = renderFallback(conceptId, conceptTitle, status);
      return;
    }
    const cta = ctaForStatus(status);
    const videosHtml = (rec.videos || []).slice(0, 3).map(v => {
      const isSearch = v.url && v.url.includes('search.bilibili.com');
      const display = isSearch
        ? (v.title || searchHintFromUrl(v.url))
        : (v.title || 'B 站视频');
      const sub = isSearch
        ? (searchHintFromUrl(v.url) || 'B 站搜索')
        : (v.author ? '👤 ' + esc(v.author) : '') + (v.plays ? '  ·  ' + esc(v.plays) : '');
      return `<a class="rec-link" href="${esc(v.url)}" target="_blank" rel="noopener">
        <span class="rec-icon">${isSearch ? '🔍' : '📺'}</span>
        <span class="rec-text">
          <span class="rec-title">${esc(display)}</span>
          ${sub ? '<span class="rec-sub">' + sub + '</span>' : ''}
        </span>
        <span class="rec-arrow">→</span>
      </a>`;
    }).join('');

    const tb = rec.textbook;
    const khan = rec.khan;
    const extraHtml = (tb || khan) ? `<div class="rec-extras">
      ${tb ? `<a class="rec-extra" href="#" onclick="return false" title="人教版/部编版教材">
        <span class="rec-extra-icon">📖</span>
        <span class="rec-extra-text">
          <span class="rec-extra-title">教材</span>
          <span class="rec-extra-sub">${esc(tb.name || '')}${tb.chapter ? ' · ' + esc(tb.chapter) : ''}${tb.page ? ' · ' + esc(tb.page) : ''}</span>
        </span>
      </a>` : ''}
      ${khan && khan.url ? `<a class="rec-extra" href="${esc(khan.url)}" target="_blank" rel="noopener">
        <span class="rec-extra-icon">🎓</span>
        <span class="rec-extra-text">
          <span class="rec-extra-title">Khan Academy</span>
          <span class="rec-extra-sub">免费公开课 · 可汗学院</span>
        </span>
      </a>` : ''}
    </div>` : '';

    c.innerHTML = `
      <div class="rec-cta">
        <span class="rec-cta-icon">${cta.icon}</span>
        <span class="rec-cta-text">${esc(cta.text)}</span>
        <span class="rec-cta-tag">// 概念: ${esc(rec.title || conceptId)}</span>
      </div>
      <div class="rec-list">${videosHtml}</div>
      ${extraHtml}
      <p class="rec-foot">// 资源来源: B 站公开视频 / 人教版教材 / Khan Academy · 长尾 1887 概念走 B 站搜索 fallback</p>
    `;
  }

  function renderFallback(conceptId, conceptTitle, status) {
    const kw = encodeURIComponent(conceptTitle || conceptId);
    const cta = ctaForStatus(status);
    return `
      <div class="rec-cta">
        <span class="rec-cta-icon">${cta.icon}</span>
        <span class="rec-cta-text">${esc(cta.text)}</span>
        <span class="rec-cta-tag">// 概念: ${esc(conceptTitle || conceptId)}</span>
      </div>
      <div class="rec-list">
        <a class="rec-link" href="https://search.bilibili.com/all?keyword=${kw}" target="_blank" rel="noopener">
          <span class="rec-icon">🔍</span>
          <span class="rec-text">
            <span class="rec-title">B 站搜: ${esc(conceptTitle || conceptId)}</span>
            <span class="rec-sub">🔍 搜索 · 长尾概念 fallback</span>
          </span>
          <span class="rec-arrow">→</span>
        </a>
        <a class="rec-link" href="https://zh.khanacademy.org/search?query=${kw}" target="_blank" rel="noopener">
          <span class="rec-icon">🎓</span>
          <span class="rec-text">
            <span class="rec-title">Khan Academy 搜: ${esc(conceptTitle || conceptId)}</span>
            <span class="rec-sub">🎓 可汗学院 · 免费公开课</span>
          </span>
          <span class="rec-arrow">→</span>
        </a>
      </div>
      <p class="rec-foot">// 长尾概念暂未手挑视频, 走 B 站搜索 + Khan Academy 搜索 fallback</p>
    `;
  }

  window.Recommender = { render };
})();
