// Open Curriculum CN - 知识图谱可视化
// 使用 cytoscape.js (通过 window 全局) 2D 力导向图

// cytoscape 已在 index.html 引入为全局变量

const wrap = document.getElementById('wrap');
const cyContainer = document.getElementById('cy-container');
const loading = document.getElementById('loading');
const loadingMsg = document.getElementById('loadingMsg');

const PALETTE = {
  math: '#5b8def', chinese: '#ef6b5b', english: '#7bc96f',
  science: '#f9a825', physics: '#ba68c8', chemistry: '#26a69a',
  biology: '#66bb6a', history: '#8d6e63', geography: '#42a5f5',
  morality_law: '#ec407a', info_tech: '#26c6da', art: '#ab47bc',
  pe_health: '#ff7043', labor: '#9ccc65', integrated: '#78909c',
};

// SUBJECT_CN 已弃用 — 改用 window.tSubject() (单一真源: i18n.js SUBJECT_CN_I18N)

let DATA = null;
window.DATA = null;
let GROUPS = [];
let GCOL = [];
let cy;
let activeGroups = new Set();
// 当前打开的 card 节点 (供 applyI18n 重渲染用)
window._currentNode = null;
// 状态: 标签显示 / 根节点高亮 (供 applyI18n 决定按钮文字)
window._labelsOn = false;
window._rootsHighlighted = false;
// 概念地图模式
let mapMode = false;
let mapBranchOnly = true;
let mapSelectedNode = null; // 树中当前选中的概念 id

async function loadData() {
  loadingMsg.textContent = window.t ? window.t('loading') : '加载知识图谱...';
  try {
    const res = await fetch('./data/graph.json');
    if (!res.ok) throw new Error('graph.json 不存在');
    DATA = await res.json();
    window.DATA = DATA;
    console.log('Loaded', DATA.nodes.length, 'nodes,', DATA.edges.length, 'edges');
  } catch (e) {
    console.error(e);
    loadingMsg.innerHTML = `<div class="err">${window.t ? window.t('err_no_data') : '未找到图谱数据 (graph.json)<br><br>数据仍在采集中'}</div>`;
    return;
  }

  GROUPS = [...new Set(DATA.nodes.map(n => n.subject))].sort();
  GCOL = GROUPS.map(s => PALETTE[s] || '#888');
  activeGroups = new Set(GROUPS);

  // 启动时为每个节点存一份 title_orig (修复 i18n review Bug 7)
  DATA.nodes.forEach(n => { n.title_orig = n.title; });
  cy_nodes_initialized = true;

  document.getElementById('nCount').textContent = DATA.nodes.length.toLocaleString();
  document.getElementById('eCount').textContent = DATA.edges.length.toLocaleString();
  document.getElementById('gCount').textContent = GROUPS.length;

  buildLegend();
  initGraph();
  setupSearch();
  setupLangSwitch();
  setupKeyboardShortcuts();
  setupCardActions();
  setupKbdModal();
  // 启动后计算根节点
  setTimeout(() => updateRootCount(), 2000);
  loading.classList.add('done');
}

let cy_nodes_initialized = false;

function setupLangSwitch() {
  document.querySelectorAll('.lang-switch button').forEach(btn => {
    btn.onclick = () => {
      const lang = btn.dataset.lang;
      // 切到繁体前, 先确保 title_orig 已存 (修复隐性 bug: 之前永不被存)
      if (lang === 'zh-TW' && cy) {
        cy.nodes().forEach(n => {
          if (!n.data('title_orig') && n.data('title')) {
            n.data('title_orig', n.data('title'));
          }
        });
      }
      // 1) 切换 UI 文本 + 图例 (subject 名 / search / header / 按钮)
      setLang(lang);
      document.querySelectorAll('.lang-switch button').forEach(b => {
        b.classList.remove('on');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('on');
      btn.setAttribute('aria-selected', 'true');
      // 显式重画图例 (applyI18n 里的 buildLegend 调用因 module scope 看不到, 手动调)
      if (typeof buildLegend === 'function') buildLegend();
      // 2) 转换所有概念标题 (zh-TW 简→繁; 其他语言 恢复原文)
      if (cy) {
        if (lang === 'zh-TW') {
          cy.nodes().forEach(n => {
            const orig = n.data('title_orig') || n.data('title');
            if (orig && !n.data('title_trad')) {
              n.data('title_trad', simpToTrad(orig));
            }
            n.data('title', n.data('title_trad') || orig);
          });
        } else {
          cy.nodes().forEach(n => {
            if (n.data('title_orig')) n.data('title', n.data('title_orig'));
          });
        }
      }
      // 3) 标题转换后, 重渲染已打开的 showCard 让标题同步
      if (window._currentNode && typeof showCard === 'function') {
        showCard(window._currentNode);
      }
    };
  });
}

function buildLegend() {
  const legend = document.getElementById('legend');
  legend.innerHTML = '';
  const counts = GROUPS.map(s => DATA.nodes.filter(n => n.subject === s).length);
  GROUPS.forEach((s, i) => {
    const el = document.createElement('div');
    el.className = 'chip';
    el.dataset.subject = s;
    el.dataset.idx = i;
    el.title = window.t ? window.t('btn_fly_to') : '双击飞到该学科';
    // V2.3 a11y: chip 改为可聚焦 + aria
    el.setAttribute('role', 'button');
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-pressed', el.classList.contains('off') ? 'false' : 'true');
    el.setAttribute('aria-label', `${window.t('btn_chip_toggle') || '切换'} ${window.tSubject(s)} ${counts[i]} ${window.t('chip_count_unit') || '个概念'}`);
    el.innerHTML = `<span class="sw" style="background:${GCOL[i]}"></span><span class="nm">${window.tSubject(s)}</span><span class="ct">${counts[i]}</span>`;
    el.onclick = (e) => {
      // 双击才飞向该学科, 单击只切换显隐
      if (e.shiftKey) {
        flyToSubject(s);
        return;
      }
      el.classList.toggle('off');
      el.setAttribute('aria-pressed', el.classList.contains('off') ? 'false' : 'true');
      updateFilter();
    };
    el.ondblclick = () => flyToSubject(s);
    // 键盘: Enter / Space 触发单击
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        el.click();
      }
    });
    legend.appendChild(el);
  });
}

