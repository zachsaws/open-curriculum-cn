import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {cleanModel,measure,newSession,recordObservation,restore,freshState,reportMarkdown,finish} from '../web/planet/core.mjs';
import {questionRoute,fieldAction,parseGuideReply,feedbackPayload} from '../web/planet/inquiry-core.mjs';
import {experimentSVG} from '../web/planet/visuals.mjs';
import {fieldSVG,fieldAngleAt} from '../web/planet/fieldwork.mjs';
import {createPlanetServer,validRequest,buildMessages} from '../tools/serve_planet.mjs';
test('same-light shadow ratios recover height across all supported scenes, angles and reference heights',()=>{
 for(const poleHeight of [3,6,9,12])for(let angle=25;angle<=65;angle+=5)for(const rodHeight of [.5,1,1.5,2]){
  const m=measure('flagpole',{angle,poleHeight,rodHeight});assert.equal(m.estimate,poleHeight);assert.equal(m.valid,true);assert.ok(Math.abs(m.shadowRatio-poleHeight/rodHeight)<.011);assert.doesNotMatch(fieldSVG(m),/NaN|Infinity/);
 }
});
test('different light produces a counterexample and cannot be represented as a valid height calculation',()=>{
 for(const angle of [25,45,65]){const m=measure('flagpole',{angle,poleHeight:6,rodHeight:1,sameLight:false});assert.equal(m.valid,false);assert.notEqual(m.rodAngle,m.angle);assert.notEqual(m.estimate,m.poleHeight);}
 const state=freshState(),s=newSession('flagpole');state.sessions.flagpole=s;s.model.sameLight=false;recordObservation(s);assert.match(reportMarkdown(state),/光线不同，不能直接/);
});
test('AI actions keep chosen scene and reference height; unknown operations cannot execute',()=>{
 const model={angle:45,rodHeight:2,poleHeight:12,sameLight:true};const a=fieldAction('shared-low',model);assert.equal(a.model.angle,30);assert.equal(a.model.poleHeight,12);assert.equal(a.model.rodHeight,2);assert.equal(fieldAction('__proto__',model),null);
 assert.equal(parseGuideReply(JSON.stringify({answer:'先比较光线不同的情况。',actionId:'different-light'}),'flagpole',model).action.model.sameLight,false);
 assert.equal(parseGuideReply(JSON.stringify({answer:'当前已经相同。',actionId:'restore-light'}),'flagpole',model).action,null);
});
test('routing regressions distinguish astronomical causes, analogies and actual measurement intent',()=>{
 for(const q of ['为什么地球上一半是白天，一半是黑夜？','地球的一半为什么是亮的？','一半同学感冒是什么原因'])assert.equal(questionRoute(q).kind,'unsupported',q);
 const milk=questionRoute('为什么妈妈的半杯牛奶比我的一杯还多？');assert.equal(milk.kind,'clarify');assert.deepEqual(milk.topics,['halves']);assert.match(milk.note,/类比|容量/);
 assert.equal(questionRoute('怎么用影子测量旗杆高度？').topic,'flagpole');assert.equal(questionRoute('不爬上去能知道大树有多高吗').topic,'flagpole');
});
test('mixed prose and JSON is decoded into plain language; malformed internal output fails closed',()=>{
 const answer='当前没有昼夜实验，可以先留下这个问题。';const raw=answer+'\n'+JSON.stringify({answer,actionId:null,inScope:false});const parsed=parseGuideReply(raw,'halves');assert.equal(parsed.answer,answer);assert.equal(parsed.inScope,false);assert.doesNotMatch(parsed.answer,/answer|actionId|[{}]/);
 assert.equal(parseGuideReply(JSON.stringify({answer:raw,inScope:false}),'halves').answer,answer);
 assert.throws(()=>parseGuideReply('格式错误 {"answer":"未结束','halves'));
 assert.equal(parseGuideReply(JSON.stringify({answer:'题外问题',actionId:'shared-low',inScope:false}),'flagpole',{angle:45}).action,null);
});
test('new and legacy sessions survive refresh; field evidence and feedback remain explicitly scoped',()=>{
 const state=freshState();state.sessions.halves=newSession('halves');const s=newSession('flagpole');state.sessions.flagpole=s;s.entryQuestion='旗杆多高？';s.guess='比较影子';s.heightGuess='6';recordObservation(s);s.model.angle=30;recordObservation(s);s.reflection='需要两边光线相同，再比较影长的倍数。';s.answer=1;assert.equal(finish(s),true);
 const restored=restore(JSON.stringify(state));assert.deepEqual(restored,state);assert.match(reportMarkdown(state),/旗杆多高/);assert.match(reportMarkdown(state),/高度估计（使用者填写）：6 米/);const feedback=feedbackPayload(s);assert.ok(validRequest(feedback));assert.match(buildMessages(validRequest(feedback))[0].content,/光线不同/);
});
test('model boundaries and direct sunlight control never generate nonfinite measurements',()=>{
 const m=measure('flagpole',{angle:Infinity,rodHeight:-100,poleHeight:999});assert.ok(Object.values(m).filter(x=>typeof x==='number').every(Number.isFinite));assert.equal(cleanModel('flagpole',null).poleHeight,6);assert.doesNotMatch(experimentSVG('flagpole',{angle:45}),/data-field-sun|role="slider"/);
 for(const angle of [25,45,65])assert.equal(fieldAngleAt(440-300*Math.cos(angle*Math.PI/180),300-300*Math.sin(angle*Math.PI/180)),angle);
});
test('out-of-scope HTTP answer carries no source attribution or experiment action',async()=>{
 const server=createPlanetServer({apiKey:'fixture-only',fetchImpl:async()=>new Response(JSON.stringify({choices:[{message:{content:'当前不支持。\n{"answer":"当前不支持。","actionId":"shared-low","inScope":false}'},finish_reason:'stop'}]}))});server.listen(0,'127.0.0.1');await once(server,'listening');try{const r=await fetch(`http://127.0.0.1:${server.address().port}/api/guide`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:'flagpole',question:'昼夜为什么变化？',model:{angle:45}})});const data=await r.json();assert.equal(r.status,200);assert.equal(data.answer,'当前不支持。');assert.deepEqual(data.sources,[]);assert.equal(data.action,null);}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
