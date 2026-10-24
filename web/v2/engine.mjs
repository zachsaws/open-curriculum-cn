// Pure state helpers. Completion describes activity, never inferred mastery.
export const STORAGE_KEY='opencurriculum:product:v3';
export const newState=version=>({schema:1,contentVersion:version,started:false,lastLesson:'whole',resume:'learn/whole',completed:[],runs:[],notes:{},reviewCursor:0});
const safeId=v=>typeof v==='string'&&/^[a-z0-9_-]{1,90}$/.test(v);
export function restore(raw,version,questionIds,lessonIds){
  const empty=newState(version),allowedResume=new Set(['check-in','final','review','practice/review',...[...lessonIds].flatMap(id=>[`learn/${id}`,`practice/${id}`])]);
  try{
    const s=JSON.parse(raw);
    if(s?.schema!==1||s.contentVersion!==version)return empty;
    const runs=Array.isArray(s.runs)?s.runs.filter(r=>safeId(r?.id)&&['baseline','lesson','final','review'].includes(r.kind)&&safeId(r.target)&&Array.isArray(r.ids)&&r.ids.length>0&&r.ids.length<=40&&new Set(r.ids).size===r.ids.length&&r.ids.every(id=>questionIds.has(id))&&r.answers&&typeof r.answers==='object'&&!Array.isArray(r.answers)).map(r=>({...r,answers:Object.fromEntries(Object.entries(r.answers).filter(([id,a])=>r.ids.includes(id)&&/^[A-D]$/.test(a))),completedAt:typeof r.completedAt==='string'?r.completedAt:null})).slice(-40):[];
    return {...empty,started:s.started===true,resume:allowedResume.has(s.resume)?s.resume:empty.resume,lastLesson:lessonIds.has(s.lastLesson)?s.lastLesson:empty.lastLesson,completed:Array.isArray(s.completed)?[...new Set(s.completed.filter(id=>lessonIds.has(id)))]:[],runs,notes:s.notes&&typeof s.notes==='object'&&!Array.isArray(s.notes)?Object.fromEntries(Object.entries(s.notes).filter(([k,v])=>lessonIds.has(k)&&typeof v==='string').map(([k,v])=>[k,v.slice(0,4000)])): {},reviewCursor:Number.isSafeInteger(s.reviewCursor)&&s.reviewCursor>=0?s.reviewCursor:0};
  }catch{return empty;}
}
export function grade(question,answer){return question&&/^[A-D]$/.test(question.answer||'')&&/^[A-D]$/.test(answer||'')&&question.choices?.length===4?answer===question.answer:null;}
export function runComplete(run){return !!run&&Array.isArray(run.ids)&&run.ids.length>0&&run.ids.every(id=>/^[A-D]$/.test(run.answers[id]||''));}
export function runScore(run,byId){return run.ids.reduce((n,id)=>n+Number(grade(byId.get(id),run.answers[id])===true),0);}
export function latestRun(state,kind,target){return [...state.runs].reverse().find(r=>r.kind===kind&&r.target===target);}
export function wrongQuestionIds(state,byId){
  const latest=new Map();
  for(const r of state.runs)if(r.kind!=='baseline')for(const id of r.ids)if(r.answers[id])latest.set(id,r.answers[id]);
  return [...latest].filter(([id,a])=>grade(byId.get(id),a)===false).map(([id])=>id);
}
export function submit(run,id,answer,byId){
  if(!run?.ids.includes(id)||run.answers[id]||grade(byId.get(id),answer)===null)return false;
  run.answers[id]=answer;
  if(runComplete(run))run.completedAt=new Date().toISOString();
  return true;
}
export function reviewBatch(pool,cursor,size=4){if(!pool.length)return [];return Array.from({length:Math.min(size,pool.length)},(_,i)=>pool[(cursor+i)%pool.length]);}
export function fractionValues(parts,total){if(!Number.isInteger(parts)||!Number.isInteger(total)||total<1||parts<0||parts>total)throw new RangeError('Invalid fraction');return {fraction:`${parts}/${total}`,decimal:String(parts/total),percent:`${Number((parts*100/total).toFixed(4))}%`};}
export function escapeHTML(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