function flyToSubject(s) {
  if (!cy) return;
  const nodes = cy.nodes().filter(n => n.data('subject') === s);
  if (nodes.length === 0) return;
  // 计算中心 + 缩放
  const bb = nodes.boundingBox();
  cy.animate({
    center: { x: (bb.x1 + bb.x2) / 2, y: (bb.y1 + bb.y2) / 2 },
    zoom: 1.2,
    duration: 600,
  });
}

function updateFilter() {
  const chips = document.querySelectorAll('.chip');
  const newActive = new Set();
  chips.forEach(chip => {
    if (!chip.classList.contains('off')) newActive.add(chip.dataset.subject);
  });
  activeGroups = new Set(newActive);
  if (cy) {
    cy.nodes().forEach(n => {
      if (activeGroups.has(n.data('subject'))) {
        n.style('opacity', 1);
      } else {
        n.style('opacity', 0.1);
      }
    });
  }
}

// 计算"可学起入口" — V2.3 缩窄定义为 (indegree=0 && grade_start<=2)
// 课标 G1-2 阶段概念 = 真正"零基础可学", 无 G1-2 之前的学段
// 历史: V2.2 用纯 indegree=0 → 629/758 节点 (83%) 高亮, 视觉无意义
function isLearnableEntry(n) {
  return n.indegree() === 0 && (n.data('grade_start') || 99) <= 2;
}

function updateRootCount() {
  if (!cy) return 0;
  const entries = cy.nodes().filter(isLearnableEntry);
  const totalRoots = cy.nodes().filter(n => n.indegree() === 0).length;
  document.getElementById('rCount').textContent = entries.length;
  // 副标题: "可学起入口" (G1-2 阶段无先决), 总根数是参考
  const sub = document.getElementById('rCountSub');
  if (sub) sub.textContent = `/${totalRoots}`;
  return entries.length;
}

// 切换根节点高亮 — V2.3 缩窄到 G1-2 阶段无先决
function toggleRootsHighlight() {
  if (!cy) return;
  window._rootsHighlighted = !window._rootsHighlighted;
  cy.nodes().removeClass('root-node');
  if (window._rootsHighlighted) {
    cy.nodes().filter(isLearnableEntry).addClass('root-node');
  }
  document.getElementById('toggleRoots').textContent = window.t(window._rootsHighlighted ? 'btn_roots_off' : 'btn_roots');
  document.getElementById('toggleRoots').setAttribute('aria-pressed', String(!!window._rootsHighlighted));
  // V2.3 浮动按钮联动
  if (window._rootsHighlighted) {
    renderStartHereButtons();
  } else {
    removeStartHereButtons();
  }
}

// 搜索功能
function setupSearch() {
  const input = document.getElementById('searchInput');
  const results = document.getElementById('searchResults');
  let debounce = null;
  input.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => doSearch(input.value.trim()), 120);
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      input.value = '';
      results.classList.remove('on');
      cy.elements().removeClass('search-hit');
    }
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search')) results.classList.remove('on');
  });
}

function doSearch(q) {
  const results = document.getElementById('searchResults');
  if (!q || q.length < 1) {
    results.classList.remove('on');
    cy.elements().removeClass('search-hit');
    return;
  }
  const ql = q.toLowerCase();
  const hits = DATA.nodes.filter(n => {
    if (!activeGroups.has(n.subject)) return false;
    return (n.title || '').toLowerCase().includes(ql)
        || (n.id || '').toLowerCase().includes(ql)
        || (n.subdomain || '').toLowerCase().includes(ql)
        || (n.domain || '').toLowerCase().includes(ql)
        || (n.summary || '').toLowerCase().includes(ql);
  }).slice(0, 30);

  // 高亮
  cy.elements().removeClass('search-hit');
  const hitIds = new Set(hits.map(n => n.id));
  cy.nodes().forEach(n => {
    if (hitIds.has(n.id())) n.addClass('search-hit');
  });

  // 渲染结果列表
  if (hits.length === 0) {
    results.innerHTML = `<div class="r-empty">${window.t('empty_concepts')}</div>`;
  } else {
    const suffix = window.t('search_count_suffix');
    let html = `<div class="r-count">${hits.length} ${suffix}</div>`;
    hits.forEach((n) => {
      html += `<div class="r-item" data-id="${n.id}">
        <span class="r-dot" style="background:${PALETTE[n.subject] || '#888'}"></span>
        <span class="r-t">${n.title}</span>
        <span class="r-m">G${n.grade_start}${n.grade_end !== n.grade_start ? '-' + n.grade_end : ''}</span>
      </div>`;
    });
    results.innerHTML = html;
    // 绑定点击
    results.querySelectorAll('.r-item').forEach(el => {
      el.onclick = () => {
        const id = el.dataset.id;
        const n = cy.getElementById(id);
        if (n.length) {
          results.classList.remove('on');
          document.getElementById('searchInput').value = '';
          showCard(n.data());
          cy.animate({ center: { eles: n }, zoom: 2.5 }, { duration: 500 });
          cy.elements().unselect();
          n.select();
        }
      };
    });
  }
  results.classList.add('on');
}

