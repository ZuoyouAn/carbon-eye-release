// Original single-player rules. No network, wall-clock dependency, or hidden autoplay.
export const PROFESSIONS = Object.freeze([
  { id: 'ranger', name: '游侠', color: '#247ba0', weapon: '星弩', note: '精准远射，弹幕与贯穿路线。', hp: 100, damage: 22, interval: .48 },
  { id: 'guardian', name: '守卫', color: '#b87937', weapon: '环刃', note: '近身范围攻击，重装与狂战路线。', hp: 150, damage: 36, interval: .7 },
  { id: 'mage', name: '术士', color: '#7960ad', weapon: '秘法星球', note: '穿透法球，风暴与寒霜路线。', hp: 90, damage: 27, interval: .65 },
])
const BRANCHES = {
  ranger: [{ id: 'volley', name: '弹幕游侠', note: '额外 2 发投射物，基础伤害 +6。' }, { id: 'sniper', name: '穿云猎手', note: '贯穿 +3，伤害 ×1.6。' }],
  guardian: [{ id: 'bastion', name: '坚壁守卫', note: '护甲 +8，最大生命 +70，立即回满。' }, { id: 'berserker', name: '破阵狂战', note: '伤害 ×1.65，攻击间隔 ×0.8。' }],
  mage: [{ id: 'tempest', name: '风暴术士', note: '法球命中后，电弧打击附近 2 个敌人。' }, { id: 'frost', name: '寒霜术士', note: '命中减速 65%，攻击范围扩大。' }],
}
const UPGRADES = [
  { id: 'damage', name: '磨砺锋芒', note: '基础伤害 +8。' }, { id: 'haste', name: '连击节奏', note: '攻击间隔 ×0.88，最低 0.16 秒。' },
  { id: 'multi', name: '分裂星芒', note: '远程增加 1 发；守卫攻击范围 +22。' }, { id: 'vitality', name: '生命之泉', note: '最大生命 +25，恢复 35。' },
  { id: 'speed', name: '轻盈步伐', note: '移动速度 +24。' }, { id: 'magnet', name: '星尘共鸣', note: '经验吸引半径 +75。' },
  { id: 'armor', name: '坚韧皮甲', note: '护甲 +3，最低伤害仍为 2。' }, { id: 'reach', name: '延伸领域', note: '攻击范围 +35，贯穿 +1。' },
]
export const SWARM_LIMITS = Object.freeze({ enemies: 180, bullets: 240, gems: 300, effects: 70 })
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x))
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)
function random(s) { s.random = (Math.imul(s.random, 1664525) + 1013904223) >>> 0; return s.random / 4294967296 }
export function createSwarm(profession = 'ranger', difficulty = 'normal', endless = false, seed = 7319) {
  const def = PROFESSIONS.find(p => p.id === profession)
  if (!def || !['normal', 'practice'].includes(difficulty) || !Number.isInteger(seed)) throw Error('无效职业或难度。')
  return {
    status: 'playing', profession, difficulty, endless: Boolean(endless), random: seed >>> 0, elapsed: 0, ids: 1,
    player: { x: 0, y: 0, hp: def.hp, maxHp: def.hp, speed: 220, damage: def.damage, interval: def.interval, range: profession === 'guardian' ? 115 : 460, armor: 0, multi: 1, pierce: profession === 'mage' ? 1 : 0, magnet: 155, invulnerable: 0, dash: 0, dashCooldown: 0, skillCooldown: 0, shotCooldown: 0, facing: 0 },
    level: 1, xp: 0, nextXp: 5, kills: 0, bosses: 0, bossWave: 0, spawnCooldown: .4,
    animation: { stride: 0, moving: false, attack: 0, skill: 0, hurt: 0, trail: 0 },
    enemies: [], bullets: [], gems: [], effects: [], choices: [], branch: '', upgrades: {}, note: '移动收集星尘；经验满后选择强化。',
  }
}
function effect(s, x, y, radius, color, life = .3, kind = 'ring', tx = x, ty = y) {
  if (s.effects.length >= SWARM_LIMITS.effects) s.effects.shift()
  s.effects.push({ x, y, radius, color, life, maxLife: life, kind, tx, ty })
}
function offer(s) {
  if (s.choices.length || s.xp < s.nextXp) return
  s.xp -= s.nextXp; s.level++; s.nextXp = 5 + (s.level - 1) * 3
  if (s.level >= 4 && !s.branch) s.choices = BRANCHES[s.profession].map(c => ({ ...c, branch: true }))
  else {
    const pool = [...UPGRADES]
    s.choices = Array.from({ length: 3 }, () => pool.splice(Math.floor(random(s) * pool.length), 1)[0])
  }
  s.note = s.choices[0].branch ? '选择职业进阶路线，整局不可更改。' : '时间暂停，选择一项强化。'
}
export function chooseSwarmUpgrade(s, id) {
  const choice = s.choices.find(c => c.id === id)
  if (s.status !== 'playing' || !choice) return false
  const p = s.player
  if (choice.branch) {
    s.branch = id
    if (id === 'volley') { p.multi += 2; p.damage += 6 }
    if (id === 'sniper') { p.pierce += 3; p.damage *= 1.6 }
    if (id === 'bastion') { p.armor += 8; p.maxHp += 70; p.hp = p.maxHp }
    if (id === 'berserker') { p.damage *= 1.65; p.interval *= .8 }
    if (id === 'frost') p.range += 60
  } else {
    s.upgrades[id] = (s.upgrades[id] || 0) + 1
    if (id === 'damage') p.damage += 8
    if (id === 'haste') p.interval = Math.max(.16, p.interval * .88)
    if (id === 'multi') { if (s.profession === 'guardian') p.range += 22; else p.multi = Math.min(7, p.multi + 1) }
    if (id === 'vitality') { p.maxHp += 25; p.hp = Math.min(p.maxHp, p.hp + 35) }
    if (id === 'speed') p.speed = Math.min(420, p.speed + 24)
    if (id === 'magnet') p.magnet = Math.min(600, p.magnet + 75)
    if (id === 'armor') p.armor = Math.min(24, p.armor + 3)
    if (id === 'reach') { p.range = Math.min(750, p.range + 35); p.pierce = Math.min(8, p.pierce + 1) }
  }
  effect(s, p.x, p.y, 75, '#64aaa7', .65, 'level')
  s.choices = []; s.note = `获得 ${choice.name}。`; offer(s); return true
}
function hit(s, en, damage) {
  if (en.hp <= 0) return
  en.hp -= damage; en.flash = .18
  effect(s, en.x, en.y, en.radius, '#e3b878', .24, 'impact')
  effect(s, en.x, en.y - 22, Math.round(damage), '#526f85', .45, 'damage')
  if (s.branch === 'frost') en.slow = 2.2
  if (en.hp <= 0) {
    s.kills++; if (en.type === 'boss') { s.bosses++; s.player.hp = Math.min(s.player.maxHp, s.player.hp + 30) }
    if (s.gems.length >= SWARM_LIMITS.gems) { const old = s.gems.shift(); s.xp += old.value }
    s.gems.push({ id: s.ids++, x: en.x, y: en.y, value: en.type === 'boss' ? 12 : en.type === 'tank' ? 2 : 1 })
    effect(s, en.x, en.y, en.radius + 10, '#87c9b9', .42, 'burst')
  }
}
function projectile(s, angle, damage = s.player.damage) {
  if (s.bullets.length >= SWARM_LIMITS.bullets) return
  const p = s.player
  s.bullets.push({ id: s.ids++, x: p.x, y: p.y, vx: Math.cos(angle) * 650, vy: Math.sin(angle) * 650, life: p.range / 650 + .2, damage, pierce: p.pierce, hits: [] })
}
function attack(s, aim) {
  const p = s.player, targets = s.enemies.filter(e => e.hp > 0 && distance(e, p) <= p.range).sort((a, b) => distance(a, p) - distance(b, p))
  if (!targets.length && !aim) return
  p.facing = aim ? Math.atan2(aim.y, aim.x) : Math.atan2(targets[0].y - p.y, targets[0].x - p.x)
  if (s.profession === 'guardian') {
    targets.forEach(en => hit(s, en, p.damage)); effect(s, p.x, p.y, p.range, '#d6a264', .32, 'slash', p.facing)
  } else for (let i = 0; i < p.multi; i++) projectile(s, p.facing + (i - (p.multi - 1) / 2) * .14)
  s.animation.attack = .24
  if (s.profession !== 'guardian') effect(s, p.x + Math.cos(p.facing) * 26, p.y + Math.sin(p.facing) * 26, 12, s.profession === 'mage' ? '#ad8cda' : '#72c5d4', .18, 'impact')
  p.shotCooldown = p.interval
}
export function swarmSkill(s) {
  const p = s.player
  if (s.status !== 'playing' || s.choices.length || p.skillCooldown > 0) return false
  p.skillCooldown = 9; s.animation.skill = .6
  effect(s, p.x, p.y, s.profession === 'guardian' ? 210 : s.profession === 'mage' ? 280 : 135, s.profession === 'guardian' ? '#d3a264' : s.profession === 'mage' ? '#9d89d0' : '#55a5bc', .6, 'nova')
  if (s.profession === 'ranger') { for (let i = 0; i < 14; i++) projectile(s, i * Math.PI / 7, p.damage * 1.8) }
  else {
    const radius = s.profession === 'guardian' ? 210 : 280
    s.enemies.filter(e => distance(e, p) <= radius).forEach(en => { hit(s, en, p.damage * 2.4); en.slow = 3; if (s.profession === 'guardian') { const d = Math.max(1, distance(en, p)); en.knockX = (en.x - p.x) / d; en.knockY = (en.y - p.y) / d; en.knock = .3 } })
    effect(s, p.x, p.y, radius, s.profession === 'guardian' ? '#e6b96e' : '#8fb3ef', .5)
    if (s.profession === 'guardian') p.invulnerable = 1.4
  }
  return true
}
function spawn(s, boss = false) {
  if (s.enemies.length >= SWARM_LIMITS.enemies) {
    if (!boss) return
    const replace = s.enemies.filter(e => e.type !== 'boss').sort((a,b) => distance(b,s.player)-distance(a,s.player))[0]
    if (!replace) return
    s.enemies = s.enemies.filter(e => e !== replace)
  }
  const angle = random(s) * Math.PI * 2, ring = boss ? 520 : 540 + random(s) * 110, tier = Math.floor(s.elapsed / 35)
  const type = boss ? 'boss' : random(s) < .13 ? 'tank' : random(s) < .25 ? 'runner' : 'walker'
  const hp = type === 'boss' ? 700 + s.bossWave * 180 : type === 'tank' ? 75 + tier * 12 : 26 + tier * 5
  s.enemies.push({ id: s.ids++, type, x: s.player.x + Math.cos(angle) * ring, y: s.player.y + Math.sin(angle) * ring, hp, maxHp: hp, radius: boss ? 35 : type === 'tank' ? 22 : 14, speed: boss ? 62 : type === 'runner' ? 118 : type === 'tank' ? 50 : 78, slow: 0, flash: 0, pulseCooldown: 6, charge: 0 })
  if (boss) s.note = '巨型异兽出现：离开红色预警圈，边移动边输出。'
}
// Point-to-segment test prevents fast projectiles tunnelling through enemies.
function segmentDistance(en, x, y, nx, ny) {
  const dx = nx - x, dy = ny - y, den = dx * dx + dy * dy
  const t = den ? clamp(((en.x - x) * dx + (en.y - y) * dy) / den, 0, 1) : 0
  return Math.hypot(en.x - x - dx * t, en.y - y - dy * t)
}
export function stepSwarm(s, input = {}, seconds = 0) {
  if (s.status !== 'playing' || s.choices.length || !Number.isFinite(seconds) || seconds <= 0) return
  const dt = Math.min(seconds, .05), p = s.player
  s.elapsed += dt
  for (const key of ['invulnerable', 'dash', 'dashCooldown', 'skillCooldown', 'shotCooldown']) p[key] = Math.max(0, p[key] - dt)
  for (const key of ['attack', 'skill', 'hurt', 'trail']) s.animation[key] = Math.max(0, s.animation[key] - dt)
  let x = Number.isFinite(input.x) ? clamp(input.x, -1, 1) : 0, y = Number.isFinite(input.y) ? clamp(input.y, -1, 1) : 0
  const length = Math.max(1, Math.hypot(x, y)); x /= length; y /= length
  s.animation.moving = Math.hypot(x, y) > .01
  if (s.animation.moving) s.animation.stride += dt * (p.dash > 0 ? 24 : 12)
  if (input.dash && !p.dashCooldown) { p.dash = .22; p.dashCooldown = 3; p.invulnerable = .4 }
  const velocity = p.dash > 0 ? 760 : p.speed
  p.x = clamp(p.x + x * velocity * dt, -4000, 4000); p.y = clamp(p.y + y * velocity * dt, -4000, 4000)
  if (p.dash > 0 && s.animation.moving && !s.animation.trail) { effect(s, p.x, p.y, 18, '#74b4c7', .22, 'trail', p.facing); s.animation.trail = .045 }
  if (input.skill) swarmSkill(s)
  const aim = input.aim && Number.isFinite(input.aim.x) && Number.isFinite(input.aim.y) && Math.hypot(input.aim.x, input.aim.y) > .01 ? input.aim : null
  if (!p.shotCooldown && (input.auto !== false || input.fire)) attack(s, aim)
  s.spawnCooldown -= dt
  if (s.spawnCooldown <= 0) {
    const count = 1 + Math.min(4, Math.floor(s.elapsed / 28))
    for (let i = 0; i < count; i++) spawn(s)
    s.spawnCooldown = s.difficulty === 'practice' ? 1.15 : .8
  }
  const wave = Math.floor(s.elapsed / 60)
  if (wave > s.bossWave) { s.bossWave = wave; spawn(s, true) }
  for (const en of s.enemies) {
    if (en.hp <= 0) continue
    en.slow = Math.max(0, en.slow - dt); en.flash = Math.max(0, en.flash - dt)
    const d = distance(en, p), speed = en.speed * (en.slow > 0 ? .35 : 1) * (s.difficulty === 'practice' ? .72 : 1)
    if (en.knock > 0) { en.x += en.knockX * 420 * dt; en.y += en.knockY * 420 * dt; en.knock = Math.max(0, en.knock - dt) }
    else if (d > en.radius + 12 && !en.charge) { en.x += (p.x - en.x) / d * speed * dt; en.y += (p.y - en.y) / d * speed * dt }
    if (distance(en, p) < en.radius + 17 && !p.invulnerable) { p.hp = Math.max(0, p.hp - Math.max(2, (en.type === 'boss' ? 27 : 13) - p.armor) * (s.difficulty === 'practice' ? .65 : 1)); p.invulnerable = .7; s.animation.hurt = .35 }
    if (en.type === 'boss') {
      en.pulseCooldown -= dt
      if (en.pulseCooldown <= 0 && !en.charge) { en.charge = 1.1; en.pulseCooldown = 7 }
      if (en.charge > 0) { en.charge = Math.max(0, en.charge - dt); if (!en.charge) { effect(s, en.x, en.y, 150, '#d17d73', .4, 'nova'); if (distance(en, p) < 150 && !p.invulnerable) { p.hp = Math.max(0, p.hp - 32); p.invulnerable = .7; s.animation.hurt = .35 } } }
    }
  }
  for (const bullet of s.bullets) {
    const nx = bullet.x + bullet.vx * dt, ny = bullet.y + bullet.vy * dt; bullet.life -= dt
    for (const en of s.enemies) {
      if (en.hp <= 0 || bullet.hits.includes(en.id) || segmentDistance(en, bullet.x, bullet.y, nx, ny) > en.radius + 5) continue
      hit(s, en, bullet.damage); bullet.hits.push(en.id)
      if (s.branch === 'tempest') {
        s.enemies.filter(other => other !== en && other.hp > 0 && distance(en, other) < 125).slice(0, 2).forEach(other => { hit(s, other, bullet.damage * .6); effect(s, en.x, en.y, 1, '#9e94d4', .16, 'line', other.x, other.y) })
      }
      if (bullet.hits.length > bullet.pierce) { bullet.life = 0; break }
    }
    bullet.x = nx; bullet.y = ny
  }
  s.enemies = s.enemies.filter(en => en.hp > 0 && distance(en, p) < 1300)
  s.bullets = s.bullets.filter(b => b.life > 0)
  for (const gem of s.gems) {
    const d = distance(gem, p)
    if (d < p.magnet && d > 14) { const move = Math.min(d, (360 + p.magnet) * dt); gem.x += (p.x - gem.x) / d * move; gem.y += (p.y - gem.y) / d * move }
    if (d <= 18) { s.xp += gem.value; gem.value = 0; effect(s, p.x, p.y, 24, '#70babb', .24, 'pickup') }
  }
  s.gems = s.gems.filter(g => g.value > 0 && distance(g, p) < 1600)
  s.effects.forEach(e => { e.life -= dt }); s.effects = s.effects.filter(e => e.life > 0)
  if (p.hp <= 0) { s.status = 'lost'; s.note = '星灯熄灭了。试试另一条职业路线。'; return }
  if (!s.endless && s.elapsed >= 180) { s.status = 'won'; s.note = '坚持三分钟，撤离成功！无尽模式可以继续挑战。'; return }
  offer(s)
}
export function swarmBranchName(s) { return BRANCHES[s.profession].find(b => b.id === s.branch)?.name || '尚未进阶' }
