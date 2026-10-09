import test from 'node:test'
import assert from 'node:assert/strict'
import { paintSwarm } from './swarmScene.js'
import { createSwarm, stepSwarm, swarmSkill, chooseSwarmUpgrade, SWARM_LIMITS } from './swarm.js'

function recordingContext() {
  const calls=[]
  const c=new Proxy({}, {get(target,key){if(key in target)return target[key];return (...args)=>{assert.ok(args.every(a=>typeof a!=='number'||Number.isFinite(a)),`${String(key)} has invalid geometry`);calls.push([key,...args])}},set(target,key,value){target[key]=value;return true}})
  return {c,calls}
}
test('upright original professions, creatures and every effect render on desktop and mobile',()=>{
  for(const job of ['ranger','guardian','mage']) for(const reduced of [false,true]) {
    const s=createSwarm(job);stepSwarm(s,{x:1,skill:true,dash:true},.05)
    s.enemies=['walker','runner','tank','boss'].map((type,i)=>({id:i+50,type,x:80+i*50,y:20,hp:60,maxHp:100,radius:type==='boss'?35:16,flash:.1,slow:1,charge:type==='boss'?.6:0}))
    for(const kind of ['damage','impact','burst','slash','trail','line','nova','level','pickup','ring'])s.effects.push({kind,x:10,y:10,tx:80,ty:30,radius:30,life:.2,maxLife:.4,color:'#70babb'})
    const before=structuredClone(s),{c,calls}=recordingContext()
    paintSwarm(c,320,680,s,reduced);paintSwarm(c,1440,900,s,reduced)
    assert.ok(calls.length>100);assert.deepEqual(s,before,'painting must not mutate gameplay or random state')
  }
})
test('painted renderer uses local atlas cutouts without changing physics or pause state',()=>{
  const s=createSwarm('mage'),image={naturalWidth:1536,naturalHeight:1024}
  s.enemies=[{id:1,type:'tank',x:50,y:0,hp:80,maxHp:100,radius:22,flash:0,slow:0}]
  const before=structuredClone(s),{c,calls}=recordingContext();paintSwarm(c,390,700,s,false,image)
  assert.equal(calls.filter(call=>call[0]==='drawImage').length,2);assert.deepEqual(s,before)
})
test('walking, weapon recoil and dash trails use simulation time and freeze for upgrades',()=>{
  const s=createSwarm();stepSwarm(s,{x:1,dash:true,fire:true,aim:{x:1,y:0}},.05)
  assert.ok(s.animation.stride>0);assert.ok(s.animation.attack>0);assert.ok(s.effects.some(e=>e.kind==='trail'))
  s.xp=s.nextXp;stepSwarm(s,{},.05);assert.ok(s.choices.length)
  const before=structuredClone(s);stepSwarm(s,{x:1,skill:true},.05);assert.deepEqual(s,before)
  chooseSwarmUpgrade(s,s.choices[0].id);assert.ok(s.effects.some(e=>e.kind==='level'))
  stepSwarm(s,{auto:false},.05);assert.equal(s.animation.moving,false)
})
test('guardian shockwave has actual timed knockback rather than visual-only claims',()=>{
  const s=createSwarm('guardian');s.enemies=[{id:55,type:'tank',x:100,y:0,hp:500,maxHp:500,radius:22,speed:50,slow:0,flash:0}]
  assert.ok(swarmSkill(s));assert.equal(s.enemies[0].knock,.3)
  stepSwarm(s,{auto:false},.05);assert.ok(s.enemies[0].x>100);assert.ok(s.enemies[0].hp<500)
  for(let i=0;i<10;i++)stepSwarm(s,{auto:false},.05)
  assert.equal(s.enemies[0].knock,0);assert.ok(s.effects.length<=SWARM_LIMITS.effects)
})
test('charging boss holds its telegraph position and essential warning survives reduced motion',()=>{
  const s=createSwarm();s.enemies=[{id:88,type:'boss',x:100,y:0,hp:1000,maxHp:1000,radius:35,speed:62,slow:0,flash:0,charge:1,pulseCooldown:7}]
  stepSwarm(s,{auto:false},.05);assert.equal(s.enemies[0].x,100)
  const {c,calls}=recordingContext();paintSwarm(c,390,620,s,true)
  assert.ok(calls.some(call=>call[0]==='fillText'&&call[1]==='离开红圈'))
})