function initGraph() {
  console.log('initGraph starting...');
  const r = wrap.getBoundingClientRect();
  console.log('Wrap size:', r.width, 'x', r.height);

  // 准备 cytoscape 数据
  // 兼容两种 edges 格式: V0.5 list [from, to, type] 或 V0.6 dict {from, to, type}
  const elements = [
    ...DATA.nodes.map(n => ({
      group: 'nodes',
      data: { ...n },
    })),
    ...DATA.edges.map((e, i) => {
      // 兼容 V2.2 [from, to, type] 数组 和 V3.0+ 对象
      const fromId = Array.isArray(e) ? e[0] : e.from;
      const toId = Array.isArray(e) ? e[1] : e.to;
      const eType = Array.isArray(e) ? (e[2] || 'hard') : (e.type === 0 ? 'soft' : 'hard');
      // 兼容 V2.2 source/rationale 字段 (cytoscape 强制 data.source/data.target, 不能 spread e 全部字段)
      const { source, rationale, from, to, type, ...rest } = e;
      return {
        group: 'edges',
        data: {
          id: 'e' + i,
          source: fromId,
          target: toId,
          type: eType,
          // V3.2: 完整保留 rel / reason / weight + V2.2 source/rationale
          rel: e.rel || (eType === 0 ? 'relates_to' : 'prerequisite'),
          reason: e.reason || '',
          weight: e.weight || (eType === 0 ? 0.5 : 1.0),
          edge_source: source || 'curriculum',  // V2.2 source 改名, 避免和 cytoscape 内部冲突
          rationale: rationale || '',
          ...rest,
        },
      };
    }),
  ];

  const nodeCount = DATA.nodes.length;
  // 大图 (500+) 优化: 缩小节点,默认不显示 label,加 zoom-based label
  const isLarge = nodeCount > 400;
  const nodeSize = isLarge ? 8 : 14;
  const baseFont = isLarge ? '10px' : '12px';

  cy = cytoscape({
    container: cyContainer,
    elements: elements,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': ele => {
            const s = ele.data('subject');
            return PALETTE[s] || '#5b8def';
          },
          'width': nodeSize,
          'height': nodeSize,
          'label': isLarge ? '' : 'data(title)',  // 大图默认不显示 label
          'color': '#e6e9f2',
          'font-size': baseFont,
          'font-family': '-apple-system, "PingFang SC", sans-serif',
          'text-valign': 'bottom',
          'text-margin-y': 4,
          'text-outline-color': '#0a0d18',
          'text-outline-width': 3,
          'opacity': 1,
        },
      },
      {
        selector: 'edge',
        style: {
          'width': isLarge ? 0.4 : 0.6,
          'line-color': 'rgba(180,195,235,0.35)',
          'curve-style': 'bezier',
          'opacity': isLarge ? 0.35 : 0.6,
        },
      },
      {
        selector: 'node:selected',
        style: {
          'border-color': '#fff',
          'border-width': 2,
          'border-opacity': 1,
          'label': 'data(title)',  // 选中时显示 label
          'font-size': '13px',
          'z-index': 99,
        },
      },
      {
        selector: 'node.hover',
        style: {
          'label': 'data(title)',
          'font-size': '12px',
          'z-index': 50,
        },
      },
      // 概念地图模式: 分支淡化 (V3.2.2 P0-9 修: 0.08 → 0.3 避免全黑屏)
      {
        selector: 'node.branch-dim',
        style: { 'opacity': 0.3 },
      },
      {
        selector: 'edge.branch-dim',
        style: { 'opacity': 0.1 },
      },
      {
        selector: 'node.branch-hl',
        style: {
          'border-color': '#7bc96f',
          'border-width': 3,
          'border-opacity': 1,
          'label': 'data(title)',
          'font-size': '13px',
          'z-index': 100,
        },
      },
      {
        selector: 'edge.branch-hl',
        style: {
          'line-color': '#7bc96f',
          'width': 1.5,
          'opacity': 0.9,
          'z-index': 90,
        },
      },
    ],
    layout: isLarge ? {
      // 大图: 先 random 撒开,再 cose 收敛
      name: 'preset',
      positions: {},
      fit: true,
    } : {
      name: 'cose',
      animate: false,
      nodeRepulsion: 80000,
      idealEdgeLength: 100,
      edgeElasticity: 0.45,
      gravity: 0.25,
      numIter: 1000,
      fit: true,
      padding: 50,
    },
    // 大图走两步 layout
    ...(isLarge ? { ready: undefined } : {}),
    wheelSensitivity: 0.2,
    minZoom: 0.15,
    maxZoom: 5,
  });

  // Hover 显示 label
  cy.on('mouseover', 'node', evt => {
    evt.target.addClass('hover');
  });
  cy.on('mouseout', 'node', evt => {
    evt.target.removeClass('hover');
  });

  // 大图两步 layout: 1) 按学科分块预设位置 2) cose 收敛
  if (isLarge) {
    setTimeout(() => {
      const W = cy.width();
      const H = cy.height();
      const padding = 60;
      // 把 GROUPS 按数量排序, 数量多的学科占地大
      const subjStats = GROUPS.map(s => ({
        s,
        n: DATA.nodes.filter(x => x.subject === s).length,
      }));
      // 按学科块面积比分配位置
      const total = subjStats.reduce((a, b) => a + b.n, 0);
      const usableW = W - padding * 2;
      const usableH = H - padding * 2;
      // 排成 4 列 N 行, 按数量从大到小排
      subjStats.sort((a, b) => b.n - a.n);
      const COLS = 4;
      const cellW = usableW / COLS;
      const rows = Math.ceil(subjStats.length / COLS);
      const cellH = usableH / rows;
      const pos = {};
      subjStats.forEach((s, idx) => {
        const col = idx % COLS;
        const row = Math.floor(idx / COLS);
        // 学科块中心
        const cx = padding + cellW * (col + 0.5);
        const cy_ = padding + cellH * (row + 0.5);
        // 学科内按 grade 排
        const ownNodes = cy.nodes().filter(n => n.data('subject') === s.s);
        const cols2 = Math.ceil(Math.sqrt(s.n * (cellW / cellH)));
        ownNodes.forEach((n, i) => {
          const c = i % cols2;
          const r = Math.floor(i / cols2);
          const rows2 = Math.ceil(s.n / cols2);
          const subW = cellW * 0.85;
          const subH = cellH * 0.85;
          pos[n.id()] = {
            x: cx - subW / 2 + (c + 0.5) * subW / cols2 + (Math.random() - 0.5) * 4,
            y: cy_ - subH / 2 + (r + 0.5) * subH / rows2 + (Math.random() - 0.5) * 4,
          };
        });
      });
      cy.layout({ name: 'preset', positions: pos, fit: true, padding: padding }).run();
      console.log('Big layout done —', DATA.nodes.length, 'nodes');
    }, 200);
  }

  cy.on('tap', 'node', evt => {
    showCard(evt.target.data());
    // 高亮 1-2 层邻居
    cy.elements().removeClass('neighbor-highlight').removeClass('neighbor-dim');
    const n = evt.target;
    const neighborhood = n.neighborhood().union(n);
    cy.elements().not(neighborhood).addClass('neighbor-dim');
    neighborhood.addClass('neighbor-highlight');
  });

  // EN 模式: 节点 label 用英文 (兜底用 CONCEPT_EN 字典)
  // 切换语言时由 applyI18n 重渲
  cy.on('tap', evt => {
    if (evt.target === cy) {
      document.getElementById('card').classList.remove('on');
      cy.elements().removeClass('neighbor-highlight').removeClass('neighbor-dim');
    }
  });

  // 自动 fit
  setTimeout(() => {
    cy.fit(undefined, 50);
  }, 200);

  console.log('initGraph done, nodes:', cy.nodes().length);
  window.cy = cy;  // 调试用
  setupCyViewSync();
}

