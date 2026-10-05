// Original local-only base-building simulation; deterministic and independently testable.
export const CAMP_BOUND = 14
export const DAY_SECONDS = 60
export const BUILDINGS = Object.freeze([
  {id:'wall',name:'围墙',note:'阻挡移动，吸引近距离敌人攻击。',wood:2,scrap:0,hp:100,solid:true},
  {id:'turret',name:'自动炮塔',note:'消耗 1 电力，射程 7，自动攻击。',wood:4,scrap:6,hp:85,solid:true},
  {id:'generator',name:'发电机',note:'提供 2 电力；保护它让炮塔持续运作。',wood:4,scrap:4,hp:70,solid:true},
  {id:'garden',name:'菜地',note:'每个黎明产出 3 食物。',wood:3,scrap:0,food:1,hp:60,solid:false},
  {id:'water',name:'净水站',note:'每个黎明产出 3 饮水。',wood:3,scrap:3,hp:70,solid:true},
])
export const CAMP_ROCKS = [{x:-8,z:-8},{x:8,z:6},{x:-8,z:8},{x:10,z:-6}]
const dist=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z)
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n))
const nodeLocations=[[-4,4],[-6,2],[-4,-6],[6,4],[8,2],[4,-6],[-12,0],[12,8],[-10,-10],[10,-10],[-4,10],[4,10],[0,12],[0,-12],[12,0],[-12,10]]
export function createSettlement(seed='余烬营地',difficulty='normal') {
  if(typeof seed!=='string'||!seed.trim()||seed.length>48||!['normal','relaxed'].includes(difficulty))throw Error('营地种子或难度无效。')
  let random=2166136261;for(const ch of seed)random=Math.imul(random^ch.charCodeAt(0),16777619)>>>0
  const state={seed,difficulty,random,status:'playing',elapsed:0,day:1,cycle:0,night:false,nightSpawned:false,spawned:0,nextSpawn:0,ids:1,crew:3,kills:0,harvests:0,buildCount:0,
    player:{x:2,z:3,facing:0,hp:100,dash:0,dashCooldown:0,shotCooldown:0,invulnerable:0},base:{x:0,z:0,hp:180,maxHp:180},resources:{wood:18,scrap:16,food:6,water:6},buildings:[{id:0,kind:'turret',x:0,z:-4,hp:85,maxHp:85,cooldown:0,level:1,powered:true}],enemies:[],beams:[],particles:[],nodes:nodeLocations.map(([x,z],i)=>({id:i,x,z,kind:i%4===0?'wood':i%4===1?'scrap':i%4===2?'food':'water',remaining:3})),notes:['建造一座菜地和净水站；供电不足时补发电机。'],upgrades:[],awaitUpgrade:false}
  allocatePower(state);return state
}
function note(s,text){if(s.notes.at(-1)!==text)s.notes.push(text);if(s.notes.length>6)s.notes.shift()}
function rng(s){s.random=(Math.imul(s.random,1664525)+1013904223)>>>0;return s.random/4294967296}
export function allocatePower(s){let available=1+s.buildings.filter(b=>b.kind==='generator'&&b.hp>0).length*2;for(const b of s.buildings){if(b.kind==='turret'){b.powered=available>0;if(b.powered)available--}}s.power={capacity:1+s.buildings.filter(b=>b.kind==='generator'&&b.hp>0).length*2,demand:s.buildings.filter(b=>b.kind==='turret').length,free:available}}
export function canWalkCamp(s,x,z,radius=.35){if(!Number.isFinite(x)||!Number.isFinite(z)||Math.abs(x)>CAMP_BOUND-radius||Math.abs(z)>CAMP_BOUND-radius)return false;if(Math.abs(x)<1.1+radius&&Math.abs(z)<1.1+radius)return false
  return !CAMP_ROCKS.some(b=>Math.abs(x-b.x)<1.2+radius&&Math.abs(z-b.z)<1.2+radius)&&!s.buildings.some(b=>BUILDINGS.find(d=>d.id===b.kind).solid&&Math.abs(x-b.x)<.72+radius&&Math.abs(z-b.z)<.72+radius)
}
export function placement(s,kind,x,z){const def=BUILDINGS.find(b=>b.id===kind),at={x:Math.round(x/2)*2,z:Math.round(z/2)*2};if(!def||!Number.isFinite(x)||!Number.isFinite(z))return {...at,ok:false,reason:'无效建筑或位置。'}
  if(s.status!=='playing'||s.awaitUpgrade)return {...at,ok:false,reason:'当前不能建造。'}
  if(Math.abs(at.x)>12||Math.abs(at.z)>12||Math.abs(at.x)<2&&Math.abs(at.z)<2||CAMP_ROCKS.some(b=>Math.abs(at.x-b.x)<2&&Math.abs(at.z-b.z)<2)||s.nodes.some(n=>n.remaining>0&&dist(n,at)<1.2)||s.buildings.some(b=>dist(b,at)<1.9)||dist(s.player,at)<1.1)return {...at,ok:false,reason:'此格被占用；先采完资源或走开。'}
  if(dist(s.player,at)>7)return {...at,ok:false,reason:'太远了，走近到 7 米内再建造。'}
  if(s.buildings.length>=32)return {...at,ok:false,reason:'首版营地最多 32 座设施。'}
  if(['wood','scrap','food'].some(key=>(def[key]||0)>s.resources[key]))return {...at,ok:false,reason:'资源不足，先采集。'}
  return {...at,ok:true,reason:`建造${def.name}：${def.wood} 木材、${def.scrap} 零件${def.food?'、1 食物':''}`}
}
export function buildCamp(s,kind,x,z){const target=placement(s,kind,x,z);if(!target.ok){note(s,target.reason);return false}const def=BUILDINGS.find(b=>b.id===kind);for(const key of ['wood','scrap','food'])s.resources[key]-=def[key]||0;s.buildings.push({id:s.ids++,kind,x:target.x,z:target.z,hp:def.hp,maxHp:def.hp,cooldown:0,level:1,powered:false});s.buildCount++;allocatePower(s);note(s,`${def.name}建成。`);return true}
export function campInteract(s){if(s.status!=='playing'||s.awaitUpgrade)return false
  const nearest=s.nodes.filter(n=>n.remaining>0&&dist(n,s.player)<1.9).sort((a,b)=>dist(a,s.player)-dist(b,s.player))[0]
  if(nearest){nearest.remaining--;s.resources[nearest.kind]+=nearest.kind==='wood'||nearest.kind==='scrap'?3:2;s.harvests++;note(s,`采集${{wood:'木材',scrap:'零件',food:'食物',water:'饮水'}[nearest.kind]}；此处剩余 ${nearest.remaining} 次。`);return true}
  const target=[s.base,...s.buildings].filter(b=>b.hp<b.maxHp&&dist(b,s.player)<2.3).sort((a,b)=>dist(a,s.player)-dist(b,s.player))[0]
  if(target&&s.resources.wood>=1&&s.resources.scrap>=1){s.resources.wood--;s.resources.scrap--;target.hp=Math.min(target.maxHp,target.hp+40);note(s,'维修完成，恢复最多 40 耐久。');return true}note(s,'靠近资源按 E 采集；靠近受损基地或设施，消耗 1 木材与 1 零件维修。');return false
}
export function upgradeCamp(s,id){if(!s.awaitUpgrade||!s.upgrades.some(item=>item.id===id))return false
  if(id==='supply'){s.resources.wood+=8;s.resources.scrap+=8}else if(id==='reinforce'){s.base.maxHp+=40;s.base.hp=Math.min(s.base.maxHp,s.base.hp+70);s.player.hp=100}else if(id==='efficiency'){s.turretBonus=(s.turretBonus||0)+4}
  s.awaitUpgrade=false;s.upgrades=[];note(s,'黎明到了，继续建设营地。');return true
}
export function startNight(s){if(s.status!=='playing'||s.awaitUpgrade||s.night)return false;s.cycle=Math.max(s.cycle,s.difficulty==='relaxed'?40:34);note(s,'你提前结束了建设时段，准备迎战。');return true}
function dawn(s){s.day++;s.cycle=0;s.night=false;s.nightSpawned=false;s.spawned=0;s.nextSpawn=0;for(const b of s.buildings){if(b.kind==='garden')s.resources.food+=3;if(b.kind==='water')s.resources.water+=3}
  const foodShort=Math.max(0,2-s.resources.food),waterShort=Math.max(0,2-s.resources.water);s.resources.food=Math.max(0,s.resources.food-2);s.resources.water=Math.max(0,s.resources.water-2);s.base.hp=Math.max(0,s.base.hp-12*(foodShort+waterShort))
  if(foodShort||waterShort)note(s,'补给不足，营地受到损耗：黎明需要 2 食物与 2 饮水。')
  if(s.day>3){s.status=s.base.hp>0?'won':'lost';note(s,s.status==='won'?'三个夜晚后，营地仍然亮着。救援队已抵达！':'营地失守。');return}
  if(s.base.hp<=0){s.status='lost';return}s.awaitUpgrade=true;s.upgrades=[{id:'supply',name:'补给箱',note:'+8 木材、+8 零件'},{id:'reinforce',name:'紧急加固',note:'基地上限 +40、恢复 70；角色回满血'},{id:'efficiency',name:'炮塔校准',note:'所有炮塔伤害 +4'}]
}
function spawn(s){const side=Math.floor(rng(s)*4),offset=(rng(s)*20)-10,type=s.day===3&&s.spawned===0?'brute':s.spawned%3===2?'runner':'scout';const x=side===0?-13:side===1?13:offset,z=side===2?-13:side===3?13:offset
  s.enemies.push({id:s.ids++,x,z,type,hp:type==='brute'?130:type==='runner'?20:32,maxHp:type==='brute'?130:type==='runner'?20:32,cooldown:0});s.spawned++
}
function enemyWalkable(x,z){return Math.abs(x)<=14&&Math.abs(z)<=14&&!CAMP_ROCKS.some(r=>Math.abs(x-r.x)<1.65&&Math.abs(z-r.z)<1.65)}
export function campRoute(from,to){
  const start={x:clamp(Math.round(from.x),-14,14),z:clamp(Math.round(from.z),-14,14)},end={x:clamp(Math.round(to.x),-14,14),z:clamp(Math.round(to.z),-14,14)},key=p=>`${p.x},${p.z}`,queue=[start],parent=new Map([[key(start),null]]);let found=null
  for(let i=0;i<queue.length;i++){const here=queue[i];if(here.x===end.x&&here.z===end.z){found=here;break}for(const [dx,dz] of [[1,0],[-1,0],[0,1],[0,-1]]){const next={x:here.x+dx,z:here.z+dz};if(enemyWalkable(next.x,next.z)&&!parent.has(key(next))){parent.set(key(next),here);queue.push(next)}}}
  if(!found)return [];const route=[];for(let node=found;node;node=parent.get(key(node)))route.push(node);return route.reverse()
}
function beam(s,from,to,color='#51a8f4'){s.beams.push({id:s.ids++,x:from.x,z:from.z,tx:to.x,tz:to.z,life:.13,color})}
function hit(s,enemy,damage,from){enemy.hp-=damage;beam(s,from,enemy);if(enemy.hp<=0){s.kills++;s.resources.scrap++;s.particles.push({id:s.ids++,x:enemy.x,z:enemy.z,life:.55});if(s.kills%4===0)s.resources.wood+=2}}
export function stepSettlement(s,input={},seconds=0){if(s.status!=='playing'||s.awaitUpgrade)return s;const dt=Number.isFinite(seconds)?clamp(seconds,0,.05):0;if(!dt)return s
  s.elapsed+=dt;s.cycle+=dt;const p=s.player;p.dashCooldown=Math.max(0,p.dashCooldown-dt);p.shotCooldown=Math.max(0,p.shotCooldown-dt);p.invulnerable=Math.max(0,p.invulnerable-dt)
  let dx=Number.isFinite(input.x)?clamp(input.x,-1,1):0,dz=Number.isFinite(input.z)?clamp(input.z,-1,1):0;const length=Math.hypot(dx,dz);if(length>1){dx/=length;dz/=length}
  p.moving=length>.1
  if(input.dash&&p.dashCooldown===0&&Math.hypot(dx,dz)>.1){p.dash=.18;p.dashCooldown=2.4;p.invulnerable=.24}p.dash=Math.max(0,p.dash-dt)
  const speed=p.dash>0?14:4.4;const steps=Math.ceil(speed*dt/.12)
  for(let i=0;i<steps;i++){const x=p.x+dx*speed*dt/steps,z=p.z+dz*speed*dt/steps;if(canWalkCamp(s,x,p.z))p.x=x;if(canWalkCamp(s,p.x,z))p.z=z}if(length>.1)p.facing=Math.atan2(dx,dz)
  if(input.fire&&p.shotCooldown===0){const target=s.enemies.filter(en=>en.hp>0&&dist(en,p)<6).sort((a,b)=>dist(a,p)-dist(b,p))[0];if(target){hit(s,target,14,p);p.shotCooldown=.36}}
  const nightStart=s.difficulty==='relaxed'?40:34
  if(s.cycle>=nightStart){if(!s.night){s.night=true;note(s,`第 ${s.day} 夜来袭。炮塔需供电；空格防卫，Shift 冲刺。`)}const target=4+s.day*2;if(s.spawned<target&&s.cycle>=nightStart+s.spawned*2.4)spawn(s)}
  for(const b of s.buildings){b.cooldown=Math.max(0,b.cooldown-dt);if(b.kind==='turret'&&b.powered&&b.cooldown===0){const enemy=s.enemies.filter(en=>en.hp>0&&dist(en,b)<7).sort((a,c)=>dist(a,b)-dist(c,b))[0];if(enemy){hit(s,enemy,10+(s.turretBonus||0),b);b.cooldown=.48}}}
  for(const en of s.enemies){if(en.hp<=0)continue;en.cooldown=Math.max(0,en.cooldown-dt);const nearby=[s.base,...s.buildings].filter(b=>dist(b,en)<1.9).sort((a,b)=>dist(a,en)-dist(b,en))[0];const victim=nearby||(dist(p,en)<2.8?p:s.base),distance=dist(en,victim)
    if(distance<1.55){if(en.cooldown===0){const damage=(en.type==='brute'?15:7)*(s.difficulty==='relaxed'?.65:1);if(victim!==p||p.invulnerable===0){victim.hp-=damage;if(victim===p)p.invulnerable=.45;beam(s,en,victim,'#d77562')}en.cooldown=1}}
    else{const speed=(en.type==='brute'?1.3:en.type==='runner'?3:1.9)*(s.difficulty==='relaxed'?.8:1)
      en.routeTimer=Math.max(0,(en.routeTimer||0)-dt)
      if(!en.route||!en.goal||dist(en.goal,victim)>1.5||en.routeTimer===0){en.route=campRoute(en,victim);en.goal={x:victim.x,z:victim.z};en.routeTimer=1}
      while(en.route.length&&dist(en,en.route[0])<.2)en.route.shift()
      const next=en.route[0]||victim,segment=dist(en,next),movement=Math.min(speed*dt,segment),mx=segment?(next.x-en.x)/segment*movement:0,mz=segment?(next.z-en.z)/segment*movement:0
      if(enemyWalkable(en.x+mx,en.z))en.x+=mx;if(enemyWalkable(en.x,en.z+mz))en.z+=mz
    }
  }
  s.enemies=s.enemies.filter(en=>en.hp>0);const before=s.buildings.length;s.buildings=s.buildings.filter(b=>b.hp>0);if(before!==s.buildings.length){allocatePower(s);note(s,'设施被摧毁；检查炮塔供电。')}
  s.beams=s.beams.filter(v=>(v.life-=dt)>0);s.particles=s.particles.filter(v=>(v.life-=dt)>0)
  if(s.base.hp<=0||p.hp<=0){s.base.hp=Math.max(0,s.base.hp);p.hp=Math.max(0,p.hp);s.status='lost';note(s,'营地失守。换个布局再试一次。')}
  else if(s.cycle>=DAY_SECONDS&&s.spawned>=4+s.day*2&&s.enemies.length===0)dawn(s)
  return s
}
