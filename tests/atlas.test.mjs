import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {GUIDES,guideFor,subjectIndex,subjectCatalog,placeLabels} from '../web/planet/atlas.mjs';
import {TOPICS,SUBJECTS} from '../web/planet/content.mjs';
const graph=JSON.parse(await readFile(new URL('../web/data/graph_lite.json',import.meta.url),'utf8'));
test('the entire published catalog belongs to exactly one navigable subject and domain',()=>{
 const subjects=subjectIndex(graph);assert.equal(subjects.length,14);assert.deepEqual(new Set(subjects.map(s=>s.subject)),new Set(Object.keys(SUBJECTS)));
 const all=subjects.flatMap(s=>s.groups.flatMap(g=>g.nodes));assert.equal(all.length,graph.nodes.length);assert.equal(new Set(all.map(n=>n.id)).size,graph.nodes.length);
 for(const s of subjects){assert.ok(s.groups.length);assert.equal(s.groups.reduce((n,g)=>n+g.nodes.length,0),s.nodes.length);}
 assert.equal(subjectCatalog(graph,'math').topics.length,2);assert.equal(subjectCatalog(graph,'science').topics.length,2);assert.equal(subjectCatalog(graph,'history').topics.length,0);
});
test('available guides cover real experiments without upgrading the remaining catalog to lessons',()=>{
 const linked=new Set(TOPICS.flatMap(t=>t.concepts));assert.equal(Object.keys(GUIDES).length,10);
 for(const id of linked){const g=guideFor(id);assert.ok(g,id);assert.ok(graph.nodes.some(n=>n.id===id));assert.ok(g.idea&&g.example&&g.question&&g.scope);assert.match(g.source.url,/^https:\/\//);}
 assert.equal(guideFor('EN_G56_PH_02'),null);assert.equal(guideFor('__proto__'),null);assert.equal(guideFor(undefined),null);
 assert.ok(Object.keys(GUIDES).every(id=>linked.has(id)));
});
test('projected subject labels never overlap or expose a label on the back of the globe',()=>{
 const candidates=[{id:'math',front:.8,x:100,y:100,width:70},{id:'science',front:.7,x:105,y:105,width:70},{id:'history',front:-.2,x:300,y:200,width:60},{id:'art',front:.7,x:200,y:250,width:60},{id:'edge',front:.9,x:0,y:50,width:60}];
 assert.deepEqual([...placeLabels(candidates,400,300,'science')],['science','art']);
 assert.deepEqual([...placeLabels(candidates,400,300,'all')],['math','art']);
 assert.equal(placeLabels([],390,400,'math').size,0);
});
