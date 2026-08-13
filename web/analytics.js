// web/analytics.js — 轻量隐私友好埋点 (M3 可衡量)
// 设计: 零依赖, 事件先入 localStorage 队列 (最多留 200 条);
// 若配置了上报端点, 用 sendBeacon 异步上报 (不阻塞主线程); 否则仅本地累积。
// 配置方式 (任选其一):
//   1) <meta name="occ-analytics-endpoint" content="https://your.endpoint/collect">
//   2) window.OCC_ANALYTICS_ENDPOINT = 'https://...';
// 调试: 控制台 window.OCC_dumpEvents() / window.OCC_clearEvents()
(function () {
  'use strict';
  var KEY = 'occ_events';
  function load() { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; } }
  function save(a) { try { localStorage.setItem(KEY, JSON.stringify(a.slice(-200))); } catch (e) {} }
  var queue = load();

  function endpoint() {
    if (window.OCC_ANALYTICS_ENDPOINT) return window.OCC_ANALYTICS_ENDPOINT;
    try {
      var m = document.querySelector('meta[name="occ-analytics-endpoint"]');
      if (m && m.getAttribute('content')) return m.getAttribute('content');
    } catch (e) {}
    return null;
  }

  function trackEvent(name, props) {
    var ref = 'direct';
    try {
      var sp = new URLSearchParams(location.search);
      var f = sp.get('from');
      ref = f ? f : (sp.get('ref') || 'direct');
    } catch (e) {}
    var ev = { n: name, p: props || {}, t: Date.now(), ref: ref, u: location.pathname };
    queue.push(ev);
    save(queue);
    var ep = endpoint();
    if (ep) {
      try {
        var body = JSON.stringify(ev);
        if (navigator.sendBeacon) {
          navigator.sendBeacon(ep, new Blob([body], { type: 'application/json' }));
        } else {
          fetch(ep, { method: 'POST', body: body, keepalive: true }).catch(function () {});
        }
      } catch (e) {}
    }
    if (window.OCC_ANALYTICS_DEBUG) console.log('[track]', name, ev);
  }

  window.trackEvent = trackEvent;
  window.OCC_dumpEvents = function () { return queue; };
  window.OCC_clearEvents = function () { queue = []; save(queue); };
})();
