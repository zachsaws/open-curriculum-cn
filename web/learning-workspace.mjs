import {SUBJECTS,RELATIONS,STORAGE_KEY,escapeHTML as esc,filterConcepts,groupNeighbors,hasReviewRecord,eligibleQuestions,gradeChoice,initialState,restoreState} from './learning-core.mjs';

const $ = id => document.getElementById(id);
let graph, graphDigest, blocked = new Set(), reviews = [], nodeById = new Map();
let activeId = '', activePayload = null, activeTab = 'concept', activeEdge = null, loading = false, loadError = '';
let requestSerial = 0, indexSerial = 0, listLimit = 60, listView = 'all';
let showRelated = false, questions = [], questionIndex = 0, choice = null, submitted = false;
let scale = 1, translate = {x:0,y:0}, focusHistory = [], payloadCache = new Map(), relationPromise;
let mobileLayout = matchMedia('(max-width:720px)').matches;
let storageAvailable = true;
let userState;
try { userState = restoreState(localStorage.getItem(STORAGE_KEY)); } catch { userState = initialState(); storageAvailable = false; }

function announce(message) { $('announcer').textContent = message; }
function saveState(message='已保存在本机浏览器') {
  try { localStorage.setItem(STORAGE_KEY,JSON.stringify(userState)); storageAvailable = true; }
  catch { storageAvailable = false; }
  $('storage-status').textContent = storageAvailable ? message : '浏览器无法保存，本次笔记和记录仅在当前页面保留';
  $('storage-status').classList.toggle('error', !storageAvailable);
}
function meta(node) { return `${SUBJECTS[node.subject] || node.subject} · ${node.grade_start || '?'}–${node.grade_end || '?'} 年级`; }
function currentNode() { return nodeById.get(activeId); }
async function json(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`资源暂不可用 (${response.status})`);
  return response.json();
}
async function loadIndex() {
  const serial = ++indexSerial;
  $('concept-list').innerHTML = '<div class="skeleton-line"></div><div class="skeleton-line"></div>';
  $('results-summary').textContent = '正在加载概念…';
  try {
    const [text,flags,reviewData] = await Promise.all([
      fetch('./data/graph_lite.json').then(r=>{if(!r.ok) throw new Error('概念列表暂不可用'); return r.text();}),
      json('./data/quality_flags.json'),json('./data/relation_reviews.json')]);
    if (serial !== indexSerial) return;
    graph = JSON.parse(text);
    if (!Array.isArray(graph.nodes) || !Array.isArray(graph.edges) || !Array.isArray(flags.blocked_concept_ids) || !Array.isArray(reviewData.reviews)) throw new Error('学习数据格式需要检查');
    graphDigest = crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)).then(buffer=>Array.from(new Uint8Array(buffer),b=>b.toString(16).padStart(2,'0')).join(''));
    blocked = new Set(flags.blocked_concept_ids); reviews = reviewData.reviews;
    nodeById = new Map(graph.nodes.map(n=>[n.id,n]));
    $('total-count').textContent = graph.nodes.length.toLocaleString();
    renderList(); renderStarters();
    const requested = new URLSearchParams(location.search).get('concept');
    if (requested) selectConcept(requested,{push:false});
    else if (nodeById.has(userState.lastConcept)) selectConcept(userState.lastConcept,{replace:true});
    else renderMap();
    if (!storageAvailable) saveState();
  } catch(error) {
    $('results-summary').textContent = '加载失败';
    $('concept-list').innerHTML = '<div class="empty-state"><p>概念列表或质量状态暂不可用。</p><button class="secondary-button" data-action="retry-index">重新加载</button></div>';
    $('inspector-content').innerHTML = `<div class="empty-state"><h2>暂时无法打开工作台</h2><p>${esc(error.message)}。请检查网络后重试。</p><div class="action-row"><button class="primary-button" data-action="retry-index">重新加载</button></div></div>`;
  }
}
function renderStarters() {
  $('starter-concepts').innerHTML = ['M_G3_NS_10','M_G4_GM_08','P_P2_17'].filter(id=>nodeById.has(id)).map(id=>`<button data-concept="${esc(id)}">${esc(nodeById.get(id).title)} ↗</button>`).join('');
}
function renderList() {
  if (!graph) return;
  const matches = filterConcepts(graph.nodes,{query:$('concept-search').value,subject:$('subject-filter').value,grade:$('grade-filter').value,reviewIds:listView==='review'?userState.review:null});
  matches.sort((a,b)=>Number(b.id===activeId)-Number(a.id===activeId));
  $('results-summary').textContent = `${matches.length.toLocaleString()} 个概念${matches.length>listLimit?` · 先显示 ${listLimit} 个`:''}`;
  $('review-count').textContent = userState.review.filter(id=>nodeById.has(id)).length;
  $('concept-list').innerHTML = matches.slice(0,listLimit).map(n=>`<button class="concept-row ${n.id===activeId?'active':''}" data-concept="${esc(n.id)}" ${n.id===activeId?'aria-current="true"':''}><strong>${esc(n.title)}</strong><small>${esc(meta(n))}${blocked.has(n.id)?' · 暂停练习':''}</small></button>`).join('') || `<div class="empty-state"><p>${listView==='review'&&!userState.review.length?'还没有待复习概念。打开一个概念后即可添加。':'没有匹配的概念。可以换个词或清除筛选。'}</p><button class="quiet-button" data-action="clear-filters">清除筛选</button></div>`;
  if(matches.length>listLimit) $('concept-list').insertAdjacentHTML('beforeend','<button class="load-more" data-action="more">显示更多概念 ↓</button>');
}
function conceptPayload(id) {
  if (!payloadCache.has(id)) {
    payloadCache.set(id,json(`./data/concepts/${encodeURIComponent(id)}.json`).then(data=>{
      if(data.node?.id !== id || !Array.isArray(data.exercises)) throw new Error('概念详情格式需要检查');
      return data;
    }).catch(error=>{payloadCache.delete(id);throw error;}));
  }
  return payloadCache.get(id);
}
async function selectConcept(id,{push=true,replace=false}={}) {
  if (!graph) return;
  const previous = activeId;
  const serial = ++requestSerial;
  activeId = id; activePayload = null; activeEdge = null; activeTab='concept'; loadError=''; loading = true;
  questionIndex=0; choice=null; submitted=false; questions=[];
  if (previous && previous!==id && nodeById.has(previous)) focusHistory.push(previous);
  if (push || replace) {
    const url = new URL(location.href);url.searchParams.set('concept',id);
    history[replace?'replaceState':'pushState']({concept:id},'',url);
  }
  closeLibrary();
  renderList(); renderMap(); renderTabs(); renderInspector();
  if(!nodeById.has(id)) {
    loading=false;loadError='这个概念不在当前图谱中。请重新搜索。';
    $('breadcrumb').textContent='未找到概念';$('original-map').href='./explore.html';
    document.title='概念未找到 · 学习工作台';renderInspector();return;
  }
  document.title=`${currentNode().title} · 学习工作台`;
  $('breadcrumb').textContent=`${SUBJECTS[currentNode().subject] || ''} / ${currentNode().title}`;
  $('original-map').href=`./explore.html?concept=${encodeURIComponent(id)}`;
  userState.lastConcept=id;saveState();
  announce(`已打开${currentNode().title}`);
  try {
    const data=await conceptPayload(id);
    if(serial!==requestSerial) return;
    activePayload=data;loading=false;
    questions=eligibleQuestions(data.exercises,blocked.has(id));renderInspector();
  } catch(error) {if(serial!==requestSerial)return;loading=false;loadError=error.message;renderInspector();}
}
function renderTabs() {
  document.querySelectorAll('[data-tab]').forEach(button=>{
    const selected=button.dataset.tab===activeTab || (activeTab==='relations' && button.dataset.tab==='concept');
    button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;
  });
  $('inspector-content').setAttribute('aria-labelledby',activeTab==='relations'?'tab-concept':`tab-${activeTab}`);
}
function setTab(tab) { activeTab=tab;activeEdge=null;renderTabs();renderInspector(); }
function renderMap() {
  const n=currentNode();
  $('back-concept').disabled=!focusHistory.length;
  $('map-empty').hidden=!!n;
  $('map-world').innerHTML='';
  $('map-title').textContent=n?n.title:'从正在学的概念开始';
  $('map-subtitle').textContent=n?meta(n):'在左侧搜索，或选择一个例子。';
  if(!n) {fitMap();return;}
  const grouped=groupNeighbors(graph,n.id,showRelated);
  const items=[];
  const before=grouped.before.slice(0,3),after=grouped.after.slice(0,3),related=grouped.related.slice(0,3);
  const mobile = matchMedia('(max-width:720px)').matches;
  const center=mobile?{x:106,y:148}:{x:326,y:160};
  if(mobile){
    before.forEach((r,i)=>items.push({...r,x:210-before.length*66+i*132+10,y:38,side:'before'}));
    after.forEach((r,i)=>items.push({...r,x:210-after.length*66+i*132+10,y:296,side:'after'}));
    related.forEach((r,i)=>items.push({...r,x:210-related.length*66+i*132+10,y:410,side:'related'}));
  }else{
    const positions = [{items:before,x:35,side:'before'},{items:after,x:635,side:'after'}];
    for(const group of positions) group.items.forEach((r,i)=>items.push({...r,x:group.x,y:160+(i-(group.items.length-1)/2)*115,side:group.side}));
    related.forEach((r,i)=>items.push({...r,x:180+i*225,y:390,side:'related'}));
  }
  $('map-world').style.width=mobile?'420px':'860px';
  $('map-world').style.height=mobile?(related.length?'510px':'390px'):'520px';
  let svg=`<svg width="${mobile?420:860}" height="${mobile?(related.length?510:390):520}" aria-hidden="true">`;
  items.forEach(r=>{
    const x=mobile?r.x+56:r.side==='before'?217:r.side==='after'?635:r.x+91;
    const y=mobile?(r.side==='before'?r.y+78:r.y):r.side==='related'?390:r.y+43;
    const centerX=mobile?210:r.side==='before'?326:r.side==='after'?534:430;
    const centerY=mobile?(r.side==='before'?148:260):r.side==='related'?272:216;
    svg+=`<path class="connection ${r.side==='related'?'related':''}" d="M ${centerX} ${centerY} C ${(centerX+x)/2} ${centerY}, ${(centerX+x)/2} ${y}, ${x} ${y}"/>`;
  });
  svg+='</svg>';
  const label=(title,x,y)=>`<span class="node-group-label" style="left:${x}px;top:${y}px">${title}</span>`;
  const node=(n,x,y,current=false)=>`<button class="node ${current?'current':''}" data-map-node="${esc(n.id)}" style="left:${x}px;top:${y}px" aria-label="${current?'当前概念：':'打开概念：'}${esc(n.title)}">${current?'<span class="node-eyebrow">正在学习</span>':''}<strong>${esc(n.title)}</strong><small>${esc(meta(n))}</small></button>`;
  $('map-world').innerHTML=svg+label(`前置 / 进阶来源 · ${grouped.before.length}`,mobile?12:35,mobile?6:28)+label(`可继续探索 · ${grouped.after.length}`,mobile?12:635,mobile?271:28)+node(n,center.x,center.y,true)+items.map(r=>node(r.node,r.x,r.y)).join('')+
    (!before.length?`<span class="node-group-label" style="left:${mobile?12:35}px;top:${mobile?55:200}px;max-width:180px">暂无前置记录<br>不代表不需要基础</span>`:'')+
    (!after.length?`<span class="node-group-label" style="left:${mobile?12:635}px;top:${mobile?315:200}px;max-width:180px">暂无后续记录</span>`:'')+
    (related.length?label('关联探索 · 待核验',mobile?12:180,mobile?385:362):'');
  const total=Object.values(grouped).reduce((s,list)=>s+list.length,0), shown=items.length;
  $('map-caption').textContent=`直接相连 ${total} 个${total>shown?` · 图中展示 ${shown} 个，列表可看全部`:''}`;
  fitMap();
}
function applyTransform(){ $('map-world').style.transform=`translate(${translate.x}px,${translate.y}px) scale(${scale})`;$('zoom-level').textContent=`${Math.round(scale*100)}%`; }
function fitMap() {
  const box=$('map-viewport').getBoundingClientRect();
  const width=parseFloat($('map-world').style.width)||860,height=parseFloat($('map-world').style.height)||520;
  scale=Math.min(1,Math.max(.25,Math.min((box.width-16)/width,(box.height-10)/height)));
  translate={x:(box.width-width*scale)/2,y:(box.height-height*scale)/2};applyTransform();
}
function zoom(amount) {
  const box=$('map-viewport').getBoundingClientRect(),previous=scale;
  scale=Math.min(1.6,Math.max(.25,scale+amount));
  translate={x:box.width/2-(box.width/2-translate.x)*scale/previous,y:box.height/2-(box.height/2-translate.y)*scale/previous};applyTransform();
}
function statusBadge(edge) {return hasReviewRecord(edge,reviews)?'<span class="review-badge">有人工审核记录</span>':'<span class="review-badge">待复核</span>';}
function renderInspector() {
  const panel=$('inspector-content');
  if(!activeId)return;
  if(loading){panel.innerHTML='<span class="eyebrow">正在打开概念</span><div class="skeleton-text"></div><div class="skeleton-text"></div><div class="skeleton-text"></div>';return;}
  if(loadError){panel.innerHTML=`<div class="empty-state"><h2>暂时无法打开概念</h2><p>${esc(loadError)}</p><div class="action-row"><button class="secondary-button" data-action="retry-detail">重试详情</button><button class="quiet-button" data-action="open-library">查找其他概念</button></div></div>`;return;}
  if(activeEdge){renderEdge();return;}
  if(activeTab==='relations'){renderRelations();return;}
  const node=activePayload?.node;
  if(!node)return;
  if(activeTab==='source'){renderSource(node);return;}
  if(activeTab==='practice'){renderPractice();return;}
  const marked=userState.review.includes(node.id);
  const lastAttempt=userState.attempts.findLast(a=>a.conceptId===node.id);
  panel.innerHTML=`<span class="eyebrow">概念讲解</span><h2>${esc(node.title)}</h2><div class="meta">${esc(meta(node))} · ${esc(node.domain||'')}</div><div class="inspector-section"><p>${esc(node.teaching_voice||node.description||'暂无讲解内容。')}</p><div class="provenance">AI 辅助整理 · 待专业复核</div></div>
    ${blocked.has(node.id)?'<div class="inspector-section"><h3>内容正在复核</h3><p>年级与内容对应需要检查，暂不提供自测。</p></div>':''}
    <div class="action-row"><button class="primary-button" data-action="start-practice">练一题 <span aria-hidden="true">→</span></button><button class="secondary-button" data-action="toggle-review" aria-pressed="${marked}">${marked?'✓ 已加入待复习':'＋ 加入待复习'}</button></div>
    <div class="inspector-section"><div class="relation-summary"><h3>理解它的来处与去处</h3></div><p class="meta">看一条具体关系，再判断它是否有帮助。</p><button class="relation-row" data-action="relations"><strong>查看全部直接关系</strong><span class="arrow">↗</span><small>方向、关系理由与复核状态</small></button></div>
    ${lastAttempt?`<div class="inspector-section"><details><summary>上次作答 · ${lastAttempt.correct?'这题答对了':'这题需要回看'}</summary><p style="margin-top:12px">${esc(lastAttempt.questionText||'已记录的选择题')}</p><p class="meta">你的选项 ${esc(lastAttempt.selected)} · 当时参考答案 ${esc(lastAttempt.answerKey)}。这是单题记录。</p></details></div>`:''}
    <div class="inspector-section"><label for="learning-note"><h3>用自己的话记一下</h3></label><textarea id="learning-note" maxlength="6000" placeholder="我理解了什么？还有哪个问题？">${esc(userState.notes[node.id]||'')}</textarea><p class="meta">个人笔记只记录你的理解，不改变资料审核状态。</p></div>
    <div class="action-row"><button class="quiet-button" data-action="show-source">查看来源与原始片段 ↗</button></div>`;
}
function renderSource(node) {
  $('inspector-content').innerHTML=`<span class="eyebrow">来源与整理状态</span><h2>${esc(node.title)}</h2><div class="provenance">OCR / AI 整理 · 对应关系待核对</div><dl class="metadata-list"><dt>资料来源</dt><dd>${esc(node.source||'暂无来源记录')}</dd><dt>参考页码</dt><dd>${node.src_page?`P${esc(node.src_page)} · 原始记录，未核准`:'暂无页码记录'}</dd><dt>内容状态</dt><dd>${node.review_status==='pending'?'待专业复核':`原始状态：${esc(node.review_status||'未记录')}`}</dd></dl><div class="inspector-section"><h3>课标相关片段</h3><div class="evidence-block"><p>${esc(node.content_req||'暂无片段')}</p></div><p class="practice-note">下方链接打开资料目录，不能直接定位本片段。页码、OCR 文字与概念的对应仍需人工核对。</p><div class="action-row"><a class="secondary-button" href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank" rel="noopener noreferrer">打开课标资源目录 ↗</a></div></div><div class="inspector-section"><h3>学习要求参考</h3><p>${esc(node.academic_req||'暂无记录')}</p><p class="practice-note">这是现有数据中的整理文本，不等同于已核准的课标原文。</p></div><div class="inspector-section"><h3>发现不一致？</h3><p>可在个人笔记记录疑问。核对前保留不确定性，不把资料片段当作已证实的关系依据。</p><div class="action-row"><button class="quiet-button" data-action="back-concept-tab">返回讲解与笔记 →</button></div></div>`;
}
function renderRelations() {
  const groups=groupNeighbors(graph,activeId,true);
  const labels={before:'前置 / 进阶来源',after:'图谱中的后续记录',related:'关联探索'};
  let html=`<span class="eyebrow">直接关系</span><h2>${esc(currentNode().title)}</h2><p class="meta">每条关系都可以查看方向和记录依据。未经复核的连接供探索参考。</p>`;
  for(const [key,list]of Object.entries(groups)){
    html+=`<section class="inspector-section"><div class="relation-summary"><h3>${labels[key]}</h3><span>${list.length} 个概念</span></div>`;
    if(!list.length)html+=`<p class="small-empty">${key==='before'?'暂无前置记录，不代表不需要基础。':'暂无收录。'}</p>`;
    for(const row of list){
      html+=`<div class="relation-item"><button class="relation-row" data-concept="${esc(row.node.id)}"><strong>${esc(row.node.title)}</strong><span class="arrow">↗</span><small>${esc(meta(row.node))}</small></button>`;
      html+=row.edges.map(edge=>`<button class="quiet-button" data-edge="${esc(edge.id)}" aria-label="查看关系依据：${esc(nodeById.get(edge.from).title)}到${esc(nodeById.get(edge.to).title)}，${esc(RELATIONS[edge.rel])}">${esc(RELATIONS[edge.rel])} · 查看依据 ${hasReviewRecord(edge,reviews)?'◉':'◌'}</button>`).join('')+'</div>';
    }
    html+='</section>';
  }
  $('inspector-content').innerHTML=html;
}
function relationDetails(){
  if(!relationPromise)relationPromise=json('./data/learning_relations.json').then(async data=>{
    if(data.graph_sha256!==await graphDigest||!Array.isArray(data.edges))throw new Error('关系依据与当前图谱版本不一致');
    return new Map(data.edges.map(e=>[e.id,e]));
  }).catch(error=>{relationPromise=null;throw error;});
  return relationPromise;
}
async function renderEdge(){
  const edge=activeEdge, serial=requestSerial;
  const direction=`<div class="edge-direction">${esc(nodeById.get(edge.from)?.title)}<span>${edge.rel==='relates_to'?'↔':'→'}</span>${esc(nodeById.get(edge.to)?.title)}</div>`;
  const header=`<button class="quiet-button" data-action="relations">← 全部直接关系</button><div class="inspector-section"><span class="eyebrow">${esc(RELATIONS[edge.rel])}</span>${direction}${statusBadge(edge)}</div>`;
  $('inspector-content').innerHTML=header+'<div class="skeleton-text"></div><p class="meta">正在加载关系记录…</p>';
  try{
    const details=(await relationDetails()).get(edge.id);
    if(serial!==requestSerial||activeEdge?.id!==edge.id)return;
    const review=reviews.find(r=>r.edge_id===edge.id);
    $('inspector-content').innerHTML=header+`<div class="inspector-section"><h3>记录的关系理由</h3><div class="evidence-block"><p>${esc(details?.reason||details?.rationale||'暂无具体理由记录')}</p></div><dl class="metadata-list"><dt>来源标记</dt><dd>${esc(details?.source||'未记录')}</dd><dt>关系编号</dt><dd>${esc(edge.id)}</dd></dl><p class="practice-note">来源标记与模板理由不等于原始引用。请先核对具体教学内容，再将它用作学习建议。</p></div>`+
      (hasReviewRecord(edge,reviews)?`<div class="inspector-section"><h3>人工审核记录</h3><p>${esc(review.rationale)}</p><dl class="metadata-list"><dt>证据</dt><dd>${esc(review.evidence_source)}</dd><dt>定位</dt><dd>${esc(review.evidence_locator)}</dd><dt>审核者</dt><dd>${esc(review.reviewer_role)}</dd><dt>日期</dt><dd>${esc(review.reviewed_at)}</dd></dl></div>`:'<div class="inspector-section"><h3>还缺什么依据？</h3><p>暂无符合现有审核协议的人工记录。需要具体来源定位与学科教师的关系判断，才能用于可靠的复习建议。</p></div>')+
      '<div class="action-row"><button class="secondary-button" data-action="back-concept-tab">回到讲解记下疑问</button></div>';
  }catch(error){if(serial!==requestSerial||activeEdge?.id!==edge.id)return;$('inspector-content').innerHTML=header+`<div class="empty-state"><p>${esc(error.message)}</p><button class="secondary-button" data-action="retry-edge">重试关系依据</button></div>`;}
}
function renderPractice(){
  const panel=$('inspector-content');
  if(blocked.has(activeId)){panel.innerHTML='<div class="empty-state"><span class="eyebrow">练习暂缓</span><h2>先把内容核对清楚</h2><p>这个概念的年级与内容对应正在复核，暂不提供自测。你可以查看来源，并在笔记中留下问题。</p><div class="action-row"><button class="secondary-button" data-action="show-source">查看来源</button></div></div>';return;}
  if(!questions.length){panel.innerHTML='<div class="empty-state"><span class="eyebrow">题目尚未齐备</span><h2>暂无可计分选择题</h2><p>当前概念尚无满足答案契约的选择题。可以先阅读讲解，或到原练习页对照简答参考答案。</p><div class="action-row"><a class="secondary-button" href="./exercise.html?id='+encodeURIComponent(activeId)+'">查看原练习页 ↗</a></div></div>';return;}
  const q=questions[questionIndex],correct=submitted?gradeChoice(q,choice):null;
  const previous=userState.attempts.filter(a=>a.conceptId===activeId).length;
  panel.innerHTML=`<div class="question-head"><span>本概念 ${questions.length} 道选择题</span><span>${questionIndex+1} / ${questions.length}</span></div><form id="practice-form"><fieldset class="question-text"><legend>${esc(q.question)}</legend>${q.options.map((text,i)=>{const letter='ABCD'[i],isAnswer=letter===String(q.answer).trim();return `<label class="choice ${submitted&&isAnswer?'correct':submitted&&letter===choice&&!correct?'wrong':''}"><input type="radio" name="answer" value="${letter}" ${choice===letter?'checked':''} ${submitted?'disabled':''} required><span>${esc(text)}</span></label>`;}).join('')}</fieldset><div class="question-actions">${submitted?`<button type="button" class="secondary-button" data-action="next-question">${questionIndex+1<questions.length?'下一题 →':'再练这一组 ↺'}</button>`:'<button class="primary-button" type="submit" id="submit-choice" '+(!choice?'disabled':'')+'>提交并看解析 →</button>'}</div></form>`+
    (submitted?`<div class="feedback" role="status"><h3>${correct?'这题答对了':'这题需要回看'}</h3><p>你的选项：${esc(choice)} · 参考答案：${esc(q.answer)}</p><p style="margin-top:10px">${esc(q.explanation||'暂无解析，请与老师一起核对思路。')}</p><small>这是本题表现，不代表已经掌握或缺少某个前置概念。</small></div><div class="action-row"><button class="secondary-button" data-action="toggle-review">${userState.review.includes(activeId)?'✓ 已加入待复习':'＋ 加入待复习'}</button><button class="quiet-button" data-action="back-concept-tab">回看讲解与关系 →</button></div>`:'')+
    `<p class="practice-note">题目来自现有练习库，AI 辅助整理，尚待教师复核。只计分明确答案的选择题。${previous?` 本机已记录 ${previous} 次本概念作答。`:''}</p>`;
}
function syncLibrary(){
  const narrow=matchMedia('(max-width:1100px)').matches,open=$('library').classList.contains('open')&&narrow;
  $('library').inert=narrow&&!open;
  $('library').setAttribute('aria-hidden',String(narrow&&!open));
  $('workspace-main').inert=open;
  $('open-library').setAttribute('aria-expanded',String(open));
  $('drawer-backdrop').hidden=!open;
}
function closeLibrary(){ $('library').classList.remove('open');syncLibrary(); }
function openLibrary(){ $('library').classList.add('open');syncLibrary();$('concept-search').focus(); }
function toggleReview(){
  userState.review=userState.review.includes(activeId)?userState.review.filter(id=>id!==activeId):[...userState.review,activeId];
  saveState();renderList();renderInspector();announce(userState.review.includes(activeId)?'已加入待复习':'已移出待复习');
}

