// Original winter settlement simulation, not a port of a commercial game's assets/code.
export const WINTER_DAY = 48
export const WINTER_BUILDINGS = Object.freeze([
  { id: 'hut', name: '保温住宅', wood: 14, iron: 2, note: '增加 4 个床位；放在暖炉供热圈内。' },
  { id: 'sawmill', name: '锯木场', wood: 12, iron: 2, note: '伐木工效率提高；每次升级再提升。' },
  { id: 'coal', name: '燃料站', wood: 14, iron: 4, note: '采煤工效率提高，保障暖炉燃料。' },
  { id: 'kitchen', name: '猎人厨房', wood: 14, iron: 3, note: '食物工效率提高，丰盛配给更可持续。' },
  { id: 'mine', name: '铁矿井', wood: 20, iron: 4, note: '允许矿工生产铁，用于高阶建筑。' },
  { id: 'clinic', name: '医务所', wood: 18, iron: 6, note: '医护人员缓慢恢复全体居民健康。' },
  { id: 'workshop', name: '研究工坊', wood: 22, iron: 8, note: '解锁保温、机械与医学研究。' },
  { id: 'outpost', name: '远征哨站', wood: 20, iron: 6, note: '派 2 人寻找燃料、物资或幸存者。' },
])
export const WINTER_JOBS = Object.freeze([{ id: 'wood', name: '伐木' }, { id: 'coal', name: '采煤' }, { id: 'food', name: '狩猎' }, { id: 'iron', name: '采铁' }, { id: 'medic', name: '医护' }])
export const WINTER_RESEARCH = Object.freeze([
  { id: 'insulation', name: '保温墙板', wood: 16, iron: 6, note: '居民体感温度 +7°C。' },
  { id: 'tools', name: '机械工具', wood: 18, iron: 8, note: '资源生产提高 30%。' },
  { id: 'medicine', name: '基础医学', wood: 14, iron: 8, note: '医护治疗提高 60%。' },
])
const clamp = (n, a, b) => Math.max(a, Math.min(b, n))
const totalJobs = s => Object.values(s.jobs).reduce((a, b) => a + b, 0)
const count = (s, kind) => s.buildings.filter(b => b.kind === kind).reduce((sum, b) => sum + b.level, 0)
function log(s, text) { if (s.notes.at(-1) !== text) s.notes.push(text); s.notes = s.notes.slice(-7) }
export function createWinter(endless = false) {
  const s = { status: 'playing', endless: Boolean(endless), day: 1, clock: 0, elapsed: 0, residents: 6, health: 100, morale: 85, resources: { wood: 42, coal: 38, food: 35, iron: 20 }, jobs: { wood: 2, coal: 2, food: 2, iron: 0, medic: 0 }, furnace: 1, heatMode: 1, ration: 'normal', buildings: [], ids: 1, research: [], expedition: null, gatherCooldown: 0, choices: [], claimed: [], supplyBonus: 0, notes: ['先建锯木场和燃料站。寒潮前升级暖炉，安排食物与医护。'] }
  winterClimate(s); return s
}
export function winterCapacity(s) { return 6 + count(s, 'hut') * 4 }
export function winterIdle(s) { return Math.max(0, s.residents - totalJobs(s) - (s.expedition ? 2 : 0)) }
export function winterClimate(s) {
  s.storm = s.clock >= 34 || (s.day >= 4 && s.clock >= 24)
  s.outside = -18 - Math.min(9, s.day - 1) * 6 - (s.storm ? 14 : 0)
  s.radius = 1.6 + s.furnace * .65
  const coldHomes = s.buildings.filter(b => b.kind === 'hut' && Math.hypot(b.x - 3, b.y - 3) > s.radius).length
  const powered = s.heatMode > 0 && s.resources.coal > 0
  s.comfort = s.outside + (powered ? 28 + s.furnace * 10 + (s.heatMode === 2 ? 14 : 0) : 0) + (s.research.includes('insulation') ? 7 : 0) + s.supplyBonus - coldHomes * 3
  s.powered = powered
}
export function winterPlacement(s, kind, x, y) {
  const def = WINTER_BUILDINGS.find(b => b.id === kind)
  if (s.status !== 'playing' || s.choices.length || !def || !Number.isInteger(x) || !Number.isInteger(y) || x < 0 || x > 6 || y < 0 || y > 6) return { ok: false, reason: '当前不能建造。' }
  if ((x === 3 && y === 3) || s.buildings.some(b => b.x === x && b.y === y)) return { ok: false, reason: '这块土地已被占用。' }
  if (s.resources.wood < def.wood || s.resources.iron < def.iron) return { ok: false, reason: '木材或铁不足，先安排采集。' }
  if (s.buildings.length >= 30) return { ok: false, reason: '最多建造 30 座设施。' }
  return { ok: true, reason: `${def.name}：${def.wood} 木材 · ${def.iron} 铁` }
}
export function buildWinter(s, kind, x, y) {
  const at = winterPlacement(s, kind, x, y); if (!at.ok) { log(s, at.reason); return false }
  const def = WINTER_BUILDINGS.find(b => b.id === kind)
  s.resources.wood -= def.wood; s.resources.iron -= def.iron
  s.buildings.push({ id: s.ids++, kind, x, y, level: 1 }); log(s, `${def.name}建成，生产设施需要分配对应工人。`); winterClimate(s); return true
}
export function upgradeWinterBuilding(s, id) {
  if (s.status !== 'playing' || s.choices.length) return false
  const b = s.buildings.find(item => item.id === id); if (!b || b.level >= 3) return false
  const def = WINTER_BUILDINGS.find(item => item.id === b.kind), wood = def.wood * b.level, iron = def.iron * b.level
  if (s.resources.wood < wood || s.resources.iron < iron) { log(s, `升级需要 ${wood} 木材、${iron} 铁。`); return false }
  s.resources.wood -= wood; s.resources.iron -= iron; b.level++; winterClimate(s); log(s, `${def.name}升至 ${b.level} 级。`); return true
}
export function upgradeFurnace(s) {
  if (s.status !== 'playing' || s.choices.length || s.furnace >= 4) return false
  const wood = 18 + s.furnace * 10, iron = 4 + s.furnace * 4
  if (s.resources.wood < wood || s.resources.iron < iron) { log(s, `暖炉升级需要 ${wood} 木材、${iron} 铁。`); return false }
  s.resources.wood -= wood; s.resources.iron -= iron; s.furnace++; winterClimate(s); log(s, `暖炉升至 ${s.furnace} 级，供热圈扩大。`); return true
}
export function assignWinter(s, job, delta) {
  if (s.status !== 'playing' || s.choices.length || !WINTER_JOBS.some(j => j.id === job) || ![-1, 1].includes(delta)) return false
  if (delta > 0 && (!winterIdle(s) || (job === 'iron' && !count(s, 'mine')) || (job === 'medic' && !count(s, 'clinic')))) return false
  if (delta < 0 && !s.jobs[job]) return false
  s.jobs[job] += delta; return true
}
export function researchWinter(s, id) {
  const def = WINTER_RESEARCH.find(r => r.id === id)
  if (s.status !== 'playing' || s.choices.length || !def || !count(s, 'workshop') || s.research.includes(id) || s.resources.wood < def.wood || s.resources.iron < def.iron) return false
  s.resources.wood -= def.wood; s.resources.iron -= def.iron; s.research.push(id); winterClimate(s); log(s, `${def.name}研究完成。`); return true
}
export function gatherWinter(s, kind) {
  if (s.status !== 'playing' || s.choices.length || !['wood', 'coal', 'food'].includes(kind) || s.gatherCooldown > 0) return false
  s.resources[kind] += 4; s.gatherCooldown = 3; log(s, '领取紧急野外补给 +4；3 个游戏秒后可再次领取。'); return true
}
export function setWinterHeat(s, mode) { if (s.status !== 'playing' || s.choices.length || ![0, 1, 2].includes(mode)) return false; s.heatMode = mode; winterClimate(s); return true }
export function setWinterRation(s, ration) { if (s.status !== 'playing' || s.choices.length || !['scarce', 'normal', 'generous'].includes(ration)) return false; s.ration = ration; return true }
export function sendWinterExpedition(s, destination) {
  if (s.status !== 'playing' || s.choices.length || s.expedition || !count(s, 'outpost') || !['fuel', 'ruins', 'survivors'].includes(destination)) return false
  if (s.residents < 4) return false
  let needed = Math.max(0, 2 - winterIdle(s))
  for (const job of ['wood', 'coal', 'food', 'iron', 'medic']) while (needed > 0 && s.jobs[job] > 0) { s.jobs[job]--; needed-- }
  s.expedition = { destination, remaining: 20, total: 20 }; log(s, '2 位居民出发，岗位已腾出；归来后需重新分工。'); return true
}
function expeditionReturn(s) {
  const where = s.expedition.destination; s.expedition = null
  if (where === 'fuel') { s.resources.coal += 32; s.resources.wood += 10; log(s, '远征归来：32 煤、10 木材。') }
  if (where === 'ruins') { s.resources.iron += 18; s.resources.wood += 20; log(s, '远征归来：18 铁、20 木材。') }
  if (where === 'survivors') { const added = Math.min(3, winterCapacity(s) - s.residents); s.residents += added; s.resources.food += 12; log(s, `救援归来：${added} 位居民安置成功；床位不足者未加入。食物 +12。`) }
}
export function chooseWinterSupply(s, id) {
  if (s.status !== 'playing' || !s.choices.some(c => c.id === id)) return false
  if (id === 'fuel') { s.resources.coal += 20; s.resources.wood += 14 }
  if (id === 'care') { s.resources.food += 18; s.health = Math.min(100, s.health + 12) }
  if (id === 'lining') s.supplyBonus += 3
  s.choices = []; log(s, '黎明补给已领取，下一天开始。'); winterClimate(s); return true
}
export function stepWinter(s, seconds) {
  if (s.status !== 'playing' || s.choices.length || !Number.isFinite(seconds) || seconds <= 0) return
  const dt = Math.min(.1, seconds); s.elapsed += dt; s.clock += dt; s.gatherCooldown = Math.max(0, s.gatherCooldown - dt); winterClimate(s)
  const efficiency = (.65 + s.health / 285) * (s.research.includes('tools') ? 1.3 : 1) * (s.storm ? .78 : 1)
  s.resources.wood += s.jobs.wood * (.3 + count(s, 'sawmill') * .25) * efficiency * dt
  s.resources.coal += s.jobs.coal * (.27 + count(s, 'coal') * .23) * efficiency * dt
  s.resources.food += s.jobs.food * (.4 + count(s, 'kitchen') * .23) * efficiency * dt
  s.resources.iron += s.jobs.iron * count(s, 'mine') * .2 * efficiency * dt
  const fuel = s.heatMode === 0 ? 0 : (.15 + s.furnace * .1) * (s.heatMode === 2 ? 2.2 : 1)
  s.resources.coal = Math.max(0, s.resources.coal - fuel * dt)
  const appetite = s.ration === 'scarce' ? .07 : s.ration === 'generous' ? .15 : .1
  s.resources.food = Math.max(0, s.resources.food - s.residents * appetite * dt)
  const cold = Math.max(0, 5 - s.comfort), hungry = s.resources.food < .01
  const heal = s.jobs.medic * count(s, 'clinic') * .22 * (s.research.includes('medicine') ? 1.6 : 1)
  s.health = clamp(s.health + (heal + (s.comfort >= 10 && !hungry ? .06 : 0) - cold * .08 - (hungry ? .6 : 0)) * dt, 0, 100)
  s.morale = clamp(s.morale + ((s.ration === 'generous' && !hungry ? .2 : s.ration === 'scarce' ? -.12 : .02) - cold * .024 - (hungry ? .3 : 0)) * dt, 0, 100)
  if (s.expedition) { s.expedition.remaining -= dt; if (s.expedition.remaining <= 0) expeditionReturn(s) }
  if (s.health <= 0 || s.morale <= 0) { s.status = 'lost'; log(s, '聚落无法继续维持。下次优先保证供热、食物和医护。'); return }
  if (s.clock >= WINTER_DAY) {
    s.clock -= WINTER_DAY; s.day++
    if (!s.endless && s.day > 5) { s.status = 'won'; log(s, '五场寒潮之后，火种仍在。聚落迎来了救援！') }
    else { s.choices = [{ id: 'fuel', name: '燃料物资', note: '+20 煤，+14 木材。' }, { id: 'care', name: '医疗口粮', note: '+18 食物，健康 +12。' }, { id: 'lining', name: '加厚内衬', note: '永久体感温度 +3°C。' }]; log(s, '黎明到来。时间暂停，选择一份补给。') }
  }
  winterClimate(s)
}
