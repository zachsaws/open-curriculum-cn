// Open Curriculum CN — i18n 翻译词典
// 支持 zh-CN (简体) / zh-TW (繁体) / en (英文)

const I18N = {
  'zh-CN': {
    app_title: '2022 新课标知识图谱',
    app_subtitle: 'Open Curriculum CN · 1:1 复刻 <a href="https://withmarble.com/curriculum/" target="_blank">Marble</a> 范式 · 数据来自 <a href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">教育部 2022 义教新课标</a> · CC-BY-SA 4.0',
    stats_concepts: '概念数',
    stats_edges: '关系数',
    stats_subjects: '学科数',
    stats_roots: '缺先决根节点 (可学起)',
    stats_roots_pre: '缺先决根节点',
    stats_roots_label: '可学起入口',
    btn_labels: '显示标签',
    btn_labels_hide: '隐藏标签',
    btn_roots: '高亮入口',
    btn_roots_off: '取消高亮',
    btn_relayout: '重排',
    search_placeholder: '搜索概念 ID / 标题 / 标签...',
    empty_concepts: '无匹配概念',
    btn_fly_to: '双击飞到该学科',
    card_difficulty: '难度',
    card_minutes: '分钟',
    card_grade: '年级',
    card_content_req: '📋 课标内容要求',
    card_academic_req: '🎯 课标学业要求',
    card_key_points: '💡 知识要点',
    card_examples: '📚 课标例题',
    card_prereq: '直接先决',
    card_unlocks: '解锁后继',
    card_no_prereq: '没有先决概念',
    card_no_unlock: '没有后继概念',
    grade_label: 'G',
    source_link: '课标原文 ↗',
    loading: '加载知识图谱...',
    err_no_data: '未找到图谱数据 (graph.json)<br><br>数据仍在采集中',
    search_count_suffix: '匹配 (按 ESC 关闭)',
    chip_off: '已隐藏',
    // V2.3 新增
    btn_chip_toggle: '切换',
    chip_count_unit: '个概念',
    btn_start_here: '从这里学起 →',
    btn_start_here_aria: '从此概念开始学习',
    btn_started: '已展开 ✓',
    btn_expanded: '已展开',
    btn_concepts: '个概念',
    kbd_hint: '在搜索框内输入时, 快捷键不触发',
    kbd_close: '关闭 (Esc)',
    lang_zh_cn: '简',
    lang_zh_tw: '繁',
    lang_en: 'EN',
  },
  'zh-TW': {
    app_title: '2022 新課標知識圖譜',
    app_subtitle: 'Open Curriculum CN · 1:1 復刻 <a href="https://withmarble.com/curriculum/" target="_blank">Marble</a> 範式 · 數據來自 <a href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">教育部 2022 義教新課標</a> · CC-BY-SA 4.0',
    stats_concepts: '概念數',
    stats_edges: '關係數',
    stats_subjects: '學科數',
    stats_roots: '缺先決根節點 (可學起)',
    stats_roots_pre: '缺先決根節點',
    stats_roots_label: '可學起入口',
    btn_labels: '顯示標籤',
    btn_labels_hide: '隱藏標籤',
    btn_roots: '高亮入口',
    btn_roots_off: '取消高亮',
    btn_relayout: '重排',
    search_placeholder: '搜尋概念 ID / 標題 / 標籤...',
    empty_concepts: '無匹配概念',
    btn_fly_to: '雙擊飛到該學科',
    card_difficulty: '難度',
    card_minutes: '分鐘',
    card_grade: '年級',
    card_content_req: '📋 課標內容要求',
    card_academic_req: '🎯 課標學業要求',
    card_key_points: '💡 知識要點',
    card_examples: '📚 課標例題',
    card_prereq: '直接先決',
    card_unlocks: '解鎖後繼',
    card_no_prereq: '沒有先決概念',
    card_no_unlock: '沒有後繼概念',
    grade_label: 'G',
    source_link: '課標原文 ↗',
    loading: '載入知識圖譜...',
    err_no_data: '未找到圖譜資料 (graph.json)<br><br>資料仍在採集中',
    search_count_suffix: '匹配 (按 ESC 關閉)',
    chip_off: '已隱藏',
    // V2.3 新增
    btn_chip_toggle: '切換',
    chip_count_unit: '個概念',
    btn_start_here: '從這裡學起 →',
    btn_start_here_aria: '從此概念開始學習',
    btn_started: '已展開 ✓',
    btn_expanded: '已展開',
    btn_concepts: '個概念',
    kbd_hint: '在搜尋框內輸入時, 快捷鍵不觸發',
    kbd_close: '關閉 (Esc)',
    lang_zh_cn: '簡',
    lang_zh_tw: '繁',
    lang_en: 'EN',
  },
  'en': {
    app_title: '2022 New Curriculum Knowledge Graph',
    app_subtitle: 'Open Curriculum CN · 1:1 reproduction of <a href="https://withmarble.com/curriculum/" target="_blank">Marble</a> paradigm · data from <a href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">PRC MoE 2022 Compulsory Curriculum Standards</a> · CC-BY-SA 4.0',
    stats_concepts: 'Concepts',
    stats_edges: 'Edges',
    stats_subjects: 'Subjects',
    stats_roots: 'Root nodes (no prereq)',
    stats_roots_pre: 'Root nodes',
    stats_roots_label: 'Learnable entry points',
    btn_labels: 'Show labels',
    btn_labels_hide: 'Hide labels',
    btn_roots: 'Highlight roots',
    btn_roots_off: 'Remove highlight',
    btn_relayout: 'Re-layout',
    search_placeholder: 'Search concept ID / title / tag...',
    empty_concepts: 'No matching concepts',
    btn_fly_to: 'Double-click to fly to this subject',
    card_difficulty: 'Difficulty',
    card_minutes: 'min',
    card_grade: 'Grade',
    card_content_req: '📋 Curriculum Content Requirements',
    card_academic_req: '🎯 Curriculum Academic Requirements',
    card_key_points: '💡 Key Points',
    card_examples: '📚 Curriculum Examples',
    card_prereq: 'Direct Prerequisites',
    card_unlocks: 'Unlocks',
    card_no_prereq: 'No prerequisites',
    card_no_unlock: 'No unlocks',
    grade_label: 'G',
    source_link: 'curriculum source ↗',
    loading: 'Loading knowledge graph...',
    err_no_data: 'Graph data not found (graph.json)<br><br>Data is still being collected',
    search_count_suffix: 'matches (press ESC to close)',
    chip_off: 'hidden',
    // V2.3 new keys
    btn_chip_toggle: 'Toggle',
    chip_count_unit: 'concepts',
    btn_start_here: 'Start from here →',
    btn_start_here_aria: 'Start learning from this concept',
    btn_started: 'Expanded ✓',
    btn_expanded: 'Expanded',
    btn_concepts: 'concepts',
    kbd_hint: 'Shortcuts are disabled while typing in the search box',
    kbd_close: 'Close (Esc)',
    lang_zh_cn: 'CN',
    lang_zh_tw: 'TW',
    lang_en: 'EN',
  },
};

