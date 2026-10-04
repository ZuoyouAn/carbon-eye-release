// Original local-only 3D game rules. No account, server, payments or remote models.
export const LIMIT_SECONDS = 180
export const WORLD = Object.freeze({
  bound: 17,
  spawn: { x: -12, z: 12 }, beacon: { x: 0, z: -10 }, exit: { x: 12, z: -12 },
  buildings: [
    { x: -8, z: -8, w: 5, d: 5, h: 4.4 }, { x: -8, z: 0, w: 4, d: 5, h: 3.2 },
    { x: 8, z: 10, w: 4, d: 4, h: 3.5 }, { x: 9, z: -5, w: 4, d: 4, h: 5 },
    { x: -1, z: 16, w: 6, d: 2, h: 2.4 },
  ],
})
const LOOT = [
  ['scrap', -10, 12], ['scrap', -6, 12], ['scrap', 0, 12], ['scrap', 4, 8], ['scrap', 12, 4], ['scrap', 12, -1],
  ['cell', -2, 6], ['cell', 6, 0], ['med', -12, 6], ['med', 3, -4],
]
const clamp = (v, low, high) => Math.max(low, Math.min(high, v))
const distance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z)
function hash(seed) { let value = 2166136261; for (const char of seed) { value ^= char.charCodeAt(0); value = Math.imul(value, 16777619) } return value >>> 0 }
export function createExpedition(seed = '晨光营地', { difficulty = 'standard' } = {}) {
  if (typeof seed !== 'string' || !seed.trim() || seed.length > 64) throw new Error('世界种子需要1至64个字符。')
  if (!['standard', 'practice'].includes(difficulty)) throw new Error('请选择标准探索或练习模式。')
  const value = hash(seed)
  return {
    seed, difficulty, limitSeconds: difficulty === 'practice' ? 300 : LIMIT_SECONDS, status: 'playing', elapsed: 0, repaired: false,
    player: { ...WORLD.spawn, facing: Math.PI, health: 100, stamina: 100, invulnerable: 3, scrap: 0, cells: 0, meds: 1 },
    loot: LOOT.map(([kind, x, z], id) => ({ id, kind, x, z, taken: false })),
    enemies: [{ x: 6, z: -12, homeX: 6, homeZ: -12, phase: value % 360 / 57.3 }, { x: -13, z: -7, homeX: -13, homeZ: -7, phase: value % 120 / 57.3 }],
    note: '沿街搜寻4个零件和2块电芯。靠近物资后按 E 拾取。', changes: 0,
  }
}
export function walkable(x, z, radius = .36) {
  if (!Number.isFinite(x) || !Number.isFinite(z) || Math.abs(x) > WORLD.bound - radius || Math.abs(z) > WORLD.bound - radius) return false
  return !WORLD.buildings.some(b => {
    const nearestX = clamp(x, b.x - b.w / 2, b.x + b.w / 2), nearestZ = clamp(z, b.z - b.d / 2, b.z + b.d / 2)
    return Math.hypot(x - nearestX, z - nearestZ) < radius
  })
}
function move(body, dx, dz) {
  const x = clamp(body.x + dx, -16.64, 16.64), z = clamp(body.z + dz, -16.64, 16.64)
  if (walkable(x, body.z)) body.x = x
  if (walkable(body.x, z)) body.z = z
}
function say(state, note) { state.note = note; state.changes++ }
export function screenDirection(x, z, yaw) {
  return { x: Math.cos(yaw) * x + Math.sin(yaw) * z, z: -Math.sin(yaw) * x + Math.cos(yaw) * z }
}
export function nearby(state) {
  const candidates = state.loot.filter(item => !item.taken).map(item => ({ ...item, action: 'loot', distance: distance(state.player, item) }))
  if (!state.repaired) candidates.push({ ...WORLD.beacon, action: 'repair', distance: distance(state.player, WORLD.beacon) })
  return candidates.filter(item => item.distance <= 1.9).sort((a, b) => a.distance - b.distance)[0] || null
}
export function interact(state) {
  if (state.status !== 'playing') return false
  const item = nearby(state)
  if (!item) { say(state, '再靠近一点：箱子是零件，蓝色电芯，白色补给是急救包。'); return false }
  if (item.action === 'repair') {
    if (state.player.scrap < 4 || state.player.cells < 2) { say(state, '修复信标需要4个零件与2块电芯。'); return false }
    state.player.scrap -= 4; state.player.cells -= 2; state.repaired = true
    say(state, '信标亮了！前往东北方的绿色撤离坪，别被巡逻者追上。'); return true
  }
  state.loot.find(row => row.id === item.id).taken = true
  if (item.kind === 'scrap') { state.player.scrap++; say(state, `拾取零件：${state.player.scrap} / 4`) }
  if (item.kind === 'cell') { state.player.cells++; say(state, `拾取电芯：${state.player.cells} / 2`) }
  if (item.kind === 'med') { state.player.meds++; say(state, '找到急救包。受伤后按 F 使用。') }
  return true
}
export function heal(state) {
  if (state.status !== 'playing' || state.player.meds <= 0 || state.player.health >= 100) return false
  state.player.meds--; state.player.health = Math.min(100, state.player.health + 35)
  say(state, '使用急救包，恢复35点健康。'); return true
}
export function stepExpedition(state, input = {}, seconds = 1 / 60) {
  if (state.status !== 'playing') return state
  const dt = clamp(Number.isFinite(seconds) ? seconds : 0, 0, .05)
  if (!dt) return state
  const limit = state.limitSeconds || LIMIT_SECONDS, practice = state.difficulty === 'practice'
  state.elapsed = Math.min(limit, state.elapsed + dt)
  const p = state.player
  let x = Number.isFinite(input.x) ? clamp(input.x, -1, 1) : 0, z = Number.isFinite(input.z) ? clamp(input.z, -1, 1) : 0
  const magnitude = Math.hypot(x, z)
  if (magnitude > 1) { x /= magnitude; z /= magnitude }
  const sprinting = Boolean(input.sprint && magnitude > .05 && p.stamina > 1)
  const speed = sprinting ? 5.8 : 3.5
  move(p, x * dt * speed, z * dt * speed)
  if (magnitude > .05) p.facing = Math.atan2(x, z)
  p.stamina = clamp(p.stamina + (sprinting ? -28 : 18) * dt, 0, 100)
  p.invulnerable = Math.max(0, p.invulnerable - dt)
  for (const enemy of state.enemies) {
    const chase = distance(enemy, p) < 5.5
    const target = chase ? p : { x: enemy.homeX + Math.sin(state.elapsed * .35 + enemy.phase) * 2, z: enemy.homeZ + Math.cos(state.elapsed * .35 + enemy.phase) * 2 }
    const length = distance(enemy, target)
    if (length > .1) { const speed = (chase ? 2.5 : .85) * (practice ? .65 : 1); move(enemy, (target.x - enemy.x) / length * dt * speed, (target.z - enemy.z) / length * dt * speed) }
    if (distance(enemy, p) < .85 && !p.invulnerable) { p.health = Math.max(0, p.health - (practice ? 8 : 12)); p.invulnerable = 1.5; say(state, '被巡逻者发现了！按住 Shift 冲刺，或用 F 急救。') }
  }
  if (p.health <= 0 || state.elapsed >= limit) { state.status = 'lost'; say(state, p.health <= 0 ? '本次探索结束。换条路线，再试一次。' : '撤离窗口已关闭。下一次，尽量沿开阔街道前进。') }
  else if (state.repaired && distance(p, WORLD.exit) <= 1.8) { state.status = 'won'; say(state, '晨光营地收到你的信号。你为这座城市留下了新的坐标。') }
  return state
}