function showCard(node) {
  const card = document.getElementById('card');
  // 记录当前节点 (供 applyI18n 重渲染)
  window._currentNode = node;
  document.getElementById('card-sw').style.background = PALETTE[node.subject] || '#888';
  document.getElementById('card-cs').textContent = `${window.tSubject(node.subject)} · G${node.grade_start || ''}-${node.grade_end || ''} · ${node.domain || ''}`;
  document.getElementById('card-ctl').textContent = window.tConcept ? window.tConcept(node) : node.title;

  // 标签行: bloom / difficulty / estimated_minutes / subdomain
  const tagRow = document.getElementById('card-tags');
  tagRow.innerHTML = '';
  // bloom
  (node.bloom || []).forEach(b => {
    const t = document.createElement('span');
    t.className = 'tag bloom';
    t.textContent = '✦ ' + b;
    tagRow.appendChild(t);
  });
  // difficulty
  if (node.difficulty) {
    const t = document.createElement('span');
    t.className = 'tag diff-' + node.difficulty;
    t.textContent = window.t('card_difficulty') + ' ' + '●'.repeat(node.difficulty) + '○'.repeat(5 - node.difficulty);
    tagRow.appendChild(t);
  }
  // estimated minutes
  if (node.estimated_minutes) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = '⏱ ' + node.estimated_minutes + ' ' + window.t('card_minutes');
    tagRow.appendChild(t);
  }
  // subdomain
  if (node.subdomain) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = node.subdomain;
    tagRow.appendChild(t);
  }

  // 内容要求 — 用 data-i18n 属性, applyI18n 会扫描
  const cr = document.getElementById('card-content-req');
  const crBlock = document.getElementById('card-content-req-block');
  if (node.content_req) {
    cr.textContent = node.content_req;
    crBlock.style.display = '';
  } else {
    crBlock.style.display = 'none';
  }
  // 页码链接
  const pageLink = document.getElementById('card-page-link');
  if (node.src_page) {
    const srcText = window.t('source_link');
    pageLink.innerHTML = ` · <a class="src-link" href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">P${node.src_page} ${srcText}</a>`;
  } else {
    pageLink.textContent = '';
  }

  // 学业要求 / 知识要点 / 例题 — 标题在 HTML 里已加 data-i18n, applyI18n 会扫
  const ar = document.getElementById('card-academic-req');
  const arBlock = document.getElementById('card-academic-req-block');
  if (node.academic_req) {
    ar.textContent = node.academic_req;
    arBlock.style.display = '';
  } else {
    arBlock.style.display = 'none';
  }

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
  } else {
    kpBlock.style.display = 'none';
  }

  const exRow = document.getElementById('card-examples');
  const exBlock = document.getElementById('card-examples-block');
  exRow.innerHTML = '';
  if (node.examples && node.examples.length) {
    node.examples.forEach(e => {
      const t = document.createElement('span');
      t.className = 'ex';
      t.textContent = e;
      exRow.appendChild(t);
    });
    exBlock.style.display = '';
  } else {
    exBlock.style.display = 'none';
  }

  // V3.2: 概念元信息 (type / age / centrality)
  const metaBlock = document.getElementById('card-meta-block');
  const meta = document.getElementById('card-meta');
  const metaItems = [];
  if (node.type) metaItems.push(`<span class="meta-tag type-${node.type.toLowerCase()}">${node.type}</span>`);
  if (node.age_range_start) metaItems.push(`<span class="meta-tag">🎂 ${node.age_range_start}-${node.age_range_end || node.age_range_start} 岁</span>`);
  if (node.centrality !== undefined) {
    const centPct = Math.round(node.centrality * 100);
    metaItems.push(`<span class="meta-tag" title="中心度 (被需要 + 能解锁)">⭐ 中心度 ${centPct}%</span>`);
  }
  if (node.bloom) metaItems.push(`<span class="meta-tag bloom-tag">${node.bloom}</span>`);
  if (metaItems.length) {
    meta.innerHTML = metaItems.join(' ');
    metaBlock.style.display = '';
  } else {
    metaBlock.style.display = 'none';
  }

  // V3.2: 评估提示
  const assBlock = document.getElementById('card-assessment-block');
  const ass = document.getElementById('card-assessment');
  if (node.assessment_prompt) {
    ass.textContent = node.assessment_prompt;
    assBlock.style.display = '';
  } else {
    assBlock.style.display = 'none';
  }

  // sec 标签 — 用 data-i18n attr 配 t() 字符串拼接 (避免 innerHTML 改 span.k)
  const preLabel = document.querySelector('.sec-pre .label');
  const nextLabel = document.querySelector('.sec-next .label');
  // V3.2.2: 严格区分硬先决 (prerequisite + progresses_to) vs 软关联 (relates_to)
  // 卡片"直接先决 / 解锁后继"只显示硬先决; 软关联另外显示
  const allPre = cy.edges().filter(e => e.target().data('id') === node.id);
  const allNext = cy.edges().filter(e => e.source().data('id') === node.id);
  const preEdges = allPre.filter(e => {
    const r = e.data('rel') || 'prerequisite';
    return r !== 'relates_to';
  });
  const nextEdges = allNext.filter(e => {
    const r = e.data('rel') || 'prerequisite';
    return r !== 'relates_to';
  });
  const softPre = allPre.filter(e => (e.data('rel') || 'prerequisite') === 'relates_to');
  const softNext = allNext.filter(e => (e.data('rel') || 'prerequisite') === 'relates_to');
  preLabel.innerHTML = `<span data-i18n="card_prereq">${window.t('card_prereq')}</span> · <span class="k" id="card-pre-k">${preEdges.length}</span>${softPre.length ? ` <span class="soft-hint">(+${softPre.length} 软关联)</span>` : ''}`;
  nextLabel.innerHTML = `<span data-i18n="card_unlocks">${window.t('card_unlocks')}</span> · <span class="k" id="card-next-k">${nextEdges.length}</span>${softNext.length ? ` <span class="soft-hint">(+${softNext.length} 软关联)</span>` : ''}`;

  // V3.2: 边的 reason (人话解释)
  const fillReasons = (container, edges, side) => {
    container.innerHTML = '';
    const withReason = edges.filter(e => e.data('reason'));
    if (!withReason.length) return;
    withReason.slice(0, 3).forEach(e => {
      const other = side === 'pre' ? e.source() : e.target();
      const otherData = other.data();
      const rel = e.data('rel') || 'relates_to';
      const relLabels = { prerequisite: '先决', progresses_to: '进阶', relates_to: '关联' };
      const d = document.createElement('div');
      d.className = 'reason-row';
      d.innerHTML = `<span class="rel-tag rel-${rel}">${relLabels[rel] || rel}</span><span class="reason-txt">${e.data('reason')}</span>`;
      container.appendChild(d);
    });
  };
  fillReasons(document.getElementById('card-pre-reasons'), preEdges, 'pre');
  fillReasons(document.getElementById('card-next-reasons'), nextEdges, 'next');

  const fillRows = (container, edges, side) => {
    container.innerHTML = '';
    if (!edges.length) {
      const d = document.createElement('div');
      d.className = 'empty';
      d.textContent = window.t(side === 'pre' ? 'card_no_prereq' : 'card_no_unlock');
      container.appendChild(d);
      return;
    }
    edges.forEach(e => {
      const other = side === 'pre' ? e.source() : e.target();
      const data = other.data();
      const btn = document.createElement('button');
      btn.className = 'row';
      btn.innerHTML = `<span class="rdot" style="background:${PALETTE[data.subject] || '#888'}"></span><span class="rt">${data.title}</span><span class="ra">G${data.grade_start || ''}</span>`;
      btn.onclick = () => {
        showCard(data);
        cy.elements().unselect();
        other.select();
        cy.animate({ center: { eles: other }, zoom: 2 }, { duration: 600 });
      };
      container.appendChild(btn);
    });
  };
  fillRows(document.getElementById('card-pre-rows'), preEdges, 'pre');
  fillRows(document.getElementById('card-next-rows'), nextEdges, 'next');

  card.classList.add('on');
  card.setAttribute('aria-hidden', 'false');
  cy.elements().unselect();
  const me = cy.getElementById(node.id);
  if (me.length) me.select();
  // 渲染完面板后, 浮动按钮跟着 cy 节点坐标更新位置
  scheduleStartHereButtonUpdate();
}

