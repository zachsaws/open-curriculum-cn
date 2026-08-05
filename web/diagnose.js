// V4.0.2 智能诊断 PoC — 客户端版本 (GitHub Pages 静态部署)
// 算法跟 api/diagnose.py 保持一致, 避免 doc/API drift
// V4.0.5 phase 2.2: IRT 自适应难度 (动态题调整 + 加权算分)
'use strict';

// 难度 1-5 → 薄弱/巩固阈值
const DIFFICULTY_THRESHOLDS = {
  1: { weak: 80, consolidate: 95 },
  2: { weak: 80, consolidate: 95 },
  3: { weak: 70, consolidate: 90 },
  4: { weak: 60, consolidate: 80 },
  5: { weak: 50, consolidate: 70 },
};

// V4.0.5 IRT 自适应: 维护"已用题"和"动态题"两个状态
// IRT_CURRENT: 当前诊断状态 (单概念模式), 含 answers + history
let IRT_CURRENT = null;  // { conceptId, difficulty, answers: [{ex, correct}], pool: [...], adaptiveQ: [], step: 0, maxQ: 5 }

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
let MULTI_EXS = [];     // 当前混合题列表 (subject 来自 concept_id 前缀)

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

// 概念 id → 该题适合的"代表年级" (用 GRAPH.nodes 查 grade_start/grade_end, 不依赖 ID 格式)
function gradeFromConceptId(cid) {
  if (!cid) return null;
  const n = getConceptById(cid);
  if (!n) return null;
  // 优先用 grade_start (节点的"起始年级"), 4 年级就匹配 grade_start <= 4 <= grade_end
  // 这里返回"该概念主要归属的年级": grade_start
  return n.grade_start || null;
}

// 概念 id → 该题是否适合给定年级 (用 grade_start/grade_end 范围匹配, 兼容 chinese stage 字段)
function conceptMatchesGrade(cid, grade) {
  if (!grade) return true;  // 没指定 grade 不过滤
  const n = getConceptById(cid);
  if (!n) return false;
  // 数学/物理/化学等: grade_start / grade_end 字段 (1-12)
  if (n.grade_start && n.grade_end) {
    return grade >= n.grade_start && grade <= n.grade_end;
  }
  // chinese/english 等: stage 字段 (1=1-2, 2=3-4, 3=5-6, 4=7-9)
  if (n.stage) {
    // 4 年级 → 包含在 stage 2 (3-4) 或 stage 1 (1-2) 的话... 直接把 grade 转 stage 反向查
    // 实际: 4 年级 → stage 2 (3-4), 7 年级 → stage 4 (7-9)
    // 这里粗略: grade 落在该 stage 对应的范围内
    const stageRanges = { 1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 9] };
    const r = stageRanges[n.stage];
    return r ? grade >= r[0] && grade <= r[1] : true;
  }
  return true;  // 没有 grade 信息的不过滤
}

