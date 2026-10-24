// Data semantics shared by the workspace and its regression checks.
export const SUBJECTS = { math:'数学', chinese:'语文', english:'英语', science:'科学', physics:'物理', chemistry:'化学', biology:'生物', history:'历史', geography:'地理', morality_law:'道德与法治', info_tech:'信息科技', art:'艺术', pe_health:'体育与健康', labor:'劳动' };
export const RELATIONS = { prerequisite:'前置记录', progresses_to:'进阶记录', relates_to:'关联记录' };
export const STORAGE_KEY = 'opencurriculum:workspace:v2';
export function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
export function filterConcepts(nodes, {query='',subject='',grade='',reviewIds=null}={}) {
  const text = query.trim().toLocaleLowerCase();
  return nodes.filter(n => (!subject || n.subject === subject) &&
    (!grade || (Number.isFinite(n.grade_start) && Number.isFinite(n.grade_end) && n.grade_start <= +grade && n.grade_end >= +grade)) &&
    (!reviewIds || reviewIds.includes(n.id)) &&
    (!text || `${n.title} ${n.id} ${n.title_pinyin || ''}`.toLocaleLowerCase().includes(text)));
}
export function groupNeighbors(graph, id, includeRelated=false) {
  const byId = new Map(graph.nodes.map(n => [n.id,n]));
  const groups = {before:[],after:[],related:[]};
  for (const e of graph.edges) {
    if (e.from !== id && e.to !== id) continue;
    if (!RELATIONS[e.rel] || e.from === e.to) continue;
    const neighborId = e.from === id ? e.to : e.from;
    if (!byId.has(neighborId)) continue;
    let group;
    if (e.rel === 'relates_to') { if (!includeRelated) continue; group = groups.related; }
    else group = e.to === id ? groups.before : groups.after;
    let row = group.find(r => r.node.id === neighborId);
    if (!row) { row = {node:byId.get(neighborId),edges:[]}; group.push(row); }
    row.edges.push(e);
  }
  for (const list of Object.values(groups)) list.sort((a,b)=>(a.node.grade_start-b.node.grade_start) || a.node.title.localeCompare(b.node.title,'zh-CN'));
  return groups;
}
export function hasReviewRecord(edge, reviews) {
  // Match the existing documented protocol; do not invent a new approval schema.
  return edge.rel === 'prerequisite' && reviews.some(r => r.edge_id === edge.id &&
    ['evidence_source','evidence_locator','reviewer_role','reviewed_at','rationale'].every(k=>typeof r[k] === 'string' && r[k].trim()));
}
export function eligibleQuestions(exercises, blocked=false) {
  if (blocked) return [];
  return exercises.filter(e => e.type === 'multiple_choice' && /^[A-D]$/.test(String(e.answer).trim()) &&
    Array.isArray(e.options) && e.options.length === 4 && typeof e.question === 'string' && e.question.trim());
}
export function gradeChoice(question, selected) {
  if (!eligibleQuestions([question]).length || !/^[A-D]$/.test(selected || '')) return null;
  return selected === String(question.answer).trim();
}
export function initialState() { return {version:2,notes:{},review:[],attempts:[],lastConcept:''}; }
export function restoreState(raw) {
  try {
    const state = JSON.parse(raw);
    if (state?.version !== 2 || !state.notes || typeof state.notes !== 'object' || Array.isArray(state.notes) ||
      !Array.isArray(state.review) || !Array.isArray(state.attempts)) return initialState();
    return {version:2,notes:Object.fromEntries(Object.entries(state.notes).filter(([k,v])=>/^[A-Za-z0-9_]+$/.test(k) && typeof v === 'string')),
      review:state.review.filter(x=>typeof x==='string'),attempts:state.attempts.filter(a=>a && typeof a.conceptId==='string' && typeof a.questionId==='string' && typeof a.correct==='boolean').slice(-500),
      lastConcept:typeof state.lastConcept==='string'?state.lastConcept:''};
  } catch { return initialState(); }
}
