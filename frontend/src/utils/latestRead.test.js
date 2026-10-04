import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createLatestRead } from './latestRead.js'

function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
test('latest response wins even when old transport ignores abort', async () => {
  const results = [], slow = deferred(); let oldSignal
  const lane = createLatestRead({ success: data => results.push(data) })
  const old = lane.run(signal => { oldSignal = signal; return slow.promise })
  await lane.run(async () => 'new')
  slow.resolve('old'); await old
  assert.equal(oldSignal.aborted, true); assert.deepEqual(results, ['new'])
})
test('stale errors do not replace current results or call finish again', async () => {
  const errors = [], slow = deferred(); let finishes = 0
  const lane = createLatestRead({ failure: e => errors.push(e.message), finish: () => finishes++ })
  const old = lane.run(() => slow.promise)
  await lane.run(async () => 'new')
  slow.reject(new Error('stale')); await old
  assert.deepEqual(errors, []); assert.equal(finishes, 2)
})
test('current failure is recoverable and loading always finishes', async () => {
  const events = [], lane = createLatestRead({ start: () => events.push('start'), failure: e => events.push(e.message), success: data => events.push(data), finish: () => events.push('finish') })
  await lane.run(async () => { throw new Error('offline') })
  await lane.run(async () => 'recovered')
  assert.deepEqual(events, ['start', 'offline', 'finish', 'start', 'recovered', 'finish'])
})
test('cancel stops effects and permits another read', async () => {
  const results = [], slow = deferred(), lane = createLatestRead({ success: data => results.push(data) })
  const pending = lane.run(() => slow.promise); lane.cancel(); slow.resolve('cancelled'); await pending
  await lane.run(async () => 'next'); assert.deepEqual(results, ['next'])
})
test('disposed page cannot apply results or start future requests', async () => {
  const slow = deferred(); let effects = 0, calls = 0
  const lane = createLatestRead({ success: () => effects++, failure: () => effects++ })
  const pending = lane.run(() => slow.promise); lane.dispose(); slow.reject(new Error('late')); await pending
  await lane.run(async () => calls++); assert.equal(effects, 0); assert.equal(calls, 0)
})