// V4.1.1 多学科抽题: 按学科均匀抽 N 道 (用 quick pick 概念池优先, 不足时用全部)
function pickMultiExercises(subjects, count, grade) {
  // 每学科目标题数: 平均分配, 前几个学科 +1
  // 例 count=5 subjects=2 → [3, 2]; count=10 subjects=3 → [4, 3, 3]
  const base = Math.floor(count / subjects.length);
  const extra = count - base * subjects.length;
  const perCounts = subjects.map((_, i) => base + (i < extra ? 1 : 0));
  const out = [];
  subjects.forEach((subj, idx) => {
    const perSubj = perCounts[idx];
    // 该学科的所有题 (优先用该年级, 不足时 fallback 到全学科)
    let pool = EXERCISES.filter(e => subjFromConceptId(e.concept_id) === subj);
    if (grade) {
      const gradePool = pool.filter(e => conceptMatchesGrade(e.concept_id, grade));
      if (gradePool.length >= perSubj) pool = gradePool;
      // 否则保留全学科池 (题不够时兜底)
    }
    // 按 concept_id 均匀: 每概念先抽 1, 不足时再每概念抽 2...
    const byCid = {};
    pool.forEach(e => {
      if (!byCid[e.concept_id]) byCid[e.concept_id] = [];
      byCid[e.concept_id].push(e);
    });
    const cids = Object.keys(byCid);
    const picked = [];
    for (let round = 0; picked.length < perSubj && round < 5; round++) {
      // 每轮: 每个未用完的概念抽 1 题
      let added = false;
      for (const cid of cids) {
        if (picked.length >= perSubj) break;
        if (byCid[cid].length > round) {
          picked.push(byCid[cid][round]);
          added = true;
        }
      }
      if (!added) break;  // 所有概念都没题了
    }
    out.push(...picked);
  });
  // 打乱顺序
  return out.sort(() => Math.random() - 0.5).slice(0, count);
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
    // V4.0.4 + V4.1.3: 并行加载 3 份数据 (graph_lite + exercises + recommendations)
    const [gRes, eRes, rRes] = await Promise.all([
      fetch('./data/graph_lite.json'),  // V4.1.3: lite 版 (1.7MB gz, 比 full 7.8MB 快 4 倍)
      fetch('./data/exercises.json'),
      fetch('./data/recommendations.json').catch(() => null),
    ]);
    if (!gRes.ok) throw new Error(`graph_lite.json ${gRes.status}`);
    if (!eRes.ok) throw new Error(`exercises.json ${eRes.status}`);
    GRAPH = await gRes.json();
    const eData = await eRes.json();
    EXERCISES = eData.exercises || [];
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
  // V4.0.5 phase 2.3: ?plan=7d 直接进 7 天复习计划
  if (getQueryParam('plan') === '7d') {
    render7DayPlan();
    return;
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
    <p class="lead">按 ${mm.subjects.length} 个学科均匀出题 (每学科 ${Math.floor(mm.count / mm.subjects.length)} 道)。答完会按学科分组告诉你每个学科的薄弱状态。</p>
    <div class="quick-pick" style="margin-top: 24px;">
      <button class="btn" style="background: var(--primary, #00875a); color: #fff; border: none; padding: 14px 24px; border-radius: 8px; font-weight: 600; cursor: pointer;" onclick="startMultiTest()">开始 ${mm.count} 道题测试 →</button>
      <button class="btn" style="background: transparent; color: var(--text-2, #4a4a4a); border: 1px solid var(--border, #e8e0cc); padding: 14px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; margin-left: 8px;" onclick="window.location.href='./test.html'">重选学段/学科</button>
    </div>
  `;
}

// V4.1.1 多学科模式: 选学科+年级+题数 → 抽混合题 → step2
function startMultiTest() {
  if (!MULTI_MODE) { renderStep1(); return; }
  const { subjects, count, grade } = MULTI_MODE;
  MULTI_EXS = pickMultiExercises(subjects, count, grade);
  if (MULTI_EXS.length < count) {
    // 题不够, 提示用户
    const c = document.getElementById('content');
    c.innerHTML = `<div class="err">混合题抽取不足 (需要 ${count} 道, 实际 ${MULTI_EXS.length} 道)。请先回 test.html 减少学科数或题数。</div>`;
    return;
  }
  USER_ANSWERS = {};
  renderMultiStep2();
}

// V4.1.1 多学科模式 step2: 混合题展示, 每题带学科 chip
function renderMultiStep2() {
  setStep(2);
  const c = document.getElementById('content');
  c.className = 'container step2';
  const mm = MULTI_MODE;
  const subjList = mm.subjects.map(s => SUBJECT_CN[s] || s).join(' + ');
  c.innerHTML = `
    <div class="multi-chip" style="background: var(--primary-soft, #e6f5ee); border: 1px solid var(--primary, #00875a); color: var(--primary, #00875a); padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 16px;">📚 多学科 · ${esc(subjList)} · ${MULTI_EXS.length} 道</div>
    <h2>${MULTI_EXS.length} 道题混合测试</h2>
    <p class="lead">// 每道题可能来自不同学科, 看学科 chip 判断. 客观题自动判分, 简答题只计"答了没".</p>
    <div id="q-list">
      ${MULTI_EXS.map((ex, i) => renderMultiQuestion(ex, i)).join('')}
    </div>
    <div class="actions">
      <button class="btn secondary" onclick="backToMultiLanding()">← 重选学段/学科</button>
      <button class="btn" onclick="submitMultiTest()">提交混合题 →</button>
    </div>
  `;
}

// V4.1.1 多学科模式: 单题渲染,带学科 chip
function renderMultiQuestion(ex, i) {
  const num = i + 1;
  const typeLabel = TYPE_LABEL[ex.type] || ex.type;
  const typeClass = TYPE_CLASS[ex.type] || 'short';
  const subj = subjFromConceptId(ex.concept_id);
  const subjCn = SUBJECT_CN[subj] || '';
  const subjColor = PALETTE[subj] || '#888';
  const concept = getConceptById(ex.concept_id);
  const conceptName = concept ? concept.title : ex.concept_id;
  const diff = ex.difficulty ? `<span class="q-diff d${ex.difficulty}">难 ${esc(ex.difficulty)}</span>` : '';
  const real = ex.is_real_exam ? `<span class="q-real">📋 真题</span>` : '';
  const bloom = ex.bloom ? `<span class="q-bloom">${esc(ex.bloom)}</span>` : '';
  let input = '';
  if (ex.type === 'multiple_choice' && ex.options) {
    let opts;
    if (typeof ex.options === 'string') {
      try { opts = JSON.parse(ex.options); } catch (e) { opts = []; }
    } else if (Array.isArray(ex.options)) {
      opts = ex.options;
    } else {
      opts = [];
    }
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
      <span class="q-subj-chip" style="background: ${subjColor}; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700;">${esc(subjCn)}</span>
      <span class="q-type ${typeClass}">${esc(typeLabel)}</span>
      <span class="q-concept">${esc(conceptName)}</span>
      ${bloom}${diff}${real}
    </div>
    <div class="q-question">${esc(ex.question)}</div>
    ${input}
  </div>`;
}

function backToMultiLanding() {
  renderMultiLanding();
}

// V4.1.1 多学科模式: 评分
function gradeMultiAnswers() {
  const toStr = v => v == null ? '' : (Array.isArray(v) ? v.join('|') : String(v));
  const norm = s => toStr(s).replace(/[\s，。、,.!?！？;；:：]/g, '').toLowerCase();
  return MULTI_EXS.map(ex => {
    const ua = USER_ANSWERS[ex.id];
    if (!ua) return false;
    if (ex.type === 'multiple_choice') {
      const correct = toStr(ex.answer).trim().toUpperCase();
      return toStr(ua.value).trim().toUpperCase() === correct;
    } else if (ex.type === 'fill_blank') {
      const candidates = Array.isArray(ex.answer) ? ex.answer : [ex.answer];
      const user = norm(ua.value);
      if (!user) return false;
      return candidates.some(c => {
        const cN = norm(c);
        return user === cN || user.includes(cN) || cN.includes(user);
      });
    } else {
      return toStr(ua.value).trim().length > 5;
    }
  });
}

// V4.1.1 多学科模式: 提交 → 写 history + 错题本 + 渲染按学科分组结果
function submitMultiTest() {
  const answers = gradeMultiAnswers();
  // 写错题本: 每道错题按学科入
  MULTI_EXS.forEach((ex, i) => {
    if (answers[i] === false) {
      const ua = USER_ANSWERS[ex.id] || {};
      const concept = getConceptById(ex.concept_id);
      window.HistoryStore.recordWrong({
        exercise_id: ex.id,
        concept_id: ex.concept_id,
        concept_title: concept ? concept.title : '',
        subject: subjFromConceptId(ex.concept_id) || '',
        question: ex.question,
        user_answer: toStrUser(ua.value),
        correct_answer: toStrCorrect(ex.answer),
        type: ex.type,
        difficulty: ex.difficulty,
        ts: Date.now(),
      });
    }
  });
  // 写诊断历史: 每学科一份 (用首个答对的 concept_id 作代表)
  const bySubj = groupBySubject(MULTI_EXS, answers);
  Object.keys(bySubj).forEach(subj => {
    const list = bySubj[subj];
    const correct = list.filter(x => x.correct).length;
    const total = list.length;
    const scorePct = Math.round((correct / total) * 100);
    // 阈值用难度 1 默认 (简化: 多学科统一用 70%)
    let status = 'mastered';
    if (scorePct < 50) status = 'weak';
    else if (scorePct < 70) status = 'consolidate';
    // 用该学科首道题的 concept_id 作代表
    const rep = list[0];
    window.HistoryStore.recordDiagnosis({
      concept_id: rep.ex.concept_id,
      concept_title: (getConceptById(rep.ex.concept_id) || { title: SUBJECT_CN[subj] || subj }).title,
      subject: subj,
      score: correct,
      score_pct: scorePct,
      status: status,
      entry: 'multi',
      subjects: MULTI_MODE.subjects,
    });
  });
  renderMultiStep3(answers);
}

function groupBySubject(exs, answers) {
  const out = {};
  exs.forEach((ex, i) => {
    const subj = subjFromConceptId(ex.concept_id);
    if (!subj) return;
    if (!out[subj]) out[subj] = [];
    out[subj].push({ ex, correct: answers[i] });
  });
  return out;
}

// V4.1.1 多学科模式: 渲染按学科分组结果
function renderMultiStep3(answers) {
  setStep(3);
  const c = document.getElementById('content');
  c.className = 'container step3';
  const bySubj = groupBySubject(MULTI_EXS, answers);
  const subjects = Object.keys(bySubj);
  // 算每学科 status
  const subjResults = subjects.map(subj => {
    const list = bySubj[subj];
    const correct = list.filter(x => x.correct).length;
    const total = list.length;
    const scorePct = Math.round((correct / total) * 100);
    let status = 'mastered';
    if (scorePct < 50) status = 'weak';
    else if (scorePct < 70) status = 'consolidate';
    return { subj, correct, total, scorePct, status, list };
  });
  // 整体 = 最差
  const STATUS_ORDER = { 'mastered': 3, 'consolidate': 2, 'weak': 1 };
  const overallStatus = subjResults.reduce((a, b) => STATUS_ORDER[a.status] < STATUS_ORDER[b.status] ? a : b).status;
  const totalCorrect = subjResults.reduce((s, r) => s + r.correct, 0);
  const totalAll = subjResults.reduce((s, r) => s + r.total, 0);
  const overallPct = Math.round((totalCorrect / totalAll) * 100);
  // 状态中文 + emoji
  const STATUS_LABEL = { mastered: { cn: '已掌握', emoji: '🎉' }, consolidate: { cn: '巩固', emoji: '👍' }, weak: { cn: '薄弱', emoji: '📌' } };
  const overall = STATUS_LABEL[overallStatus];
  // 整体 banner
  c.innerHTML = `
    <div class="result-banner ${overallStatus}" style="padding: 32px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
      <div class="emoji" style="font-size: 56px; line-height: 1; margin-bottom: 12px;">${overall.emoji}</div>
      <div class="status-text" style="font-size: 28px; font-weight: 800; margin-bottom: 8px;">${overall.cn}</div>
      <div class="score-big" style="font-size: 16px; color: var(--text-2, #4a4a4a);">多学科 ${subjects.length} 个 · ${totalCorrect}/${totalAll} (${overallPct}%)</div>
    </div>
    <div class="explanation" style="background: var(--bg-elevated, #fff); border: 1px solid var(--border, #e8e0cc); border-radius: 10px; padding: 20px 24px; margin-bottom: 20px;">
      <h3 style="font-size: 14px; color: var(--text-2, #4a4a4a); margin-bottom: 12px;">// 按学科分组结果</h3>
      ${subjResults.map(r => {
        const subjCn = SUBJECT_CN[r.subj] || r.subj;
        const subjColor = PALETTE[r.subj] || '#888';
        const st = STATUS_LABEL[r.status];
        return `<div style="display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border, #e8e0cc);">
          <span style="background: ${subjColor}; color: #fff; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 700; min-width: 60px; text-align: center;">${esc(subjCn)}</span>
          <span style="font-size: 18px;">${st.emoji}</span>
          <span style="font-size: 16px; font-weight: 700;">${st.cn}</span>
          <span style="font-size: 13px; color: var(--text-3, #8a8a8a); margin-left: auto;">${r.correct}/${r.total} (${r.scorePct}%)</span>
        </div>`;
      }).join('')}
    </div>
    <div class="actions" style="margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap;">
      <button class="btn" style="flex: 1; padding: 14px 20px; font-size: 14px; font-weight: 600; background: var(--primary, #00875a); color: #fff; border: 1px solid var(--primary, #00875a); border-radius: 8px; cursor: pointer;" onclick="window.location.href='./test.html'">再测一次 (换学段/学科)</button>
      <button class="btn secondary" style="flex: 1; padding: 14px 20px; font-size: 14px; font-weight: 600; background: var(--bg-elevated, #fff); color: var(--text, #0a0d18); border: 1px solid var(--border, #e8e0cc); border-radius: 8px; cursor: pointer;" onclick="window.location.href='./wrongbook.html'">看错题本 →</button>
      <button class="btn secondary" style="flex: 1; padding: 14px 20px; font-size: 14px; font-weight: 600; background: var(--bg-elevated, #fff); color: var(--text, #0a0d18); border: 1px solid var(--border, #e8e0cc); border-radius: 8px; cursor: pointer;" onclick="window.location.href='./diagnose.html?plan=7d'">📅 7 天复习计划</button>
      <button class="btn secondary" style="flex: 1; padding: 14px 20px; font-size: 14px; font-weight: 600; background: var(--bg-elevated, #fff); color: var(--text, #0a0d18); border: 1px solid var(--border, #e8e0cc); border-radius: 8px; cursor: pointer;" onclick="exportDiagnosisReport()">🖨 导出报告 (PDF)</button>
    </div>
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
    <div style="margin: 16px 0 20px; padding: 12px 16px; background: rgba(0,135,90,0.06); border: 1px solid rgba(0,135,90,0.2); border-radius: 8px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
      <span style="font-size: 24px;">📅</span>
      <div style="flex: 1; min-width: 200px;">
        <div style="font-size: 14px; font-weight: 700; color: #0a0d18;">已经测过一些概念?</div>
        <div style="font-size: 12px; color: #4a4a4a; margin-top: 2px;">基于诊断历史生成 7 天复习计划, 每天 3 个概念, 薄弱优先</div>
      </div>
      <a class="btn" href="./diagnose.html?plan=7d" style="background: #00875a; color: #fff; border: 1px solid #00875a; padding: 10px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; text-decoration: none;">看 7 天复习计划 →</a>
    </div>
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
  // V4.0.5 phase 2.2: IRT 初始化 — 5 题按 difficulty 平均抽, 答完 1 题后动态换
  IRT_CURRENT = initIRTSession(SELECTED_CONCEPT, exs, 5);
  const subjCn = SUBJECT_CN[concept.subject] || '';
  c.innerHTML = `
    <h2>5 道题快速测试 <span style="font-size: 12px; font-weight: 500; color: #00875a; background: rgba(0,135,90,0.10); padding: 3px 10px; border-radius: 12px; margin-left: 8px;">🎯 IRT 自适应</span></h2>
    <p class="lead">// 客观题 (选择/填空) 自动判分, 简答题只计"答了没". 每答 1 题, 下一题会按你的水平自动调难度.</p>
    <div class="concept-banner">
      <div class="name">${esc(concept.title)}</div>
      <div class="meta">${esc(subjCn)} · ${esc(concept.grade_start || '')}-${esc(concept.grade_end || '')}年级 · 难度 ${esc(concept.difficulty || '?')}</div>
    </div>
    <div id="q-list" data-irt-active="1">
      ${renderIRTQuestions(IRT_CURRENT)}
    </div>
    <div class="actions">
      <button class="btn secondary" onclick="goBack()">← 重选概念</button>
      <button class="btn" onclick="submitIRTStep()">提交诊断 →</button>
    </div>
  `;
}

// V4.0.5 phase 2.2: IRT 会话初始化
function initIRTSession(conceptId, exs, maxQ) {
  // 概念 difficulty (默认 3)
  const concept = getConceptById(conceptId);
  const startDiff = concept ? (concept.difficulty || 3) : 3;
  // 抽 N 道题按 difficulty 平均 (从 exs 里选 N 道, 尽量覆盖难度)
  // 简化: 按 difficulty 排序, 选 N 道均匀分布
  const sorted = exs.slice().sort((a, b) => (a.difficulty || 3) - (b.difficulty || 3));
  const picked = [];
  for (let i = 0; i < maxQ && i < sorted.length; i++) {
    const idx = Math.floor(i * sorted.length / maxQ);
    picked.push(sorted[idx]);
  }
  // 打乱顺序 (避免按难度从低到高)
  picked.sort(() => Math.random() - 0.5);
  return {
    conceptId,
    pool: exs.slice(),  // 全部可用题 (含已用)
    usedIds: new Set(picked.map(e => e.id)),
    adaptiveQ: picked,  // 当前 5 道题 (会动态调)
    answers: [],  // {ex, correct, difficulty}
    step: 0,
    maxQ,
    startDiff,
  };
}

// 渲染 IRT 当前 5 道题 (每题加"自适应标签"显示当前难度档位)
function renderIRTQuestions(irt) {
  return irt.adaptiveQ.map((ex, i) => {
    const num = i + 1;
    const typeLabel = TYPE_LABEL[ex.type] || ex.type;
    const typeClass = TYPE_CLASS[ex.type] || 'short';
    const diff = ex.difficulty ? `<span class="q-diff d${ex.difficulty}">难 ${esc(ex.difficulty)}</span>` : '';
    const real = ex.is_real_exam ? `<span class="q-real">📋 真题</span>` : '';
    const bloom = ex.bloom ? `<span class="q-bloom">${esc(ex.bloom)}</span>` : '';
    // IRT 标记: 第 1 题 (已答) 显示"自适应中" / 未答显示"当前难度 X"
    const answered = i < irt.step;
    const statusLabel = answered
      ? (irt.answers[i].correct ? '✅ 答对' : '❌ 答错')
      : `第 ${num} 题 · 难度 ${ex.difficulty || '?'}`;
    let input = '';
    if (ex.type === 'multiple_choice' && ex.options) {
      let opts;
      if (typeof ex.options === 'string') {
        try { opts = JSON.parse(ex.options); } catch (e) { opts = []; }
      } else if (Array.isArray(ex.options)) {
        opts = ex.options;
      } else { opts = []; }
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
    return `<div class="q-card" id="qcard-${esc(ex.id)}" style="${answered ? 'opacity: 0.7;' : ''}">
      <div class="q-head">
        <span class="q-num">Q${num}</span>
        <span class="q-type ${typeClass}">${esc(typeLabel)}</span>
        <span class="q-irt-status" style="font-size: 10px; padding: 2px 8px; border-radius: 3px; background: ${answered ? 'rgba(10,13,24,0.06)' : 'rgba(0,135,90,0.10)'}; color: ${answered ? '#8a8a8a' : '#00875a'}; font-weight: 600;">${statusLabel}</span>
        ${bloom}${diff}${real}
      </div>
      <div class="q-question">${esc(ex.question)}</div>
      ${input}
    </div>`;
  }).join('');
}

// V4.0.5: 用户答完 1 题后, IRT 调整下一题 (答对→更难, 答错→更易)
function onAnswerRecorded(exId, correct) {
  if (!IRT_CURRENT) return;
  const i = IRT_CURRENT.step;
  if (i >= IRT_CURRENT.maxQ) return;
  // 幂等: 如果这题已经记录过, 跳过
  if (IRT_CURRENT.answers.some(a => a.ex.id === exId)) return;
  const ex = IRT_CURRENT.adaptiveQ[i];
  IRT_CURRENT.answers.push({ ex, correct, difficulty: ex.difficulty || 3 });
  IRT_CURRENT.step = i + 1;
  // 如果还有下一题, 调整
  if (IRT_CURRENT.step < IRT_CURRENT.maxQ) {
    const nextIdx = IRT_CURRENT.step;
    const targetDiff = correct
      ? Math.min(5, (ex.difficulty || 3) + 1)  // 答对 → 难题
      : Math.max(1, (ex.difficulty || 3) - 1); // 答错 → 易题
    // 从 pool 找最接近 targetDiff 的未用题
    const pool = IRT_CURRENT.pool;
    const used = new Set([...IRT_CURRENT.usedIds, ...IRT_CURRENT.adaptiveQ.slice(0, nextIdx).map(e => e.id)]);
    const candidates = pool.filter(e => !used.has(e.id));
    if (candidates.length > 0) {
      // 找 difficulty 最接近 targetDiff 的
      candidates.sort((a, b) => {
        const da = Math.abs((a.difficulty || 3) - targetDiff);
        const db = Math.abs((b.difficulty || 3) - targetDiff);
        return da - db;
      });
      const newEx = candidates[0];
      IRT_CURRENT.adaptiveQ[nextIdx] = newEx;
      IRT_CURRENT.usedIds.add(newEx.id);
    }
  }
  // 重渲染 (更新状态标签 + 第 N+1 题)
  const list = document.getElementById('q-list');
  if (list) list.innerHTML = renderIRTQuestions(IRT_CURRENT);
}
window.onAnswerRecorded = onAnswerRecorded;

// V4.0.5: IRT 加权算分
function gradeIRT() {
  if (!IRT_CURRENT) return { score: 0, scorePct: 0, weighted: 0, maxWeighted: 0, answers: [] };
  const answers = IRT_CURRENT.answers;
  const totalCorrect = answers.filter(a => a.correct).length;
  const score = totalCorrect / IRT_CURRENT.maxQ;
  // 加权: 答对题 difficulty 总和 / 5 道题 difficulty 总和 (用 adaptiveQ 的 difficulty)
  const weighted = answers.filter(a => a.correct).reduce((s, a) => s + (a.difficulty || 3), 0);
  const maxWeighted = IRT_CURRENT.adaptiveQ.reduce((s, ex) => s + (ex.difficulty || 3), 0);
  const weightedPct = maxWeighted > 0 ? Math.round((weighted / maxWeighted) * 100) : 0;
  // 答对率优先 (简单直观), 加权作为补充
  const scorePct = Math.round(score * 100);
  return { score, scorePct, weighted, maxWeighted, weightedPct, answers };
}

// V4.0.5: 提交 IRT 测试
function submitIRTStep() {
  if (!IRT_CURRENT) { submitTest(); return; }
  // 把还没评的题按"答了/没答"评, 用 onAnswerRecorded 触发 IRT 调整 (包括填空/简答)
  while (IRT_CURRENT.step < IRT_CURRENT.maxQ) {
    const i = IRT_CURRENT.step;
    const ex = IRT_CURRENT.adaptiveQ[i];
    const ua = USER_ANSWERS[ex.id];
    if (ua) {
      const correct = gradeOneEx(ex, ua);
      onAnswerRecorded(ex.id, correct);  // 触发 IRT 调整下一题
    } else {
      // 未答 = 错, 直接 push answers 但不调 onAnswerRecorded (因为是未答,不需要再调)
      IRT_CURRENT.answers.push({ ex, correct: false, difficulty: ex.difficulty || 3 });
      IRT_CURRENT.step = i + 1;
    }
  }
  // 算分
  const r = gradeIRT();
  // 走诊断逻辑 (跟 V4.0.2 一致)
  const concept = getConceptById(SELECTED_CONCEPT);
  const scorePct = r.scorePct;
  const d = concept.difficulty || 3;
  const th = DIFFICULTY_THRESHOLDS[d] || DIFFICULTY_THRESHOLDS[3];
  let status;
  if (scorePct < th.weak) status = '薄弱';
  else if (scorePct < th.consolidate) status = '巩固';
  else status = '已掌握';
  // BFS 找先决链 (跟 V4.0.2 一致)
  const adjTo = buildAdjTo();
  const prereqDist = bfsPrereqsWithDepth(SELECTED_CONCEPT, adjTo);
  const prereqNodes = Object.entries(prereqDist).map(([id, dist]) => {
    const n = getConceptById(id);
    return n ? { id, title: n.title, distance: dist, difficulty: n.difficulty, subject: n.subject } : null;
  }).filter(Boolean);
  const recommendPath = prereqNodes
    .sort((a, b) => (a.distance - b.distance) || ((a.difficulty || 3) - (b.difficulty || 3)))
    .slice(0, 7);
  const weakConcepts = prereqNodes.filter(n => (n.difficulty || 3) <= d);
  const subjCn = SUBJECT_CN[concept.subject] || '';
  const gradeRange = `${concept.grade_start || '?'}-${concept.grade_end || '?'}`;
  // 走 buildHumanExplanation 拿 status_emoji
  const explain = buildHumanExplanation(status, scorePct, concept.title, subjCn, gradeRange, d, recommendPath, concept);
  const result = {
    concept_id: SELECTED_CONCEPT,
    concept_title: concept.title,
    subject: concept.subject,
    score: r.score,
    score_pct: scorePct,
    weighted_pct: r.weightedPct,
    status,
    difficulty: d,
    weak_threshold: th.weak,
    consolidate_threshold: th.consolidate,
    weak_concepts: weakConcepts,
    recommend_path: recommendPath,
    human_explanation: explain,
    irt: {
      maxQ: r.answers.length,
      adaptiveQ: IRT_CURRENT.adaptiveQ.map(e => ({id: e.id, difficulty: e.difficulty})),
      answers: r.answers.map(a => ({ex_id: a.ex.id, correct: a.correct, difficulty: a.difficulty})),
    },
  };
  recordHistoryAndRender(result, 'test');
}
window.submitIRTStep = submitIRTStep;

// 评 1 道题
function gradeOneEx(ex, ua) {
  const toStr = v => v == null ? '' : (Array.isArray(v) ? v.join('|') : String(v));
  const norm = s => toStr(s).replace(/[\s，。、,.!?！？;：:：]/g, '').toLowerCase();
  if (!ua) return false;
  if (ex.type === 'multiple_choice') {
    const correct = toStr(ex.answer).trim().toUpperCase();
    return toStr(ua.value).trim().toUpperCase() === correct;
  } else if (ex.type === 'fill_blank') {
    const candidates = Array.isArray(ex.answer) ? ex.answer : [ex.answer];
    const user = norm(ua.value);
    if (!user) return false;
    return candidates.some(c => {
      const cN = norm(c);
      return user === cN || user.includes(cN) || cN.includes(user);
    });
  } else {
    return toStr(ua.value).trim().length > 5;
  }
}

// V4.0.5: 包装原 selectChoice / setFillAnswer / setShortAnswer, 触发 IRT 动态调整
// 原始定义在文件下面, 这里重写
window._origSelectChoice = null;

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
  // V4.0.5 IRT: 答完 1 题后自动调整下一题
  if (IRT_CURRENT) {
    const ex = IRT_CURRENT.adaptiveQ[IRT_CURRENT.step];
    if (ex && ex.id === exId) {
      const correct = gradeOneEx(ex, USER_ANSWERS[exId]);
      onAnswerRecorded(exId, correct);
    }
  }
};
window.setFillAnswer = function(exId, val) {
  USER_ANSWERS[exId] = { type: 'fill', value: val };
  // V4.0.5 IRT: 填空题在用户输入时只记录答案, 不立即判 (需要"提交"或"答完"才评)
  // 简化: 填空题答完一题触发时机难定, 让 submitIRTStep 统一评
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
            <a class="path-row distance-${Math.min(3, r.distance)}" href="./print.html?id=${esc(r.id)}" target="_blank">
              <span class="order">${i + 1}</span>
              <span class="name">${esc(r.title)}</span>
              <span class="meta">${esc(SUBJECT_CN[r.subject] || '')} · 距离 ${r.distance} · 难 ${r.difficulty || '?'}</span>
              <span class="path-video" data-concept-id="${esc(r.id)}" style="margin-left: auto; font-size: 11px; color: #00875a;"></span>
            </a>
          `).join('')}
        </div>
      </div>
    ` : ''}

    <div class="actions" style="margin-top: 32px;">
      <button class="btn secondary" onclick="goBack()">← 测另一个概念</button>
      <button class="btn secondary" onclick="location.href='./wrongbook.html'">❌ 错题本 (${window.HistoryStore.getWrongbookStats().total})</button>
      <button class="btn secondary" onclick="location.href='./diagnose.html?plan=7d'">📅 7 天复习计划</button>
      <button class="btn secondary" onclick="exportDiagnosisReport()">🖨 导出报告 (PDF)</button>
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
    // V4.1.2 视频图标
    try { renderPathVideos(); } catch (e) { console.error('renderPathVideos failed:', e); }
  }, 50);

  // 滚动到顶
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// V4.0.5 phase 2.1: 导出诊断报告为 PDF (用 window.print() + print CSS)
function exportDiagnosisReport() {
  // 把当前日期写到 .container.step3 的 data-pdf-date 属性
  const c = document.querySelector('.container.step3') || document.getElementById('content');
  if (c) c.setAttribute('data-pdf-date', new Date().toLocaleString('zh-CN', { hour12: false }));
  // 触发打印 (浏览器内置, 用户可另存为 PDF)
  window.print();
}
window.exportDiagnosisReport = exportDiagnosisReport;

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

// V4.1.2 视频数据 (按 concept_id 索引)
let VIDEOS_BY_CONCEPT = {};
async function loadVideos() {
  try {
    const r = await fetch('./data/videos.json');
    if (!r.ok) return;
    const data = await r.json();
    (data.videos || []).forEach(v => {
      if (!VIDEOS_BY_CONCEPT[v.concept_id]) VIDEOS_BY_CONCEPT[v.concept_id] = [];
      VIDEOS_BY_CONCEPT[v.concept_id].push(v);
    });
  } catch (e) { console.warn('[videos] load failed:', e); }
}
// 渲染复习路径每行的视频图标
function renderPathVideos() {
  document.querySelectorAll('.path-video[data-concept-id]').forEach(el => {
    const cid = el.dataset.conceptId;
    const vids = VIDEOS_BY_CONCEPT[cid] || [];
    if (vids.length > 0) {
      el.innerHTML = `<a href="${esc(vids[0].url)}" target="_blank" style="color: #00875a; text-decoration: none; font-weight: 600;">📺 ${esc(vids[0].title.length > 18 ? vids[0].title.slice(0, 18) + '…' : vids[0].title)}</a>`;
    }
  });
}
window.loadVideos = loadVideos;
window.renderPathVideos = renderPathVideos;

// V4.0.5 phase 2.3: 7 天复习计划
// 输入: history 里的薄弱/巩固概念 + 它们的先决链
// 输出: 7 天日程, 每天 3-5 个概念, 按 status 优先级 + 难度 排
function render7DayPlan() {
  setStep(3);
  const c = document.getElementById('content');
  c.className = 'container step3';
  const hist = window.HistoryStore ? window.HistoryStore.getAllHistory() : [];
  if (hist.length === 0) {
    c.innerHTML = `<div class="empty" style="padding: 60px 20px; text-align: center; color: #8a8a8a;">
      <p style="font-size: 48px; margin-bottom: 16px;">📅</p>
      <p style="font-size: 16px; color: #4a4a4a; margin-bottom: 8px;">还没有诊断记录</p>
      <p style="font-size: 13px; color: #8a8a8a; margin-bottom: 24px;">先去测几个概念, 找出薄弱在哪儿, 才有 7 天计划</p>
      <a class="btn" href="./diagnose.html" style="display:inline-block; padding: 10px 20px; font-size: 13px; background: rgba(0,135,90,0.15); border: 1px solid rgba(0,135,90,0.3); color: #0a0d18; border-radius: 6px; text-decoration: none;">🩺 去诊断</a>
    </div>`;
    return;
  }
  // 收集待复习概念 (按 status 优先级 + 难度)
  // 兼容 status 中英文 (历史可能是 'weak'/'consolidate' 也可能是 '薄弱'/'巩固')
  const statusWeight = { weak: 0, 薄弱: 0, consolidate: 1, 巩固: 1, mastered: 2, 已掌握: 2 };
  const todo = hist
    .filter(h => {
      const w = statusWeight[h.status];
      return w === 0 || w === 1;  // 只看薄弱/巩固
    })
    .sort((a, b) => {
      // 优先按 status (weak 先), 然后按概念 title 长度 / 难度
      const wA = statusWeight[a.status] || 1;
      const wB = statusWeight[b.status] || 1;
      if (wA !== wB) return wA - wB;
      return (a.concept_title || '').localeCompare(b.concept_title || '');
    })
    .slice(0, 21)  // 7 天 × 3 个, 最多 21 个
    .map(h => {
      const n = getConceptById(h.concept_id);
      // 把中文 status 归一为 'weak' / 'consolidate' (用于显示色)
      const sKey = statusWeight[h.status] === 0 ? 'weak' : 'consolidate';
      return {
        id: h.concept_id,
        title: h.concept_title || (n ? n.title : h.concept_id),
        status: sKey,
        subject: h.subject,
        difficulty: n ? n.difficulty : 1,
        subjectCn: SUBJECT_CN[h.subject] || h.subject,
        subjectColor: PALETTE[h.subject] || '#888',
      };
    });
  if (todo.length === 0) {
    c.innerHTML = `<div class="empty" style="padding: 60px 20px; text-align: center; color: #8a8a8a;">
      <p style="font-size: 48px; margin-bottom: 16px;">🎉</p>
      <p style="font-size: 16px; color: #4a4a4a;">你的薄弱清单已清空!</p>
      <p style="font-size: 13px; color: #8a8a8a; margin-top: 12px;">所有诊断过的概念都已掌握, 继续保持。</p>
    </div>
    <div class="actions" style="margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap;">
      <button class="btn secondary" onclick="goBack()" style="flex: 1; padding: 14px 20px; font-size: 14px; font-weight: 600; background: var(--bg-elevated, #fff); color: var(--text, #0a0d18); border: 1px solid var(--border, #e8e0cc); border-radius: 8px; cursor: pointer;">← 测另一个概念</button>
    </div>`;
    return;
  }
  // 按每天 3 个分 7 天 (不足 3 个时合并)
  const perDay = 3;
  const days = [];
  for (let i = 0; i < todo.length; i += perDay) {
    days.push(todo.slice(i, i + perDay));
  }
  while (days.length < 7) days.push([]);
  // 计算日期 (从今天起)
  const dayNames = ['今天', '明天', '第 3 天', '第 4 天', '第 5 天', '第 6 天', '第 7 天'];
  const today = new Date();
  const dayDate = (offset) => {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', weekday: 'short' });
  };
  c.innerHTML = `
    <div style="background: linear-gradient(135deg, #00875a 0%, #00a86b 100%); color: #fff; padding: 18px 24px; border-radius: 12px; margin-bottom: 20px;">
      <h2 style="font-size: 20px; font-weight: 800; margin-bottom: 4px;">📅 你的 7 天复习计划</h2>
      <p style="font-size: 13px; opacity: 0.9;">基于 ${hist.length} 次诊断历史,挑出 ${todo.length} 个薄弱/巩固概念。每天 3 个,按薄弱优先 + 难度从低到高排。</p>
    </div>
    <div class="week-plan">
      ${days.map((day, di) => `
        <div class="day-row" style="display: flex; gap: 16px; align-items: stretch; margin-bottom: 12px; padding: 16px; background: rgba(10,13,24,0.03); border: 1px solid rgba(10,13,24,0.08); border-radius: 10px; ${di === 0 ? 'border-color: #00875a; background: rgba(0,135,90,0.06);' : ''}">
          <div class="day-label" style="min-width: 80px; display: flex; flex-direction: column; justify-content: center; ${di === 0 ? 'color: #00875a;' : ''}">
            <div style="font-size: 16px; font-weight: 800;">${dayNames[di]}</div>
            <div style="font-size: 11px; color: #8a8a8a; font-family: 'SF Mono', monospace; margin-top: 2px;">${dayDate(di)}</div>
          </div>
          <div class="day-concepts" style="flex: 1; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
            ${day.length === 0
              ? '<span style="color: #a5a5a5; font-size: 13px; padding: 8px;">— 休息 / 自由复习 —</span>'
              : day.map(c => {
                const statusBg = c.status === 'weak' ? 'rgba(239,107,91,0.12)' : 'rgba(249,168,37,0.12)';
                const statusBorder = c.status === 'weak' ? 'rgba(239,107,91,0.3)' : 'rgba(249,168,37,0.3)';
                const statusIcon = c.status === 'weak' ? '📌' : '👍';
                const hasVideo = (VIDEOS_BY_CONCEPT[c.id] || []).length > 0;
                const videoBadge = hasVideo ? '<span style="font-size: 11px;">📺</span>' : '';
                return `<a href="./diagnose.html?concept_id=${esc(c.id)}" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; background: ${statusBg}; border: 1px solid ${statusBorder}; border-radius: 6px; text-decoration: none; color: #0a0d18; font-size: 13px; transition: all 0.12s;" onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 2px 6px rgba(0,0,0,0.1)';" onmouseout="this.style.transform=''; this.style.boxShadow='';">
                  <span style="background: ${c.subjectColor}; color: #fff; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 700;">${esc(c.subjectCn)}</span>
                  <span>${esc(c.title)}</span>
                  <span style="opacity: 0.6; font-size: 11px;">${statusIcon} 难 ${c.difficulty}</span>
                  ${videoBadge}
                </a>`;
              }).join('')
            }
          </div>
        </div>
      `).join('')}
    </div>
    <div class="actions" style="margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap;">
      <button class="btn secondary" onclick="goBack()" style="flex: 1; padding: 14px 20px; font-size: 14px; font-weight: 600; background: var(--bg-elevated, #fff); color: var(--text, #0a0d18); border: 1px solid var(--border, #e8e0cc); border-radius: 8px; cursor: pointer;">← 测另一个概念</button>
      <button class="btn" onclick="exportDiagnosisReport()" style="flex: 1; padding: 14px 20px; font-size: 14px; font-weight: 600; background: var(--primary, #00875a); color: #fff; border: 1px solid var(--primary, #00875a); border-radius: 8px; cursor: pointer;">🖨 导出 7 天计划 (PDF)</button>
    </div>
  `;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
window.render7DayPlan = render7DayPlan;

// --- 启动 ---
loadData();
loadVideos();
