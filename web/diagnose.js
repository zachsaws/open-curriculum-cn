// V4.0.2 智能诊断 PoC — 客户端版本 (GitHub Pages 静态部署)
// 算法跟 api/diagnose.py 保持一致, 避免 doc/API drift
'use strict';

// 难度 1-5 → 薄弱/巩固阈值
const DIFFICULTY_THRESHOLDS = {
  1: { weak: 80, consolidate: 95 },
  2: { weak: 80, consolidate: 95 },
  3: { weak: 70, consolidate: 90 },
  4: { weak: 60, consolidate: 80 },
  5: { weak: 50, consolidate: 70 },
};

const PALETTE = {
  math: '#5b8def', chinese: '#ef6b5b', english: '#7bc96f',
  science: '#f9a825', physics: '#ba68c8', chemistry: '#26a69a',
  biology: '#66bb6a', history: '#8d6e63', geography: '#42a5f5',
  morality_law: '#ec407a', info_tech: '#26c6da', art: '#ab47bc',
  pe_health: '#ff7043', labor: '#9ccc65', integrated: '#78909c',
};

const SUBJECT_CN = {
  math: '数学', chinese: '语文', english: '英语', physics: '物理',
  chemistry: '化学', biology: '生物', history: '历史', geography: '地理',
  morality_law: '道德与法治', science: '科学', info_tech: '信息科技',
  art: '艺术', pe_health: '体育与健康', labor: '劳动',
  integrated: '综合实践',
};

const TYPE_LABEL = { multiple_choice: '选择题', fill_blank: '填空题', short_answer: '简答题' };
const TYPE_CLASS = { multiple_choice: 'choice', fill_blank: 'fill', short_answer: 'short' };

// V4.0.3 全 14 学科 quick pick (math 6 + 其他 13 学科各 1 个 highest-centrality 节点)
const QUICK_PICKS = [
  { id: 'M_G4_NS_16', reason: 'math' },
  { id: 'M_G4_GM_08', reason: 'math' },
  { id: 'M_G4_QR_05', reason: 'math' },
  { id: 'M_G4_QR_11', reason: 'math' },
  { id: 'M_G4_GM_10', reason: 'math' },
  { id: 'M_G3_GM_04', reason: 'math' },
  { id: 'CN_G56_WR_04', reason: 'chinese' },
  { id: 'EN_E4_GR_03', reason: 'english' },
  { id: 'P_P2_17', reason: 'physics' },
  { id: 'CH_C1_04', reason: 'chemistry' },
  { id: 'B_B1_03', reason: 'biology' },
  { id: 'H_H2_CM_01', reason: 'history' },
  { id: 'G_G1_05', reason: 'geography' },
  { id: 'ML_ML_G9_01', reason: 'morality_law' },
  { id: 'SC_S2_MS_05', reason: 'science' },
  { id: 'IT_I3_03', reason: 'info_tech' },
  { id: 'ART_A2_07', reason: 'art' },
  { id: 'PE_PE3_04', reason: 'pe_health' },
  { id: 'L_L1_01', reason: 'labor' },
];

// 全局状态
let GRAPH = null;
let EXERCISES = [];
let EXERCISES_BY_CONCEPT = {};
let REC_DATA = null;  // V4.0.4 推荐数据 (从 recommendations.json 加载)
let MODE = 'test';  // 'test' = 5 道题测试 / 'quick' = 手输答对率
let CURRENT_STEP = 1;
let SELECTED_CONCEPT = null;
let USER_ANSWERS = {};  // {exId: userValue}
let QUICK_SCORE = 60;   // slider 默认 60

// V4.1 多学科模式 (test.html 跳过来)
let MULTI_MODE = null;  // { subjects: [], stage, grade, count }

// 学科 ID 前缀 → 学科 key (从 concept_id 推)
function subjFromConceptId(cid) {
  if (!cid) return null;
  const m = cid.match(/^([A-Z]+)_/);
  if (!m) return null;
  const prefix = m[1];
  const map = {
    'M': 'math', 'CN': 'chinese', 'EN': 'english',
    'P': 'physics', 'CH': 'chemistry', 'B': 'biology',
    'H': 'history', 'G': 'geography', 'ML': 'morality_law',
    'SC': 'science', 'IT': 'info_tech', 'ART': 'art',
    'PE': 'pe_health', 'L': 'labor'
  };
  return map[prefix] || null;
}

