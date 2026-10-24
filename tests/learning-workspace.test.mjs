import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {filterConcepts,groupNeighbors,hasReviewRecord,eligibleQuestions,gradeChoice,restoreState,initialState,escapeHTML} from '../web/learning-core.mjs';
const data=async name=>JSON.parse(await readFile(new URL(`../web/data/${name}`,import.meta.url),'utf8'));
const graph=await data('graph_lite.json');
const full=await data('graph.json');
const flags=await data('quality_flags.json');

test('grade filtering uses metadata rather than the concept ID',()=>{
  assert.equal(filterConcepts(graph.nodes,{query:'M_G3_NS_01',grade:'3'}).length,0);
  assert.equal(filterConcepts(graph.nodes,{query:'M_G3_NS_01',grade:'5'})[0].title,'分数意义');
  assert.equal(filterConcepts(graph.nodes,{query:'分数',subject:'physics'}).length,0);
});
test('unreviewed concepts do not acquire an invented mastery or diagnosis',()=>{
  const groups=groupNeighbors(graph,'M_G3_NS_10');
  assert.equal(groups.before.length,3);
  assert.equal(groups.related.length,0);
  assert.ok(groupNeighbors(graph,'M_G3_NS_10',true).related.length>0);
  assert.equal(hasReviewRecord(groups.before[0].edges[0],[]),false);
});
test('parallel relationship types and reciprocal soft links retain evidence without duplicate neighbors',()=>{
  const sample={nodes:[{id:'a',title:'A'},{id:'b',title:'B'}],edges:[{id:'1',from:'a',to:'b',rel:'prerequisite'},{id:'2',from:'a',to:'b',rel:'progresses_to'},{id:'3',from:'a',to:'b',rel:'relates_to'},{id:'4',from:'b',to:'a',rel:'relates_to'}]};
  const grouped=groupNeighbors(sample,'b',true);
  assert.equal(grouped.before.length,1);assert.equal(grouped.before[0].edges.length,2);
  assert.equal(grouped.related.length,1);assert.equal(grouped.related[0].edges.length,2);
});
test('review records must match the existing protocol and prerequisite type',()=>{
  const edge={id:'x',rel:'prerequisite'};
  assert.equal(hasReviewRecord(edge,[{edge_id:'x'}]),false);
  const record={edge_id:'x',evidence_source:'source',evidence_locator:'p.1',reviewer_role:'teacher',reviewed_at:'2026-10-22',rationale:'specific rationale'};
  assert.equal(hasReviewRecord(edge,[record]),true);
  assert.equal(hasReviewRecord({...edge,rel:'relates_to'},[record]),false);
});
test('choices require a valid contract, no answer stays unscored, open responses stay unscored',()=>{
  const q={id:'q',type:'multiple_choice',question:'Question',options:['A','B','C','D'],answer:'D'};
  assert.equal(gradeChoice(q,null),null);assert.equal(gradeChoice(q,'A'),false);assert.equal(gradeChoice(q,'D'),true);
  assert.equal(gradeChoice({...q,type:'short_answer'},'D'),null);
  assert.deepEqual(eligibleQuestions([q],true),[]);
  assert.deepEqual(eligibleQuestions([{...q,answer:'AB'}]),[]);
});
test('all 23 held concepts are excluded from the workspace scored practice',()=>{
  for(const id of flags.blocked_concept_ids){const p=full.nodes.find(n=>n.id===id);assert.ok(p);assert.deepEqual(eligibleQuestions([{type:'multiple_choice',question:'held',options:['a','b','c','d'],answer:'A'}],true),[]);}
});
test('local state fails closed on malformed storage and escapes saved notes as text',()=>{
  for(const raw of [null,'{','[]','{"version":2}','{"version":2,"notes":[],"review":[],"attempts":[]}'])assert.deepEqual(restoreState(raw),initialState());
  const state=initialState();state.notes.M_G3_NS_01='<img src=x onerror=alert(1)>';
  const restored=restoreState(JSON.stringify(state));assert.equal(restored.notes.M_G3_NS_01,state.notes.M_G3_NS_01);
  assert.ok(!escapeHTML(restored.notes.M_G3_NS_01).includes('<img'));
});
test('relation payload is tied to the exact published lite graph and original explanations',async()=>{
  const derived=await data('learning_relations.json');
  const bytes=await readFile(new URL('../web/data/graph_lite.json',import.meta.url));
  assert.equal(derived.graph_sha256,createHash('sha256').update(bytes).digest('hex'));
  const byId=new Map(full.edges.map(e=>[e.id,e]));assert.equal(derived.edges.length,graph.edges.length);
  for(const edge of derived.edges){assert.equal(edge.reason,byId.get(edge.id).reason);assert.equal(edge.source,byId.get(edge.id).source);}
});
test('all published concepts have matching lazy payloads and a well-formed eligible question set',async()=>{
  for(const node of graph.nodes){
    const payload=await data(`concepts/${node.id}.json`);assert.equal(payload.node.id,node.id);
    const questions=eligibleQuestions(payload.exercises,flags.blocked_concept_ids.includes(node.id));
    for(const q of questions){assert.equal(q.concept_id,node.id);assert.equal(gradeChoice(q,q.answer),true);}
  }
});
