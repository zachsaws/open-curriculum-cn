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
  const elements = [
    ...DATA.nodes.map(n => ({
      group: 'nodes',
      data: { ...n },
    })),
    ...DATA.edges.map((e, i) => ({
      group: 'edges',
      data: { id: 'e' + i, source: e[0], target: e[1], type: e[2] || 'hard' },
    })),
  ];

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
          'width': 20,
          'height': 20,
          'label': 'data(title)',
          'color': '#e6e9f2',
          'font-size': '12px',
          'font-family': '-apple-system, "PingFang SC", sans-serif',
          'text-valign': 'bottom',
          'text-margin-y': 6,
          'text-outline-color': '#0a0d18',
          'text-outline-width': 3,
          'opacity': 1,
        },
      },
      {
        selector: 'edge',
        style: {
          'width': 0.6,
          'line-color': 'rgba(180,195,235,0.35)',
          'curve-style': 'bezier',
          'opacity': 0.6,
        },
      },
      {
        selector: 'node:selected',
        style: {
          'border-color': '#fff',
          'border-width': 2,
          'border-opacity': 1,
        },
      },
    ],
    layout: {
      name: 'cose',
      animate: false,
      // 拉开节点
      nodeRepulsion: 80000,
      idealEdgeLength: 100,
      edgeElasticity: 0.45,
      gravity: 0.25,
      numIter: 100,
      fit: true,
      padding: 50,
    },
    wheelSensitivity: 0.2,
    minZoom: 0.3,
    maxZoom: 5,
  });

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
  document.getElementById('card-cs').textContent = `${SUBJECT_CN[node.subject] || node.subject} · ${node.stage || ''} · G${node.grade_start || ''}`;
  document.getElementById('card-ctl').textContent = node.title;
  document.getElementById('card-cq').textContent = node.example || node.description || '';

  // 计算 prerequisites & unlocks
  const preEdges = cy.edges().filter(e => e.target().data('id') === node.id);
  const nextEdges = cy.edges().filter(e => e.source().data('id') === node.id);
  document.getElementById('card-count').textContent = preEdges.length;
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

loadData();
