import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createExpedition, stepExpedition, WORLD, walkable, interact, nearby, heal, screenDirection, LIMIT_SECONDS } from './expedition.js'

test('seeded world is deterministic and mission supplies are sufficient', () => {
  const a = createExpedition('test'), b = createExpedition('test')
  assert.deepEqual(a, b)
  assert.equal(a.loot.filter(i => i.kind === 'cell').length, 2)
  assert.ok(a.loot.filter(i => i.kind === 'scrap').length >= 4)
  assert.ok(a.loot.every(i => walkable(i.x, i.z)))
  for (const point of [WORLD.spawn, WORLD.beacon, WORLD.exit]) assert.ok(walkable(point.x, point.z))
  for (const seed of ['', ' '.repeat(3), 99, 'a'.repeat(65)]) assert.throws(() => createExpedition(seed))
})
test('keyboard movement is continuous and diagonal speed is normalized', () => {
  const a = createExpedition(), b = createExpedition(); a.enemies = []; b.enemies = []
  for (let i = 0; i < 60; i++) { stepExpedition(a, { x: 1 }); stepExpedition(b, { x: 1, z: -1 }) }
  assert.ok(Math.abs(a.player.x - WORLD.spawn.x - 3.5) < .01)
  assert.ok(Math.abs(Math.hypot(b.player.x - WORLD.spawn.x, b.player.z - WORLD.spawn.z) - 3.5) < .01)
})
test('walls, map limits and large frame gaps do not allow tunneling', () => {
  const s = createExpedition(); s.player.x = -12; s.player.z = -8; s.enemies = []
  for (let i = 0; i < 600; i++) stepExpedition(s, { x: 1 }, 999)
  assert.ok(s.player.x <= -10.85 && walkable(s.player.x, s.player.z))
  assert.equal(walkable(999, 0), false); assert.equal(walkable(NaN, 0), false)
  assert.equal(walkable(WORLD.buildings[0].x, WORLD.buildings[0].z), false)
})
test('sprint spends stamina and resting restores it', () => {
  const s = createExpedition(); s.enemies = []
  for (let i = 0; i < 60; i++) stepExpedition(s, { x: 1, sprint: true })
  assert.ok(s.player.stamina < 80 && s.player.x > WORLD.spawn.x + 5)
  for (let i = 0; i < 300; i++) stepExpedition(s, {})
  assert.equal(s.player.stamina, 100)
})
test('loot needs proximity, can only be taken once, and repair needs real inventory', () => {
  const s = createExpedition(); assert.equal(interact(s), false)
  s.player.x = s.loot[0].x; s.player.z = s.loot[0].z
  assert.equal(nearby(s).action, 'loot'); assert.equal(interact(s), true); assert.equal(s.player.scrap, 1)
  assert.equal(interact(s), false); assert.equal(s.player.scrap, 1)
  Object.assign(s.player, WORLD.beacon); assert.equal(interact(s), false); assert.equal(s.repaired, false)
})
test('collect, repair and extract is a complete winning loop', () => {
  const s = createExpedition()
  for (const row of s.loot.filter(i => i.kind !== 'med')) { s.player.x = row.x; s.player.z = row.z; interact(s) }
  Object.assign(s.player, WORLD.exit); stepExpedition(s); assert.equal(s.status, 'playing')
  Object.assign(s.player, WORLD.beacon); assert.equal(interact(s), true); assert.equal(s.repaired, true)
  Object.assign(s.player, WORLD.exit); stepExpedition(s); assert.equal(s.status, 'won')
  const previous = structuredClone(s); stepExpedition(s, { x: 1 }); interact(s); heal(s); assert.deepEqual(s, previous)
})
test('damage has a cooldown and medkit cannot be wasted at full health', () => {
  const s = createExpedition(); assert.equal(heal(s), false); assert.equal(s.player.meds, 1)
  s.player.invulnerable = 0; s.enemies = [{ ...s.player, homeX: s.player.x, homeZ: s.player.z, phase: 0 }]
  stepExpedition(s); assert.equal(s.player.health, 88)
  stepExpedition(s); assert.equal(s.player.health, 88)
  assert.equal(heal(s), true); assert.equal(s.player.health, 100); assert.equal(s.player.meds, 0)
})
test('timeout, death and invalid frame/input values stay bounded', () => {
  const s = createExpedition(); s.enemies = []; stepExpedition(s, { x: Infinity, z: NaN }, NaN)
  assert.equal(s.elapsed, 0)
  s.elapsed = LIMIT_SECONDS - .01; stepExpedition(s); assert.equal(s.status, 'lost')
  const dead = createExpedition(); dead.player.health = 0; stepExpedition(dead); assert.equal(dead.status, 'lost')
})
test('camera-relative directions preserve magnitude', () => {
  for (const yaw of [0, Math.PI / 4, Math.PI, -Math.PI / 2]) assert.ok(Math.abs(Math.hypot(...Object.values(screenDirection(0, -1, yaw))) - 1) < 1e-9)
  assert.deepEqual(screenDirection(0, -1, 0), { x: 0, z: -1 })
})
test('100 seeded random journeys keep coordinates and resources finite and valid', () => {
  for (let seed = 0; seed < 100; seed++) {
    const s = createExpedition(String(seed))
    for (let i = 0; i < 600; i++) {
      stepExpedition(s, { x: Math.sin(i + seed), z: Math.cos(i * .1), sprint: i % 4 === 0 }, .05)
      assert.ok(walkable(s.player.x, s.player.z))
      for (const key of ['health', 'stamina']) assert.ok(Number.isFinite(s.player[key]) && s.player[key] >= 0 && s.player[key] <= 100)
    }
  }
})