// 年级 (M_G4_GM_08 → 4)
function gradeFromConceptId(cid) {
  if (!cid) return null;
  const m = cid.match(/^M?_?G(\d+)_/);
  return m ? parseInt(m[1], 10) : null;
}

// --- 工具 ---
function esc(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}
function getQueryParam(name) {
  const m = window.location.search.match(new RegExp('[?&]' + name + '=([^&]*)'));
  return m ? decodeURIComponent(m[1]) : null;
}
function getConceptById(id) {
  return GRAPH.nodes.find(n => n.id === id);
}

// --- 数据加载 ---
async function loadData() {
  try {
    // V4.0.4: 并行加载 3 份数据 (graph + exercises + recommendations)
    const [gRes, eRes, rRes] = await Promise.all([
      fetch('./data/graph.json'),
      fetch('./data/exercises.json'),
      fetch('./data/recommendations.json').catch(() => null),  // 推荐数据非关键, 失败 fallback
    ]);
    if (!gRes.ok) throw new Error(`graph.json ${gRes.status}`);
    if (!eRes.ok) throw new Error(`exercises.json ${eRes.status}`);
    GRAPH = await gRes.json();
    const eData = await eRes.json();
    EXERCISES = eData.exercises || [];
    // 按 concept_id 索引
    EXERCISES.forEach(e => {
      if (!EXERCISES_BY_CONCEPT[e.concept_id]) EXERCISES_BY_CONCEPT[e.concept_id] = [];
      EXERCISES_BY_CONCEPT[e.concept_id].push(e);
    });
    if (rRes && rRes.ok) {
      REC_DATA = await rRes.json();
    }
    render();
  } catch (e) {
    document.getElementById('content').innerHTML =
      `<div class="err">数据加载失败: ${esc(e.message)}<br>请检查网络 (GitHub Pages 静态站)</div>`;
  }
}

// --- 核心算法: 跟 api/diagnose.py 保持一致 ---
function bfsPrereqsWithDepth(conceptId, adjTo) {
  const visited = {};
  const queue = [{ id: conceptId, dist: 0 }];
  while (queue.length > 0) {
    const { id: cur, dist } = queue.shift();
    const pres = adjTo[cur] || [];
    for (const pre of pres) {
      if (!(pre in visited) && pre !== conceptId) {
        visited[pre] = dist + 1;
        queue.push({ id: pre, dist: dist + 1 });
      }
    }
  }
  return visited;
}

function buildAdjTo() {
  const adj = {};
  for (const e of GRAPH.edges) {
    const rel = e.rel || (e.type === 1 ? 'prerequisite' : 'relates_to');
    if (rel === 'prerequisite' || rel === 'progresses_to') {
      if (!adj[e.to]) adj[e.to] = [];
      adj[e.to].push(e.from);
    }
  }
  return adj;
}

function diagnose(conceptId, answers, score) {
  const concept = getConceptById(conceptId);
  if (!concept) return { error: `概念不存在: ${conceptId}` };

  // 1. 算 score
  if (answers) {
    if (answers.length !== 5) return { error: `answers 必须 5 道, 实际 ${answers.length} 道` };
    score = answers.filter(a => a).length / 5.0;
  } else if (score == null) {
    return { error: '必须传 score 或 answers' };
  }
  const scorePct = Math.round(score * 100);

  // 2. 算 status
  const d = concept.difficulty || 3;
  const th = DIFFICULTY_THRESHOLDS[d] || DIFFICULTY_THRESHOLDS[3];
  let status;
  if (scorePct < th.weak) status = '薄弱';
  else if (scorePct < th.consolidate) status = '巩固';
  else status = '已掌握';

  // 3. BFS 找先决链
  const adjTo = buildAdjTo();
  const prereqDist = bfsPrereqsWithDepth(conceptId, adjTo);
  const prereqNodes = Object.entries(prereqDist).map(([id, dist]) => {
    const n = getConceptById(id);
    return n ? {
      id, title: n.title, distance: dist,
      difficulty: n.difficulty, subject: n.subject,
    } : null;
  }).filter(Boolean);

  // 4. 复习路径: 距离近 + 难度低优先
  const recommendPath = prereqNodes
    .sort((a, b) => (a.distance - b.distance) || ((a.difficulty || 3) - (b.difficulty || 3)))
    .slice(0, 8);

  // 5. 人话解释
  const title = concept.title || '';
  const subjectCn = SUBJECT_CN[concept.subject] || concept.subject;
  const gradeRange = `${concept.grade_start || ''}-${concept.grade_end || ''}年级`;

  return {
    concept_id: conceptId,
    concept_title: title,
    subject: concept.subject,
    subject_cn: subjectCn,
    difficulty: d,
    grade_range: gradeRange,
    score, score_pct: scorePct,
    status, weak_threshold: th.weak, consolidate_threshold: th.consolidate,
    weak_concepts: prereqNodes.slice(0, 10),
    recommend_path: recommendPath,
    human_explanation: buildHumanExplanation(status, scorePct, title, subjectCn, gradeRange, d, recommendPath, concept),
  };
}

