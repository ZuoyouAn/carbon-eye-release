import test from 'node:test'
import assert from 'node:assert/strict'
import { mergeLatest, prependHistory, composerReason, HISTORY_LIMIT } from './history.js'

const rows = (start, end) => Array.from({ length: end - start + 1 }, (_, index) => ({ id: start + index, content: String(start + index) }))
test('live history refresh returns the latest window without gaps or duplicate messages', () => {
  assert.deepEqual(mergeLatest(rows(1, 50), rows(55, 104)), { items: rows(55, 104), hasNew: false })
})
test('reading history preserves existing IDs while detecting new messages', () => {
  const current = rows(1, 100), incoming = rows(75, 124)
  const result = mergeLatest(current, incoming, true)
  assert.deepEqual(result.items.map(row => row.id), current.map(row => row.id))
  assert.equal(result.hasNew, true); assert.equal(current.length, 100)
})
test('retractions update overlapping rows even when reading history', () => {
  const incoming = [{ id: 9, content: '', is_deleted: true }]
  assert.equal(mergeLatest(rows(1, 10), incoming, true).items[8].is_deleted, true)
  assert.equal(mergeLatest(rows(1, 10), incoming, true).hasNew, false)
})
test('older pagination deduplicates, sorts and bounds memory while preserving oldest rows', () => {
  const result = prependHistory(rows(101, 250), rows(51, 105))
  assert.equal(result.length, HISTORY_LIMIT)
  assert.equal(result[0].id, 51); assert.equal(result.at(-1).id, 250)
  assert.deepEqual(prependHistory(result, rows(1, 50)).map(row => row.id), rows(1, 200).map(row => row.id))
})
test('closed, pending, blocked and unknown states prevent composing without changing roles', () => {
  const user = { role: 'user' }, room = { status: 'accepted', kind: 'direct', send_state: 'ready' }
  assert.equal(composerReason(room, user), '')
  for (const state of ['pending', 'closed', 'blocked', 'unknown']) assert.ok(composerReason({ ...room, send_state: state }, user))
  assert.ok(composerReason({ ...room, blocked: true }, user))
  assert.ok(composerReason({ ...room, status: 'invited' }, user))
  for (const actor of [null, { role: 'owner' }, { ...user, is_muted: true }, { ...user, is_deleted: true }]) assert.ok(composerReason(room, actor))
})
test('history reading without incoming changes does not erase existing content', () => {
  assert.deepEqual(mergeLatest(rows(1, 10), [], true), { items: rows(1, 10), hasNew: false })
})
