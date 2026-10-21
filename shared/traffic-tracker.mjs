// Framework-independent first-party page tracker. Never send URLs or user data.
export const OPT_OUT_KEY = 'space-analytics-optout-v1'
const ID_KEY = 'space-analytics-browser-v1'
const VIDEO = new Set(['/', '/watch', '/cinema', '/live', '/about'])
const SPACE = new Set(['/', '/novels', '/posts', '/articles', '/projects', '/human3', '/chat', '/games', '/games/swarm', '/games/winter', '/wasteland', '/solar-system', '/life-guide', '/document-tools', '/libretv', '/ghosttrack', '/crypto-lab', '/secure-geometry', '/secure-geometry/paper', '/store', '/roadmap', '/timeline', '/messages', '/changelog'])
SPACE.add('/carbon-eye')
export function pagePath(site, input) {
  if (typeof input !== 'string' || !input.startsWith('/') || input.startsWith('//')) return null
  const path = input.split(/[?#]/, 1)[0].replace(/\/+$/, '') || '/'
  if ((site === 'video' ? VIDEO : SPACE).has(path)) return path
  const match = site === 'space' && path.match(/^\/(articles|novels|posts)\/\d+$/)
  return match ? `/${match[1]}/:id` : null
}
export function optedOut() {
  try { return window.localStorage.getItem(OPT_OUT_KEY) === '1' } catch { return false }
}
export function setOptOut(value) {
  try {
    window.localStorage.setItem(OPT_OUT_KEY, value ? '1' : '0')
    if (value) window.localStorage.removeItem(ID_KEY)
    window.dispatchEvent(new Event('space-analytics-preference'))
  } catch { /* unavailable storage must not break reading or playback */ }
}
export function createPageTracker({ site, endpoint, enabled = true, ignore = () => false }) {
  let lastPath = null, lastAt = 0, ephemeral = null, stopped = false
  const controllers = new Set()
  function disabled() {
    return stopped || !enabled || typeof window === 'undefined' || window.navigator.webdriver ||
      window.navigator.doNotTrack === '1' || window.navigator.globalPrivacyControl === true || optedOut() || ignore() ||
      ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)
  }
  function browserId() {
    const now = Date.now()
    try {
      const old = JSON.parse(window.localStorage.getItem(ID_KEY) || 'null')
      if (old && /^[0-9a-f-]{36}$/i.test(old.id) && old.expires > now && old.expires < now + 31 * 86400000) return old.id
      const id = window.crypto.randomUUID()
      window.localStorage.setItem(ID_KEY, JSON.stringify({ id, expires: now + 30 * 86400000 }))
      return id
    } catch { return ephemeral ||= window.crypto.randomUUID() }
  }
  async function send(body, attempt = 0) {
    if (disabled()) return
    const controller = new AbortController(); controllers.add(controller)
    const timeout = setTimeout(() => controller.abort(), 65000)
    try {
      const response = await window.fetch(endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        credentials: 'omit', referrerPolicy: 'no-referrer', keepalive: true, signal: controller.signal,
      })
      if (response.status >= 500 && attempt === 0) void send(body, 1)
    } catch {
      if (attempt === 0 && !disabled()) void send(body, 1)
    } finally { clearTimeout(timeout); controllers.delete(controller) }
  }
  function track(input) {
    if (disabled()) return
    const path = pagePath(site, input), now = Date.now()
    if (!path || (path === lastPath && now - lastAt < 1500)) return
    lastPath = path; lastAt = now
    try { void send({ site, path, visitor_id: browserId(), event_id: window.crypto.randomUUID() }) } catch { /* no tracking support */ }
  }
  const cancel = () => { if (optedOut()) { for (const c of controllers) c.abort(); ephemeral = null } }
  if (typeof window !== 'undefined') window.addEventListener('space-analytics-preference', cancel)
  return { track, stop() { stopped = true; for (const c of controllers) c.abort(); window.removeEventListener('space-analytics-preference', cancel) } }
}
