export const BOOK_COMMIT = 'b4048d14960fec19c0367f8c0e6891f2b038c7ef'
export function createGuideLoader(fetcher = (...args) => fetch(...args)) {
  let manifest
  const cache = new Map()
  async function json(url, signal) {
    signal?.throwIfAborted()
    const response = await fetcher(url, { signal })
    if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('原文资源暂时不可用，请重试。')
    return response.json()
  }
  return {
    async manifest(signal) {
      signal?.throwIfAborted()
      if (manifest) return manifest
      const data = await json('/life-guide/manifest.json', signal)
      if (data.commit !== BOOK_COMMIT || !Array.isArray(data.chapters) || data.chapters.length !== 34 || data.count !== 657 || data.chapters.some((item, i) => item.number !== i + 1 || item.url !== `/life-guide/chapter-${String(i + 1).padStart(2, '0')}.json` || !Number.isInteger(item.count))) throw new Error('原文版本不匹配，请刷新后重试。')
      signal?.throwIfAborted(); manifest = data
      return data
    },
    async chapter(item, signal) {
      signal?.throwIfAborted()
      if (cache.has(item.number)) return cache.get(item.number)
      if (item.url !== `/life-guide/chapter-${String(item.number).padStart(2, '0')}.json`) throw new Error('原文章节路径异常。')
      const data = await json(item.url, signal)
      if (data.number !== item.number || !Array.isArray(data.entries) || data.entries.length !== item.count || data.entries.some((entry, i) => entry.id !== `${item.number}-${i + 1}` || entry.number !== i + 1 || typeof entry.markdown !== 'string' || !entry.tags)) throw new Error('原文章节不完整，请重试。')
      signal?.throwIfAborted(); cache.set(item.number, data)
      return data
    },
  }
}
// Route-lifetime cache only: no book text, queries or reading history in storage.
export const guideLoader = createGuideLoader()
