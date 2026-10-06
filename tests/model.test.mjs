import test from 'node:test';
import assert from 'node:assert/strict';
import { seed, stats, moveDeal, dateKey, validateBackup } from '../dist/model.js';
test('metrics count closed deals in period while active pipeline remains independent',()=>{
  const data=seed();const result=stats(data,30);
  assert.equal(result.won,40000000);assert.equal(result.wonCount,2);
  assert.equal(result.pipeline,127500000);assert.equal(result.winRate,67);
  assert.equal(stats(data,90).won,50000000);
});
test('moving a deal updates closing date and reopening removes it from won metrics',()=>{
  const data=seed();assert.equal(moveDeal(data,'d1','Berhasil'),true);
  assert.equal(data.deals[0].closed,dateKey());assert.equal(stats(data,30).won,58000000);
  moveDeal(data,'d1','Proposal');assert.equal(data.deals[0].closed,'');assert.equal(stats(data,30).won,40000000);
  assert.equal(moveDeal(data,'d1','unknown'),false);
});
test('backup preserves valid relationships and rejects corrupt records',()=>{
  assert.equal(validateBackup(seed()).version,1);
  const bad=seed();bad.deals[0].contact='missing';assert.throws(()=>validateBackup(bad));
  const bad2=seed();bad2.tasks[0].done='true';assert.throws(()=>validateBackup(bad2));
  const bad3=seed();bad3.contacts.push(bad3.contacts[0]);assert.throws(()=>validateBackup(bad3));
});