// Actions use stable IDs/data attributes, never generated inline JavaScript.
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.concept){selectConcept(button.dataset.concept);return;}
  if(button.dataset.edge){activeEdge=graph.edges.find(e=>e.id===button.dataset.edge);activeTab='relations';renderTabs();renderInspector();return;}
  if(button.dataset.tab){setTab(button.dataset.tab);return;}
  if(button.dataset.view){listView=button.dataset.view;listLimit=60;document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});renderList();return;}
  const action=button.dataset.action;
  if(action==='retry-index')loadIndex();
  if(action==='retry-detail')selectConcept(activeId,{push:false});
  if(action==='retry-edge')renderEdge();
  if(action==='open-library')openLibrary();
  if(action==='more'){listLimit+=60;renderList();}
  if(action==='clear-filters'){$('concept-search').value='';$('subject-filter').value='';$('grade-filter').value='';listLimit=60;renderList();}
  if(action==='relations')setTab('relations');
  if(action==='show-source')setTab('source');
  if(action==='start-practice')setTab('practice');
  if(action==='back-concept-tab')setTab('concept');
  if(action==='toggle-review')toggleReview();
  if(action==='next-question'){questionIndex=(questionIndex+1)%questions.length;choice=null;submitted=false;renderPractice();}
});
document.addEventListener('input',event=>{
  if(event.target.id==='concept-search'){listLimit=60;renderList();}
  if(event.target.id==='learning-note' && activeId){userState.notes[activeId]=event.target.value;saveState('笔记已保存在本机浏览器');}
});
document.addEventListener('change',event=>{
  if(['subject-filter','grade-filter'].includes(event.target.id)){listLimit=60;renderList();}
  if(event.target.name==='answer'){choice=event.target.value;$('submit-choice').disabled=false;}
});
document.addEventListener('submit',event=>{
  if(event.target.id!=='practice-form')return;event.preventDefault();
  const q=questions[questionIndex],correct=gradeChoice(q,choice);
  if(correct===null||submitted)return;
  submitted=true;
  // Keep item-level evidence separate from the old diagnostic history store.
  userState.attempts.push({conceptId:activeId,questionId:q.id,questionText:q.question,answerKey:q.answer,selected:choice,correct,at:new Date().toISOString()});
  userState.attempts=userState.attempts.slice(-500);saveState('本题作答已保存在本机浏览器');renderPractice();announce(correct?'这题答对了，解析已展开':'这题需要回看，解析已展开');
});
$('subject-filter').insertAdjacentHTML('beforeend',Object.entries(SUBJECTS).map(([key,label])=>`<option value="${key}">${label}</option>`).join(''));
$('grade-filter').insertAdjacentHTML('beforeend',Array.from({length:9},(_,i)=>`<option value="${i+1}">${i+1} 年级</option>`).join(''));
$('related-toggle').addEventListener('change',event=>{showRelated=event.target.checked;renderMap();});
$('show-relations').addEventListener('click',()=>{if(activeId)setTab('relations');});
$('back-concept').addEventListener('click',()=>{const id=focusHistory.pop();if(id){const previous=activeId;selectConcept(id);if(focusHistory.at(-1)===previous)focusHistory.pop();$('back-concept').disabled=!focusHistory.length;}});
$('zoom-in').addEventListener('click',()=>zoom(.1));$('zoom-out').addEventListener('click',()=>zoom(-.1));$('fit-map').addEventListener('click',fitMap);
$('open-library').addEventListener('click',openLibrary);$('close-library').addEventListener('click',()=>{closeLibrary();$('open-library').focus();});$('drawer-backdrop').addEventListener('click',closeLibrary);
window.addEventListener('popstate',()=>{const id=new URLSearchParams(location.search).get('concept');if(id)selectConcept(id,{push:false});else{requestSerial++;activeId='';activePayload=null;activeEdge=null;loading=false;loadError='';$('breadcrumb').textContent='从一个概念开始';$('original-map').href='./explore.html';renderMap();renderList();$('inspector-content').innerHTML='<div class="inspector-welcome"><h2>从一个概念开始</h2><p>在左侧查找概念，或从图中的例子继续。</p></div>';}});
document.addEventListener('keydown',event=>{
  const editing=/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||'');
  if(event.key==='/'&&!editing){event.preventDefault();if(innerWidth<=1100)openLibrary();else $('concept-search').focus();}
  if(event.key==='Escape'){closeLibrary();if(document.activeElement?.closest('.library')&&innerWidth<=1100)$('open-library').focus();}
  if(event.target.matches('[role=tab]')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
    event.preventDefault();const tabs=[...document.querySelectorAll('[data-tab]')],i=tabs.indexOf(event.target);
    const next=event.key==='Home'?0:event.key==='End'?2:(i+(event.key==='ArrowRight'?1:2))%3;
    setTab(tabs[next].dataset.tab);tabs[next].focus();
  }
  if(event.key==='Tab'&&$('library').classList.contains('open')){
    const items=[...$('library').querySelectorAll('a,button,input,select')].filter(el=>!el.disabled&&el.getClientRects().length);
    const first=items[0],last=items.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
});

