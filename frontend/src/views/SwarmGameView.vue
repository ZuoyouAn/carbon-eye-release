<template>
  <main class="content-page">
    <header class="arc-heading"><div><p class="section-kicker">SPACE ARCADE / STARFALL</p><h1>星潮幸存者</h1><p>选一个职业，走一条自己的路。敌人从四面涌来，你的每次升级都能改变战斗。</p></div><RouterLink class="arc-back" to="/games">← 游戏大厅</RouterLink></header>
    <div class="arc-layout"><section>
      <div ref="stage" class="arc-stage swarm-stage" :class="{'is-expanded':expanded}" tabindex="0" aria-label="星潮幸存者键盘与触屏游戏" :data-phase="phase" :data-level="hud.level" :data-kills="hud.kills" :data-x="hud.player.x.toFixed(1)" :data-y="hud.player.y.toFixed(1)" :data-time="hud.elapsed.toFixed(2)" :data-branch="hud.branch" :data-loot-x="nearestGem?.x.toFixed(1)" :data-loot-y="nearestGem?.y.toFixed(1)" @pointerdown="pointerDown" @pointermove="aimAt" @pointerup="fire=false" @pointercancel="fire=false" @pointerleave="fire=false">
        <div ref="mount" class="arc-canvas" />
        <div class="arc-hud"><div><span>{{professionName}} · Lv.{{hud.level}} · {{hud.kills}} 击退</span><strong>生命 {{Math.ceil(hud.player.hp)}} / {{hud.player.maxHp}}</strong><meter :value="hud.player.hp" min="0" :max="hud.player.maxHp" aria-label="角色生命" /></div><div><span>{{endless?'无尽挑战':'三分钟撤离'}} · {{timeLabel}}</span><strong>经验 {{hud.xp}} / {{hud.nextXp}}</strong><meter :value="hud.xp" min="0" :max="hud.nextXp" aria-label="升级经验" /></div></div>
        <div class="arc-stage-actions"><button type="button" @click.stop="toggle">{{expanded?'收起战场':'放大战场'}}</button><button v-if="phase==='playing' && !hud.choices.length" type="button" @click.stop="pause">暂停</button><RouterLink to="/games" @click.stop>大厅 ↗</RouterLink></div>
        <div v-if="phase==='playing' && !hud.choices.length" class="arc-touch"><div ref="joystick" class="arc-stick" aria-label="拖动摇杆移动" @pointerdown.stop.prevent="stickStart" @pointermove.stop.prevent="stickMove" @pointerup.stop="stickStop" @pointercancel.stop="stickStop" @lostpointercapture="stickStop"><span :style="{transform:`translate(${stick.x*22}px,${stick.y*22}px)`}">✥</span></div><div><button type="button" @click.stop="dash=true;focus()">冲刺 {{hud.player.dashCooldown>0?Math.ceil(hud.player.dashCooldown)+'s':''}}</button><button type="button" :disabled="hud.player.skillCooldown>0" @click.stop="skill=true;focus()">{{hud.player.skillCooldown>0?'技能 '+Math.ceil(hud.player.skillCooldown)+'s':'职业技能'}}</button><button v-if="!autoFire" type="button" @pointerdown.stop.prevent="fire=true" @pointerup.stop="fire=false" @pointercancel.stop="fire=false" @pointerleave="fire=false">攻击</button></div></div>
        <div v-if="phase!=='playing'||hud.choices.length||error" class="arc-overlay"><div>
          <p class="section-kicker">{{hud.choices.length?'CHOOSE YOUR PATH':'STARFALL / SOLO SURVIVAL'}}</p><h2>{{error?'暂时无法打开画面。':hud.choices.length?(hud.choices[0].branch?'选择职业进阶。':'这一次，强化什么？'):phase==='paused'?'战斗已暂停。':phase==='won'?'你守住了星灯。':phase==='lost'?'再试一条新的路线。':'四面敌潮，三种答案。'}}</h2>
          <p>{{error || (hud.choices.length?hud.note:phase==='ready'?'自动攻击默认开启：移动躲避、拾取星尘升级。第 4 级选择职业分支；每分钟出现巨型异兽。':phase==='paused'?'时间与敌人都已暂停，手动继续后恢复。':`${Math.floor(hud.elapsed)} 秒 · ${hud.kills} 击退 · ${hud.bosses} 异兽 · ${branchName}`)}}</p>
          <div v-if="hud.choices.length" class="arc-choices"><button v-for="choice in hud.choices" :key="choice.id" type="button" :data-upgrade="choice.id" @click.stop="upgrade(choice.id)"><strong>{{choice.name}}</strong><span>{{choice.note}}</span></button></div>
          <template v-else-if="!error"><template v-if="phase!=='paused'"><div class="arc-professions"><button v-for="p in PROFESSIONS" :key="p.id" type="button" :data-profession="p.id" :aria-pressed="profession===p.id" @click.stop="profession=p.id"><b aria-hidden="true">{{glyph[p.id]}}</b><strong>{{p.name}}</strong><small>{{p.weapon}}</small></button></div><p>{{PROFESSIONS.find(p=>p.id===profession).note}}</p><label>挑战<select v-model="endless"><option :value="false">三分钟撤离</option><option :value="true">无尽挑战 · 随时结束一局</option></select></label><label>难度<select v-model="difficulty"><option value="normal">标准敌潮</option><option value="practice">练习 · 敌人更慢、伤害更低</option></select></label></template><button class="button button-primary" type="button" @click.stop="phase==='paused'?resume():start()">{{phase==='paused'?'继续战斗':phase==='ready'?'进入敌潮':'重新出发'}}</button></template>
        </div></div>
      </div>
      <section class="arc-card arc-help"><h2>不是原地等升级。</h2><p class="swarm-loot-hint">{{lootHint}}</p><p>WASD / 方向键移动，Shift 冲刺，E 施放职业技能，空格攻击，Esc 暂停。移动到星尘附近会吸引并收集经验；升级时世界暂停。默认自动瞄准最近的敌人，按住鼠标可朝指针方向射击。</p><p>手机使用摇杆、冲刺和技能按钮。红圈是异兽即将释放的范围攻击；离开预警范围。每个职业都有独立技能，进阶路线每局只能选择一次。</p></section>
    </section><aside class="arc-sidebar">
      <section class="arc-card"><p class="section-kicker">BUILD YOUR CHARACTER</p><h2>{{branchName}}</h2><div class="arc-stats"><div><small>基础伤害</small><strong>{{hud.player.damage.toFixed(0)}}</strong></div><div><small>攻击间隔</small><strong>{{hud.player.interval.toFixed(2)}}s</strong></div><div><small>护甲</small><strong>{{hud.player.armor}}</strong></div><div><small>{{hud.profession==='guardian'?'范围':'投射物 / 贯穿'}}</small><strong>{{hud.profession==='guardian'?hud.player.range.toFixed(0):`${hud.player.multi} / ${hud.player.pierce}`}}</strong></div></div><div class="arc-route-pills"><span v-for="(count,id) in hud.upgrades" :key="id">{{upgradeNames[id]}} ×{{count}}</span><span v-if="!Object.keys(hud.upgrades).length">拾取星尘，开始你的构筑</span></div><p class="arc-note" role="status">{{hud.note}}</p></section>
      <section class="arc-card"><h3>你的战斗方式</h3><label><input v-model="autoFire" type="checkbox" /> 自动攻击</label><p class="arc-note">关闭后按住空格、鼠标或手机“攻击”。改变操作方式不重置升级。</p><button v-if="phase==='playing'||phase==='paused'" type="button" class="arc-small" @click="finish">结束本局并查看结果</button><p>游侠技能：环形齐射。守卫技能：震退范围伤害与短暂护盾。术士技能：范围爆发与减速。</p></section>
      <p class="arc-note">原创程序绘图与规则。免费、单机、无需登录；不保存或上传进度，不调用模型 API。切换标签页、失去窗口焦点或离开页面都会停止战斗。</p>
    </aside></div>
  </main>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import { RouterLink } from 'vue-router'