// V2.3 "从这里学起" — 浮动按钮 + 下游 BFS 路径高亮
// 入口高亮开启后, 在每条黄色"可学起入口"节点上方显示一个小按钮
// 点击后, 从该节点向下 BFS N 层, 用动画高亮学习路径
function isLearnableEntryNode(nodeData) {
  // 客户端再判一次 (cy 实例可能有部分属性)
  if (!nodeData) return false;
  const me = cy && cy.getElementById(nodeData.id);
  if (!me || !me.length) return false;
  return isLearnableEntry(me);
}

let _startHereButtons = [];
function removeStartHereButtons() {
  _startHereButtons.forEach(b => b.remove());
  _startHereButtons = [];
}

function renderStartHereButtons() {
  if (!cy || !window._rootsHighlighted) {
    removeStartHereButtons();
    return;
  }
  removeStartHereButtons();
  const entries = cy.nodes().filter(isLearnableEntry);
  entries.forEach(n => {
    const pos = n.renderedPosition();
    if (!pos) return;
    const btn = document.createElement('button');
    btn.className = 'start-here-btn';
    btn.textContent = window.t('btn_start_here') || '从这里学起 →';
    btn.setAttribute('aria-label', `${window.t('btn_start_here_aria') || '从此概念开始学习'}: ${n.data('title')}`);
    btn.dataset.nodeId = n.id();
    // cy 节点 renderedPosition 是 canvas 像素, 直接定位 fixed
    const contRect = cyContainer.getBoundingClientRect();
    btn.style.left = (contRect.left + pos.x) + 'px';
    btn.style.top = (contRect.top + pos.y) + 'px';
    btn.onclick = (e) => {
      e.stopPropagation();
      // 高亮下游路径
      const me = cy.getElementById(n.id());
      if (me.length) {
        showCard(me.data());  // 打开详情面板
        // 立即高亮下游 3 层
        highlightDownstream(me, 3);
        // 标记按钮已点击
        _startHereButtons.forEach(b => b.classList.remove('started'));
        btn.classList.add('started');
        btn.textContent = window.t('btn_started') || '已展开 ✓';
      }
    };
    document.body.appendChild(btn);
    _startHereButtons.push(btn);
  });
}

// 浮动按钮随 cy 缩放/平移同步
let _startHereScheduled = false;
function scheduleStartHereButtonUpdate() {
  if (_startHereScheduled) return;
  _startHereScheduled = true;
  requestAnimationFrame(() => {
    _startHereScheduled = false;
    if (!cy) return;
    // 重新计算所有浮动按钮位置
    const contRect = cyContainer.getBoundingClientRect();
    _startHereButtons.forEach(btn => {
      const id = btn.dataset.nodeId;
      const n = cy.getElementById(id);
      if (!n.length) { btn.remove(); return; }
      const pos = n.renderedPosition();
      btn.style.left = (contRect.left + pos.x) + 'px';
      btn.style.top = (contRect.top + pos.y) + 'px';
    });
  });
}

