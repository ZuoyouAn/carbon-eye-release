<template>
  <main class="content-page expedition-page">
    <div class="expedition-heading"><div><p class="section-kicker">AN ORIGINAL SPACE GAME</p><h1>晨光行动。</h1><p class="page-subtitle">走进末世城市，搜集物资，让一座信标重新亮起。</p></div><span class="expedition-tag">实时 3D · 原创低多边形</span></div>
    <section class="expedition-layout">
      <div ref="stage" class="expedition-stage" :class="{ 'is-expanded': expanded }" tabindex="0" aria-label="3D 城市探索，用方向键或 WASD 移动" aria-describedby="game-instructions" :data-status="phase" :data-difficulty="hud.difficulty" :data-x="hud.x.toFixed(2)" :data-z="hud.z.toFixed(2)" :data-elapsed="hud.elapsed.toFixed(2)" @pointerdown="focusStage">
        <div ref="mount" class="expedition-canvas" />
        <div class="expedition-hud"><span>健康 {{ hud.health }}%<meter min="0" max="100" :value="hud.health" aria-label="健康" /></span><span>体力 {{ hud.stamina }}%<meter min="0" max="100" :value="hud.stamina" aria-label="体力" /></span><strong>{{ remaining }}</strong></div>
        <button class="expedition-expand" type="button" :aria-pressed="expanded" @click="toggleScene">{{ expanded ? '收起场景' : '放大场景' }}</button>
        <div v-if="phase === 'playing'" class="expedition-context"><span>{{ hud.objective?.label }} · {{ Math.ceil(hud.objective?.distance || 0) }} 米（示意）</span><button v-if="hud.nearby" type="button" @click="act">{{ hud.nearby.action === 'repair' ? 'E · 修复信标' : 'E · 拾取物资' }}</button><small v-else>沿街移动，绕开建筑</small></div>
        <div v-if="phase !== 'playing'" class="expedition-overlay"><div>
          <p class="section-kicker">{{ phase === 'won' ? 'MISSION COMPLETE' : 'DAYBREAK / 01' }}</p>
          <h2>{{ error ? '换一种方式探索。' : phase === 'won' ? '你点亮了晨光。' : phase === 'lost' ? '下一次，会更远。' : phase === 'paused' ? '稍作停留。' : '城市，还在等你。' }}</h2>
          <p>{{ error || (phase === 'ready' ? '搜集 4 个零件、2 块电芯，修复北侧蓝色信标，再前往绿色撤离坪。侧边小地图和金色目标圈帮助你找路。' : phase === 'paused' ? '计时已暂停。离开页面、切换窗口时也会自动暂停。' : hud.note) }}</p>
          <label v-if="!error && phase !== 'paused'" class="expedition-difficulty">探索难度<select v-model="difficulty"><option value="standard">标准 · 3 分钟</option><option value="practice">练习 · 5 分钟，巡逻更慢</option></select></label>
          <button v-if="!error" class="button button-primary" type="button" @click="phase === 'paused' ? resume() : start()">{{ phase === 'paused' ? '继续探索' : phase === 'ready' ? '开始探索' : '再玩一次' }}</button>
          <RouterLink v-else class="button button-primary" to="/wasteland?mode=story">进入三十天剧情</RouterLink>
        </div></div>
        <div v-if="phase === 'playing'" class="expedition-camera"><button type="button" aria-label="向左旋转视角" @click="rotate(-1)">↶</button><button type="button" aria-label="向右旋转视角" @click="rotate(1)">↷</button><button type="button" aria-label="放大" @click="zoomBy(-2)">＋</button><button type="button" aria-label="缩小" @click="zoomBy(2)">−</button><button type="button" @click="pause">暂停</button></div>
        <div v-if="phase === 'playing'" class="expedition-touch">
          <div ref="joystick" class="expedition-stick" aria-label="拖动摇杆移动" @pointerdown.stop.prevent="stickStart" @pointermove.stop.prevent="stickMove" @pointerup="stickStop" @pointercancel="stickStop" @lostpointercapture="stickStop"><span :style="{ transform: `translate(${stick.x * 26}px, ${stick.z * 26}px)` }">✥</span></div>
          <div><button type="button" @pointerdown.stop.prevent="sprinting = true" @pointerup="sprinting = false" @pointercancel="sprinting = false" @pointerleave="sprinting = false">冲刺</button><button type="button" @click="act">拾取 / 修复</button><button type="button" @click="aid">急救</button></div>
        </div>
      </div>
      <aside class="expedition-brief"><p class="section-kicker">你的行动清单</p><h2>从营地，到晨光。</h2><ol><li :class="{ complete: hud.scrap >= 4 || hud.repaired }">搜集零件 <strong>{{ hud.repaired ? '完成' : `${hud.scrap} / 4` }}</strong></li><li :class="{ complete: hud.cells >= 2 || hud.repaired }">找到电芯 <strong>{{ hud.repaired ? '完成' : `${hud.cells} / 2` }}</strong></li><li :class="{ complete: hud.repaired }">靠近蓝色信标，修复</li><li :class="{ complete: phase === 'won' }">走进绿色撤离坪</li></ol><ExpeditionMap :player="hud" :loot="hud.loot" :enemies="hud.enemies" :objective="hud.objective" /><p class="expedition-note" role="status" aria-live="polite">{{ hud.note }}</p><p>急救包：{{ hud.meds }} 个<br>箱子＝零件 · 蓝柱＝电芯<br>巡逻者会追踪靠近的人。</p><div id="game-instructions"><h3>不是只有点击。</h3><p>WASD / 方向键移动，Shift 冲刺，E 拾取或修复，F 急救，Esc 暂停。移动方向随视角旋转。</p><p>手机可拖动左下摇杆，配合右侧操作按钮。先点击游戏区域获取键盘焦点。地图固定北向，距离为直线示意，不会自动穿墙寻路。</p></div><small>探索模式仅在本机运行，不上传数据，离开后不保存进度。剧情模式的旧存档保持独立。</small></aside>
    </section>
  </main>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import { RouterLink } from 'vue-router'
