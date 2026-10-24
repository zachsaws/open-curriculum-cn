import {cleanModel,measure,guideContext,addQuestion} from './core.mjs';

export const PAPER_ACTIONS=Object.freeze({
 'same-whole':{label:'让两条纸带一样长',reason:'都设为 40 厘米，再比较各自的一半。',model:{whole:40,parts:2,taken:1}},
 'different-whole':{label:'比较 60 厘米的一半',reason:'保持都取一半，只改变左边整体。',model:{whole:60,parts:2,taken:1}},
 'equivalent':{label:'试试四分之二',reason:'同一条 40 厘米纸带，换一种平均分法。',model:{whole:40,parts:4,taken:2}}
});
export const paperAction=id=>Object.hasOwn(PAPER_ACTIONS,id)?{...PAPER_ACTIONS[id],id,model:{...PAPER_ACTIONS[id].model}}:null;
// Deliberately bounded local routing; no question is transmitted while typing.
export function questionRoute(raw){
 const q=String(raw||'').normalize('NFKC').trim().slice(0,300),s=q.replace(/\s/g,'');
 if(!s)return {kind:'empty'};
 if(/月亮|月球|月相|地球|半球|白天|黑夜|昼夜|自转|股票|概率|几率|分数加法|感冒|生病/.test(s))return {kind:'unsupported',note:'这个问题还没有对应的探索，可以先留下。'};
 if(/旗杆|旗桿|大树|高楼/.test(s)&&/高|测|影/.test(s))return {kind:'match',topic:'flagpole'};
 if(/半杯|半瓶|半碗|半桶/.test(s)&&/多|少|一样|不同|比|为什么/.test(s))return {kind:'clarify',topics:['halves'],note:'可以先用纸带比较“整体不同，一半也不同”。这是类比：杯子的容量还需要另外比较。'};
 const topics=[];
 const shadow=/影子|影长/.test(s)&&/长|短|光|太阳|高|变化|为什么|怎么/.test(s);
 if(shadow)topics.push('shadow');
 if(/一半|二分之一|1\/2|四分之二|2\/4|纸带/.test(s)&&(!shadow||/纸带|涂色/.test(s)))topics.push('halves');
 if(/面积/.test(s)&&/放大|倍|长宽|边长|变化|变大|变小/.test(s))topics.push('scale');
 if(topics.length===1)return {kind:'match',topic:topics[0]};
 if(topics.length>1)return {kind:'clarify',topics};
 if(/分数|整体/.test(s))return {kind:'clarify',topics:['halves']};
 return {kind:'unsupported'};
}
export const FIELD_ACTIONS={
 'shared-low':{label:'让两边光线都低一点',reason:'保持两根杆不变，把共同光线调到 30°。',patch:{angle:30,sameLight:true}},
 'shared-high':{label:'让两边光线都高一点',reason:'保持两根杆不变，把共同光线调到 60°。',patch:{angle:60,sameLight:true}},
 'different-light':{label:'试试光线不一样',reason:'让木杆单独换一种光线，看看按影长推算还可靠吗。',patch:{sameLight:false}},
 'restore-light':{label:'恢复相同光线',reason:'让两根杆回到相同方向的光线下比较。',patch:{sameLight:true}}
};
export function fieldAction(id,model){if(!Object.hasOwn(FIELD_ACTIONS,id))return null;const a=FIELD_ACTIONS[id];return {id,label:a.label,reason:a.reason,model:cleanModel('flagpole',{...cleanModel('flagpole',model),...a.patch})};}
export function actionsFor(topic,model){return topic==='halves'?Object.keys(PAPER_ACTIONS).map(paperAction):topic==='flagpole'?Object.keys(FIELD_ACTIONS).map(id=>fieldAction(id,model)):[];}
export function actionFor(topic,id,model){return topic==='halves'?paperAction(id):topic==='flagpole'?fieldAction(id,model):null;}
export function paperLengthAt(x){return cleanModel('halves',{whole:(x-80)/8}).whole;}
export function feedbackPayload(session){if(session.reflection.trim().length<4)throw new RangeError('Write an explanation first');return {...guideContext(session.id,session,'请对照我的实验记录，看看我的解释哪里清楚、哪里还需要补充。'),intent:'reflection',reflection:session.reflection.slice(0,1200)};}
// Some providers surround JSON with prose. Extract a complete object instead of
// exposing serialization or executable action fields in a child's answer.
function replyObject(text){
 const raw=String(text).trim().replace(/^```(?:json)?\s*|\s*```$/g,'');
 try{return {value:JSON.parse(raw)};}catch{}
 const start=raw.indexOf('{');if(start>=0){let depth=0,quoted=false,escaped=false;for(let i=start;i<raw.length;i++){const ch=raw[i];if(quoted){if(escaped)escaped=false;else if(ch==='\\')escaped=true;else if(ch==='"')quoted=false;}else if(ch==='"')quoted=true;else if(ch==='{')depth++;else if(ch==='}'&&!--depth){try{return {value:JSON.parse(raw.slice(start,i+1))};}catch{break;}}}}
 if(/[{}]|"(?:answer|actionId|quoteId)"/.test(raw))throw new TypeError('Malformed structured guide reply');
 return {plain:raw};
}
function cleanAnswer(raw){let answer=raw;const nested=raw.indexOf('{');if(nested>=0){const parsed=replyObject(raw);if(parsed.value?.answer&&parsed.value.answer!==raw)answer=parsed.value.answer;else throw new TypeError('Unexpected serialized reply');}return answer.slice(0,2500).replace(/\*\*/g,'').replace(/[，,]?\s*(?:操作\s*(?:id|编号)|actionId)\s*[为是:：=]*\s*(?:same-whole|different-whole|equivalent)[，,]?/gi,'').replace(/same-whole|different-whole|equivalent/g,id=>paperAction(id).label);}
export function parseGuideReply(text,topic,currentModel,reflection){
 const parsed=replyObject(text);if(parsed.plain!==undefined){if(reflection)throw new TypeError('Expected grounded feedback');return {answer:cleanAnswer(parsed.plain),action:null,inScope:true};}
 const value=parsed.value;if(!value||typeof value.answer!=='string'||!value.answer.trim())throw new TypeError('Invalid guide reply');
 const inScope=value.inScope!==false;let action=inScope?actionFor(topic,value.actionId,currentModel):null;if(action&&currentModel&&JSON.stringify(cleanModel(topic,currentModel))===JSON.stringify(action.model))action=null;
 let quoteKind='selected';if(reflection&&value.quoteId!==undefined){if(!Number.isInteger(value.quoteId))throw new TypeError('Invalid quote selection');value.quote=reflectionQuotes(reflection)[value.quoteId];}
 if(reflection&&value.quoteId===undefined&&value.quote===undefined){value.quote=reflection;quoteKind='submitted';}
 if(reflection&&(typeof value.quote!=='string'||value.quote.length<2||!reflection.includes(value.quote)))throw new TypeError('Ungrounded reflection quote');
 return {answer:cleanAnswer(value.answer),action,inScope,...(reflection?{evidenceQuote:value.quote,quoteKind}: {})};
}
export function paperFacts(raw){const m=measure('halves',raw);return `左边整体 ${m.whole} 厘米，取 ${m.taken}/${m.parts}，涂色 ${m.length} 厘米；右边整体 40 厘米，取 1/2，涂色 20 厘米。`;}

export function attachEntryQuestion(state,session,raw){const text=String(raw||'').trim().slice(0,300);if(!text)return false;if(session.completedAt||session.entryQuestion&&session.entryQuestion!==text){addQuestion(state,text,session.id);return false;}session.entryQuestion=text;return true;}

export function inquiryPhase(s){if(s.completedAt)return 'done';if(!s.guess.trim())return 'guess';if(s.observations.length<2)return 'try';if(s.reflection.trim().length<4)return 'explain';return 'challenge';}

export function reflectionQuotes(text){return String(text).split(/[，。；！？\n]/u).map(t=>t.trim().slice(0,100)).filter(t=>t.length>=2).slice(0,8);}
