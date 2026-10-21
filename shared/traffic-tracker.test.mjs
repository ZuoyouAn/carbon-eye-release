import { test } from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { createPageTracker, pagePath, setOptOut } from './traffic-tracker.mjs'

function browser(overrides = {}) {
  const values = new Map(), calls = [], listeners = new Map()
  globalThis.window = {
    location: { hostname: 'carbon-eye-sip.netlify.app' }, navigator: {}, crypto: { randomUUID },
    localStorage: { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) },
    fetch: async (url, options) => { calls.push({ url, options, body: JSON.parse(options.body) }); return { status: 204 } },
    addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name),
    dispatchEvent: event => listeners.get(event.type)?.(), ...overrides,
  }
  return { calls, values }
}
const tick = () => new Promise(resolve => setTimeout(resolve, 0))
test('paths exclude endpoints, private pages and all parameters', () => {
  assert.equal(pagePath('video', '/cinema?room=secret#private'), '/cinema')
  assert.equal(pagePath('video', '/watch?url=https://private.example/x'), '/watch')
  assert.equal(pagePath('space', '/articles/123?token=secret'), '/articles/:id')
  for (const path of ['/api/cinema', '/admin', '/login', '/profile', '/foo.ts', '//other.example']) assert.equal(pagePath('space', path), null)
})
test('one page event, no account/query/referrer, same-browser anonymous identity', async () => {
  const { calls } = browser()
  const tracker = createPageTracker({ site: 'video', endpoint: '/api/analytics' })
  tracker.track('/cinema?room=secret'); tracker.track('/cinema?room=other'); tracker.track('/live'); await tick()
  assert.equal(calls.length, 2)
  assert.equal(calls[0].body.visitor_id, calls[1].body.visitor_id)
  assert.notEqual(calls[0].body.event_id, calls[1].body.event_id)
  assert.equal(calls[0].options.referrerPolicy, 'no-referrer')
  assert.equal(calls[0].options.credentials, 'omit')
  assert.deepEqual(Object.keys(calls[0].body).sort(), ['event_id', 'path', 'site', 'visitor_id'])
  assert.ok(!JSON.stringify(calls).includes('secret'))
  tracker.stop()
})
test('localhost, opt-out, DNT, GPC, webdriver and admin do not allocate IDs or send', async () => {
  for (const overrides of [{ location: { hostname: 'localhost' } }, { navigator: { webdriver: true } }, { navigator: { doNotTrack: '1' } }, { navigator: { globalPrivacyControl: true } }]) {
    const { calls, values } = browser(overrides), tracker = createPageTracker({ site: 'space', endpoint: '/collect' })
    tracker.track('/'); await tick(); assert.equal(calls.length, 0); assert.equal(values.size, 0); tracker.stop()
  }
  const { calls } = browser(), tracker = createPageTracker({ site: 'space', endpoint: '/collect', ignore: () => true })
  tracker.track('/'); assert.equal(calls.length, 0); tracker.stop()
})
test('opt-out removes the ID and blocks subsequent page events', async () => {
  const { calls, values } = browser(), tracker = createPageTracker({ site: 'space', endpoint: '/collect' })
  tracker.track('/'); await tick(); setOptOut(true); tracker.track('/projects'); await tick()
  assert.equal(calls.length, 1); assert.equal(values.has('space-analytics-browser-v1'), false); tracker.stop()
})
test('retry keeps the original event ID and does not attach authorization', async () => {
  const { calls } = browser(); let first = true
  window.fetch = async (_url, options) => { calls.push({ body: JSON.parse(options.body), options }); if (first) { first = false; throw new TypeError('offline') } return { status: 204 } }
  const tracker = createPageTracker({ site: 'space', endpoint: '/collect' }); tracker.track('/'); await tick()
  assert.equal(calls.length, 2); assert.equal(calls[0].body.event_id, calls[1].body.event_id)
  assert.deepEqual(calls[0].options.headers, { 'Content-Type': 'application/json' }); tracker.stop()
})