// cy 视图变化时同步浮动按钮
function setupCyViewSync() {
  if (!cy) return;
  cy.on('pan zoom viewport', scheduleStartHereButtonUpdate);
}

// V2.3 下游 BFS 路径高亮 — 从起点向下展开 N 层, 高亮节点 + 边
// 沿用现有 .path-node / .path-edge CSS class
function highlightDownstream(startNode, depth) {
  if (!cy || !startNode || !startNode.length) return;
  // 清旧
  cy.elements().removeClass('path-node path-edge');
  const visited = new Set([startNode.id()]);
  const pathEdges = new Set();
  let frontier = [startNode];
  for (let d = 0; d < depth; d++) {
    const nextFrontier = [];
    frontier.forEach(n => {
      const out = n.outgoers('edge');
      out.forEach(e => {
        const t = e.target();
        if (!visited.has(t.id())) {
          visited.add(t.id());
          nextFrontier.push(t);
          pathEdges.add(e.id());
        }
      });
    });
    if (nextFrontier.length === 0) break;
    frontier = nextFrontier;
  }
  // 应用高亮 class
  cy.nodes().forEach(n => {
    if (visited.has(n.id())) n.addClass('path-node');
  });
  pathEdges.forEach(eid => {
    const e = cy.getElementById(eid);
    if (e.length) e.addClass('path-edge');
  });
  // 平滑飞到该子图
  const allHighlighted = cy.nodes().filter('.path-node').union(cy.edges().filter('.path-edge'));
  if (allHighlighted.length > 1) {
    cy.animate({ fit: { eles: allHighlighted, padding: 100 }, duration: 700 });
  }
  return visited.size - 1;  // 返回展开节点数 (不含起点)
}

// 详情面板里的"查看下游 3 层"按钮 + ARIA 状态同步
function setupCardActions() {
  const btn = document.getElementById('card-btn-path');
  if (!btn) return;
  btn.onclick = () => {
    if (!window._currentNode) return;
    const me = cy.getElementById(window._currentNode.id);
    if (!me.length) return;
    const count = highlightDownstream(me, 3);
    btn.textContent = `${window.t('btn_expanded') || '已展开'} ${count} ${window.t('btn_concepts') || '个概念'} (按 Esc 清除)`;
  };
}

document.querySelector('#card .close').onclick = () => closeCard();

// 关闭详情面板 — 统一入口 (Esc 也会调用)
function closeCard() {
  const card = document.getElementById('card');
  card.classList.remove('on');
  card.setAttribute('aria-hidden', 'true');
  if (cy) {
    cy.elements().unselect();
    cy.elements().removeClass('neighbor-highlight neighbor-dim path-node path-edge');
  }
  window._currentNode = null;
  removeStartHereButtons();
}

// V2.3 键盘快捷键 — 在搜索框聚焦时不抢键
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // 模态打开时, Esc 关 modal 而不是面板
    const modal = document.getElementById('kbdModal');
    if (modal && modal.classList.contains('on')) {
      if (e.key === 'Escape' || e.key === '?') {
        e.preventDefault();
        closeKbdModal();
      }
      return;
    }
    // 输入框/textarea/contenteditable 元素内不抢键
    const tag = (e.target.tagName || '').toUpperCase();
    if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) return;
    // 修饰键组合让给浏览器
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    const k = e.key;
    if (k === '/') {
      e.preventDefault();
      document.getElementById('searchInput').focus();
      document.getElementById('searchInput').select();
      return;
    }
    if (k === '?') {
      e.preventDefault();
      openKbdModal();
      return;
    }
    if (k === 'Escape') {
      e.preventDefault();
      // 优先关详情面板; 否则清搜索
      const card = document.getElementById('card');
      if (card.classList.contains('on')) {
        closeCard();
      } else {
        const input = document.getElementById('searchInput');
        if (input.value) {
          input.value = '';
          document.getElementById('searchResults').classList.remove('on');
          if (cy) cy.elements().removeClass('search-hit');
        }
      }
      return;
    }
    if (k === 'l' || k === 'L') {
      e.preventDefault();
      document.getElementById('toggleLabels').click();
      return;
    }
    if (k === 'r') {
      e.preventDefault();
      document.getElementById('toggleRoots').click();
      return;
    }
    if (k === 'R') {
      e.preventDefault();
      document.getElementById('reLayout').click();
      return;
    }
    if (k === '0') {
      e.preventDefault();
      // 全部学科显隐切换
      const chips = document.querySelectorAll('.chip');
      const allOn = Array.from(chips).every(c => !c.classList.contains('off'));
      chips.forEach(c => {
        c.classList.toggle('off', allOn);
        c.setAttribute('aria-pressed', allOn ? 'false' : 'true');
      });
      updateFilter();
      return;
    }
    if (/^[1-9]$/.test(k)) {
      e.preventDefault();
      const idx = parseInt(k, 10) - 1;
      const chip = document.querySelector(`.chip[data-idx="${idx}"]`);
      if (chip) chip.click();
      return;
    }
  });
}

// V2.3 键盘快捷键 modal
function setupKbdModal() {
  const modal = document.getElementById('kbdModal');
  const closeBtn = document.getElementById('kbdModalClose');
  const showBtn = document.getElementById('showKbd');
  if (showBtn) showBtn.onclick = openKbdModal;
  if (closeBtn) closeBtn.onclick = closeKbdModal;
  // 点 modal 背景关闭
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeKbdModal();
    });
  }
}
function openKbdModal() {
  const modal = document.getElementById('kbdModal');
  if (modal) {
    modal.classList.add('on');
    modal.setAttribute('aria-hidden', 'false');
    setTimeout(() => document.getElementById('kbdModalClose').focus(), 50);
  }
}
function closeKbdModal() {
  const modal = document.getElementById('kbdModal');
  if (modal) {
    modal.classList.remove('on');
    modal.setAttribute('aria-hidden', 'true');
  }
}

