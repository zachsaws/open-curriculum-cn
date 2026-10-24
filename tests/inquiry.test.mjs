import test from 'node:test';
import assert from 'node:assert/strict';
import {questionRoute,paperAction,paperLengthAt,feedbackPayload,parseGuideReply,attachEntryQuestion,inquiryPhase,reflectionQuotes} from '../web/planet/inquiry-core.mjs';
import {freshState,newSession,restore,guideContext,measure,reportMarkdown} from '../web/planet/core.mjs';
import {validRequest,buildMessages,createPlanetServer} from '../tools/serve_planet.mjs';
import {once} from 'node:events';
test('natural questions route conservatively to real experiments, with explicit ambiguity and unsupported scope',()=>{
 assert.equal(questionRoute('为什么都是一半，拿到的却不一样多？').topic,'halves');assert.equal(questionRoute('1/2 和 2/4 一样多吗').topic,'halves');assert.equal(questionRoute('放大两倍面积也会翻倍吗').topic,'scale');assert.equal(questionRoute('太阳低一点影子为什么变长').topic,'shadow');
 assert.equal(questionRoute('分数是什么意思').kind,'clarify');assert.equal(questionRoute('影子为什么变长一半').topic,'shadow');
 for(const q of ['月亮为什么有一半是黑的','如何做分数加法','一半的概率是什么意思','恐龙为什么灭绝',''])assert.ok(['unsupported','empty'].includes(questionRoute(q).kind),q);
});
test('direct manipulation snaps to supported sizes and all suggested operations produce finite, valid experiments',()=>{
 assert.equal(paperLengthAt(240),20);assert.equal(paperLengthAt(400),40);assert.equal(paperLengthAt(-100),10);assert.equal(paperLengthAt(10000),60);
 for(const id of ['same-whole','different-whole','equivalent']){const a=paperAction(id),m=measure('halves',a.model);assert.ok(Number.isFinite(m.length));assert.ok(m.taken<=m.parts);}
 assert.equal(paperAction('__proto__'),null);assert.equal(paperAction('javascript:alert(1)'),null);const a=paperAction('same-whole');a.model.whole=999;assert.equal(paperAction('same-whole').model.whole,40);
});
test('ordinary help excludes private explanations; explicit explanation feedback is scoped and validated',()=>{
 const s=newSession('halves');s.guess='private guess';s.reflection='private explanation';const normal=guideContext('halves',s,'为什么？');assert.doesNotMatch(JSON.stringify(normal),/private/);
 const feedback=feedbackPayload(s);assert.equal(feedback.intent,'reflection');assert.equal(feedback.reflection,s.reflection);assert.doesNotMatch(JSON.stringify(feedback),/private guess/);const valid=validRequest(feedback);assert.ok(valid);assert.match(buildMessages(valid)[1].content,/submittedExplanation/);
 for(const p of [{...feedback,intent:'question'},{...feedback,intent:'other'},{...feedback,topic:'scale'},{...feedback,reflection:'x'.repeat(1201)},{...feedback,reflection:''}])assert.equal(validRequest(p),null);
});
test('AI suggestions resolve only to registered operations; no-op, cross-topic, malformed and missing-answer output cannot execute',()=>{
 assert.equal(parseGuideReply('{"answer":"比较同一整体。","actionId":"same-whole"}','halves',{whole:20,parts:2,taken:1}).action.model.whole,40);
 assert.equal(parseGuideReply('{"answer":"当前已经一样长。","actionId":"same-whole"}','halves',{whole:40,parts:2,taken:1}).action,null);
 assert.equal(parseGuideReply('{"answer":"试一试","actionId":"__proto__"}','halves').action,null);assert.equal(parseGuideReply('{"answer":"试一试","actionId":"same-whole"}','shadow').action,null);
 assert.doesNotMatch(parseGuideReply('{"answer":"建议比较，操作id为different-whole，看看差异。","actionId":null}','halves').answer,/操作id|different-whole/);
 assert.throws(()=>parseGuideReply('{"answer":','halves'));assert.throws(()=>parseGuideReply('{"actionId":"same-whole"}','halves'));
 assert.equal(parseGuideReply('旧版纯文本回复','shadow').answer,'旧版纯文本回复');
});
test('entry questions survive refresh and report export; another question never rewrites a saved exploration',()=>{
 const state=freshState(),s=newSession('halves');state.sessions.halves=s;attachEntryQuestion(state,s,'为什么都是一半却不同？');assert.equal(restore(JSON.stringify(state)).sessions.halves.entryQuestion,s.entryQuestion);assert.match(reportMarkdown(state),/为什么都是一半却不同/);
 attachEntryQuestion(state,s,'四分之二呢？');assert.equal(s.entryQuestion,'为什么都是一半却不同？');assert.equal(state.questions[0].text,'四分之二呢？');
 s.completedAt=new Date().toISOString();attachEntryQuestion(state,s,'另一个问题');assert.equal(s.entryQuestion,'为什么都是一半却不同？');assert.equal(state.questions.length,2);
});
test('actual HTTP adapter returns a trusted action without accepting model-provided arbitrary parameter values',async()=>{
 const server=createPlanetServer({apiKey:'synthetic-test-key',fetchImpl:async()=>new Response(JSON.stringify({choices:[{message:{content:'{"answer":"试着比较。","actionId":"equivalent","model":{"whole":999}}'},finish_reason:'stop'}]}),{status:200})});server.listen(0,'127.0.0.1');await once(server,'listening');
 try{const r=await fetch(`http://127.0.0.1:${server.address().port}/api/guide`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:'halves',question:'四分之二呢？',model:{whole:20,parts:2,taken:1}})});const data=await r.json();assert.equal(r.status,200);assert.deepEqual(data.action.model,{whole:40,parts:4,taken:2});assert.match(data.sources[0].url,/openstax/);assert.doesNotMatch(JSON.stringify(data),/synthetic-test-key|999/);}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});

