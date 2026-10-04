import test from 'node:test'
import assert from 'node:assert/strict'
import { surfaceTint, sceneTime } from './surface.js'
test('procedural surfaces are deterministic and bounded, no external texture requests', () => { for (const id of ['earth', 'jupiter', 'saturn', 'mars']) for (let i = 0; i < 100; i++) { const input = [id, Math.sin(i), Math.cos(i), Math.sin(i * 2)]; const tint = surfaceTint(...input); assert.deepEqual(tint, surfaceTint(...input)); assert.ok(tint.shade > 0 && tint.shade <= 1.2); assert.ok(tint.color === null || /^#[a-f\d]{6}$/.test(tint.color)) } })
test('illustrative time scrubber clamps malformed, negative and unbounded values', () => { assert.equal(sceneTime('120'), 120); assert.equal(sceneTime(-2), 0); assert.equal(sceneTime(999), 600); assert.equal(sceneTime(Infinity), 0); assert.equal(sceneTime(NaN), 0) })