function buildHumanExplanation(status, scorePct, title, subjectCn, gradeRange, d, recommendPath, concept) {
  let summary = '', why = '';
  const actions = [];

  if (status === '薄弱') {
    summary = `「${title}」对你来说还有点早，${scorePct}% 的答对率说明基础没打牢。`;
    why = `${title}是${subjectCn}${gradeRange}的${d <= 3 ? '核心' : '拔高'}考点，通常需要先掌握 ${recommendPath.length} 个前置概念。`;
    const direct = recommendPath.filter(r => r.distance === 1).slice(0, 3);
    if (direct.length) {
      actions.push({
        type: 'review',
        icon: '📚',
        text: `先回看这 ${direct.length} 个直接基础: ${direct.map(r => r.title).join('、')}`,
      });
    }
    actions.push({ type: 'concept', icon: '🔍', text: `看「${title}」概念卡 + 先决复习` });
    actions.push({ type: 'exercise', icon: '✏️', text: `重新做 5 道「${title}」练习题 (客观题自动判分)` });
  } else if (status === '巩固') {
    summary = `「${title}」你掌握了一部分（${scorePct}%），再练练就能稳。`;
    why = `${title}是${subjectCn}${gradeRange}的重要概念，你已经有基础但细节和综合应用还差点意思。`;
    actions.push({ type: 'exercise', icon: '✏️', text: `再做 5 道「${title}」综合题 (T4/T5 应用+压轴)` });
    actions.push({ type: 'review', icon: '🎯', text: '重点看错题解析, 标记易错点' });
  } else {
    summary = `「${title}」你掌握得不错（${scorePct}%），可以放心往后走。`;
    why = `${title}这层你已经稳了，可以去看它后面解锁的概念，或者挑战更高难度的真题。`;
    actions.push({ type: 'next', icon: '🚀', text: `查看「${title}」解锁的后续概念` });
    actions.push({ type: 'challenge', icon: '📋', text: `挑战 5 道「${title}」真题 (is_real_exam=true)` });
  }
  const emoji = { 薄弱: '😟', 巩固: '🙂', 已掌握: '🎉' }[status] || '🤔';
  return { summary, why, actions, status_emoji: emoji };
}

// --- 渲染 ---
function setStep(n) {
  CURRENT_STEP = n;
  for (let i = 1; i <= 3; i++) {
    const el = document.getElementById(`prog-${i}`);
    el.classList.remove('active', 'done');
    if (i < n) el.classList.add('done');
    else if (i === n) el.classList.add('active');
  }
}

function render() {
  // V4.1 多学科模式 (test.html 跳过来)
  const testMode = getQueryParam('test');
  if (testMode === 'multi') {
    const subjectsParam = getQueryParam('subjects') || '';
    const subjects = subjectsParam.split(',').filter(Boolean);
    const stage = getQueryParam('stage');
    const grade = parseInt(getQueryParam('grade'), 10) || null;
    const count = parseInt(getQueryParam('count'), 10) || 5;
    if (subjects.length > 0) {
      MULTI_MODE = { subjects, stage, grade, count };
      renderMultiLanding();
      return;
    }
  }
  // URL ?concept_id= 直接进 Step 2 (兼容从概念卡点进来)
  const directConcept = getQueryParam('concept_id');
  if (directConcept && getConceptById(directConcept)) {
    SELECTED_CONCEPT = directConcept;
    if (MODE === 'test') renderStep2();
    else renderStep2Quick();
    return;
  }
  renderStep1();
}

