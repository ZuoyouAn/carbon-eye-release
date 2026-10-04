import test from 'node:test'
import assert from 'node:assert/strict'
import { NASA_SOURCE, PLANETS, positionAt } from './planets.js'
test('eight identified planets remain in heliocentric order with primary-source reference', () => {
  assert.equal(PLANETS.length, 8); assert.equal(new Set(PLANETS.map(p => p.id)).size, 8)
  assert.deepEqual(PLANETS.map(p => p.order), [1, 2, 3, 4, 5, 6, 7, 8]); assert.match(NASA_SOURCE, /^https:\/\/science\.nasa\.gov\//)
  assert.equal(PLANETS.filter(p => p.type === '类地行星').length, 4)
})
test('illustrative orbits are bounded and periodic, including invalid input and huge time', () => {
  for (const planet of PLANETS) {
    const a = positionAt(planet, 0), b = positionAt(planet, planet.period)
    assert.ok(Math.abs(a.x - b.x) < 1e-10 && Math.abs(a.z - b.z) < 1e-10)
    for (const time of [NaN, Infinity, -100, 1e10]) { const p = positionAt(planet, time); assert.ok(Number.isFinite(p.x + p.z)); assert.ok(Math.abs(Math.hypot(p.x, p.z) - planet.orbit) < 1e-9) }
  }
})
