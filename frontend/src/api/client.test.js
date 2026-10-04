import { test, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'
import { apiRequest, postJson } from './client.js'

const originals = { fetch: globalThis.fetch, localStorage: globalThis.localStorage, window: globalThis.window }
let token = '', events
beforeEach(() => {
  events = []
  token = ''
  globalThis.localStorage = { getItem: () => token }
  globalThis.window = { dispatchEvent: event => events.push(event.type) }
})
afterEach(() => { for (const [key, value] of Object.entries(originals)) { if (value === undefined) delete globalThis[key]; else globalThis[key] = value } })
test('public GET is simple: no JSON header or Authorization', async () => {
  globalThis.fetch = async (url, options) => { assert.deepEqual(options.headers, {}); assert.equal(options.method, undefined); return Response.json({ ok: true }) }
  assert.deepEqual(await apiRequest('/api/site-summary'), { ok: true })
})
test('JSON writes keep correct header, body and bearer token', async () => {
  token = 'isolated-test-token'
  globalThis.fetch = async (url, options) => { assert.equal(options.headers['Content-Type'], 'application/json'); assert.equal(options.headers.Authorization, 'Bearer isolated-test-token'); assert.equal(options.body, '{"a":1}'); return Response.json({ ok: true }) }
  await postJson('/api/example', { a: 1 })
})
test('custom content type is not overwritten', async () => {
  globalThis.fetch = async (url, options) => { assert.equal(options.headers['content-type'], 'text/plain'); assert.equal(options.headers['Content-Type'], undefined); return Response.json({}) }
  await apiRequest('/api/example', { method: 'POST', headers: { 'content-type': 'text/plain' }, body: 'text' })
})
test('empty 204 response is valid', async () => {
  globalThis.fetch = async () => new Response(null, { status: 204 })
  assert.equal(await apiRequest('/api/example'), null)
})
test('invalid successful JSON differs from a network failure', async () => {
  globalThis.fetch = async () => new Response('<html>not JSON</html>')
  await assert.rejects(apiRequest('/api/example'), e => e.code === 'INVALID_RESPONSE')
  globalThis.fetch = async () => { throw new TypeError('network') }
  await assert.rejects(apiRequest('/api/example'), e => e.code === 'NETWORK')
})
test('non-JSON server errors preserve status and explain service failure', async () => {
  globalThis.fetch = async () => new Response('gateway error', { status: 503 })
  await assert.rejects(apiRequest('/api/example'), e => e.status === 503 && e.message.includes('服务暂不可用'))
})
test('structured validation details are not leaked as raw objects', async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ input: 'sensitive' }] }, { status: 422 })
  await assert.rejects(apiRequest('/api/example'), e => e.status === 422 && !e.message.includes('sensitive'))
})
test('unauthorized requests still notify existing auth store', async () => {
  token = 'isolated-test-token'
  globalThis.fetch = async () => Response.json({ detail: '登录已失效' }, { status: 401 })
  await assert.rejects(apiRequest('/api/auth/me'), e => e.status === 401)
  assert.deepEqual(events, ['auth-invalidated'])
})
test('external cancellation is distinct from network failure and removes listener', async () => {
  const controller = new AbortController(); let removed = 0
  const remove = controller.signal.removeEventListener.bind(controller.signal)
  controller.signal.removeEventListener = (...args) => { removed++; return remove(...args) }
  globalThis.fetch = (url, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('abort', 'AbortError')), { once: true }))
  const pending = apiRequest('/api/example', { signal: controller.signal }); controller.abort()
  await assert.rejects(pending, e => e.name === 'AbortError' && e.code === 'ABORTED')
  assert.equal(removed, 1)
})
test('timeout is explained separately from intentional cancellation', async context => {
  context.mock.timers.enable({ apis: ['setTimeout'] })
  globalThis.fetch = (url, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('timeout', 'AbortError')), { once: true }))
  const pending = apiRequest('/api/example'); context.mock.timers.tick(60000)
  await assert.rejects(pending, e => e.code === 'TIMEOUT' && e.message.includes('唤醒'))
})
