import {acceptedGlobeMessage} from './globe-contract.mjs';
export function renderGlobeHero(continueTo,hasActivity){
  return `<section class="globe-hero" aria-label="探索知识全貌"><h1 class="sr-only">知识地图</h1><iframe id="knowledge-globe" title="可旋转、可点选的知识球体" data-src="../explore.html?embed=1&amp;surface=product"></iframe><div class="globe-home-actions"><a class="button" href="#/${hasActivity?continueTo:'unit'}">${hasActivity?'继续上次学习':'进入分数学习'}<span aria-hidden="true">→</span></a><a class="globe-topics-link" href="#/topics">学习主题 ↗</a></div><div class="globe-status" role="status"><span>正在打开知识球…</span><button type="button" hidden>重新打开球体</button></div><a class="globe-stage-next" href="#/topics">选择一个主题，开始学习 ↓</a></section>`;
}
export function mountGlobe(frame){
  if(!frame)return ()=>{};
  const hero=frame.closest('.globe-hero'),status=hero.querySelector('.globe-status'),retry=status.querySelector('button');
  let timer,ready=false,visible=true;
  const fail=()=>{if(!ready){status.hidden=false;status.querySelector('span').textContent='知识球暂时没有打开。也可以先进入学习主题。';retry.hidden=false;}};
  const receive=event=>{
    const d=acceptedGlobeMessage(event,frame.contentWindow,location.origin);if(!d)return;
    if(d.type==='ready'){ready=true;clearTimeout(timer);status.hidden=true;frame.contentWindow?.postMessage({type:'occ:globe-visibility',visible},location.origin);}
    if(d.type==='state')hero.classList.toggle('has-selection',d.selected);
    if(d.type==='learn')location.hash=`/${d.route}`;
  };
  const start=()=>{ready=false;hero.classList.remove('has-selection');status.hidden=false;retry.hidden=true;status.querySelector('span').textContent='正在打开知识球…';clearTimeout(timer);timer=setTimeout(fail,15000);frame.src=frame.dataset.src;};
  window.addEventListener('message',receive);
  retry.addEventListener('click',start);
  const observer=new IntersectionObserver(entries=>{for(const e of entries){visible=e.isIntersecting;frame.contentWindow?.postMessage({type:'occ:globe-visibility',visible},location.origin);}},{threshold:0});
  observer.observe(hero);start();
  return ()=>{clearTimeout(timer);window.removeEventListener('message',receive);retry.removeEventListener('click',start);observer.disconnect();};
}