// V4.1 多学科模式: 落地页 (选学科后, 自动选首个学科 quick pick 概念, 进入 5 道题)
function renderMultiLanding() {
  setStep(1);
  const c = document.getElementById('content');
  c.className = 'container step1';
  const mm = MULTI_MODE;
  // 找首个学科的 quick pick 概念
  const stageQuicks = QUICK_PICKS.filter(q => mm.subjects.includes(q.reason));
  if (stageQuicks.length === 0) {
    c.innerHTML = `<h2>多学科模式</h2>
      <p class="lead">所选学科 ${mm.subjects.join(' / ')} 暂未配置 quick pick 概念。</p>
      <button class="btn" onclick="renderStep1()">→ 选单个概念</button>`;
    return;
  }
  const firstQuick = stageQuicks[0];
  const concept = getConceptById(firstQuick.id);
  const subjList = mm.subjects.map(s => SUBJECT_CN[s] || s).join(' + ');
  const stageNm = mm.stage === 'primary' ? '小学' : (mm.stage === 'junior' ? '初中' : '学段');
  c.innerHTML = `
    <div class="multi-chip" style="background: var(--primary-soft, #e6f5ee); border: 1px solid var(--primary, #00875a); color: var(--primary, #00875a); padding: 8px 14px; border-radius: 999px; font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 16px;">📚 多学科模式 · ${esc(stageNm)} ${mm.grade || '?'} 年级 · ${esc(subjList)} · ${mm.count} 道题</div>
    <h2>${mm.count} 道题找出薄弱在哪儿</h2>
    <p class="lead">你先选了 ${mm.subjects.length} 个学科。先测 [${SUBJECT_CN[firstQuick.reason] || firstQuick.reason}] 的 "${esc(concept ? concept.title : firstQuick.id)}",5 道题测完后会帮你列各学科的薄弱清单。</p>
    <div class="quick-pick" style="margin-top: 24px;">
      <button class="btn" style="background: var(--primary, #00875a); color: #fff; border: none; padding: 14px 24px; border-radius: 8px; font-weight: 600; cursor: pointer;" onclick="pickConcept('${firstQuick.id}')">开始测试 ${SUBJECT_CN[firstQuick.reason] || firstQuick.reason} · "${esc(concept ? concept.title : firstQuick.id)}" →</button>
      <button class="btn" style="background: transparent; color: var(--text-2, #4a4a4a); border: 1px solid var(--border, #e8e0cc); padding: 14px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; margin-left: 8px;" onclick="renderStep1()">换学科/概念</button>
    </div>
    <p style="color: var(--text-3, #8a8a8a); font-size: 12px; margin-top: 24px;">⏳ 这次先帮你测第一个学科。测完后可点"换学科/概念"再测下一个,把各学科的薄弱都收齐。</p>
  `;
}

function renderStep1() {
  setStep(1);
  const c = document.getElementById('content');
  c.className = 'container step1';
  const titleMap = {
    'M_G4_GM_08': '勾股定理',
    'M_G4_QR_05': '一元二次方程',
    'M_G4_QR_11': '二次函数',
    'M_G4_GM_10': '三角形相似',
    'M_G3_GM_04': '圆的面积',
  };
  c.innerHTML = `
    <h2>选一个概念开始诊断</h2>
    <p class="lead">PoC 范围: math 5 核心考点. 先选 1 个, 5 分钟测出你的薄弱程度.</p>
    <div class="quick-pick-label">// MATH 5 大常考</div>
    <div class="quick-pick">
      ${QUICK_PICKS.map(q => {
        const t = titleMap[q.id] || q.id;
        return `<button class="qp-btn" onclick="pickConcept('${q.id}')">${esc(t)}<span class="badge">${esc(q.reason)}</span></button>`;
      }).join('')}
    </div>
    <div class="quick-pick-label">// 或搜索任意概念 (全 14 学科 1906 概念)</div>
    <div class="search-box">
      <input type="text" id="search-input" placeholder="输入概念名/关键词, 如 '分数' '牛顿' '古诗'…" oninput="onSearch(this.value)">
    </div>
    <div class="search-results" id="search-results"></div>
  `;
}