// 学科名翻译 (单一真源 — app.js / api/server.py 都从这里读)
const SUBJECT_CN_I18N = {
  'math':         { 'zh-CN': '数学',         'zh-TW': '數學',         'en': 'Math' },
  'chinese':      { 'zh-CN': '语文',         'zh-TW': '語文',         'en': 'Chinese' },
  'english':      { 'zh-CN': '英语',         'zh-TW': '英語',         'en': 'English' },
  'physics':      { 'zh-CN': '物理',         'zh-TW': '物理',         'en': 'Physics' },
  'chemistry':    { 'zh-CN': '化学',         'zh-TW': '化學',         'en': 'Chemistry' },
  'biology':      { 'zh-CN': '生物',         'zh-TW': '生物',         'en': 'Biology' },
  'history':      { 'zh-CN': '历史',         'zh-TW': '歷史',         'en': 'History' },
  'geography':    { 'zh-CN': '地理',         'zh-TW': '地理',         'en': 'Geography' },
  'morality_law': { 'zh-CN': '道德与法治',   'zh-TW': '道德與法治',   'en': 'Civics' },
  'science':      { 'zh-CN': '科学',         'zh-TW': '科學',         'en': 'Science' },
  'info_tech':    { 'zh-CN': '信息科技',     'zh-TW': '資訊科技',     'en': 'Info Tech' },
  'art':          { 'zh-CN': '艺术',         'zh-TW': '藝術',         'en': 'Arts' },
  'pe_health':    { 'zh-CN': '体育与健康',   'zh-TW': '體育與健康',   'en': 'PE & Health' },
  'labor':        { 'zh-CN': '劳动',         'zh-TW': '勞動',         'en': 'Labor' },
  'integrated':   { 'zh-CN': '综合实践',     'zh-TW': '綜合實踐',     'en': 'Integrated Practice' },
};

