import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {TOPICS,VERSION,BY_ID,conceptContext} from '../web/planet/content.mjs';
import {freshState,newSession,restore,cleanModel,measure,recordObservation,finish,canFinish,submitChallenge,addQuestion,evidence,reportMarkdown,guideContext,persist,esc} from '../web/planet/core.mjs';
import {experimentSVG} from '../web/planet/visuals.mjs';
test('shadow physics is monotonic, proportional, and correct at 45 degrees',()=>{
 assert.equal(measure('shadow',{angle:45,height:1}).length,1);
 for(const h of [.5,1,1.5,2]){let previous=Infinity;for(let a=15;a<=75;a++){const x=measure('shadow',{angle:a,height:h}).length;assert.ok(x<=previous);previous=x;assert.ok(x>0);}}
 assert.equal(measure('shadow',{angle:45,height:2}).length,2);
 assert.equal(measure('shadow',{angle:30,height:1}).length,1.73);
 assert.equal(measure('shadow',{angle:60,height:1}).length,.58);
});
test('fraction comparison includes the whole; equivalent fractions preserve actual length',()=>{
 assert.equal(measure('halves',{whole:20,parts:2,taken:1}).length,10);
 assert.equal(measure('halves',{whole:40,parts:2,taken:1}).length,20);
 assert.equal(measure('halves',{whole:40,parts:4,taken:2}).length,20);
 assert.equal(measure('halves',{whole:60,parts:2,taken:1}).length,30);
});
test('both dimensions scale and area scales quadratically, not linearly',()=>{
 for(const f of [1,2,3]){const x=measure('scale',{factor:f});assert.equal(x.area,(3*f)*(2*f));assert.equal(x.ratio,f*f);}
 assert.equal(measure('scale',{factor:3}).area,54);
});
test('out-of-range and malformed models cannot produce nonfinite experiment values',()=>{
 for(const t of TOPICS)for(const raw of [null,[],{angle:Infinity,height:-9,parts:100,taken:100,whole:1e9,factor:Infinity},{angle:'bad',height:{},factor:'x'}]){
  const data=measure(t.id,raw);for(const v of Object.values(data))if(typeof v==='number')assert.ok(Number.isFinite(v));
 }
 assert.throws(()=>cleanModel('unknown',{}));
});
test('completion requires a guess, distinct observations, own explanation and a submitted choice',()=>{
 const s=newSession('shadow');assert.equal(finish(s),false);s.guess='光源的位置';assert.equal(recordObservation(s),true);assert.equal(recordObservation(s),false);s.model.angle=60;assert.equal(recordObservation(s),true);assert.equal(finish(s),false);s.reflection='光线更贴近地面时影子更长。';assert.equal(finish(s),false);s.answer=0;assert.equal(finish(s),true);assert.equal(s.phase,'done');assert.ok(s.completedAt);
});
test('a wrong answer is recorded honestly, not represented as mastery',()=>{
 const state=freshState(),s=newSession('scale');state.sessions.scale=s;s.guess='两倍';recordObservation(s);s.model.factor=3;recordObservation(s);s.reflection='每行和行数都增加了。';s.answer=0;finish(s);const rows=evidence(state);assert.equal(rows[0].correct,false);assert.match(reportMarkdown(state),/可回看解释/);assert.doesNotMatch(reportMarkdown(state),/已掌握|提升了|能力超过/);
});
test('retry preserves prior attempts and rejects duplicate submissions',()=>{
 const s=newSession('scale');assert.equal(submitChallenge(s,0),true);assert.equal(submitChallenge(s,2),false);s.answer=null;assert.equal(submitChallenge(s,2),true);assert.deepEqual(s.attempts.map(a=>a.answer),[0,2]);assert.equal(submitChallenge(s,9),false);
});
test('refresh restores evidence and model; prior product versions remain isolated',()=>{
 const state=freshState(),s=newSession('halves');state.sessions.halves=s;s.guess='要看整体';s.model={whole:40,parts:4,taken:2};recordObservation(s);s.model.whole=60;recordObservation(s);s.reflection='整体大小也影响实际长度。';s.answer=1;finish(s);state.resume='halves';state.globe.position=[200,180,240];addQuestion(state,'为什么分母不同也能一样多？','halves');const out=restore(JSON.stringify(state));assert.deepEqual(out,state);assert.equal(restore(JSON.stringify({...state,version:'earlier'})).resume,null);
});
test('malformed saved data cannot forge a completed finding without evidence',()=>{
 const s={...freshState(),sessions:{shadow:{...newSession('shadow'),model:null,phase:'done',completedAt:'2026-10-23T00:00:00Z',reflection:'想法',answer:99,observations:[{model:{},at:'bad'}]}}};const out=restore(JSON.stringify(s));assert.equal(out.sessions.shadow.completedAt,null);assert.notEqual(out.sessions.shadow.phase,'done');assert.equal(out.sessions.shadow.answer,null);assert.equal(canFinish(out.sessions.shadow),false);assert.equal(restore('broken').version,VERSION);
});
test('questions are bounded, deduplicated and not automatically diagnosed',()=>{
 const state=freshState();assert.equal(addQuestion(state,'   '),null);const q=addQuestion(state,'为什么？','shadow');assert.equal(addQuestion(state,'为什么？','shadow').id,q.id);addQuestion(state,'x'.repeat(800));assert.equal(state.questions[1].text.length,300);assert.equal(state.questions[1].topic,null);assert.equal(state.questions[1].resolved,false);
});
test('storage write failure preserves in-memory exploration and report export',()=>{
 const state=freshState();state.sessions.shadow=newSession('shadow');state.sessions.shadow.guess='想试试';assert.equal(persist(state,()=>{throw new Error('quota');}),false);assert.match(reportMarkdown(state),/想试试/);let saved;assert.equal(persist(state,raw=>saved=raw),true);assert.equal(restore(saved).sessions.shadow.guess,'想试试');
});
test('report is built from actual records including original reflection and observation values',()=>{
 const state=freshState(),s=newSession('shadow');state.sessions.shadow=s;s.guess='高的杆子可能影子长';s.model={angle:45,height:2};recordObservation(s);s.reflection='这是我的原话。';const text=reportMarkdown(state);assert.match(text,/高的杆子可能影子长/);assert.match(text,/这是我的原话。/);assert.match(text,/木杆高 2 米，影子长约 2 米/);assert.match(text,/尚未作答/);assert.match(text,/NASA/);assert.doesNotMatch(text,/本题答对/);
});
test('downloaded report renders user text literally instead of activating Markdown or HTML',()=>{
 const state=freshState(),s=newSession('shadow');state.sessions.shadow=s;s.guess='<img src=x>';s.reflection='![image](https://elsewhere.invalid)\n# fake heading';addQuestion(state,'[click](https://elsewhere.invalid)');const text=reportMarkdown(state);assert.doesNotMatch(text,/(?<!\\)<img|!\[image\]|\n# fake heading|^- \[click\]/m);assert.match(text,/\\<img/);
});
test('AI context omits saved private notes, family report, and unrelated question history',()=>{
 const s=newSession('shadow');s.reflection='do not send this reflection';s.guess='do not send this guess';for(let a=20;a<=60;a+=10){s.model.angle=a;recordObservation(s);}const context=guideContext('shadow',s,'为什么会这样？');assert.equal(context.observations.length,3);assert.doesNotMatch(JSON.stringify(context),/do not send/);assert.equal(context.topic,'shadow');assert.throws(()=>guideContext('nope',s,'?'));
});
test('all curated concepts refer to actual graph nodes; source URLs use HTTPS',async()=>{
 const g=JSON.parse(await readFile(new URL('../web/data/graph_lite.json',import.meta.url),'utf8')),ids=new Set(g.nodes.map(n=>n.id));for(const t of TOPICS){assert.equal(t.relations.length,t.concepts.length);t.concepts.forEach(id=>assert.ok(ids.has(id),id));t.sources.forEach(s=>assert.match(s.url,/^https:\/\//));assert.ok(t.challenge.answer<t.challenge.choices.length);}
});
test('unreviewed cross-subject graph edges cannot become student relation recommendations',async()=>{
 const g=JSON.parse(await readFile(new URL('../web/data/graph_lite.json',import.meta.url),'utf8'));const c=conceptContext(g,'P_P3_05');assert.equal(c.curated,false);assert.ok(!c.neighbours.some(x=>x.node.id==='CH_C6_04'));assert.ok(c.neighbours.every(x=>x.node.subject===c.node.subject&&x.reason===''));const known=conceptContext(g,'M_G3_NS_01');assert.equal(known.curated,true);assert.ok(known.neighbours.every(x=>x.reason.length>5));assert.equal(conceptContext(g,'not-a-concept'),null);
});
test('rendered SVGs retain finite geometry across supported experiment extremes',()=>{
 for(const a of [15,45,75])for(const h of [.5,1,2]){const html=experimentSVG('shadow',{angle:a,height:h});assert.doesNotMatch(html,/NaN|Infinity/);assert.match(html,/role="img"/);}
 for(const f of [1,2,3])assert.doesNotMatch(experimentSVG('scale',{factor:f}),/NaN|Infinity/);
 assert.equal(esc('<img src=x onerror=alert(1)>'),'&lt;img src=x onerror=alert(1)&gt;');
});

test('direct light manipulation maps the visible source to bounded physical angles',async()=>{const {lightAngleAt}=await import('../web/planet/core.mjs');assert.equal(lightAngleAt(1,176.26,126.26),45);assert.equal(lightAngleAt(2,254.71,30.96),75);assert.equal(lightAngleAt(.5,130.96,229.71),15);assert.equal(lightAngleAt(1,300,-500),75);assert.equal(lightAngleAt(1,-500,500),15);assert.equal(lightAngleAt(1,NaN,0),45);});

test('catalog accepts Chinese connective wording and connects a concept to its actual experiment',async()=>{const {searchCatalog}=await import('../web/planet/content.mjs'),graph=JSON.parse(await readFile(new URL('../web/data/graph_lite.json',import.meta.url),'utf8'));const result=searchCatalog(graph,' 分数的意义 ');assert.ok(result.matches.some(n=>n.id==='M_G3_NS_01'));assert.ok(result.topics.some(t=>t.id==='halves'));assert.equal(searchCatalog(graph,'光的反射定律').topics.length,0);assert.equal(searchCatalog(graph,'尚未收录的神秘对象').matches.length,0);});