function onSearch(q) {
  const out = document.getElementById('search-results');
  if (!q || q.length < 1) { out.innerHTML = ''; return; }
  const ql = q.toLowerCase();
  const matches = GRAPH.nodes.filter(n =>
    (n.title || '').toLowerCase().includes(ql) ||
    (n.id || '').toLowerCase().includes(ql) ||
    (n.subdomain || '').toLowerCase().includes(ql) ||
    (n.domain || '').toLowerCase().includes(ql)
  ).slice(0, 30);
  if (matches.length === 0) {
    out.innerHTML = '<div class="search-row" style="cursor:default"><div class="title" style="color:#8a92a8">没找到匹配的概念</div></div>';
    return;
  }
  out.innerHTML = matches.map(n => {
    const subj = SUBJECT_CN[n.subject] || n.subject;
    return `<div class="search-row" onclick="pickConcept('${esc(n.id)}')">
      <div class="title">${esc(n.title)}</div>
      <div class="meta">${esc(subj)} · ${esc(n.grade_start || '')}-${esc(n.grade_end || '')}年级 · diff=${esc(n.difficulty || '?')}</div>
    </div>`;
  }).join('');
}

function pickConcept(id) {
  SELECTED_CONCEPT = id;
  if (MODE === 'test') renderStep2();
  else renderStep2Quick();
}

function toggleMode() {
  MODE = MODE === 'test' ? 'quick' : 'test';
  const btn = document.getElementById('mode-toggle');
  btn.textContent = MODE === 'test' ? '📊 切到手输答对率' : '📝 切到 5 道题测试';
  btn.classList.toggle('on', MODE === 'quick');
  // 如果已选概念, 重渲染
  if (SELECTED_CONCEPT) {
    if (MODE === 'test') renderStep2();
    else renderStep2Quick();
  }
}

function renderStep2() {
  setStep(2);
  const c = document.getElementById('content');
  c.className = 'container step2';
  const concept = getConceptById(SELECTED_CONCEPT);
  if (!concept) { c.innerHTML = '<div class="err">概念不存在</div>'; return; }
  // 拿 5 道题
  const exs = (EXERCISES_BY_CONCEPT[SELECTED_CONCEPT] || []).slice(0, 5);
  if (exs.length < 5) {
    c.innerHTML = `
      <div class="concept-banner">
        <div class="name">${esc(concept.title)}</div>
        <div class="meta">${esc(SUBJECT_CN[concept.subject] || '')} · ${esc(concept.grade_start || '')}-${esc(concept.grade_end || '')}年级 · 难度 ${esc(concept.difficulty || '?')}</div>
      </div>
      <div class="err">该概念题目不够 5 道 (只有 ${exs.length} 道), 请先选其他概念, 或 V4.0.3 全学科覆盖后回来.</div>
    `;
    return;
  }
  USER_ANSWERS = {};
  const subjCn = SUBJECT_CN[concept.subject] || '';
  c.innerHTML = `
    <h2>5 道题快速测试</h2>
    <p class="lead">// 客观题 (选择/填空) 自动判分, 简答题只计"答了没". 不限时.</p>
    <div class="concept-banner">
      <div class="name">${esc(concept.title)}</div>
      <div class="meta">${esc(subjCn)} · ${esc(concept.grade_start || '')}-${esc(concept.grade_end || '')}年级 · 难度 ${esc(concept.difficulty || '?')}</div>
    </div>
    <div id="q-list">
      ${exs.map((ex, i) => renderQuestion(ex, i)).join('')}
    </div>
    <div class="actions">
      <button class="btn secondary" onclick="goBack()">← 重选概念</button>
      <button class="btn" onclick="submitTest()">提交诊断 →</button>
    </div>
  `;
}