import { PROFESSIONS, createSwarm, stepSwarm, chooseSwarmUpgrade, swarmBranchName } from '../features/arcade/swarm.js'
import { createArcadeCanvas, paintSwarm } from '../features/arcade/canvas.js'
import { useArcadeLoop } from '../features/arcade/useLoop.js'
import { useExpandedScene } from '../utils/useExpandedScene.js'
import '../features/arcade/arcade.css'
const stage=ref(null), mount=ref(null), joystick=ref(null), profession=ref('ranger'), difficulty=ref('normal'), endless=ref(false), phase=ref('ready'), autoFire=ref(true), error=ref(''), fire=ref(false), dash=ref(false), skill=ref(false), stick=ref({x:0,y:0})
const glyph={ranger:'⌁',guardian:'◇',mage:'✧'}, upgradeNames={damage:'伤害',haste:'连击',multi:'分裂',vitality:'生命',speed:'移动',magnet:'吸引',armor:'护甲',reach:'射程'}
let state=createSwarm(), scene, motion, pointerId=null, aim=null; const keys=new Set(), hud=shallowRef(structuredClone(state))
const professionName=computed(()=>PROFESSIONS.find(p=>p.id===hud.value.profession).name), branchName=computed(()=>swarmBranchName(hud.value)), timeLabel=computed(()=>`${Math.floor(hud.value.elapsed/60)}:${String(Math.floor(hud.value.elapsed%60)).padStart(2,'0')}`)
const nearestGem=computed(()=>[...hud.value.gems].sort((a,b)=>Math.hypot(a.x-hud.value.player.x,a.y-hud.value.player.y)-Math.hypot(b.x-hud.value.player.x,b.y-hud.value.player.y))[0])
const lootHint=computed(()=>{const g=nearestGem.value,p=hud.value.player;if(!g)return '暂时没有星尘。击退敌人后，沿着地面的青色晶体收集经验。';return `最近星尘：${Math.abs(g.x-p.x)<25?'':g.x>p.x?'右':'左'}${Math.abs(g.y-p.y)<25?'':g.y>p.y?'下':'上'}方，约 ${Math.round(Math.hypot(g.x-p.x,g.y-p.y))} 个游戏距离单位。靠近后自动吸引。`})
const {expanded,toggle}=useExpandedScene(pause)
function publish(){hud.value=structuredClone(state)}
function paint(){scene?.render(state,motion?.matches)}
const loop=useArcadeLoop(dt=>{
  const x=Number(keys.has('d')||keys.has('arrowright'))-Number(keys.has('a')||keys.has('arrowleft'))+stick.value.x, y=Number(keys.has('s')||keys.has('arrowdown'))-Number(keys.has('w')||keys.has('arrowup'))+stick.value.y
  stepSwarm(state,{x,y,auto:autoFire.value,fire:fire.value||keys.has(' '),aim:fire.value?aim:null,dash:dash.value||keys.has('shift'),skill:skill.value},dt); dash.value=skill.value=false
  if(state.status!=='playing'){phase.value=state.status;clearInput();return false} if(state.choices.length){clearInput();return false} return true
},publish,paint)
function focus(){stage.value?.focus({preventScroll:true})}
function clearInput(){keys.clear();fire.value=dash.value=skill.value=false;stick.value={x:0,y:0};pointerId=null;aim=null}
function pause(){clearInput();if(phase.value!=='playing')return;loop.stop();phase.value='paused';publish();paint()}
function resume(){if(!scene||error.value||document.hidden)return;clearInput();phase.value='playing';focus();if(!state.choices.length)loop.start()}
function start(){state=createSwarm(profession.value,difficulty.value,endless.value);publish();paint();resume()}
function upgrade(id){if(chooseSwarmUpgrade(state,id)){publish();paint();resume()}}
function finish(){loop.stop();clearInput();state.status='ended';state.choices=[];phase.value='ended';publish();paint()}
function aimAt(event){if(event.target.closest('button,.arc-stick,.arc-overlay')||!scene)return;const p=scene.position(event);aim={x:p.x-p.width/2,y:p.y-p.height/2}}
function pointerDown(event){if(event.target.closest('button,a,select,.arc-stick,.arc-overlay'))return;focus();aimAt(event);if(event.pointerType!=='touch'&&phase.value==='playing')fire.value=true}
function keydown(event){if(document.activeElement!==stage.value||event.ctrlKey||event.metaKey||event.altKey)return;const k=event.key.toLowerCase();if(!['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright','shift',' ','e','escape'].includes(k))return;event.preventDefault();if(k==='escape'&&!event.repeat){phase.value==='paused'?resume():pause();return}if(phase.value!=='playing'||state.choices.length)return;if(k==='e'){if(!event.repeat)skill.value=true}else keys.add(k)}
function keyup(event){keys.delete(event.key.toLowerCase())}
function stickStart(event){if(phase.value!=='playing')return;pointerId=event.pointerId;event.currentTarget.setPointerCapture(pointerId);stickMove(event)}
function stickMove(event){if(pointerId!==event.pointerId)return;const r=joystick.value.getBoundingClientRect(),x=(event.clientX-r.left-r.width/2)/26,y=(event.clientY-r.top-r.height/2)/26,l=Math.max(1,Math.hypot(x,y));stick.value={x:x/l,y:y/l}}
function stickStop(){pointerId=null;stick.value={x:0,y:0}}
function visibility(){if(document.hidden)pause()}
function motionChange(){paint()}
onMounted(()=>{motion=matchMedia('(prefers-reduced-motion: reduce)');motion.addEventListener('change',motionChange);try{scene=createArcadeCanvas(mount.value,paintSwarm);paint()}catch(e){error.value=e.message}window.addEventListener('keydown',keydown);window.addEventListener('keyup',keyup);window.addEventListener('blur',pause);document.addEventListener('visibilitychange',visibility)})
onUnmounted(()=>{loop.stop();clearInput();scene?.dispose();motion?.removeEventListener('change',motionChange);window.removeEventListener('keydown',keydown);window.removeEventListener('keyup',keyup);window.removeEventListener('blur',pause);document.removeEventListener('visibilitychange',visibility)})
</script>
