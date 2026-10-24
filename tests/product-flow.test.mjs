import test from 'node:test';
import assert from 'node:assert/strict';
import {CONTENT_VERSION as V,LESSONS,QUESTIONS,LINKS,BASELINE,TRANSFER,QUESTION_BY_ID as Q} from '../web/v2/curriculum.mjs';
import {newState,restore,grade,submit,runComplete,runScore,wrongQuestionIds,reviewBatch,fractionValues,escapeHTML} from '../web/v2/engine.mjs';
import {figureData,initialVisuals} from '../web/v2/figures.mjs';
const questionIds=new Set(Q.keys()),lessonIds=new Set(LESSONS.map(l=>l.id));
const run=(ids=['w1','w2'],kind='lesson')=>({id:'test-run',kind,target:'whole',ids,answers:{},cursor:0});
test('the whole unit has distinct start, lesson, transfer and review tasks for each objective',()=>{
 assert.equal(QUESTIONS.length,33);assert.equal(questionIds.size,33);
 const all=[...BASELINE,...TRANSFER,...LESSONS.flatMap(l=>[...l.practice,...l.review])];
 assert.equal(all.length,33);assert.equal(new Set(all).size,33);assert.deepEqual(new Set(all),questionIds);
 for(const l of LESSONS){assert.equal(l.practice.length,2);assert.equal(l.review.length,2);for(const id of [...l.practice,...l.review])assert.equal(Q.get(id).lesson,l.id);assert.equal(TRANSFER.filter(id=>Q.get(id).lesson===l.id).length,1);}
 for(const q of QUESTIONS){assert.ok(lessonIds.has(q.lesson));assert.equal(q.choices.length,4);assert.equal(new Set(q.choices).size,4);assert.match(q.answer,/^[A-D]$/);assert.ok(q.prompt&&q.explanation);}
 for(const r of LINKS){assert.ok(lessonIds.has(r.from)&&lessonIds.has(r.to));assert.ok(r.reason.length>10);}
});
test('no answer, invalid choices and malformed questions stay unscored; a stored answer cannot be changed',()=>{
 assert.equal(runComplete(run([])),false);const r=run();assert.equal(grade(Q.get('w1'),''),null);assert.equal(grade(Q.get('w1'),'Z'),null);assert.equal(grade({...Q.get('w1'),answer:'unknown'},'B'),null);
 assert.equal(submit(r,'w3','C',Q),false);assert.equal(submit(r,'w1','B',Q),true);assert.equal(submit(r,'w1','A',Q),false);assert.equal(r.answers.w1,'B');assert.equal(runComplete(r),false);
 assert.equal(submit(r,'w2','A',Q),true);assert.equal(runComplete(r),true);assert.equal(runScore(r,Q),1);assert.ok(r.completedAt);
});
test('restore retains a real interrupted session, notes and activity without sharing old workspace state',()=>{
 const s=newState(V);s.started=true;s.resume='practice/whole';s.notes.whole='自己的理解 <script>';s.runs=[run()];submit(s.runs[0],'w1','B',Q);
 const restored=restore(JSON.stringify(s),V,questionIds,lessonIds);assert.equal(restored.runs[0].answers.w1,'B');assert.equal(restored.started,true);assert.equal(restored.resume,'practice/whole');assert.equal(restored.notes.whole,s.notes.whole);assert.equal(restored.completed.length,0);
 assert.equal(restore('{broken',V,questionIds,lessonIds).runs.length,0);assert.equal(restore(JSON.stringify({version:2,review:['M_G3_NS_10']}),V,questionIds,lessonIds).runs.length,0);
});
test('incompatible content never masquerades as a current result; invalid records and HTML in notes are bounded',()=>{
 const s=newState('old');s.completed=['whole'];assert.equal(restore(JSON.stringify(s),V,questionIds,lessonIds).completed.length,0);
 const current=newState(V);current.runs=[run(['not-a-question'])];current.completed=['whole','whole','unknown'];current.notes={whole:'x'.repeat(6000),unknown:'hidden'};
 const clean=restore(JSON.stringify(current),V,questionIds,lessonIds);assert.equal(clean.runs.length,0);assert.deepEqual(clean.completed,['whole']);assert.equal(clean.notes.whole.length,4000);assert.equal(clean.notes.unknown,undefined);assert.equal(escapeHTML('<script>'), '&lt;script&gt;');
});
test('review uses the latest answer, excludes baseline guesses and rotates distinct practice batches',()=>{
 const s=newState(V),b=run(['b1'],'baseline');submit(b,'b1','A',Q);s.runs.push(b);const r=run();submit(r,'w1','A',Q);submit(r,'w2','B',Q);s.runs.push(r);assert.deepEqual(wrongQuestionIds(s,Q),['w1']);
 const retry=run(['w1'],'review');submit(retry,'w1','B',Q);s.runs.push(retry);assert.deepEqual(wrongQuestionIds(s,Q),[]);
 const pool=LESSONS.flatMap(l=>l.review);assert.deepEqual(reviewBatch(pool,0),pool.slice(0,4));assert.deepEqual(reviewBatch(pool,4),pool.slice(4,8));assert.equal(new Set(reviewBatch(['w1','w2'],8)).size,2);assert.deepEqual(reviewBatch([],1),[]);
});
const numeric=text=>{const match=text.replaceAll(' ','').match(/(-?\d+(?:\.\d+)?)(?:\/(\d+))?(%)?/);if(!match)return NaN;return +match[1]/(match[2]?+match[2]:1)/(match[3]?100:1);};
test('arithmetical answer keys agree with independently computed quantities and rational values',()=>{
 const targets={w1:20/2,w3:300/3,f1:3/8,f3:2/5,e1:1/2,e2:2/3,e3:3/4,e4:1/3,d1:25/100,d2:6/10,d3:3/4,d4:8,p1:25/100,p2:4/10,p3:80/4,p4:5/100,c1:Math.max(.5,.6,.55,.45),c4:75/100,b2:1/4,t2:5/6,t3:3/5,t4:7/10,t5:60/2,t6:Math.max(2/5,.45,40/100)};
 for(const [id,target] of Object.entries(targets)){const q=Q.get(id),values=q.choices.map(numeric);assert.ok(Math.abs(values['ABCD'.indexOf(q.answer)]-target)<1e-10,id);assert.equal(values.filter(x=>Math.abs(x-target)<1e-10).length,1,id);}
 const group=Q.get('c2');const groups=group.choices.map(s=>s.split('、').map(numeric));assert.equal(groups.filter(g=>g.every(v=>v===g[0])).length,1);assert.ok(groups['ABCD'.indexOf(group.answer)].every(v=>v===1/4));
 const order=Q.get('c3');assert.equal(order.choices.filter(s=>{const a=s.split('<').map(numeric);return a[0]<a[1]&&a[1]<a[2];}).length,1);assert.deepEqual(order.choices['ABCD'.indexOf(order.answer)].split('<').map(numeric),[.2,.25,.3]);
});
test('interactive figures keep quantities, decimal and percent representations in sync at endpoints',()=>{
 for(const n of [0,1,7,25,50,75,100]){const v=fractionValues(n,100);assert.equal(v.percent,`${n}%`);assert.equal(Number(v.decimal),n/100);}
 assert.throws(()=>fractionValues(5,4));const v=initialVisuals();
 for(const type of Object.keys(v)){const d=figureData(type,v[type]);assert.ok(d.svg.includes('role="img"'));assert.ok(d.caption&&d.controls&&d.equation);}
 assert.match(figureData('whole',{size:40}).caption,/两份一样长/);assert.match(figureData('whole',{size:20}).equation,/10 厘米/);assert.match(figureData('percent',{n:7}).equation,/7%/);assert.match(figureData('equal',{factor:4}).svg,/4\/8/);
});
