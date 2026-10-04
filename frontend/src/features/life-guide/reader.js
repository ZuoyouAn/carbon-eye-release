export const READER_KEY = 'space-life-guide-reader-v1'
export const validEntryId = id => typeof id === 'string' && /^(?:[1-9]|[12]\d|3[0-4])-(?:[1-9]|[1-9]\d|1\d\d)$/.test(id)
export function readReader(storage) {
  try {
    const raw = storage.getItem(READER_KEY)
    if (!raw) return { enabled: false, saved: [], resume: '', warning: '' }
    if (raw.length > 65536) throw new Error('size')
    const data = JSON.parse(raw)
    if (data.version !== 1 || data.enabled !== true || !Array.isArray(data.saved)) throw new Error('shape')
    return { enabled: true, saved: [...new Set(data.saved.filter(validEntryId))].slice(0, 657), resume: validEntryId(data.resume) ? data.resume : '', warning: '' }
  } catch { return { enabled: false, saved: [], resume: '', warning: '本机记录暂时无法读取，仍可在当前会话使用收藏。' } }
}
export function writeReader(storage, state) {
  try {
    if (!state.enabled) storage.removeItem(READER_KEY)
    else storage.setItem(READER_KEY, JSON.stringify({ version: 1, enabled: true, saved: [...new Set(state.saved.filter(validEntryId))].slice(0, 657), resume: validEntryId(state.resume) ? state.resume : '' }))
    return ''
  } catch { return '浏览器未能保存记录；当前会话的收藏仍可使用。' }
}
const scalar = value => typeof value === 'string' ? value : ''
export function parseGuideQuery(query = {}) {
  const oneOf = (key, values) => values.includes(scalar(query[key])) ? query[key] : ''
  return { q: scalar(query.q).slice(0, 100), chapter: /^(?:[1-9]|[12]\d|3[0-4])$/.test(scalar(query.chapter)) ? query.chapter : '', evidence: oneOf('evidence', ['A', 'B', 'C']), benefit: oneOf('benefit', ['死亡率', '时间', '金钱', '自由']), money: oneOf('money', ['0', '少', '多']), value: oneOf('value', ['极高', '高', '一般']), page: /^\d{1,3}$/.test(scalar(query.page)) ? Math.max(1, Number(query.page)) : 1, entry: validEntryId(query.entry) ? query.entry : '' }
}
export function guideQuery(state) {
  const normalized = parseGuideQuery({ ...state, page: String(state.page || 1) })
  return Object.fromEntries(Object.entries(normalized).filter(([key, value]) => key === 'page' ? value > 1 : Boolean(value)).map(([key, value]) => [key, String(value)]))
}