// Pointer movement changes only the current view, never curriculum data.
let gesture=null,suppressClick=false;
$('map-viewport').addEventListener('pointerdown',event=>{
  if(event.button!==0)return;
  const node=event.target.closest('[data-map-node]');
  gesture={x:event.clientX,y:event.clientY,original:{...translate},node,nodeX:node?parseFloat(node.style.left):0,nodeY:node?parseFloat(node.style.top):0,moved:false};
  if(node&&node.classList.contains('current')){gesture=null;return;}
  $('map-viewport').setPointerCapture(event.pointerId);
});
$('map-viewport').addEventListener('pointermove',event=>{
  if(!gesture)return;const dx=event.clientX-gesture.x,dy=event.clientY-gesture.y;if(Math.hypot(dx,dy)>5)gesture.moved=true;if(!gesture.moved)return;
  if(gesture.node){gesture.node.style.left=`${gesture.nodeX+dx/scale}px`;gesture.node.style.top=`${gesture.nodeY+dy/scale}px`;updateConnections();}
  else{translate={x:gesture.original.x+dx,y:gesture.original.y+dy};applyTransform();}
});
function updateConnections(){
  const nodes=[...$('map-world').querySelectorAll('.node:not(.current)')];
  const paths=$('map-world').querySelectorAll('path');
  const center=$('map-world').querySelector('.current');
  if(!center)return;
  const cx=parseFloat(center.style.left)+center.offsetWidth/2,cy=parseFloat(center.style.top)+center.offsetHeight/2;
  nodes.forEach((node,i)=>{const x=parseFloat(node.style.left)+node.offsetWidth/2,y=parseFloat(node.style.top)+node.offsetHeight/2;if(paths[i])paths[i].setAttribute('d',`M ${cx} ${cy} C ${(cx+x)/2} ${cy}, ${(cx+x)/2} ${y}, ${x} ${y}`);});
}
$('map-viewport').addEventListener('pointerup',event=>{
  if(!gesture)return;const clicked=gesture.node,moved=gesture.moved;gesture=null;suppressClick=true;
  if($('map-viewport').hasPointerCapture(event.pointerId))$('map-viewport').releasePointerCapture(event.pointerId);
  if(clicked&&!moved)selectConcept(clicked.dataset.mapNode);
  setTimeout(()=>{suppressClick=false;},0);
});
$('map-viewport').addEventListener('pointercancel',()=>{gesture=null;});
$('map-viewport').addEventListener('click',event=>{const node=event.target.closest('[data-map-node]');if(node&&!suppressClick&&event.detail===0&&!node.classList.contains('current'))selectConcept(node.dataset.mapNode);});
$('map-viewport').addEventListener('wheel',event=>{if(event.ctrlKey||event.metaKey){event.preventDefault();zoom(event.deltaY<0?.08:-.08);}}, {passive:false});
new ResizeObserver(()=>{
  syncLibrary();
  const mobile=matchMedia('(max-width:720px)').matches;
  if(mobile!==mobileLayout){mobileLayout=mobile;renderMap();}else fitMap();
}).observe($('map-viewport'));
syncLibrary();
loadIndex();
