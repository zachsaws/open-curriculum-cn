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

const SUBJECT_CN = {
  math: '数学', chinese: '语文', english: '英语', science: '科学',
  physics: '物理', chemistry: '化学', biology: '生物', history: '历史',
  geography: '地理', morality_law: '道法', info_tech: '信息科技',
  art: '艺术', pe_health: '体育', labor: '劳动', integrated: '综合实践',
};

let DATA = null;
let GROUPS = [];
let GCOL = [];
let cy;
let activeGroups = new Set();

async function loadData() {
  loadingMsg.textContent = '加载知识图谱...';
  try {
    const res = await fetch('./data/graph.json');
    if (!res.ok) throw new Error('graph.json 不存在');
    DATA = await res.json();
    console.log('Loaded', DATA.nodes.length, 'nodes,', DATA.edges.length, 'edges');
  } catch (e) {
    console.error(e);
    loadingMsg.innerHTML = `<div class="err">未找到图谱数据 (graph.json)<br><br>数据仍在采集中</div>`;
    return;
  }

  GROUPS = [...new Set(DATA.nodes.map(n => n.subject))].sort();
  GCOL = GROUPS.map(s => PALETTE[s] || '#888');
  activeGroups = new Set(GROUPS);

  document.getElementById('nCount').textContent = DATA.nodes.length.toLocaleString();
  document.getElementById('eCount').textContent = DATA.edges.length.toLocaleString();
  document.getElementById('gCount').textContent = GROUPS.length;

  buildLegend();
  initGraph();
  loading.classList.add('done');
}

function buildLegend() {
  const legend = document.getElementById('legend');
  legend.innerHTML = '';
  const counts = GROUPS.map(s => DATA.nodes.filter(n => n.subject === s).length);
  GROUPS.forEach((s, i) => {
    const el = document.createElement('div');
    el.className = 'chip';
    el.dataset.subject = s;
    el.innerHTML = `<span class="sw" style="background:${GCOL[i]}"></span><span class="nm">${SUBJECT_CN[s] || s}</span><span class="ct">${counts[i]}</span>`;
    el.onclick = () => {
      el.classList.toggle('off');
      updateFilter();
    };
    legend.appendChild(el);
  });
}

function updateFilter() {
  const chips = document.querySelectorAll('.chip');
  const newActive = new Set();
  chips.forEach(chip => {
    if (!chip.classList.contains('off')) newActive.add(chip.dataset.subject);
  });
  activeGroups = newActive;
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
    ...DATA.edges.map((e, i) => ({
      group: 'edges',
      data: {
        id: 'e' + i,
        source: Array.isArray(e) ? e[0] : e.from,
        target: Array.isArray(e) ? e[1] : e.to,
        type: Array.isArray(e) ? (e[2] || 'hard') : (e.type === 0 ? 'soft' : 'hard'),
      },
    })),
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
  });
  cy.on('tap', evt => {
    if (evt.target === cy) {
      document.getElementById('card').classList.remove('on');
    }
  });

  // 自动 fit
  setTimeout(() => {
    cy.fit(undefined, 50);
  }, 200);

  console.log('initGraph done, nodes:', cy.nodes().length);
  window.cy = cy;  // 调试用
}

function showCard(node) {
  const card = document.getElementById('card');
  document.getElementById('card-sw').style.background = PALETTE[node.subject] || '#888';
  document.getElementById('card-cs').textContent = `${SUBJECT_CN[node.subject] || node.subject} · G${node.grade_start || ''}-${node.grade_end || ''} · ${node.domain || ''}`;
  document.getElementById('card-ctl').textContent = node.title;

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
    t.textContent = '难度 ' + '●'.repeat(node.difficulty) + '○'.repeat(5 - node.difficulty);
    tagRow.appendChild(t);
  }
  // estimated minutes
  if (node.estimated_minutes) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = '⏱ ' + node.estimated_minutes + ' 分钟';
    tagRow.appendChild(t);
  }
  // subdomain
  if (node.subdomain) {
    const t = document.createElement('span');
    t.className = 'tag min';
    t.textContent = node.subdomain;
    tagRow.appendChild(t);
  }

  // 内容要求
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
    pageLink.innerHTML = ` · <a class="src-link" href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">P${node.src_page} 课标原文 ↗</a>`;
  } else {
    pageLink.textContent = '';
  }

  // 学业要求
  const ar = document.getElementById('card-academic-req');
  const arBlock = document.getElementById('card-academic-req-block');
  if (node.academic_req) {
    ar.textContent = node.academic_req;
    arBlock.style.display = '';
  } else {
    arBlock.style.display = 'none';
  }

  // 知识要点
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

  // 例题
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

  // 计算 prerequisites & unlocks
  const preEdges = cy.edges().filter(e => e.target().data('id') === node.id);
  const nextEdges = cy.edges().filter(e => e.source().data('id') === node.id);
  document.getElementById('card-pre-k').textContent = preEdges.length;
  document.getElementById('card-next-k').textContent = nextEdges.length;

  const fillRows = (container, edges, side) => {
    container.innerHTML = '';
    if (!edges.length) {
      const d = document.createElement('div');
      d.className = 'empty';
      d.textContent = side === 'pre' ? '没有先决概念' : '没有后继概念';
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
  cy.elements().unselect();
  const me = cy.getElementById(node.id);
  if (me.length) me.select();
}

document.querySelector('#card .close').onclick = () => {
  document.getElementById('card').classList.remove('on');
  cy.elements().unselect();
};

// 切换 label 显示
let labelsOn = false;
document.getElementById('toggleLabels').onclick = () => {
  labelsOn = !labelsOn;
  cy.nodes().forEach(n => {
    n.style('label', labelsOn ? n.data('title') : '');
  });
  document.getElementById('toggleLabels').textContent = labelsOn ? '隐藏标签' : '显示标签';
};

// 重排 — 按学科分块
document.getElementById('reLayout').onclick = () => {
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
};

loadData();