test('explanation feedback requires an exact quote from the explanation voluntarily submitted',()=>{
 const reflection='20厘米的一半是10厘米，40厘米的一半是20厘米。';
 const valid=JSON.stringify({answer:'这两组数值说明了整体不同。',quote:'20厘米的一半是10厘米',actionId:null});assert.equal(parseGuideReply(valid,'halves',null,reflection).evidenceQuote,'20厘米的一半是10厘米');
 assert.throws(()=>parseGuideReply(JSON.stringify({answer:'你没有比较整体。',quote:'我没有比较整体',actionId:null}),'halves',null,reflection));
 assert.equal(parseGuideReply(JSON.stringify({answer:'这两组观察对应不同的整体。',actionId:null}),'halves',null,reflection).evidenceQuote,reflection);
});

test('continuous exploration progress reflects saved evidence without claiming completion before the learner saves',()=>{
 const s=newSession('halves');assert.equal(inquiryPhase(s),'guess');s.guess='比较整体';assert.equal(inquiryPhase(s),'try');s.observations=[{model:{whole:20,parts:2,taken:1}},{model:{whole:40,parts:2,taken:1}}];assert.equal(inquiryPhase(s),'explain');s.reflection='同样取一半，整体不同，长度不同。';assert.equal(inquiryPhase(s),'challenge');s.answer=1;assert.equal(inquiryPhase(s),'challenge');s.completedAt=new Date().toISOString();assert.equal(inquiryPhase(s),'done');
});

test('grounded feedback can select an original excerpt by ID without rewriting a quote',()=>{
 const text='界面核验：20厘米的一半是10厘米，40厘米的一半是20厘米。所以要先看整体。';const quotes=reflectionQuotes(text);assert.ok(quotes.every(q=>text.includes(q)));
 const reply=parseGuideReply(JSON.stringify({answer:'这两组长度是你比较的依据。',quoteId:1,actionId:null}),'halves',null,text);assert.equal(reply.evidenceQuote,'40厘米的一半是20厘米');
 assert.throws(()=>parseGuideReply(JSON.stringify({answer:'反馈',quoteId:999,actionId:null}),'halves',null,text));
 assert.ok(parseGuideReply(JSON.stringify({answer:'可以再用两组条件比较。',quoteId:0,actionId:null}),'halves',null,'整体不同').evidenceQuote);
});

test('a stalled provider is aborted and returns an explicit timeout instead of keeping a request open',async()=>{
 let aborted=false;const server=createPlanetServer({apiKey:'synthetic-test-key',timeoutMs:25,fetchImpl:async(_url,{signal})=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>{aborted=true;reject(new DOMException('Aborted','AbortError'));},{once:true}))});server.listen(0,'127.0.0.1');await once(server,'listening');
 try{const response=await fetch(`http://127.0.0.1:${server.address().port}/api/guide`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:'halves',question:'为什么一样多？',model:{whole:40,parts:2,taken:1}})});assert.equal(response.status,504);assert.equal((await response.json()).code,'ai_timeout');assert.equal(aborted,true);}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
