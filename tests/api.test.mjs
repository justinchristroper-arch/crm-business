import test from 'node:test';
import assert from 'node:assert/strict';
import {request,setCsrf,ApiError,recordPayload,stageCode} from '../dist/api.js';

test('API mutations send session cookies and CSRF without storing bearer tokens',async()=>{
  const original=globalThis.fetch;let captured;
  globalThis.fetch=async (url,options)=>{captured={url,options};return {ok:true,json:async()=>({ok:true})};};
  try{setCsrf('test-csrf');await request('/contacts',{method:'POST',body:{name:'Demo'}});
    assert.equal(captured.url,'/api/contacts');assert.equal(captured.options.credentials,'same-origin');
    assert.equal(captured.options.headers['X-CSRF-Token'],'test-csrf');assert.equal(captured.options.headers.Authorization,undefined);
  }finally{globalThis.fetch=original;setCsrf('');}
});
test('server authorization and validation errors are propagated, never treated as saved',async()=>{
  const original=globalThis.fetch;
  try{
    globalThis.fetch=async()=>({ok:false,status:403,json:async()=>({detail:'Forbidden'})});
    await assert.rejects(()=>request('/users'),e=>e instanceof ApiError&&e.status===403);
    globalThis.fetch=async()=>({ok:false,status:422,json:async()=>({detail:[{loc:['body','closing_reason'],msg:'Required'}]})});
    await assert.rejects(()=>request('/opportunities'),/closing_reason: Required/);
    globalThis.fetch=async()=>{throw Error('Offline');};
    await assert.rejects(()=>request('/workspace'),e=>e.status===0);
  }finally{globalThis.fetch=original;}
});
test('frontend payload excludes role/revision/closed_at and maps stage to canonical backend command',()=>{
  const value=recordPayload('deals',{title:'Demo',contact:'c1',value:100,due:'2026-10-10',stage:'Gagal',closing_reason:'Budget',user_role:'admin',closed_at:'fake',revision:99});
  assert.equal(value.stage,'Lost');assert.equal(value.closing_reason,'Budget');assert.equal(value.closed_at,undefined);assert.equal(value.user_role,undefined);assert.equal(value.revision,undefined);
  assert.equal(stageCode('Berhasil'),'Won');
});
