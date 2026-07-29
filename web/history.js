// V4.0.3 localStorage 持久化: 诊断历史 + 错题本
// 两个独立 store, 共享工具函数
'use strict';

const LS_PREFIX = 'opencurriculum:';

// ---------- 通用 ----------
function lsGet(key, fallback) {
  try {
    const v = localStorage.getItem(LS_PREFIX + key);
    return v ? JSON.parse(v) : fallback;
  } catch (e) {
    return fallback;
  }
}
function lsSet(key, val) {
  try {
    localStorage.setItem(LS_PREFIX + key, JSON.stringify(val));
    return true;
  } catch (e) {
    console.error('localStorage set failed:', e);
    return false;
  }
}

// ---------- 诊断历史 ----------
// 结构: [{concept_id, concept_title, subject, score, score_pct, status, date (ISO)}, ...]
const HISTORY_KEY = 'diagnose_history';
const HISTORY_MAX = 500;  // 防止爆 localStorage (5MB 上限)

function recordDiagnosis(record) {
  const hist = lsGet(HISTORY_KEY, []);
  hist.push({
    concept_id: record.concept_id,
    concept_title: record.concept_title || '',
    subject: record.subject || '',
    score: record.score,
    score_pct: record.score_pct,
    status: record.status,
    entry: record.entry || 'test',  // 'test' or 'quick-check'
    date: new Date().toISOString(),
  });
  // 保留最近 HISTORY_MAX 条
  if (hist.length > HISTORY_MAX) hist.splice(0, hist.length - HISTORY_MAX);
  return lsSet(HISTORY_KEY, hist);
}

function getAllHistory() {
  return lsGet(HISTORY_KEY, []);
}

function getConceptHistory(concept_id) {
  return getAllHistory().filter(h => h.concept_id === concept_id);
}

// 按概念聚合 (取最新一次, 用于 dashboard)
function getLatestByConcept() {
  const map = new Map();
  for (const h of getAllHistory()) {
    const cur = map.get(h.concept_id);
    if (!cur || cur.date < h.date) map.set(h.concept_id, h);
  }
  return Array.from(map.values()).sort((a, b) => b.date.localeCompare(a.date));
}

function clearHistory() {
  return lsSet(HISTORY_KEY, []);
}

// ---------- 错题本 ----------
// 结构: [{exercise_id, concept_id, concept_title, question, user_answer, correct_answer, type, date}, ...]
const WRONGBOOK_KEY = 'wrongbook';
const WRONGBOOK_MAX = 1000;

function recordWrong(ex) {
  const wb = lsGet(WRONGBOOK_KEY, []);
  // 去重 (同 ex_id 不重复入库)
  if (wb.some(w => w.exercise_id === ex.exercise_id)) return false;
  wb.push({
    exercise_id: ex.exercise_id,
    concept_id: ex.concept_id,
    concept_title: ex.concept_title || '',
    question: ex.question,
    user_answer: ex.user_answer,
    correct_answer: ex.correct_answer,
    type: ex.type,
    date: new Date().toISOString(),
  });
  if (wb.length > WRONGBOOK_MAX) wb.splice(0, wb.length - WRONGBOOK_MAX);
  return lsSet(WRONGBOOK_KEY, wb);
}

function getWrongbook() {
  return lsGet(WRONGBOOK_KEY, []);
}

function removeFromWrongbook(exercise_id) {
  const wb = getWrongbook().filter(w => w.exercise_id !== exercise_id);
  return lsSet(WRONGBOOK_KEY, wb);
}

function clearWrongbook() {
  return lsSet(WRONGBOOK_KEY, []);
}

function getWrongbookStats() {
  const wb = getWrongbook();
  const byConcept = {};
  const byType = {};
  for (const w of wb) {
    byConcept[w.concept_id] = (byConcept[w.concept_id] || 0) + 1;
    byType[w.type] = (byType[w.type] || 0) + 1;
  }
  return {
    total: wb.length,
    by_concept: byConcept,
    by_type: byType,
  };
}

// 暴露到 window
window.HistoryStore = {
  recordDiagnosis, getAllHistory, getConceptHistory, getLatestByConcept, clearHistory,
  recordWrong, getWrongbook, removeFromWrongbook, clearWrongbook, getWrongbookStats,
};
