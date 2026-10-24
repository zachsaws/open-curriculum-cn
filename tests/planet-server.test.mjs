import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {createPlanetServer,validRequest,buildMessages} from '../tools/serve_planet.mjs';
const payload={topic:'shadow',question:'光线升高时影子为什么变短？',model:{angle:60,height:1},observations:[{model:{angle:30,height:1}}]};
async function withServer(options,fn){const s=createPlanetServer(options);s.listen(0,'127.0.0.1');await once(s,'listening');const base=`http://127.0.0.1:${s.address().port}`;try{await fn(base);}finally{s.closeAllConnections();await new Promise(resolve=>s.close(resolve));}}
const post=(base,body,headers={})=>fetch(base+'/api/guide',{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(body)});
test('AI schema rejects unsupported subjects, empty queries, oversized text and malformed models',()=>{
 for(const p of [null,[],{}, {...payload,topic:'unreviewed-concept'},{...payload,question:''},{...payload,question:'x'.repeat(501)},{...payload,model:null}])assert.equal(validRequest(p),null);
 const valid=validRequest(payload);assert.equal(valid.topic.id,'shadow');const messages=buildMessages(valid);assert.match(messages[0].content,/NASA/);assert.match(messages[1].content,/0.58/);assert.match(messages[1].content,/1.73/);
});
test('unconfigured AI returns explicit unavailable status while static core remains usable',()=>withServer({apiKey:''},async base=>{
 assert.equal((await (await fetch(base+'/api/status')).json()).ai,false);const r=await post(base,payload);assert.equal(r.status,503);assert.equal((await r.json()).code,'ai_unavailable');assert.equal((await fetch(base+'/planet/index.html')).status,200);
}));
test('live adapter uses a server-only key and trusted endpoint; response includes fixed source evidence',()=>{
 let request;return withServer({apiKey:'local-test-key',fetchImpl:async(url,options)=>{request={url,options};return new Response(JSON.stringify({choices:[{message:{content:'保持木杆不变，试着比较两种光线角度。[1]'},finish_reason:'stop'}]}),{status:200});}},async base=>{
  const r=await post(base,payload),body=await r.json();assert.equal(r.status,200);assert.equal(body.mode,'live');assert.match(body.sources[0].url,/nasa/);assert.doesNotMatch(JSON.stringify(body),/local-test-key/);assert.equal(request.url,'https://ark.cn-beijing.volces.com/api/v3/chat/completions');assert.equal(request.options.headers.Authorization,'Bearer local-test-key');assert.equal(JSON.parse(request.options.body).thinking.type,'disabled');
 });
});
test('cross-site calls cannot spend provider requests',()=>withServer({apiKey:'test',fetchImpl:async()=>{throw new Error('must not call');}},async base=>{
 assert.equal((await post(base,payload,{Origin:'https://elsewhere.invalid'})).status,403);
 assert.equal((await post(base,payload,{'Sec-Fetch-Site':'cross-site'})).status,403);
}));
test('provider failures and truncated output cannot appear as a successful AI answer',async()=>{
 await withServer({apiKey:'test',fetchImpl:async()=>new Response('{}',{status:429})},async base=>{const r=await post(base,payload);assert.equal(r.status,502);assert.equal((await r.json()).code,'provider_busy');});
 await withServer({apiKey:'test',fetchImpl:async()=>new Response(JSON.stringify({choices:[{message:{content:'half answer'},finish_reason:'length'}]}),{status:200})},async base=>{const r=await post(base,payload);assert.equal(r.status,502);assert.equal((await r.json()).code,'incomplete_answer');});
});
test('server rejects large bodies, unknown APIs, non-JSON, and non-static writes',()=>withServer({apiKey:''},async base=>{
 assert.equal((await post(base,{...payload,question:'x'.repeat(10000)})).status,413);
 assert.equal((await fetch(base+'/api/nope')).status,404);
 assert.equal((await fetch(base+'/api/guide',{method:'POST',headers:{'Content-Type':'text/plain'},body:'x'})).status,415);
 assert.equal((await fetch(base+'/planet/index.html',{method:'POST'})).status,405);
}));
test('static root redirects to the product; private files and traversal stay outside the served tree',()=>withServer({apiKey:''},async base=>{
 const r=await fetch(base+'/',{redirect:'manual'});assert.equal(r.status,302);assert.equal(r.headers.get('location'),'/planet/');assert.equal((await fetch(base+'/.env')).status,403);assert.equal((await fetch(base+'/%2e%2e%2fapi%2fserver.py')).status,403);assert.equal((await fetch(base+'/api/server.py')).status,404);assert.equal((await fetch(base+'/planet/app.mjs')).headers.get('content-type'),'text/javascript; charset=utf-8');
}));