import { createExpedition, heal, interact, nearby, screenDirection, stepExpedition } from '../features/wasteland/expedition'
import { createWastelandScene } from '../features/wasteland/scene'
import { expeditionObjective } from '../features/wasteland/navigation'
import ExpeditionMap from '../components/ExpeditionMap.vue'
import { useExpandedScene } from '../utils/useExpandedScene'
const { expanded, toggle: toggleScene } = useExpandedScene(() => pause())
const stage = ref(null), mount = ref(null), joystick = ref(null), phase = ref('ready'), error = ref(''), sprinting = ref(false), stick = ref({ x: 0, z: 0 })
let state = createExpedition(), scene, frame = 0, last = 0, published = 0, painted = 0, yaw = Math.PI / 4, zoom = 18, pointer = null, motion
const keys = new Set()
const difficulty = ref('standard')
const snapshot = () => ({ ...state.player, difficulty: state.difficulty, limitSeconds: state.limitSeconds, elapsed: state.elapsed, repaired: state.repaired, note: state.note, loot: state.loot.map(item => ({ ...item })), enemies: state.enemies.map(enemy => ({ ...enemy })), objective: expeditionObjective(state), nearby: nearby(state) })
const hud = shallowRef(snapshot())
const remaining = computed(() => { const n = Math.ceil(hud.value.limitSeconds - hud.value.elapsed); return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}` })
function clearInput() { keys.clear(); stick.value = { x: 0, z: 0 }; sprinting.value = false; pointer = null }
function draw(moving = false) { scene?.render(state, yaw, zoom, motion?.matches, moving) }
function sync() { hud.value = snapshot(); draw() }
function focusStage(event) { if (!event.target.closest('button, a')) stage.value?.focus({ preventScroll: true }) }
function tick(now) {
  if (phase.value !== 'playing') return
  const seconds = last ? Math.min((now - last) / 1000, .05) : 0; last = now
  const sx = Number(keys.has('d') || keys.has('arrowright')) - Number(keys.has('a') || keys.has('arrowleft')) + stick.value.x
  const sz = Number(keys.has('s') || keys.has('arrowdown')) - Number(keys.has('w') || keys.has('arrowup')) + stick.value.z
  const input = screenDirection(sx, sz, yaw)
  stepExpedition(state, { ...input, sprint: keys.has('shift') || sprinting.value }, seconds)
  if (now - published >= 100 || state.status !== 'playing') { hud.value = snapshot(); published = now }
  if (now - painted >= 1000 / 30 || state.status !== 'playing') { draw(Math.hypot(sx, sz) > .05); painted = now }
  if (state.status !== 'playing') { phase.value = state.status; clearInput(); return }
  frame = requestAnimationFrame(tick)
}
function resume() { if (!scene || error.value) return; clearInput(); phase.value = 'playing'; last = 0; stage.value?.focus({ preventScroll: true }); cancelAnimationFrame(frame); frame = requestAnimationFrame(tick) }
function start() { state = createExpedition('晨光营地', { difficulty: difficulty.value }); sync(); resume() }
function pause() { if (phase.value !== 'playing') return; phase.value = 'paused'; cancelAnimationFrame(frame); clearInput(); sync() }
function act() { if (phase.value === 'playing') { interact(state); sync(); stage.value?.focus({ preventScroll: true }) } }
function aid() { if (phase.value === 'playing') { heal(state); sync(); stage.value?.focus({ preventScroll: true }) } }
function rotate(direction) { yaw += direction * Math.PI / 4; draw(); stage.value?.focus({ preventScroll: true }) }
function zoomBy(delta) { zoom = Math.max(9, Math.min(24, zoom + delta)); draw(); stage.value?.focus({ preventScroll: true }) }
function keyDown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey || document.activeElement !== stage.value) return
  const key = event.key.toLowerCase()
  if (!['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'shift', 'e', 'f', 'escape'].includes(key)) return
  event.preventDefault()
  if (key === 'escape' && !event.repeat) { phase.value === 'paused' ? resume() : pause(); return }
  if (phase.value !== 'playing') return
  keys.add(key)
  if (!event.repeat && key === 'e') act()
  if (!event.repeat && key === 'f') aid()
}
function keyUp(event) { keys.delete(event.key.toLowerCase()) }
function stickStart(event) { if (phase.value !== 'playing') return; pointer = event.pointerId; event.currentTarget.setPointerCapture(pointer); stickMove(event); stage.value?.focus({ preventScroll: true }) }
function stickMove(event) { if (pointer !== event.pointerId) return; const rect = joystick.value.getBoundingClientRect(); let x = (event.clientX - rect.left - rect.width / 2) / 35, z = (event.clientY - rect.top - rect.height / 2) / 35; const length = Math.max(1, Math.hypot(x, z)); stick.value = { x: x / length, z: z / length } }
function stickStop(event) { if (pointer === event.pointerId) { pointer = null; stick.value = { x: 0, z: 0 } } }
function visibility() { if (document.hidden) pause() }
function blur() { pause() }
function contextLost(event) { event.preventDefault(); pause(); error.value = '图形上下文已丢失。请刷新页面，或切换到不需要显卡的剧情模式。' }
onMounted(() => {
  motion = window.matchMedia('(prefers-reduced-motion: reduce)')
  try { scene = createWastelandScene(mount.value, state); scene.onResize = () => draw(); draw(); scene.canvas.addEventListener('webglcontextlost', contextLost) }
  catch (cause) { error.value = cause.message || '3D 场景暂时无法加载，请进入剧情模式。' }
  window.addEventListener('keydown', keyDown); window.addEventListener('keyup', keyUp); window.addEventListener('blur', blur); document.addEventListener('visibilitychange', visibility)
})
onUnmounted(() => {
  cancelAnimationFrame(frame); clearInput(); window.removeEventListener('keydown', keyDown); window.removeEventListener('keyup', keyUp); window.removeEventListener('blur', blur); document.removeEventListener('visibilitychange', visibility)
  scene?.canvas.removeEventListener('webglcontextlost', contextLost); scene?.dispose()
})
</script>
<style scoped>
.expedition-stage.is-expanded{position:fixed;inset:12px;height:auto!important;z-index:80;box-shadow:0 0 0 20px #f5f5f7}.expedition-expand{position:absolute;top:80px;left:16px;min-height:44px;padding:10px 14px;border:1px solid #fff;border-radius:12px;color:#28566e;background:#ffffffe8;font-size:14px;cursor:pointer;z-index:2}.expedition-hud meter{display:block;width:90px;height:7px;margin-top:5px;accent-color:#4f967a}.expedition-context{position:absolute;top:140px;left:16px;max-width:calc(100% - 32px);display:grid;gap:6px;padding:12px 15px;border-radius:14px;background:#ffffffe8;color:#335949;font-size:14px;pointer-events:none}.expedition-context button{pointer-events:auto;cursor:pointer;min-height:44px;padding:10px;border-radius:9px;background:#edf4fc;color:#0066cc;text-align:left;font-size:14px}.expedition-context small{font-size:14px;color:#65716c}.expedition-difficulty{display:grid;gap:8px;font-size:14px;margin:18px 0;color:#4b6058}.expedition-difficulty select{width:100%;padding:10px;border:1px solid var(--border);border-radius:10px;background:#fff;font-size:16px}.expedition-camera button,.expedition-touch button{min-height:44px;min-width:44px}.expedition-brief ol{margin-bottom:0}@media(max-width:900px){.expedition-brief .expedition-map{grid-row:2/5;grid-column:2;margin:0}}@media(max-width:540px){.expedition-stage.is-expanded{inset:6px}.expedition-context{top:150px;font-size:14px}.expedition-hud{flex-wrap:nowrap}.expedition-hud meter{width:70px}.expedition-camera{top:80px!important;right:10px!important;gap:3px!important}.expedition-camera button{padding:8px;min-width:36px}.expedition-expand{left:10px;top:80px;font-size:14px;padding:10px}.expedition-brief .expedition-map{margin:20px 0;max-width:none}}
.expedition-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:22px;margin:25px 0 30px}.expedition-heading h1{font-size:clamp(38px,5vw,64px);letter-spacing:-.05em;margin:12px 0}.expedition-tag{padding:10px 14px;border:1px solid var(--border);border-radius:99px;font-size:14px;white-space:nowrap;color:var(--muted)}.expedition-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:22px}.expedition-stage{position:relative;height:620px;overflow:hidden;border-radius:24px;background:#e5eceb;outline-offset:5px}.expedition-canvas,.expedition-canvas :deep(canvas){width:100%;height:100%;display:block}.expedition-hud{position:absolute;top:16px;left:16px;right:16px;display:flex;gap:8px;pointer-events:none}.expedition-hud>*{padding:10px 12px;background:#ffffffdf;border-radius:99px;font-size:14px}.expedition-hud strong{margin-left:auto}.expedition-overlay{position:absolute;inset:0;display:grid;place-items:center;padding:25px;background:#e5eceb50;backdrop-filter:blur(4px)}.expedition-overlay>div{background:#fffffff0;border:1px solid #fff;padding:35px;border-radius:25px;max-width:400px;box-shadow:0 15px 50px #44584c15}.expedition-overlay h2{font-size:30px;letter-spacing:-.035em}.expedition-overlay p{font-size:16px;line-height:1.9;color:var(--muted)}.expedition-camera{position:absolute;right:14px;top:67px;display:flex;gap:5px}.expedition-camera button,.expedition-touch button{border:1px solid #ffffffa0;background:#ffffffe6;border-radius:12px;color:#28566e;padding:10px;cursor:pointer}.expedition-touch{position:absolute;bottom:20px;left:20px;right:20px;display:flex;align-items:flex-end;justify-content:space-between;gap:20px}.expedition-touch>div:last-child{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}.expedition-stick{flex:0 0 88px;height:88px;border-radius:50%;background:#ffffff85;border:1px solid #fff;touch-action:none;display:grid;place-items:center;user-select:none}.expedition-stick span{width:48px;height:48px;display:grid;place-items:center;border-radius:50%;background:#ffffffe8;font-size:24px;color:#587377;pointer-events:none}.expedition-brief{border:1px solid var(--border);border-radius:24px;background:#fff;padding:24px}.expedition-brief h2{font-size:23px;letter-spacing:-.035em}.expedition-brief ol{padding-left:20px;line-height:2.8;font-size:16px}.expedition-brief li strong{float:right;color:#0066cc}.expedition-brief .complete{color:#27774d}.expedition-brief p{color:var(--muted);font-size:14px;line-height:1.9}.expedition-note{padding:14px;background:#eef5fb;border-radius:14px;min-height:80px}.expedition-brief h3{font-size:16px}.expedition-brief small{display:block;font-size:14px;color:var(--muted);line-height:1.8}@media(max-width:900px){.expedition-layout{grid-template-columns:1fr}.expedition-stage{height:560px}.expedition-brief{display:grid;grid-template-columns:1fr 1fr;gap:0 20px}.expedition-brief>small{grid-column:1/-1}.expedition-heading{align-items:flex-start}.expedition-tag{display:none}}@media(max-width:540px){.expedition-stage{height:520px;border-radius:18px}.expedition-hud{top:10px;left:10px;right:10px}.expedition-hud>*{padding:9px;font-size:14px}.expedition-overlay>div{padding:22px}.expedition-overlay h2{font-size:25px}.expedition-brief{display:block}.expedition-touch{bottom:14px;left:12px;right:12px}.expedition-touch button{padding:10px 8px;font-size:14px}}
@media(max-width:380px){.expedition-camera{top:132px!important}.expedition-camera button{min-width:44px}.expedition-context{top:194px}}
</style>