function renderQuestion(ex, i) {
  const num = i + 1;
  const typeLabel = TYPE_LABEL[ex.type] || ex.type;
  const typeClass = TYPE_CLASS[ex.type] || 'short';
  const bloom = ex.bloom ? `<span class="q-bloom">${esc(ex.bloom)}</span>` : '';
  const diff = ex.difficulty ? `<span class="q-diff d${ex.difficulty}">难 ${esc(ex.difficulty)}</span>` : '';
  const real = ex.is_real_exam ? `<span class="q-real">📋 真题</span>` : '';
  let input = '';
  if (ex.type === 'multiple_choice' && ex.options) {
    // 适配: ex.options 可能是 string (JSON), array, 或者破损/null
    let opts;
    if (typeof ex.options === 'string') {
      try { opts = JSON.parse(ex.options); } catch (e) { opts = []; }
    } else if (Array.isArray(ex.options)) {
      opts = ex.options;
    } else {
      opts = [];
    }
    // 去掉 LLM 在 value 里加的 "A. " "B. " 等前缀, 避免和 letter 重复
    const stripPrefix = (s, j) => {
      const expected = String.fromCharCode(65 + j) + '.';
      if (typeof s === 'string' && s.startsWith(expected)) return s.slice(expected.length).trim();
      return s;
    };
    input = `<div class="q-options">
      ${opts.map((opt, j) => {
        const letter = String.fromCharCode(65 + j);
        return `<div class="q-opt" data-exid="${esc(ex.id)}" data-letter="${letter}" onclick="selectChoice('${esc(ex.id)}', '${letter}')">
          <span class="letter">${letter}.</span>
          <span>${esc(stripPrefix(opt, j))}</span>
        </div>`;
      }).join('')}
    </div>`;
  } else if (ex.type === 'fill_blank') {
    input = `<input type="text" class="q-fill-input" data-exid="${esc(ex.id)}" placeholder="输入你的答案…" oninput="setFillAnswer('${esc(ex.id)}', this.value)">`;
  } else {
    input = `<textarea class="q-ta" data-exid="${esc(ex.id)}" placeholder="简要写出你的思路/答案… (简答题只计'答了没', 不判分)" oninput="setShortAnswer('${esc(ex.id)}', this.value)"></textarea>`;
  }
  return `<div class="q-card" id="qcard-${esc(ex.id)}">
    <div class="q-head">
      <span class="q-num">Q${num}</span>
      <span class="q-type ${typeClass}">${esc(typeLabel)}</span>
      ${bloom}${diff}${real}
    </div>
    <div class="q-question">${esc(ex.question)}</div>
    ${input}
  </div>`;
}

window.selectChoice = function(exId, letter) {
  const card = document.getElementById(`qcard-${exId}`);
  card.querySelectorAll('.q-opt').forEach(o => o.classList.remove('selected'));
  const sel = card.querySelector(`.q-opt[data-letter="${letter}"]`);
  if (sel) sel.classList.add('selected');
  USER_ANSWERS[exId] = { type: 'choice', value: letter };
};
window.setFillAnswer = function(exId, val) {
  USER_ANSWERS[exId] = { type: 'fill', value: val };
};
window.setShortAnswer = function(exId, val) {
  USER_ANSWERS[exId] = { type: 'short', value: val };
};

function gradeAnswers() {
  // 返回 [bool]*5
  const exs = (EXERCISES_BY_CONCEPT[SELECTED_CONCEPT] || []).slice(0, 5);
  // 转字符串辅助: 避免 number/list 类型时 .replace() 抛错
  const toStr = v => v == null ? '' : (Array.isArray(v) ? v.join('|') : String(v));
  const norm = s => toStr(s).replace(/[\s，。、,.!?！？;；:：]/g, '').toLowerCase();
  return exs.map(ex => {
    const ua = USER_ANSWERS[ex.id];
    if (!ua) return false;  // 未答 = 错
    if (ex.type === 'multiple_choice') {
      // 正确答案 (answer 字段, 也可能是 letter)
      const correct = toStr(ex.answer).trim().toUpperCase();
      return toStr(ua.value).trim().toUpperCase() === correct;
    } else if (ex.type === 'fill_blank') {
      // 模糊匹配: 包含/被包含 (去空白/标点)
      // answer 可能是 list (多个可接受答案), 任一命中就算对
      const candidates = Array.isArray(ex.answer) ? ex.answer : [ex.answer];
      const user = norm(ua.value);
      if (!user) return false;
      return candidates.some(c => {
        const cN = norm(c);
        return user === cN || user.includes(cN) || cN.includes(user);
      });
    } else {
      // short_answer: 只计"答了没" (写 > 5 字算答了)
      return toStr(ua.value).trim().length > 5;
    }
  });
}