let currentLang = 'zh-CN';

function t(key) {
  return I18N[currentLang][key] || I18N['zh-CN'][key] || key;
}

function setLang(lang) {
  if (!I18N[lang]) return;
  currentLang = lang;
  applyI18n();
}

function applyI18n() {
  document.title = I18N[currentLang].app_title;
  document.querySelector('.header h1').textContent = I18N[currentLang].app_title;
  document.querySelector('.header .sub').innerHTML = I18N[currentLang].app_subtitle;
  document.getElementById('searchInput').placeholder = I18N[currentLang].search_placeholder;

  // 通用 data-i18n 扫描: 替换所有标记节点文本
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (I18N[currentLang][key] !== undefined) {
      // 大部分节点直接 textContent, 但 app_subtitle 用 innerHTML 已在上面处理
      if (key === 'app_subtitle') {
        el.innerHTML = I18N[currentLang][key];
      } else {
        // 保留 children (例如 card-content-req-block 里的 <span class="num">)
        // 但我们只在子元素是纯文本时用 textContent
        // 简单策略: 如果有子元素 且 没有 child text nodes, 跳过
        const childEls = Array.from(el.children);
        if (childEls.length === 0) {
          el.textContent = I18N[currentLang][key];
        }
      }
    }
  });

  // V2.3 data-i18n-label 扫描: 短标签 (lang-switch 按钮等)
  document.querySelectorAll('[data-i18n-label]').forEach(el => {
    const key = el.getAttribute('data-i18n-label');
    if (I18N[currentLang][key] !== undefined) {
      el.textContent = I18N[currentLang][key];
    }
  });

  // 三按钮 — 依赖运行时状态 (window._labelsOn / window._rootsHighlighted)
  if (document.getElementById('toggleLabels')) {
    const on = typeof window._labelsOn !== 'undefined' && window._labelsOn;
    document.getElementById('toggleLabels').textContent = I18N[currentLang][on ? 'btn_labels_hide' : 'btn_labels'];
  }
  if (document.getElementById('toggleRoots')) {
    const on = typeof window._rootsHighlighted !== 'undefined' && window._rootsHighlighted;
    document.getElementById('toggleRoots').textContent = I18N[currentLang][on ? 'btn_roots_off' : 'btn_roots'];
  }
  if (document.getElementById('reLayout')) {
    document.getElementById('reLayout').textContent = I18N[currentLang].btn_relayout;
  }
  // 重新渲染图例
  if (typeof buildLegend === 'function') buildLegend();
  // 重新渲染已打开的详情面板
  if (typeof window._currentNode !== 'undefined' && window._currentNode && typeof showCard === 'function') {
    showCard(window._currentNode);
  }
}

function tSubject(s) {
  return SUBJECT_CN_I18N[s] ? SUBJECT_CN_I18N[s][currentLang] : s;
}

// 简易 简→繁 转换 — 用扩展字典 (simp_to_trad.js, 500+ 字)
// simp_to_trad.js 已定义 const SIMP_TO_TRAD 并挂到 window
// (本文件的 let SIMP_TO_TRAD 不能同名, 否则与 simp_to_trad.js 的 const 冲突)
const _SIMP_TO_TRAD_DICT = (typeof window !== 'undefined' && window.SIMP_TO_TRAD) ? window.SIMP_TO_TRAD : {};

function simpToTrad(text) {
  if (!text) return text;
  let out = '';
  for (const ch of text) {
    out += _SIMP_TO_TRAD_DICT[ch] || ch;
  }
  return out;
}

// 暴露全局
window.I18N = I18N;
window.SUBJECT_CN_I18N = SUBJECT_CN_I18N;
window.t = t;
window.setLang = setLang;
window.tSubject = tSubject;
window.simpToTrad = simpToTrad;
window.applyI18n = applyI18n;
