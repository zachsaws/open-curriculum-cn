import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CONCEPT_LESSONS,lessonForConcept,acceptedGlobeMessage} from '../web/v2/globe-contract.mjs';
import {LESSONS} from '../web/v2/curriculum.mjs';
const graph=JSON.parse(readFileSync(new URL('../web/data/graph_lite.json',import.meta.url)));
test('globe only routes explicit real graph concepts to existing curated lessons',()=>{
 const nodes=new Map(graph.nodes.map(n=>[n.id,n]));const lessons=new Set(LESSONS.map(l=>l.id));
 for(const [id,target] of Object.entries(CONCEPT_LESSONS)){assert.ok(nodes.has(id),id);assert.ok(lessons.has(target),target);}
 assert.equal(nodes.get('M_G3_NS_01').title,'分数意义');assert.equal(lessonForConcept('M_G3_NS_01'),'fraction');
 assert.equal(lessonForConcept('M_G3_NS_02'),'equal');assert.equal(lessonForConcept('M_G3_NS_09'),'percent');
 assert.equal(lessonForConcept('__proto__'),null);assert.equal(lessonForConcept('P_G12_EX_01'),null);assert.equal(lessonForConcept(undefined),null);
});
test('messages from another origin or window cannot navigate the product',()=>{
 const frame={},origin='http://127.0.0.1:4446';
 const e={source:frame,origin,data:{type:'occ:globe-learn',conceptId:'M_G3_NS_01',route:'javascript:alert(1)'}};
 assert.deepEqual(acceptedGlobeMessage(e,frame,origin),{type:'learn',route:'learn/fraction'});
 assert.equal(acceptedGlobeMessage({...e,origin:'https://other.example'},frame,origin),null);
 assert.equal(acceptedGlobeMessage({...e,source:{}},frame,origin),null);
 assert.equal(acceptedGlobeMessage(e,null,origin),null);
 assert.deepEqual(acceptedGlobeMessage({...e,data:{type:'occ:globe-learn',conceptId:'not-curated'}},frame,origin),{type:'learn',route:'topics'});
});
test('ready and selection state require the expected bounded contract',()=>{
 const frame={},origin='http://localhost';const receive=data=>acceptedGlobeMessage({source:frame,origin,data},frame,origin);
 assert.deepEqual(receive({type:'occ:globe-ready'}),{type:'ready'});
 assert.deepEqual(receive({type:'occ:globe-state',selected:false}),{type:'state',selected:false});
 assert.equal(receive({type:'occ:globe-state',selected:'false'}),null);assert.equal(receive({type:'unrecognized'}),null);assert.equal(receive(null),null);
});
