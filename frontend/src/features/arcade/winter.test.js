import test from 'node:test'
import assert from 'node:assert/strict'
import { createWinter, stepWinter, buildWinter, winterPlacement, winterCapacity, winterIdle, assignWinter, upgradeFurnace, upgradeWinterBuilding, researchWinter, gatherWinter, sendWinterExpedition, chooseWinterSupply, setWinterHeat, setWinterRation } from './winter.js'

test('real construction costs, occupancy and bounded grid placement are enforced',()=>{
  const s=createWinter();assert.ok(!winterPlacement(s,'hut',3,3).ok);assert.ok(!buildWinter(s,'hut',-1,0));assert.ok(!buildWinter(s,'forged',0,0))
  assert.ok(buildWinter(s,'hut',3,4));assert.equal(s.resources.wood,28);assert.equal(s.resources.iron,18);assert.equal(winterCapacity(s),10)
  assert.ok(!buildWinter(s,'hut',3,4));assert.ok(upgradeWinterBuilding(s,s.buildings[0].id));assert.equal(winterCapacity(s),14)
})
test('workforce cannot be oversubscribed, and advanced jobs need corresponding facilities',()=>{
  const s=createWinter();assert.equal(winterIdle(s),0);assert.ok(!assignWinter(s,'wood',1));assert.ok(assignWinter(s,'coal',-1));assert.ok(!assignWinter(s,'iron',1))
  assert.ok(buildWinter(s,'mine',2,3));assert.ok(assignWinter(s,'iron',1));assert.equal(winterIdle(s),0);assert.ok(!assignWinter(s,'forged',1));assert.ok(!assignWinter(s,'wood',10))
})
test('production, consumption and building efficiency change actual inventory',()=>{
  const a=createWinter(),b=createWinter();buildWinter(b,'sawmill',2,3);const before=b.resources.wood
  for(let i=0;i<100;i++){stepWinter(a,.1);stepWinter(b,.1)}
  assert.ok(b.resources.wood-before>a.resources.wood-42);assert.ok(a.resources.food>35);assert.ok(a.resources.coal>38)
  assert.ok(setWinterHeat(a,2));const coal=a.resources.coal;assignWinter(a,'coal',-1);assignWinter(a,'coal',-1);stepWinter(a,.1);assert.ok(a.resources.coal<coal)
})
test('cold, starvation, housing outside the heat radius and medical care have real effects',()=>{
  const s=createWinter();setWinterHeat(s,0);s.resources.food=0;const hp=s.health;stepWinter(s,.1);assert.ok(s.health<hp)
  const warm=createWinter();buildWinter(warm,'hut',0,0);const comfort=warm.comfort;assert.ok(upgradeFurnace(warm));assert.ok(warm.comfort>comfort)
  const clinic=createWinter();buildWinter(clinic,'clinic',2,3);assignWinter(clinic,'wood',-1);assignWinter(clinic,'medic',1);clinic.health=60;stepWinter(clinic,.1);assert.ok(clinic.health>60)
  assert.ok(!setWinterHeat(s,99));assert.ok(setWinterRation(s,'scarce'));assert.ok(!setWinterRation(s,'fake'))
})
test('research is gated, paid once, and changes the underlying simulation',()=>{
  const s=createWinter();assert.ok(!researchWinter(s,'insulation'));assert.ok(buildWinter(s,'workshop',2,3));const c=s.comfort;assert.ok(researchWinter(s,'insulation'));assert.equal(s.comfort,c+7);assert.ok(!researchWinter(s,'insulation'));assert.ok(!researchWinter(s,'fake'))
})
test('expeditions reserve two people, return actual supplies, and respect housing capacity',()=>{
  const s=createWinter();assert.ok(!sendWinterExpedition(s,'fuel'));buildWinter(s,'outpost',2,3);assert.ok(sendWinterExpedition(s,'ruins'));assert.equal(Object.values(s.jobs).reduce((a,b)=>a+b,0),4);assert.equal(winterIdle(s),0);assert.ok(!sendWinterExpedition(s,'fuel'))
  const iron=s.resources.iron;for(let i=0;i<201;i++)stepWinter(s,.1);assert.equal(s.expedition,null);assert.equal(s.resources.iron,iron+18);assert.equal(winterIdle(s),2)
  assert.ok(sendWinterExpedition(s,'survivors'));for(let i=0;i<201;i++)stepWinter(s,.1);assert.equal(s.residents,6)
})
test('manual supply cooldown, dawn choice freeze, invalid frame and ended state are bounded',()=>{
  const s=createWinter();assert.ok(gatherWinter(s,'wood'));assert.equal(s.resources.wood,46);assert.ok(!gatherWinter(s,'wood'));assert.ok(!gatherWinter(s,'iron'))
  stepWinter(s,100);assert.equal(s.elapsed,.1);stepWinter(s,Infinity);assert.equal(s.elapsed,.1)
  for(let i=0;i<480;i++)stepWinter(s,.1);assert.equal(s.day,2);assert.equal(s.choices.length,3);const time=s.elapsed
  stepWinter(s,.1);assert.equal(s.elapsed,time);assert.ok(!buildWinter(s,'hut',2,3));assert.ok(!chooseWinterSupply(s,'fake'));assert.ok(chooseWinterSupply(s,'fuel'))
  s.status='lost';stepWinter(s,.1);assert.equal(s.elapsed,time);assert.ok(!gatherWinter(s,'wood'))
})
test('real five-day production and furnace planning survives; ignoring heating loses',()=>{
  const s=createWinter();buildWinter(s,'sawmill',2,3);buildWinter(s,'coal',3,2)
  for(let i=0;i<2600&&s.status==='playing';i++){
    if(s.choices.length){chooseWinterSupply(s,'fuel');continue}
    if(!s.buildings.some(b=>b.kind==='mine')&&s.resources.wood>=20){buildWinter(s,'mine',4,3);assignWinter(s,'coal',-1);assignWinter(s,'iron',1)}
    if(s.furnace<3&&s.resources.wood>=18+s.furnace*10&&s.resources.iron>=4+s.furnace*4)upgradeFurnace(s)
    stepWinter(s,.1)
  }
  assert.equal(s.status,'won');assert.equal(s.day,6);assert.ok(s.health>70);assert.ok(s.furnace>=3)
  const cold=createWinter();setWinterHeat(cold,0)
  for(let i=0;i<2500&&cold.status==='playing';i++){if(cold.choices.length)chooseWinterSupply(cold,'fuel');stepWinter(cold,.1)}
  assert.equal(cold.status,'lost');assert.ok(cold.resources.coal>=0);assert.ok(cold.resources.food>=0)
})
test('endless winter crosses five days without ending while retaining daily choices',()=>{
  const s=createWinter(true);s.furnace=4;s.resources.wood=s.resources.iron=1000;s.resources.food=s.resources.coal=1000
  for(let i=0;i<2420;i++){if(s.choices.length)chooseWinterSupply(s,'lining');stepWinter(s,.1)}
  assert.equal(s.status,'playing');assert.equal(s.day,6);assert.ok(s.elapsed>=240)
})
