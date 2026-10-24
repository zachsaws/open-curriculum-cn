import {SUBJECTS, STORAGE_KEY, escapeHTML as esc, filterConcepts, groupNeighbors, eligibleQuestions, gradeChoice, restoreState, initialState} from './learning-core.mjs';

const $ = id => document.getElementById(id);
const startId = 'M_G3_NS_10';
const friendlyTitles = {'M_G3_NS_10':'分数、小数与百分数', 'M_G3_NS_01':'分数的意义'};
const fractionIds = new Set(['M_G3_NS_10']);
let graph, byId = new Map(), blocked = new Set(), active = '', payload, loadToken = 0;
let view = 'lesson', part = 1, questions = [], qi = 0, selected = '', submitted = false;
let trail = [], toastTimer, state;
try { state = restoreState(localStorage.getItem(STORAGE_KEY)); } catch { state = initialState(); }

const title = node => friendlyTitles[node?.id] || node?.title || '';
const grade = node => `${node.grade_start}–${node.grade_end} 年级`;
const iconBookmark = '<svg viewBox="0 0 16 20" aria-hidden="true"><path d="M3 2h10v15l-5-3-5 3z"/></svg>';
async function getJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error('暂时无法加载');
  return response.json();
}
function toast(message) {
  clearTimeout(toastTimer); $('toast').textContent = message; $('toast').classList.add('show');
  toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2200);
}
function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); return true; }
  catch { toast('这台设备暂时无法保存，请先复制笔记'); return false; }
}
function marked() { return state.review.includes(active); }
function bookmarkButton() {
  return `<button class="bookmark" data-action="bookmark" aria-pressed="${marked()}">${iconBookmark}<span>${marked()?'已留到稍后':'稍后再学'}</span></button>`;
}
async function init() {
  try {
    const [g, flags] = await Promise.all([getJSON('./data/graph_lite.json'),getJSON('./data/quality_flags.json')]);
    if (!Array.isArray(g.nodes) || !Array.isArray(g.edges) || !Array.isArray(flags.blocked_concept_ids)) throw new Error('资料暂时无法打开');
    graph = g; byId = new Map(g.nodes.map(n=>[n.id,n])); blocked = new Set(flags.blocked_concept_ids);
    const requested = new URLSearchParams(location.search).get('concept') || startId;
    await openConcept(requested, false);
  } catch {
    $('learning-card').classList.remove('loading');
    $('learning-card').innerHTML='<h1>暂时无法打开知识地图</h1><p class="empty-copy">请检查网络后重试。</p><button class="primary" data-action="reload">重试</button>';
  }
}
async function openConcept(id, push=true) {
  const token = ++loadToken;
  if (!byId.has(id)) { $('learning-card').innerHTML='<h1>没有找到这个知识点</h1><p class="empty-copy">换一个名称找找看。</p><button class="primary" data-action="search">搜索知识点</button>'; return; }
  if (active && active!==id) trail.push(active);
  active=id; payload=null; view='lesson'; part=1; qi=0; selected=''; submitted=false;
  if(push) { const url=new URL(location.href);url.searchParams.set('concept',id);history.pushState({},'',url); }
  document.title=`${title(byId.get(id))} · 知识地图`;
  $('topic-context').textContent=`${SUBJECTS[byId.get(id).subject] || ''} · ${byId.get(id).domain || ''}`;
  $('back-button').disabled=!trail.length;
  for(const dialog of document.querySelectorAll('dialog[open]')) dialog.close();
  $('learning-card').innerHTML='<div class="placeholder title-placeholder"></div><div class="placeholder diagram-placeholder"></div><div class="placeholder text-placeholder"></div>';
  renderNeighbors();
  try {
    const data=await getJSON(`./data/concepts/${encodeURIComponent(id)}.json`);
    if(token!==loadToken)return;
    if(data.node?.id!==id || !Array.isArray(data.exercises))throw new Error('详情暂不可用');
    payload=data; questions=eligibleQuestions(data.exercises,blocked.has(id));
    state.lastConcept=id; save();renderCard();
    $('announce').textContent=`已打开${title(data.node)}`;
  }catch{
    if(token!==loadToken)return;
    $('learning-card').innerHTML='<h1>这个知识点暂时没能打开</h1><p class="empty-copy">可以重新加载，或先看看旁边的内容。</p><button class="primary" data-action="retry">重新加载</button>';
  }
}
function miniGraphic(node) {
  if(/分数乘除/.test(node.title)) return '<span class="mini-calculation" aria-hidden="true">½ × ⅓</span>';
  if(/百分/.test(node.title)) return '<span aria-hidden="true">25<span style="font-size:19px;margin-left:2px">%</span></span>';
  if(/分数|分式/.test(node.title)) return '<span class="mini-fraction" aria-hidden="true"><i></i><i></i><i></i><i></i></span>';
  if(/比的|比例/.test(node.title)) return '<span class="mini-dots" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>';
  if(/三角|勾股/.test(node.title))return '<span aria-hidden="true">△</span>';
  if(/小数/.test(node.title))return '<span aria-hidden="true">0.25</span>';
  return `<span style="font-size:23px;letter-spacing:0" aria-hidden="true">${esc(node.domain || SUBJECTS[node.subject] || '')}</span>`;
}
function neighborCard(row) {
  return `<button class="related-card" data-concept="${esc(row.node.id)}"><div class="mini-graphic">${miniGraphic(row.node)}</div><strong>${esc(title(row.node))}<span aria-hidden="true">↗</span></strong><small>${esc(grade(row.node))}</small></button>`;
}
function renderNeighbors() {
  const groups=groupNeighbors(graph,active);
  $('before-column').innerHTML=groups.before.length?'<h2>相关知识</h2>'+groups.before.slice(0,3).map(neighborCard).join(''):'';
  $('after-column').innerHTML=groups.after.length?'<h2>继续探索</h2>'+groups.after.slice(0,2).map(neighborCard).join(''):'';
  requestAnimationFrame(drawConnections);
}
function drawConnections() {
  if(innerWidth<=720){$('connections').innerHTML='';return;}
  const board=$('board').getBoundingClientRect(), main=$('learning-card').getBoundingClientRect();
  const paths=[...document.querySelectorAll('.related-card')].filter(el=>el.getBoundingClientRect().width>0).map(el=>{
    const r=el.getBoundingClientRect(),left=r.left<main.left;
    const x1=(left?r.right:main.right)-board.left,y1=(left?r.top+r.height/2:main.top+main.height/2)-board.top;
    const x2=(left?main.left:r.left)-board.left,y2=(left?main.top+main.height/2:r.top+r.height/2)-board.top;
    return `<path d="M${x1} ${y1} C${(x1+x2)/2} ${y1},${(x1+x2)/2} ${y2},${x2} ${y2}"/>`;
  });
  $('connections').innerHTML=paths.join('');
}
function fractionSVG(n) {
  const angle=n*Math.PI/2, x=90+58*Math.sin(angle), y=90-58*Math.cos(angle);
  return `<svg class="fraction-art" viewBox="0 0 180 180" role="img" aria-label="圆平均分成四份，涂色${n}份"><circle class="disc" cx="90" cy="90" r="58"/><path class="portion" d="M90 90 L90 32 A58 58 0 ${n>2?1:0} 1 ${x} ${y} Z"/><path class="cut" d="M90 32v116M32 90h116"/></svg>`;
}
function fractionEquation(n) {
  const numerator=n===2?1:n,denominator=n===2?2:4;
  return `<span class="math-fraction" aria-label="${numerator}/${denominator}"><span>${numerator}</span><span>${denominator}</span></span><span class="equals">=</span><span>${n/4}</span><span class="equals">=</span><span>${n*25}%</span>`;
}
function fractionCopy(n) {
  return `把一个整体平均分成四份。其中的${['','一','两','三'][n]}份，可以写成 ${n===2?'1/2':`${n}/4`}，也可以写成 ${n/4} 或 ${n*25}%。`;
}
function renderCard() {
  if(!payload)return;
  const node=payload.node;
  const top=`<div class="card-top"><span>${esc(SUBJECTS[node.subject] || '')} · ${esc(grade(node))}</span><button class="card-menu" data-action="details" aria-label="查看内容说明与相关联系">···</button></div>`;
  $('learning-card').classList.remove('loading');
  if(view==='practice'){renderPractice(top);return;}
  const fraction=fractionIds.has(active),triangle=active==='M_G4_GM_08';
  let art='',copy=esc(node.description || node.teaching_voice || '这个知识点还没有讲解。');
  if(fraction){
    art=`<p class="card-subtitle">同一个整体，三种表达。</p><div class="concept-figure" id="fraction-figure">${fractionSVG(part)}</div><div class="equation" id="equation">${fractionEquation(part)}</div><div class="fraction-controls" aria-label="改变涂色部分">${[1,2,3].map(n=>`<button data-part="${n}" aria-pressed="${n===part}">${n===2?'1/2':`${n}/4`}</button>`).join('')}</div>`;
    copy=fractionCopy(part);
  }else if(triangle){
    art='<p class="card-subtitle">两条直角边，与一条斜边。</p><div class="concept-figure"><svg class="triangle-art" viewBox="0 0 240 175" role="img" aria-label="直角边为3和4，斜边为5的直角三角形"><path d="M42 140V35l140 105z" fill="#e2ebdb" stroke="#8da87e" stroke-width="2"/><path d="M42 126h14v14" fill="none" stroke="#8da87e"/><g fill="#607353" font-size="16"><text x="22" y="93">3</text><text x="108" y="163">4</text><text x="122" y="81">5</text></g></svg></div><div class="equation" style="font-size:29px">3² + 4² = 5²</div>';
    copy='在直角三角形中，两条直角边的平方和，等于斜边的平方。';
  }
  $('learning-card').innerHTML=top+`<h1>${esc(title(node))}</h1>${art}<p class="explanation">${copy}</p>`+
    `<div class="card-bottom"><button class="primary" data-action="practice">${blocked.has(active)?'查看练习状态':'试一题'}<span aria-hidden="true">→</span></button>${bookmarkButton()}</div>`;
  requestAnimationFrame(drawConnections);
}
function renderPractice(top) {
  if(!questions.length){$('learning-card').innerHTML=top+`<h1>${esc(title(payload.node))}</h1><p class="empty-copy">${blocked.has(active)?'这部分内容正在校对，暂不能练习。':'这个知识点暂时没有可计分的选择题。'}</p><button class="primary" data-action="lesson">回到讲解</button>`;return;}
  const q=questions[qi],correct=submitted?gradeChoice(q,selected):null;
  $('learning-card').innerHTML=top+`<p class="practice-progress">${esc(title(payload.node))} · ${qi+1} / ${questions.length}</p><h1 class="practice-question">${esc(q.question)}</h1><form id="answer-form"><fieldset style="border:0;padding:0;margin:0"><legend class="sr-only">选择一个答案</legend>${q.options.map((text,i)=>{const letter='ABCD'[i];return `<label class="choice ${submitted&&letter===q.answer?'correct':submitted&&letter===selected&&!correct?'wrong':''}"><input type="radio" name="answer" value="${letter}" ${selected===letter?'checked':''} ${submitted?'disabled':''} required><span>${esc(text)}</span></label>`;}).join('')}</fieldset>${submitted?`<div class="feedback" role="status"><strong>${correct?'答对了。':'再对照一下。'}</strong><p>参考答案：${esc(q.answer)}。${esc(q.explanation || '')}</p></div>`:''}<div class="card-bottom">${submitted?`<button type="button" class="primary" data-action="${qi+1<questions.length?'next':'lesson'}">${qi+1<questions.length?'下一题':'回到讲解'}<span>→</span></button>`:'<button class="primary" type="submit" id="submit-answer" '+(!selected?'disabled':'')+'>看答案 <span>→</span></button>'}<button class="quiet" type="button" data-action="lesson">${submitted?'继续看联系':'先看看讲解'}</button></div></form>`;
  requestAnimationFrame(drawConnections);
}
function searchResults(saved=false) {
  if(!graph)return;
  const query=$('search-input').value,subject=$('subject-filter').value,year=$('grade-filter').value;
  let nodes=filterConcepts(graph.nodes,{query,subject,grade:year,reviewIds:saved?state.review:null});
  if(!query&&!subject&&!year&&!saved){const ids=[active,'M_G3_NS_01','M_G3_NS_10','M_G4_GM_08','P_P2_17'];nodes=[...new Set(ids)].map(id=>byId.get(id)).filter(Boolean);}
  $('search-results').innerHTML=nodes.slice(0,30).map(n=>`<button class="search-result" data-concept="${esc(n.id)}"><span>${esc(title(n))}</span><small>${esc(SUBJECTS[n.subject]||'')} · ${esc(grade(n))}</small></button>`).join('')||`<p class="empty-copy">${saved?'还没有留到稍后学习的内容。':'没找到，试试换一个词。'}</p>`;
}
let savedMode=false;
function openSearch(saved=false) {
  if(!graph){toast('知识地图还在加载');return;}
  savedMode=saved;$('search-title').textContent=saved?'稍后再学':'找一个知识点';
  $('search-input').value='';$('subject-filter').value='';$('grade-filter').value='';
  searchResults(saved);$('search-dialog').showModal();
  $('search-input').focus();
}
function openDetails(){
  if(!payload)return;
  const n=payload.node,groups=groupNeighbors(graph,active,true);
  $('detail-title').textContent='内容说明';
  $('detail-body').className='dialog-copy';
  $('detail-body').innerHTML=`<p>这是一份学习实验。讲解、题目和知识联系由 AI 辅助整理，尚待教育专业人员复核。单题作答不代表完整掌握。</p><h3>${esc(title(n))}的资料来源</h3><p>${esc(n.source||'暂无具体来源记录')}${n.src_page?`，参考页码 P${esc(n.src_page)}。`:''}OCR 片段与页码对应仍待核对。</p><details><summary>查看原始片段</summary><blockquote>${esc(n.content_req||'暂无片段')}</blockquote><a href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank" rel="noopener noreferrer">打开课标资源目录 ↗</a></details><h3>相关知识</h3>`+
    Object.values(groups).flat().map(row=>row.edges.map(e=>`<button class="edge-link" data-edge="${esc(e.id)}">${esc(title(byId.get(e.from)))} ${e.rel==='relates_to'?'↔':'→'} ${esc(title(byId.get(e.to)))}<span style="float:right;color:#929b8a">查看说明</span></button>`).join('')).join('');
  $('detail-dialog').showModal();
}
async function openEdge(id){
  const edge=graph.edges.find(e=>e.id===id);if(!edge)return;
  const focus=active;$('detail-title').textContent='这两个知识点的联系';
  $('detail-body').innerHTML='<p class="empty-copy">正在打开说明…</p>';
  try{
    const [detail,reviewData]=await Promise.all([getJSON('./data/learning_relations.json'),getJSON('./data/relation_reviews.json')]);
    if(focus!==active)return;
    const recorded=detail.edges.find(e=>e.id===id);
    const review=reviewData.reviews.find(r=>r.edge_id===id);
    $('detail-body').innerHTML=`<h3>${esc(title(byId.get(edge.from)))} ${edge.rel==='relates_to'?'↔':'→'} ${esc(title(byId.get(edge.to)))}</h3><p>${esc(recorded?.reason||recorded?.rationale||'暂没有具体的关系说明。')}</p><p>${review?'已有人工审核记录，仍不能据此诊断个人的学习缺口。':'这条联系还没有人工审核记录，只供探索参考。'}</p><button class="quiet" data-action="details-back">← 返回内容说明</button>`;
  }catch{$('detail-body').innerHTML='<p>这条联系的说明暂时无法加载。</p><button class="quiet" data-action="details-back">返回</button>';}
}
document.addEventListener('click',event=>{
  const b=event.target.closest('button');if(!b)return;
  if(b.dataset.close){$(b.dataset.close).close();return;}
  if(b.dataset.concept){openConcept(b.dataset.concept);return;}
  if(b.dataset.edge){openEdge(b.dataset.edge);return;}
  if(b.dataset.part){part=+b.dataset.part;$('fraction-figure').innerHTML=fractionSVG(part);$('equation').innerHTML=fractionEquation(part);document.querySelector('.explanation').textContent=fractionCopy(part);document.querySelectorAll('[data-part]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));return;}
  const action=b.dataset.action;
  if(action==='reload')location.reload();
  if(action==='search')openSearch();
  if(action==='retry')openConcept(active,false);
  if(action==='practice'){view='practice';renderCard();}
  if(action==='lesson'){view='lesson';renderCard();}
  if(action==='next'){qi++;selected='';submitted=false;renderCard();}
  if(action==='details')openDetails();
  if(action==='details-back'){$('detail-dialog').close();openDetails();}
  if(action==='bookmark'){
    state.review=marked()?state.review.filter(id=>id!==active):[...state.review,active];save();
    toast(marked()?'已留到稍后学习':'已从稍后学习中移除');renderCard();
  }
});
document.addEventListener('change',event=>{
  if(event.target.name==='answer'){selected=event.target.value;$('submit-answer').disabled=false;}
  if(['subject-filter','grade-filter'].includes(event.target.id))searchResults(savedMode);
});
document.addEventListener('submit',event=>{
  if(event.target.id!=='answer-form')return;event.preventDefault();
  const q=questions[qi],correct=gradeChoice(q,selected);
  if(correct===null||submitted)return;
  submitted=true;state.attempts.push({conceptId:active,questionId:q.id,questionText:q.question,answerKey:q.answer,selected,correct,at:new Date().toISOString()});state.attempts=state.attempts.slice(-500);save();renderCard();
});
$('search-button').addEventListener('click',()=>openSearch());
$('explore-button').addEventListener('click',()=>openSearch());
$('saved-button').addEventListener('click',()=>openSearch(true));
$('search-input').addEventListener('input',()=>searchResults(savedMode));
$('search-input').addEventListener('keydown',event=>{if(event.key==='ArrowDown'){$('search-results').querySelector('button')?.focus();event.preventDefault();}});
$('about-button').addEventListener('click',openDetails);
$('notes-button').addEventListener('click',()=>{if(!payload)return;$('notes-concept').textContent=title(payload.node);$('notes-input').value=state.notes[active]||'';$('notes-dialog').showModal();});
$('notes-input').addEventListener('input',event=>{state.notes[active]=event.target.value;save();});
$('save-notes').addEventListener('click',()=>{$('notes-dialog').close();if(save())toast('笔记已保存');});
$('back-button').addEventListener('click',()=>{const id=trail.pop();if(id){active='';openConcept(id);}});
document.addEventListener('keydown',event=>{if(event.key==='/'&&!/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)&&!document.querySelector('dialog[open]')){event.preventDefault();openSearch();}});
window.addEventListener('popstate',()=>{const id=new URLSearchParams(location.search).get('concept')||startId;openConcept(id,false);});
$('subject-filter').insertAdjacentHTML('beforeend',Object.entries(SUBJECTS).map(([k,v])=>`<option value="${k}">${v}</option>`).join(''));
$('grade-filter').insertAdjacentHTML('beforeend',Array.from({length:9},(_,i)=>`<option value="${i+1}">${i+1} 年级</option>`).join(''));
new ResizeObserver(drawConnections).observe($('board'));
init();
