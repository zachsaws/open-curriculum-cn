import {lessonForConcept} from './globe-contract.mjs';
import {LESSON_BY_ID} from './curriculum.mjs';
// This adapter is dormant in the original full-screen graph.
if(new URLSearchParams(location.search).get('surface')==='product'&&parent!==window){
  const send=data=>parent.postMessage(data,location.origin);
  const card=document.querySelector('#card');
  const title=document.querySelector('#card-ctl'); title.setAttribute('role','heading'); title.setAttribute('aria-level','2');
  const summary=document.createElement('p'); summary.className='product-concept-summary';
  const original=document.createElement('a'); original.className='product-original-link';original.target='_blank';original.rel='noopener';original.textContent='查看原版概念资料 ↗';
  title.after(summary);card.append(original);
  const entry=document.createElement('button');
  entry.type='button';entry.className='card-action product-learning-entry';
  card.querySelector('.card-actions').prepend(entry);
  entry.addEventListener('click',()=>send({type:'occ:globe-learn',conceptId:window._currentNode?.id||null}));
  let selected=false,ready=false;
  function sync(){
    const next=document.body.classList.contains('has-selection');
    const lesson=LESSON_BY_ID.get(lessonForConcept(window._currentNode?.id));
    entry.textContent=lesson?'进入对应学习小节 →':'查看当前可学主题 →';
    summary.textContent=lesson?`${lesson.question} ${lesson.takeaway}`:'这个概念可以先查看知识联系；对应的完整学习单元还没有编排。';
    original.href=`./explore.html?concept=${encodeURIComponent(window._currentNode?.id||'')}`;
    card.querySelectorAll('a.card-action').forEach(a=>{if(a.id!=='card-share-btn')a.target='_blank';});
    if(next!==selected){selected=next;send({type:'occ:globe-state',selected});}
    if(!ready&&document.querySelector('#loading').classList.contains('done')){ready=true;send({type:'occ:globe-ready'});}
  }
  new MutationObserver(sync).observe(document.body,{attributes:true,attributeFilter:['class']});
  new MutationObserver(sync).observe(document.querySelector('#loading'),{attributes:true,attributeFilter:['class']});
  new MutationObserver(sync).observe(document.querySelector('#card-ctl'),{childList:true,subtree:true});
  document.querySelector('#three-canvas').setAttribute('aria-label','知识球：方向键旋转，加减号缩放，0 复位；也可以搜索概念。');
  const search=document.querySelector('#searchInput');search.placeholder='找一个知识点';
  search.addEventListener('keydown',event=>{if(event.key==='ArrowDown'){document.querySelector('#searchResults .r-item')?.focus();event.preventDefault();}});
  document.querySelector('#searchResults').addEventListener('keydown',event=>{
    const rows=[...document.querySelectorAll('#searchResults .r-item')],i=rows.indexOf(document.activeElement);
    if(event.key==='Escape'){document.querySelector('#searchResults').classList.remove('on');search.focus();}
    if(i>=0&&['ArrowDown','ArrowUp'].includes(event.key)){rows[(i+(event.key==='ArrowDown'?1:-1)+rows.length)%rows.length].focus();event.preventDefault();}
  });
  window.addEventListener('message',event=>{
    if(event.origin!==location.origin||event.source!==parent)return;
    if(event.data?.type==='occ:globe-visibility'&&typeof event.data.visible==='boolean')window.__occProductVisible=event.data.visible;
  });
  sync();
}