// 切换 label 显示
document.getElementById('toggleLabels').onclick = () => {
  window._labelsOn = !window._labelsOn;
  cy.nodes().forEach(n => {
    n.style('label', window._labelsOn ? n.data('title') : '');
  });
  document.getElementById('toggleLabels').textContent = window.t(window._labelsOn ? 'btn_labels_hide' : 'btn_labels');
  document.getElementById('toggleLabels').setAttribute('aria-pressed', String(!!window._labelsOn));
};

// 重排 — 按学科分块
function relayout() {
  const W = cy.width();
  const H = cy.height();
  const padding = 60;
  const subjStats = GROUPS.map(s => ({
    s,
    n: cy.nodes().filter(x => x.data('subject') === s).length,
  }));
  subjStats.sort((a, b) => b.n - a.n);
  const COLS = 4;
  const usableW = W - padding * 2;
  const usableH = H - padding * 2;
  const cellW = usableW / COLS;
  const rows = Math.ceil(subjStats.length / COLS);
  const cellH = usableH / rows;
  const pos = {};
  subjStats.forEach((s, idx) => {
    const col = idx % COLS;
    const row = Math.floor(idx / COLS);
    const cx = padding + cellW * (col + 0.5);
    const cy_ = padding + cellH * (row + 0.5);
    const ownNodes = cy.nodes().filter(n => n.data('subject') === s.s);
    const cols2 = Math.ceil(Math.sqrt(s.n * (cellW / cellH)));
    ownNodes.forEach((n, i) => {
      const c = i % cols2;
      const r = Math.floor(i / cols2);
      const rows2 = Math.ceil(s.n / cols2);
      const subW = cellW * 0.85;
      const subH = cellH * 0.85;
      pos[n.id()] = {
        x: cx - subW / 2 + (c + 0.5) * subW / cols2 + (Math.random() - 0.5) * 4,
        y: cy_ - subH / 2 + (r + 0.5) * subH / rows2 + (Math.random() - 0.5) * 4,
      };
    });
  });
  cy.layout({ name: 'preset', positions: pos, fit: true, padding: padding }).run();
}
document.getElementById('reLayout').onclick = relayout;

// 切换根节点高亮
document.getElementById('toggleRoots').onclick = toggleRootsHighlight;

// ============================================================
// 概念地图模式 — 左侧树状导航 (学科→学段→领域→概念)
// ============================================================

/** 学科 stage → 4 学段名 (按 grade_start) */
function stageName(g) {
  if (g <= 2) return [1, 2];    // 1-2 年级
  if (g <= 4) return [3, 4];    // 3-4 年级
  if (g <= 6) return [5, 6];    // 5-6 年级
  return [7, 8, 9];             // 7-9 年级
}

/** 构建学科→学段→领域→概念 的树状结构 */
function buildTreeData() {
  // 学科顺序按 14 学科固定顺序
  const SUBJ_ORDER = ['math','chinese','english','physics','chemistry','biology',
    'history','geography','morality_law','science','info_tech','art','pe_health','labor'];
  const tree = {};
  for (const subj of SUBJ_ORDER) {
    tree[subj] = { code: subj, name: window.tSubject(subj), stages: {} };
  }
  for (const n of DATA.nodes) {
    const subj = n.subject;
    if (!tree[subj]) continue;
    const g = n.grade_start || 1;
    const stgKey = stageName(g).join('-');
    if (!tree[subj].stages[stgKey]) {
      tree[subj].stages[stgKey] = { key: stgKey, grades: stageName(g), domains: {} };
    }
    const dom = n.domain || '其他';
    if (!tree[subj].stages[stgKey].domains[dom]) {
      tree[subj].stages[stgKey].domains[dom] = { name: dom, concepts: [] };
    }
    tree[subj].stages[stgKey].domains[dom].concepts.push(n);
  }
  return tree;
}

/** 渲染树到 #map-tree */
function renderMapTree(expandAll = false) {
  const tree = buildTreeData();
  const container = document.getElementById('map-tree');
  container.innerHTML = '';
  const html = [];
  for (const subj of Object.keys(tree)) {
    const st = tree[subj];
    const subjCount = Object.values(st.stages).reduce((a, s) =>
      a + Object.values(s.domains).reduce((a2, d) => a2 + d.concepts.length, 0), 0);
    const subjId = 'subj-' + subj;
    html.push(rowHtml(subjId, st.name, subj, subjCount, 's', expandAll, true));
    html.push(`<div class="tn-children ${expandAll ? 'open' : ''}" data-parent="${subjId}">`);
    for (const stgKey of Object.keys(st.stages)) {
      const s = st.stages[stgKey];
      const stgId = `${subjId}-stg-${stgKey}`;
      const stgCount = Object.values(s.domains).reduce((a, d) => a + d.concepts.length, 0);
      const stgLabel = window.t('map_subtitle').includes('Subject') ? `G${s.grades.join('–')}` : `${s.grades.join('-')}年级`;
      html.push(rowHtml(stgId, stgLabel, subj, stgCount, 'stg', expandAll));
      html.push(`<div class="tn-children ${expandAll ? 'open' : ''}" data-parent="${stgId}">`);
      for (const domName of Object.keys(s.domains)) {
        const d = s.domains[domName];
        const domId = `${stgId}-d-${cssId(domName)}`;
        html.push(rowHtml(domId, domName, subj, d.concepts.length, 'd', expandAll));
        html.push(`<div class="tn-children ${expandAll ? 'open' : ''}" data-parent="${domId}">`);
        for (const c of d.concepts) {
          const cId = `c-${c.id}`;
          const selectedCls = (mapSelectedNode === c.id) ? ' selected' : '';
          html.push(`<div class="tn-row c${selectedCls}" data-id="${c.id}" data-subject="${subj}" tabindex="0" role="treeitem">
            <span class="tn-toggle leaf"></span>
            <span class="tn-dot" style="background:${PALETTE[subj] || '#888'}"></span>
            <span class="tn-label" title="${escapeHtml(c.title)}">${escapeHtml(c.title)}</span>
          </div>`);
        }
        html.push(`</div>`);
      }
      html.push(`</div>`);
    }
    html.push(`</div>`);
  }
  container.innerHTML = html.join('');
  bindMapTreeEvents();
}

function cssId(s) { return String(s).replace(/[^a-zA-Z0-9_-]/g, '_'); }

