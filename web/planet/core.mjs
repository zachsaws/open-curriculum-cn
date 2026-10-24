import {VERSION,BY_ID,TOPICS,SUBJECTS} from './content.mjs';
export {escapeHTML as esc} from '../v2/engine.mjs';
export const STORAGE_KEY=`opencurriculum:planet:${VERSION}`;
export function persist(state,write){try{write(JSON.stringify(state));return true;}catch{return false;}}
const bounded=(v,min,max,step=1)=>Math.round(Math.min(max,Math.max(min,Number(v)||min))/step)*step;
export function cleanModel(id,raw={}){
 if(!raw||typeof raw!=='object'||Array.isArray(raw))raw={};
 if(id==='flagpole')return {angle:bounded(raw.angle??45,25,65,5),rodHeight:bounded(raw.rodHeight??1,.5,2,.5),poleHeight:[3,6,9,12].includes(+raw.poleHeight)?+raw.poleHeight:6,sameLight:raw.sameLight!==false};
 if(id==='shadow')return {angle:bounded(raw.angle??45,15,75),height:bounded(raw.height??1,.5,2,.5)};
 if(id==='halves'){const parts=[2,4,8].includes(+raw.parts)?+raw.parts:2;return {whole:bounded(raw.whole??20,10,60,10),parts,taken:bounded(raw.taken??1,1,parts)};}
 if(id==='scale')return {factor:bounded(raw.factor??2,1,3),width:3,height:2};
 throw new RangeError('Unknown exploration');
}
const round=n=>Math.round(n*100)/100;
export function measure(id,raw){const m=cleanModel(id,raw);
 if(id==='flagpole'){const rodAngle=m.sameLight?m.angle:(m.angle<=45?m.angle+20:m.angle-20),rodShadow=m.rodHeight/Math.tan(rodAngle*Math.PI/180),poleShadow=m.poleHeight/Math.tan(m.angle*Math.PI/180),ratio=poleShadow/rodShadow;return {...m,rodAngle,rodShadow:round(rodShadow),poleShadow:round(poleShadow),shadowRatio:round(ratio),estimate:round(ratio*m.rodHeight),valid:m.sameLight,unit:'米'};}
 if(id==='shadow')return {...m,length:round(m.height/Math.tan(m.angle*Math.PI/180)),unit:'米'};
 if(id==='halves')return {...m,length:round(m.whole*m.taken/m.parts),reference:20,unit:'厘米'};
 return {...m,columns:3*m.factor,rows:2*m.factor,cells:6*m.factor*m.factor,area:6*m.factor*m.factor,baseArea:6,ratio:m.factor*m.factor,unit:'平方厘米'};
}
export function observationText(id,raw){const m=measure(id,raw);
 if(id==='flagpole')return `木杆高 ${m.rodHeight} 米，光线 ${m.rodAngle}°，影长约 ${m.rodShadow} 米；旗杆光线 ${m.angle}°，影长约 ${m.poleShadow} 米；${m.valid?'相同光线，推算高度约 '+m.estimate+' 米':'光线不同，不能直接按影长倍数推算高度'}`;
 if(id==='shadow')return `光线角度 ${m.angle}°，木杆高 ${m.height} 米，影子长约 ${m.length} 米`;
 if(id==='halves')return `整体 ${m.whole} 厘米，取 ${m.taken}/${m.parts}，涂色长 ${m.length} 厘米；另一块长 20 厘米`;
 return `长和宽都放大 ${m.factor} 倍，面积 ${m.area} 平方厘米，是原来的 ${m.ratio} 倍`;
}
export const freshState=()=>({schema:1,version:VERSION,sessions:{},questions:[],globe:{subject:'all',position:null},resume:null});
const safeText=(v,n=800)=>typeof v==='string'?v.slice(0,n):'';
const date=v=>typeof v==='string'&&Number.isFinite(Date.parse(v))?v:null;
export function newSession(id,now=new Date().toISOString()){const t=BY_ID.get(id);if(!t)throw new RangeError('Unknown exploration');return {id,...(id==='flagpole'?{heightGuess:''}:{}),phase:'guess',entryQuestion:'',guess:'',model:{...t.defaultModel},observations:[],reflection:'',answer:null,attempts:[],completedAt:null,updatedAt:now,startedAt:now};}
export function restore(raw){const out=freshState();try{const s=JSON.parse(raw);if(s?.schema!==1||s.version!==VERSION)return out;
 for(const t of TOPICS){const r=s.sessions?.[t.id];if(!r||typeof r!=='object')continue;const a=newSession(t.id);a.phase=['guess','try','explain','challenge','done'].includes(r.phase)?r.phase:'guess';a.entryQuestion=safeText(r.entryQuestion,300);if(t.id==='flagpole')a.heightGuess=safeText(r.heightGuess,20);a.guess=safeText(r.guess,500);a.model=cleanModel(t.id,r.model);a.reflection=safeText(r.reflection,1200);a.answer=Number.isInteger(r.answer)&&r.answer>=0&&r.answer<3?r.answer:null;a.startedAt=date(r.startedAt)||a.startedAt;a.updatedAt=date(r.updatedAt)||a.updatedAt;
 const seen=new Set();a.observations=(Array.isArray(r.observations)?r.observations:[]).filter(o=>o&&typeof o.model==='object'&&date(o.at)).slice(-16).map(o=>({model:cleanModel(t.id,o.model),at:o.at})).filter(o=>{const k=JSON.stringify(o.model);if(seen.has(k))return false;seen.add(k);return true;});
 a.attempts=(Array.isArray(r.attempts)?r.attempts:[]).filter(x=>x&&Number.isInteger(x.answer)&&x.answer>=0&&x.answer<3&&date(x.at)).slice(-10).map(x=>({answer:x.answer,at:x.at}));
 a.completedAt=canFinish(a)?date(r.completedAt):null;if(a.phase==='done'&&!a.completedAt)a.phase='challenge';if(!a.guess.trim())a.phase='guess';else if(['explain','challenge'].includes(a.phase)&&a.observations.length<2)a.phase='try';else if(a.phase==='challenge'&&a.reflection.trim().length<4)a.phase='explain';out.sessions[t.id]=a;}
 out.questions=(Array.isArray(s.questions)?s.questions:[]).filter(q=>q&&/^q-[a-z0-9-]{1,70}$/.test(q.id)&&safeText(q.text,300).trim()).slice(-50).map(q=>({id:q.id,text:safeText(q.text,300),topic:BY_ID.has(q.topic)?q.topic:null,at:date(q.at)||new Date().toISOString(),resolved:q.resolved===true}));
 out.resume=BY_ID.has(s.resume)?s.resume:null;out.globe.subject=Object.hasOwn(SUBJECTS,s.globe?.subject)?s.globe.subject:'all';const p=s.globe?.position;if(Array.isArray(p)&&p.length===3&&p.every(x=>Number.isFinite(x)&&Math.abs(x)<1000)&&Math.hypot(...p)>100)out.globe.position=p;
 return out;}catch{return out;}}
