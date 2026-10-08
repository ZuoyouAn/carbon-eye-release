import test from 'node:test'
import assert from 'node:assert/strict'
import { createSwarm, stepSwarm, chooseSwarmUpgrade, swarmSkill, SWARM_LIMITS } from './swarm.js'

test('three distinct professions and seeded journeys are validated and repeatable',()=>{
  assert.deepEqual(createSwarm('mage','practice',true,33),createSwarm('mage','practice',true,33))
  assert.ok(createSwarm('guardian').player.hp>createSwarm().player.hp)
  assert.equal(createSwarm('mage').player.pierce,1)
  assert.throws(()=>createSwarm('unknown'));assert.throws(()=>createSwarm('ranger','bad'))
})
test('movement is normalized, bounded and robust to invalid inputs and large frame gaps',()=>{
  const a=createSwarm(),b=createSwarm();stepSwarm(a,{x:1},.05);stepSwarm(b,{x:1,y:1},.05)
  assert.ok(Math.abs(Math.hypot(b.player.x,b.player.y)-a.player.x)<1e-8)
  stepSwarm(a,{x:Infinity,y:NaN},NaN);assert.equal(a.elapsed,.05)
  stepSwarm(a,{x:1},100);assert.equal(a.elapsed,.1)
  for(let i=0;i<600;i++)stepSwarm(a,{x:1},.05)
  assert.ok(a.player.x<=4000);assert.ok(a.enemies.every(e=>Number.isFinite(e.x)))
})
test('dash and each profession skill have genuine cooldowns',()=>{
  for(const job of ['ranger','guardian','mage']){
    const s=createSwarm(job);assert.ok(swarmSkill(s));assert.ok(!swarmSkill(s));assert.equal(s.player.skillCooldown,9)
    stepSwarm(s,{x:1,dash:true},.05);assert.equal(s.player.dashCooldown,3);assert.ok(s.player.invulnerable>0)
    const before=s.player.dashCooldown;stepSwarm(s,{dash:true},.05);assert.ok(s.player.dashCooldown<before)
  }
})
test('bullets use swept collision; real kills drop experience, not a fake level counter',()=>{
  const s=createSwarm();s.player.damage=40;s.enemies=[{id:900,x:24,y:0,hp:26,maxHp:26,radius:10,speed:0,slow:0,flash:0,type:'walker'}]
  stepSwarm(s,{},.05);assert.equal(s.kills,1);assert.equal(s.gems.length,1)
  for(let i=0;i<20;i++)stepSwarm(s,{auto:false},.05)
  assert.equal(s.xp,1);assert.equal(s.gems.length,0)
})
test('XP choices freeze the world, reject forged choices and expose six real branch effects',()=>{
  for(const [job,branch] of [['ranger','volley'],['ranger','sniper'],['guardian','bastion'],['guardian','berserker'],['mage','tempest'],['mage','frost']]){
    const s=createSwarm(job);s.level=3;s.xp=s.nextXp;stepSwarm(s,{},.05)
    assert.equal(s.choices.length,2);const before=s.elapsed;stepSwarm(s,{x:1},.05);assert.equal(s.elapsed,before)
    assert.ok(!chooseSwarmUpgrade(s,'forged'));assert.ok(chooseSwarmUpgrade(s,branch));assert.equal(s.branch,branch)
    assert.ok(!chooseSwarmUpgrade(s,branch))
    if(branch==='volley')assert.equal(s.player.multi,3)
    if(branch==='sniper')assert.equal(s.player.pierce,3)
    if(branch==='bastion')assert.equal(s.player.hp,220)
    if(branch==='berserker')assert.ok(s.player.damage>50)
    if(branch==='frost')assert.equal(s.player.range,520)
  }
})
test('boss telegraphs have real damage and spawning/effects stay capped in endless mode',()=>{
  const s=createSwarm('guardian','practice',true);s.elapsed=59.98;stepSwarm(s,{},.05);assert.ok(s.enemies.some(e=>e.type==='boss'))
  const boss=s.enemies.find(e=>e.type==='boss');boss.x=100;boss.y=0;boss.charge=.01;const hp=s.player.hp
  stepSwarm(s,{auto:false},.05);assert.ok(s.player.hp<hp)
  const cap=createSwarm('ranger','practice',true)
  for(let i=0;i<3000&&cap.status==='playing';i++){if(cap.choices.length)chooseSwarmUpgrade(cap,cap.choices[0].id);stepSwarm(cap,{x:1,skill:true},.05)}
  assert.ok(cap.enemies.length<=SWARM_LIMITS.enemies);assert.ok(cap.bullets.length<=SWARM_LIMITS.bullets);assert.ok(cap.effects.length<=SWARM_LIMITS.effects)
})
test('actual three-minute combat with movement, drops, choices and skills wins for all professions',()=>{
  for(const job of ['ranger','guardian','mage']){
    const s=createSwarm(job,'practice')
    for(let i=0;i<5000&&s.status==='playing';i++){
      if(s.choices.length){chooseSwarmUpgrade(s,s.choices.find(c=>['damage','vitality','bastion','frost','sniper'].includes(c.id))?.id||s.choices[0].id);continue}
      const p=s.player,d=e=>Math.hypot(e.x-p.x,e.y-p.y),gem=[...s.gems].sort((a,b)=>d(a)-d(b))[0],enemy=[...s.enemies].sort((a,b)=>d(a)-d(b))[0]
      let x=0,y=0;if(enemy&&d(enemy)<90){x=p.x-enemy.x;y=p.y-enemy.y}else if(gem){x=gem.x-p.x;y=gem.y-p.y}
      const norm=Math.max(1,Math.hypot(x,y));stepSwarm(s,{x:x/norm,y:y/norm,skill:true,dash:Boolean(enemy&&d(enemy)<55)},.05)
    }
    assert.equal(s.status,'won',job);assert.ok(s.kills>100);assert.ok(s.level>=4);assert.ok(s.branch);assert.ok(s.bosses>=1)
    const end=s.elapsed;stepSwarm(s,{},.05);assert.equal(s.elapsed,end)
  }
})
