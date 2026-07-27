// Open Curriculum CN — 14 学科英文 key → 中文标签 共享字典 (V3.6.10b)
// To C 用户视角, 不显示 math/chinese 这种开发者词
// 用 var 顶层声明, 挂到 window, 让 share.js / funnel.js / 3d.js / print.html 共享
// (如果用 const, 多个 script 顶层声明会冲突: "Identifier 'SUBJECT_CN' has already been declared")

var SUBJECT_CN = {
  math: '数学', chinese: '语文', english: '英语',
  science: '科学', physics: '物理', chemistry: '化学',
  biology: '生物', history: '历史', geography: '地理',
  morality_law: '道德与法治', info_tech: '信息科技', art: '艺术',
  pe_health: '体育与健康', labor: '劳动', integrated: '综合'
};