export function recordObservation(session,now=new Date().toISOString()){
 const model=cleanModel(session.id,session.model),key=JSON.stringify(model);
 if(session.observations.some(o=>JSON.stringify(o.model)===key))return false;
 session.observations.push({model,at:now});session.observations=session.observations.slice(-16);session.updatedAt=now;return true;
}
export function canFinish(s){return !!s&&s.guess.trim().length>0&&s.observations.length>=2&&s.reflection.trim().length>=4&&Number.isInteger(s.answer)&&s.answer>=0&&s.answer<3;}
export function finish(s,now=new Date().toISOString()){if(!canFinish(s))return false;s.completedAt=now;s.updatedAt=now;s.phase='done';return true;}
export function submitChallenge(s,answer,now=new Date().toISOString()){if(!s||!Number.isInteger(answer)||answer<0||answer>2||s.answer!==null)return false;s.answer=answer;s.attempts.push({answer,at:now});s.attempts=s.attempts.slice(-10);s.updatedAt=now;return true;}
export function addQuestion(state,text,topic=null,now=new Date().toISOString()){
 const clean=safeText(text,300).trim();if(!clean)return null;
 const found=state.questions.find(q=>q.text===clean&&q.topic===topic);if(found)return found;
 const q={id:`q-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,7)}`,text:clean,topic:BY_ID.has(topic)?topic:null,at:now,resolved:false};state.questions.push(q);state.questions=state.questions.slice(-50);return q;
}
export function evidence(state){return TOPICS.filter(t=>state.sessions[t.id]).map(t=>{const s=state.sessions[t.id];return {topic:t,session:s,observations:s.observations.map(o=>({...o,text:observationText(t.id,o.model)})),correct:s.answer===null?null:s.answer===t.challenge.answer};});}
const mdText=v=>String(v).replace(/\\/g,'\\\\').replace(/([`*_[\]<>])/g,'\\$1').replace(/\r?\n/g,' ');
export function reportMarkdown(state){const rows=evidence(state);return ['# 问游 · 探索摘要','',`生成日期：${new Date().toLocaleDateString('zh-CN')}`,'本摘要来自当前浏览器的实际记录。观察是系统数值，猜想与解释为使用者原话；记录不代表完整掌握。','',...rows.flatMap(({topic:t,session:s,observations,correct})=>[`## ${t.title}`,`状态：${s.completedAt?'已保存发现':'探索中'}`,...(s.entryQuestion?[`我带来的问题：${mdText(s.entryQuestion)}`]:[]),`我的猜想：${mdText(s.guess)||'尚未填写'}`,...(s.id==='flagpole'&&s.heightGuess?[`最近一次高度估计（使用者填写）：${mdText(s.heightGuess)} 米`]:[]),'### 实验观察',...(observations.length?observations.map(o=>`- ${o.text}`):['尚无已记录的观察']),`### 我的解释`,mdText(s.reflection)||'尚未填写',`新情境作答：${s.answer===null?'尚未作答':`${t.challenge.choices[s.answer]}（${correct?'本题答对':'可回看解释'}）`}`,'### 内容来源',...t.sources.map(x=>`${x.title}：${x.url}`),'']), '## 留下的问题',...(state.questions.length?state.questions.map(q=>`- ${q.resolved?'[x]':'[ ]'} ${mdText(q.text)}`):['尚无保存的问题']),'','记录仅在当前设备；此文件由使用者主动下载。'].join('\n');}
export function guideContext(id,session,question){const t=BY_ID.get(id);if(!t)throw new RangeError('Unknown exploration');return {topic:id,question:safeText(question,500).trim(),model:cleanModel(id,session.model),observations:session.observations.slice(-3).map(o=>({model:cleanModel(id,o.model)}))};}

// Map a direct light-source drag in SVG coordinates to the supported experiment angle.
export function lightAngleAt(height,x,y){if(!Number.isFinite(x)||!Number.isFinite(y))return 45;const h=cleanModel('shadow',{height,angle:45}).height;return Math.max(15,Math.min(75,Math.round(Math.atan2(300-h*50-y,300-x)*180/Math.PI)));}
