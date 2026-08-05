// V1.0 通用组件: 顶部版本徽章 + 反馈 FAB
// 在每个页面 </body> 之前引入:
//   <script src="./v1-chrome.js"></script>

(function() {
  if (window.__V1_CHROME_LOADED__) return;
  window.__V1_CHROME_LOADED__ = true;

  // 1. V1.0 公告条 (仅首页以外页面显示, 已在 index.html 内嵌)
  // 沉浸式 3D 页面 (explore/funnel) 不显示, 避免遮挡 3D 控件
  var isImmersive = /\/(explore|funnel)\.html$/.test(window.location.pathname);
  if (!isImmersive && !document.getElementById('v10-banner') && !document.querySelector('.v10-banner')) {
    try {
      if (localStorage.getItem('occ_v10_dismissed') !== '1') {
        var banner = document.createElement('aside');
        banner.className = 'v10-banner';
        banner.id = 'v10-banner-mini';
        banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:200;padding:8px 16px;background:#00875a;color:#fff;font-size:13px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.1);';
        banner.innerHTML = '🎉 <strong>V1.0 正式版发布</strong> · 1,906 概念 / 4,736 学习路径 / 9,264 题 / 1,008 视频 — ' +
          '<a href="./index.html" style="color:#ffce4f;font-weight:600;text-decoration:underline;margin-left:6px;">看新功能</a>' +
          '<button onclick="this.parentNode.remove();try{localStorage.setItem(\'occ_v10_dismissed\',\'1\');}catch(e){}" style="margin-left:12px;background:transparent;border:0;color:#fff;font-size:16px;cursor:pointer;padding:0 4px;line-height:1;" aria-label="关闭">×</button>';
        document.body.appendChild(banner);

        // 调整页面顶部 fixed 元素的下移距离 (header 已被 banner 顶下去)
        setTimeout(function() {
          var fixed = document.querySelectorAll('.header, .nav');
          fixed.forEach(function(el) {
            var cs = window.getComputedStyle(el);
            if (cs.position === 'fixed' || cs.position === 'sticky') {
              el.dataset._origTop = el.style.top || cs.top;
              el.style.top = '36px';
            }
          });
        }, 50);
      }
    } catch (e) {}
  }

  // 2. 反馈 FAB (固定右下角)
  if (!document.querySelector('.feedback-fab')) {
    var fab = document.createElement('nav');
    fab.className = 'feedback-fab';
    fab.setAttribute('aria-label', '反馈入口');
    fab.style.cssText = 'position:fixed;right:20px;bottom:20px;z-index:100;display:flex;flex-direction:column;gap:8px;';
    fab.innerHTML =
      '<a href="https://github.com/zachsaws/open-curriculum-cn/issues/new" target="_blank" rel="noopener" ' +
      'style="display:inline-flex;align-items:center;gap:6px;padding:10px 16px;background:#0a0d18;color:#faf6ee;border-radius:999px;font-size:13px;font-weight:600;text-decoration:none;box-shadow:0 4px 12px rgba(10,13,24,0.18);">' +
      '<span>💬</span>反馈 / 报错</a>' +
      '<a href="./index.html" ' +
      'style="display:inline-flex;align-items:center;gap:6px;padding:8px 14px;background:#ffffff;color:#0a0d18;border:1px solid #e8e0cc;border-radius:999px;font-size:12px;font-weight:600;text-decoration:none;box-shadow:0 2px 6px rgba(10,13,24,0.1);">' +
      '<span>🏠</span>回首页</a>';

    // 移动端简化 (只留主按钮)
    if (window.innerWidth <= 480) {
      fab.innerHTML = '<a href="https://github.com/zachsaws/open-curriculum-cn/issues/new" target="_blank" rel="noopener" ' +
        'style="display:inline-flex;align-items:center;gap:4px;padding:8px 12px;background:#0a0d18;color:#faf6ee;border-radius:999px;font-size:12px;font-weight:600;text-decoration:none;box-shadow:0 4px 12px rgba(10,13,24,0.18);">' +
        '<span>💬</span>反馈</a>';
      fab.style.right = '12px';
      fab.style.bottom = '12px';
    }
    document.body.appendChild(fab);
  }

  // 3. 顶部右侧加版本号徽章 (轻量, 不破坏现有结构)
  // 仅在 .title-link / .logo 区域加, 不影响 fixed 元素
  if (!document.querySelector('.v10-badge')) {
    var target = document.querySelector('.title-sub') || document.querySelector('.title-link') || document.querySelector('.logo');
    if (target) {
      var badge = document.createElement('span');
      badge.className = 'v10-badge';
      badge.style.cssText = 'display:inline-block;margin-left:10px;padding:2px 8px;background:#00875a;color:#fff;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:0.05em;vertical-align:middle;';
      badge.textContent = 'V1.0';
      badge.title = 'V1.0 正式版 · 2026-08-05';
      target.appendChild(badge);
    }
  }
})();
