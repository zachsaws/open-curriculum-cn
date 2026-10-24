import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
test('original Pages entry forwards within the project and preserves deep links',async()=>{
 const html=await readFile(new URL('../web/index.html',import.meta.url),'utf8');
 const script=html.match(/<script>(.*?)<\/script>/s)[1];
 for(const base of ['https://zachsaws.github.io/open-curriculum-cn/','https://zachsaws.github.io/open-curriculum-cn/index.html']){
  let destination;const location=new URL(base+'?from=shared#/question/shadow');location.replace=x=>destination=x;
  new Function('location',script)(location);
  assert.equal(destination,'https://zachsaws.github.io/open-curriculum-cn/planet/?from=shared#/question/shadow');
 }
 const legacy=await readFile(new URL('../web/legacy.html',import.meta.url),'utf8');assert.match(legacy,/explore.html/);assert.doesNotMatch(legacy,/location.replace/);
});
test('public static app does not offer an unconnected AI form',async()=>{
 const app=await readFile(new URL('../web/planet/app.mjs',import.meta.url),'utf8');
 assert.match(app,/实时 AI 问答尚未开放/);assert.match(app,/if\(\['localhost','127.0.0.1'\].includes\(location.hostname\)\)fetch/);
 assert.doesNotMatch(app,/fetch\('\/api\//);
});
