export const COST_W = Object.freeze({ money: { '0': 0, 少: 1, 多: 2 }, time: { 少: 0, 中: 1, 多: 2 }, will: { 否: 0, 些: 1, 是: 2 } })
export function ratio(tags) {
  const values = [COST_W.money[tags.钱], COST_W.time[tags.时间], COST_W.will[tags.毅力]]
  if (values.some(v => v === undefined) || !['大', '中', '小'].includes(tags.收益)) return '未标注'
  const cost = values.reduce((a, b) => a + b, 0)
  return tags.收益 === '大' ? (cost === 0 ? '极高' : cost <= 2 ? '高' : '一般') : tags.收益 === '中' && cost === 0 ? '高' : '一般'
}
export function filterEntries(chapters, { query = '', chapter = '', evidence = '', benefit = '', money = '', value = '' } = {}) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  return chapters.flatMap(indexChapter).filter(entry =>
    (!chapter || entry.chapter === Number(chapter)) && (!evidence || entry.evidence === evidence) && (!benefit || entry.tags.口径 === benefit) && (!money || entry.tags.钱 === money) && (!value || entry.ratio === value) && words.every(word => searchText.get(entry).includes(word)))
  // Keep original chapter/entry order. Never rank money against life or freedom.
}
const chapterIndex = new WeakMap(), searchText = new WeakMap()
function indexChapter(chapter) {
  if (!chapterIndex.has(chapter)) {
    const entries = chapter.entries.map(entry => ({ ...entry, chapter: chapter.number, chapterTitle: chapter.title, file: chapter.file, ratio: ratio(entry.tags) }))
    entries.forEach(entry => searchText.set(entry, entry.markdown.toLocaleLowerCase()))
    chapterIndex.set(chapter, entries)
  }
  return chapterIndex.get(chapter)
}
export function sourceUrl(commit, file) { return `https://github.com/eternity4719/HowToLiveBetter/blob/${commit}/book/${encodeURIComponent(file)}` }
export function resolveSourceLinks(markdown, commit, file) {
  const base = `https://github.com/eternity4719/HowToLiveBetter/blob/${commit}/book/${encodeURIComponent(file)}`
  return markdown.replace(/\]\(([^)]+)\)/g, (whole, target) => {
    if (/^(https?:|mailto:|#)/i.test(target)) return whole
    try { return `](${new URL(target, base).href})` } catch { return whole }
  })
}