function submitTest() {
  const answers = gradeAnswers();
  // V4.0.3 集成 history store: 答错题自动收错题本 + 诊断历史
  const exs = (EXERCISES_BY_CONCEPT[SELECTED_CONCEPT] || []).slice(0, 5);
  const concept = getConceptById(SELECTED_CONCEPT);
  exs.forEach((ex, i) => {
    if (answers[i] === false) {
      const ua = USER_ANSWERS[ex.id] || {};
      window.HistoryStore.recordWrong({
        exercise_id: ex.id,
        concept_id: ex.concept_id,
        concept_title: concept ? concept.title : '',
        question: ex.question,
        user_answer: toStrUser(ua.value),
        correct_answer: toStrCorrect(ex.answer),
        type: ex.type,
      });
    }
  });
  const result = diagnose(SELECTED_CONCEPT, answers, null);
  recordHistoryAndRender(result, 'test');
}

function toStrUser(v) {
  if (v == null) return '';
  if (Array.isArray(v)) return v.join(', ');
  return String(v);
}
function toStrCorrect(v) {
  if (v == null) return '';
  if (Array.isArray(v)) return v.join(' / ');
  return String(v);
}

function recordHistoryAndRender(result, entry) {
  if (result.error) { showResult(result); return; }
  // 记录诊断历史
  window.HistoryStore.recordDiagnosis({
    concept_id: result.concept_id,
    concept_title: result.concept_title,
    subject: result.subject,
    score: result.score,
    score_pct: result.score_pct,
    status: result.status,
    entry,
  });
  showResult(result);
}

function renderStep2Quick() {
  setStep(2);
  const c = document.getElementById('content');
  c.className = 'container step2';
  const concept = getConceptById(SELECTED_CONCEPT);
  if (!concept) { c.innerHTML = '<div class="err">概念不存在</div>'; return; }
  const subjCn = SUBJECT_CN[concept.subject] || '';
  c.innerHTML = `
    <h2>手输答对率</h2>
    <p class="lead">// 适合"已经会但懒得做 5 道题"的人, 或快速粗测. V4.0.2 PoC 也做了这个入口.</p>
    <div class="concept-banner">
      <div class="name">${esc(concept.title)}</div>
      <div class="meta">${esc(subjCn)} · ${esc(concept.grade_start || '')}-${esc(concept.grade_end || '')}年级 · 难度 ${esc(concept.difficulty || '?')}</div>
    </div>
    <div class="quick-panel">
      <div style="color:#8a92a8; font-size:12px; font-family:'SF Mono', monospace;">// 你觉得自己答对率大概多少?</div>
      <div class="pct"><span class="sign"></span><span id="pct-num">${QUICK_SCORE}</span><span class="sign">%</span></div>
      <input type="range" min="0" max="100" step="5" value="${QUICK_SCORE}" oninput="setQuickScore(this.value)">
      <div class="scale">
        <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
      </div>
    </div>
    <div class="actions">
      <button class="btn secondary" onclick="goBack()">← 重选概念</button>
      <button class="btn" onclick="submitQuick()">看诊断结果 →</button>
    </div>
  `;
}

window.setQuickScore = function(v) {
  QUICK_SCORE = parseInt(v, 10);
  document.getElementById('pct-num').textContent = QUICK_SCORE;
};

function submitQuick() {
  const result = diagnose(SELECTED_CONCEPT, null, QUICK_SCORE / 100.0);
  recordHistoryAndRender(result, 'quick-check');
}

function goBack() {
  SELECTED_CONCEPT = null;
  USER_ANSWERS = {};
  renderStep1();
}