function rowHtml(id, label, subj, count, cls, expandAll, isSubj = false) {
  return `<div class="tn-row ${cls}" data-toggle="${id}" tabindex="0" role="treeitem" aria-expanded="${expandAll}">
    <span class="tn-toggle">${isSubj ? (expandAll ? '▾' : '▸') : (expandAll ? '▾' : '▸')}</span>
    ${isSubj ? `<span class="tn-dot" style="background:${PALETTE[subj] || '#888'}"></span>` : ''}
    <span class="tn-label">${escapeHtml(label)}</span>
    <span class="tn-count">${count}</span>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function bindMapTreeEvents() {
  // 折叠/展开
  document.querySelectorAll('#map-tree .tn-row[data-toggle]').forEach(r => {
    r.addEventListener('click', e => {
      const id = r.dataset.toggle;
      const children = document.querySelector(`#map-tree .tn-children[data-parent="${id}"]`);
      if (!children) return;
      const isOpen = children.classList.toggle('open');
      const tg = r.querySelector('.tn-toggle');
      if (tg) tg.textContent = isOpen ? '▾' : '▸';
      r.setAttribute('aria-expanded', isOpen);
    });
  });
  // 概念点击 → 飞图 + 高亮
  document.querySelectorAll('#map-tree .tn-row.c').forEach(r => {
    r.addEventListener('click', e => {
      e.stopPropagation();
      const id = r.dataset.id;
      selectMapNode(id);
    });
    r.addEventListener('dblclick', e => {
      e.stopPropagation();
      const id = r.dataset.id;
      const ele = cy.getElementById(id);
      if (ele.length) flyTo(ele, 600);
    });
  });
}

function selectMapNode(id) {
  mapSelectedNode = id;
  // 更新树的 selected 样式
  document.querySelectorAll('#map-tree .tn-row.c').forEach(r => {
    r.classList.toggle('selected', r.dataset.id === id);
  });
  // 滚到视口
  const row = document.querySelector(`#map-tree .tn-row.c[data-id="${id}"]`);
  if (row) row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  // 高亮图上节点
  highlightOnMap(id);
  // 更新状态栏
  const node = DATA.nodes.find(n => n.id === id);
  if (node) {
    document.getElementById('map-status').innerHTML =
      `<b style="color:${PALETTE[node.subject] || '#fff'}">${escapeHtml(node.title)}</b> · ${window.t('map_focus')}`;
  }
}

function flyTo(ele, duration = 400) {
  if (!ele.length) return;
  const pos = ele.position();
  cy.animate({
    center: { x: pos.x, y: pos.y },
    zoom: Math.max(cy.zoom(), 1.2),
  }, { duration });
}

function highlightOnMap(id) {
  if (!cy) return;
  // 计算该节点在 (主题/学段/领域) 分支的所有节点 id
  const branch = computeBranch(id);
  // 重置样式
  cy.nodes().removeClass('branch-dim branch-hl');
  cy.edges().removeClass('branch-dim branch-hl');
  if (mapBranchOnly) {
    cy.nodes().not(branch).addClass('branch-dim');
    cy.edges().forEach(e => {
      const inBranch = branch.has(e.data('from')) && branch.has(e.data('to'));
      if (!inBranch) e.addClass('branch-dim');
    });
  }
  // 高亮选中节点 + 直接先决/后继
  const ele = cy.getElementById(id);
  if (ele.length) {
    ele.addClass('branch-hl');
    if (!mapBranchOnly) {
      ele.connectedEdges().addClass('branch-hl');
    }
  }
}

function computeBranch(id) {
  // 主题/学段/领域 同分支 = 同 subject + 同 stageKey + 同 domain
  const target = DATA.nodes.find(n => n.id === id);
  if (!target) return new Set([id]);
  const stgKey = stageName(target.grade_start || 1).join('-');
  const branch = new Set();
  for (const n of DATA.nodes) {
    if (n.subject === target.subject &&
        stageName(n.grade_start || 1).join('-') === stgKey &&
        n.domain === target.domain) {
      branch.add(n.id);
    }
  }
  return branch;
}

/** 进入/退出 概念地图模式 */
function toggleMapMode() {
  mapMode = !mapMode;
  document.body.classList.toggle('map-mode', mapMode);
  const btn = document.getElementById('toggleMode');
  if (mapMode) {
    btn.textContent = window.t('btn_mode_force');
    btn.setAttribute('aria-pressed', 'true');
    btn.setAttribute('data-i18n', 'btn_mode_force');
    // 重新调整 cy 容器大小
    setTimeout(() => { if (cy) cy.resize(); }, 50);
    renderMapTree(false);
  } else {
    btn.textContent = window.t('btn_mode_map');
    btn.setAttribute('aria-pressed', 'false');
    btn.setAttribute('data-i18n', 'btn_mode_map');
    // 清除高亮
    if (cy) {
      cy.nodes().removeClass('branch-dim branch-hl');
      cy.edges().removeClass('branch-dim branch-hl');
      setTimeout(() => cy.resize(), 50);
    }
  }
}

document.getElementById('toggleMode').onclick = toggleMapMode;
document.getElementById('mapExpandAll').onclick = () => renderMapTree(true);
document.getElementById('mapCollapseAll').onclick = () => renderMapTree(false);
document.getElementById('mapBranchOnly').onclick = function() {
  mapBranchOnly = !mapBranchOnly;
  this.setAttribute('aria-pressed', mapBranchOnly);
  this.textContent = window.t(mapBranchOnly ? 'map_branch_only' : 'map_show_all');
  this.setAttribute('data-i18n', mapBranchOnly ? 'map_branch_only' : 'map_show_all');
  if (mapSelectedNode) highlightOnMap(mapSelectedNode);
};

// 暴露关键函数到 window, 供 i18n.js applyI18n 调用
// (i18n.js 是非模块 script, 看不到 module 内的 buildLegend/showCard)
window.buildLegend = buildLegend;
window.showCard = showCard;
window.flyToSubject = flyToSubject;
window.toggleMapMode = toggleMapMode;
window.renderMapTree = renderMapTree;

loadData();
