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
    btn_labels: '显示标签',
    btn_roots: '高亮入口',
    btn_relayout: '重排',
    search_placeholder: '搜索概念 ID / 标题 / 标签...',
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
  },
  'zh-TW': {
    app_title: '2022 新課標知識圖譜',
    app_subtitle: 'Open Curriculum CN · 1:1 復刻 <a href="https://withmarble.com/curriculum/" target="_blank">Marble</a> 範式 · 數據來自 <a href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">教育部 2022 義教新課標</a> · CC-BY-SA 4.0',
    stats_concepts: '概念數',
    stats_edges: '關係數',
    stats_subjects: '學科數',
    stats_roots: '缺先決根節點 (可學起)',
    btn_labels: '顯示標籤',
    btn_roots: '高亮入口',
    btn_relayout: '重排',
    search_placeholder: '搜尋概念 ID / 標題 / 標籤...',
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
  },
  'en': {
    app_title: '2022 New Curriculum Knowledge Graph',
    app_subtitle: 'Open Curriculum CN · 1:1 reproduction of <a href="https://withmarble.com/curriculum/" target="_blank">Marble</a> paradigm · data from <a href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">PRC MoE 2022 Compulsory Curriculum Standards</a> · CC-BY-SA 4.0',
    stats_concepts: 'Concepts',
    stats_edges: 'Edges',
    stats_subjects: 'Subjects',
    stats_roots: 'Root nodes (no prereq)',
    btn_labels: 'Show labels',
    btn_roots: 'Highlight roots',
    btn_relayout: 'Re-layout',
    search_placeholder: 'Search concept ID / title / tag...',
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
  },
};

// 学科名翻译
const SUBJECT_CN_I18N = {
  'math': { 'zh-CN': '数学', 'zh-TW': '數學', 'en': 'Math' },
  'chinese': { 'zh-CN': '语文', 'zh-TW': '語文', 'en': 'Chinese' },
  'english': { 'zh-CN': '英语', 'zh-TW': '英語', 'en': 'English' },
  'physics': { 'zh-CN': '物理', 'zh-TW': '物理', 'en': 'Physics' },
  'chemistry': { 'zh-CN': '化学', 'zh-TW': '化學', 'en': 'Chemistry' },
  'biology': { 'zh-CN': '生物', 'zh-TW': '生物', 'en': 'Biology' },
  'history': { 'zh-CN': '历史', 'zh-TW': '歷史', 'en': 'History' },
  'geography': { 'zh-CN': '地理', 'zh-TW': '地理', 'en': 'Geography' },
  'morality_law': { 'zh-CN': '道法', 'zh-TW': '道法', 'en': 'Civics' },
  'science': { 'zh-CN': '科学', 'zh-TW': '科學', 'en': 'Science' },
  'info_tech': { 'zh-CN': '信息科技', 'zh-TW': '資訊科技', 'en': 'Info Tech' },
  'art': { 'zh-CN': '艺术', 'zh-TW': '藝術', 'en': 'Arts' },
  'pe_health': { 'zh-CN': '体育', 'zh-TW': '體育', 'en': 'PE' },
  'labor': { 'zh-CN': '劳动', 'zh-TW': '勞動', 'en': 'Labor' },
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
  document.getElementById('toggleLabels').textContent = I18N[currentLang].btn_labels;
  document.getElementById('toggleRoots').textContent = I18N[currentLang].btn_roots;
  document.getElementById('reLayout').textContent = I18N[currentLang].btn_relayout;
  // 重新渲染图例
  if (typeof buildLegend === 'function') buildLegend();
  // 重新渲染 detail
  if (typeof window._currentNode === 'function') {
    // 略
  }
}

function tSubject(s) {
  return SUBJECT_CN_I18N[s] ? SUBJECT_CN_I18N[s][currentLang] : s;
}

// 简易 简→繁 转换 (覆盖 2022 课标常用字)
const SIMP_TO_TRAD = {
  '数学': '數學', '语文': '語文', '英语': '英語', '物理': '物理', '化学': '化學',
  '生物': '生物', '历史': '歷史', '地理': '地理', '科学': '科學', '艺术': '藝術',
  '体育': '體育', '劳动': '勞動', '信息': '資訊', '道德': '道德', '法治': '法治',
  '概念': '概念', '关系': '關係', '数据': '數據', '程序': '程式', '网络': '網路',
  '万': '萬', '亿': '億', '区': '區', '长': '長', '短': '短', '高': '高', '低': '低',
  '开': '開', '关': '關', '学': '學', '习': '習', '习': '習', '时': '時', '间': '間',
  '后': '後', '前': '前', '内': '內', '外': '外', '中': '中', '上': '上', '下': '下',
  '课': '課', '标': '標', '书': '書', '读': '讀', '写': '寫', '语': '語',
  '认': '認', '识': '識', '议': '議', '论': '論', '说': '說', '请': '請',
  '过': '過', '这': '這', '那': '那', '这': '這', '进': '進', '出': '出',
  '会': '會', '议': '議', '议': '議', '应': '應', '当': '當', '对': '對',
  '种': '種', '类': '類', '点': '點', '种': '種', '为': '為', '现': '現',
  '发': '發', '展': '展', '产': '產', '业': '業', '业': '業', '务': '務',
  '页': '頁', '图': '圖', '线': '線', '维': '維', '结': '結', '构': '構',
  '体': '體', '验': '驗', '单': '單', '复': '複', '杂': '雜', '简': '簡',
  '样': '樣', '种': '種', '样': '樣', '类': '類', '项': '項', '目': '目',
  '价': '價', '值': '值', '计': '計', '算': '算', '确': '確', '定': '定',
  '决': '決', '定': '定', '决': '決', '设': '設', '计': '計', '计': '計',
  '计': '計', '划': '劃', '运': '運', '动': '動', '动': '動', '态': '態',
  '变': '變', '化': '化', '变': '變', '换': '換', '转': '轉', '换': '換',
};

function simpToTrad(text) {
  if (!text) return text;
  let out = '';
  for (const ch of text) {
    out += SIMP_TO_TRAD[ch] || ch;
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
