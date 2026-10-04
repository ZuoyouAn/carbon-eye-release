import test from 'node:test'
import assert from 'node:assert/strict'
import { visibleLabels } from './labels.js'
const label = (id, x, y, priority = 0) => ({ id, x, y, width: 54, height: 26, priority, visible: true })
test('selected label takes priority over overlapping ordinary labels', () => { assert.deepEqual([...visibleLabels([label('ordinary', 100, 100), label('selected', 110, 100, 3)], 300, 400)], ['selected']) })
test('labels remain away from edges, controls and invalid projections', () => { assert.equal(visibleLabels([label('edge', 0, 100), label('controls', 100, 30), label('note', 100, 390), label('invalid', NaN, 100), { ...label('hidden', 100, 100), visible: false }], 300, 400).size, 0) })
test('well-separated labels stay visible without moving their projected positions', () => { const input = [label('earth', 70, 100), label('mars', 170, 100)]; const before = structuredClone(input); assert.equal(visibleLabels(input, 300, 400).size, 2); assert.deepEqual(input, before) })