function showResult(result) {
  if (result.error) {
    document.getElementById('content').innerHTML = `<div class="err">${esc(result.error)}</div>`;
    return;
  }
  setStep(3);
  const c = document.getElementById('content');
  c.className = 'container step3';

  const statusClass = { 薄弱: 'weak', 巩固: 'consolidate', 已掌握: 'mastered' }[result.status] || 'weak';
  const explain = result.human_explanation;

  c.innerHTML = `
    <div class="result-banner ${statusClass}">
      <div class="emoji">${explain.status_emoji}</div>
      <div class="status-text">${result.status} · 「${esc(result.concept_title)}」</div>
      <div class="score-big">答对率 ${result.score_pct}% (${result.score * 5}/5)</div>
      <div class="threshold-hint">// 自适应阈值: 难度 ${result.difficulty} → 薄弱线 ${result.weak_threshold}% / 巩固线 ${result.consolidate_threshold}%</div>
    </div>

    <div class="explanation">
      <h3>// 诊断结果</h3>
      <div class="summary-text">${esc(explain.summary)}</div>
      <div class="why-text">${esc(explain.why)}</div>
    </div>

    <div class="explanation">
      <h3>// 建议动作</h3>
      <div class="actions-list">
        ${explain.actions.map(a => `<div class="action-item ${a.type}">
          <span class="icon">${a.icon}</span>
          <span>${esc(a.text)}</span>
        </div>`).join('')}
      </div>
    </div>

    ${result.recommend_path.length > 0 ? `
      <div class="path-section">
        <h3>// 复习路径 (${result.weak_concepts.length} 个先决, 按距离+难度排序, 取前 ${result.recommend_path.length})</h3>
        <div class="path-list">
          ${result.recommend_path.map((r, i) => `
            <a class="path-row distance-${Math.min(3, r.distance)}" href="./concept.html?id=${esc(r.id)}" target="_blank">
              <span class="order">${i + 1}</span>
              <span class="name">${esc(r.title)}</span>
              <span class="meta">${esc(SUBJECT_CN[r.subject] || '')} · 距离 ${r.distance} · 难 ${r.difficulty || '?'}</span>
            </a>
          `).join('')}
        </div>
      </div>
    ` : ''}

    <div class="actions" style="margin-top: 32px;">
      <button class="btn secondary" onclick="goBack()">← 测另一个概念</button>
      <button class="btn secondary" onclick="location.href='./wrongbook.html'">❌ 错题本 (${window.HistoryStore.getWrongbookStats().total})</button>
      <button class="btn" onclick="location.href='./exercise.html?id=${esc(result.concept_id)}'">📝 直接做 5 道题</button>
    </div>
    ${renderHistorySection(result.concept_id)}
  `;

  // V4.0.4: 渲染完整 canvas 趋势图 + 个性化推荐
  // 延迟 50ms 等 innerHTML 注入 + layout 完, 才能拿到 canvas 真实尺寸
  setTimeout(() => {
    try {
      if (typeof window.TrendChart !== 'undefined') {
        const hist = window.HistoryStore.getConceptHistory(result.concept_id);
        window.TrendChart.render(
          'trend-canvas',
          hist,
          result.weak_threshold,
          result.consolidate_threshold
        );
      }
    } catch (e) { console.error('TrendChart render failed:', e); }
    try {
      if (typeof window.Recommender !== 'undefined') {
        const concept = getConceptById(result.concept_id);
        window.Recommender.render(
          'rec-area',
          REC_DATA,
          result.concept_id,
          result.status,
          concept ? concept.title : result.concept_title
        );
      }
    } catch (e) { console.error('Recommender render failed:', e); }
  }, 50);

  // 滚动到顶
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// --- V4.0.4 历史区 (错题列表 + 完整 canvas 趋势图 + 推荐区) ---
function renderHistorySection(conceptId) {
  if (typeof window.HistoryStore === 'undefined') return '';
  const hist = window.HistoryStore.getConceptHistory(conceptId);
  if (hist.length === 0) {
    // 仍渲染推荐区 (诊断结果页底部)
    return '<div id="rec-area" class="rec-area"></div>';
  }
  const rows = hist.slice().reverse().slice(0, 5).map(h => {
    const date = new Date(h.date).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
    return '<div class="history-row">' +
      '<span class="history-date">' + esc(date) + '</span>' +
      '<span class="history-status status-' + esc(h.status) + '">' + esc(h.status) + '</span>' +
      '<span class="history-score">' + esc(h.score_pct) + '%</span>' +
    '</div>';
  }).join('');
  // V4.0.4: 完整 canvas 趋势图 (≥2 次即可画, 1 次给 placeholder)
  const trendHtml = '<div class="trend-wrap">' +
    '<h3>// 进度趋势图 (最近 ' + hist.length + ' 次)</h3>' +
    '<canvas id="trend-canvas" class="trend-canvas"></canvas>' +
    '<p class="trend-tip">// 鼠标 hover 点查看详情 · 红=薄弱 / 黄=巩固 / 绿=已掌握</p>' +
  '</div>';
  return '<div class="path-section">' +
    '<h3>// 诊断历史 (' + hist.length + ' 次)</h3>' +
    '<div class="history-list">' + rows + '</div>' +
    trendHtml +
    '<div id="rec-area" class="rec-area"></div>' +
  '</div>';
}

// --- 启动 ---
loadData();
