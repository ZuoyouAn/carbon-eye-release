import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { filterEntries, ratio, resolveSourceLinks, sourceUrl } from './library.js'
const root = new URL('../../../public/life-guide/', import.meta.url)
const manifest = JSON.parse(readFileSync(new URL('manifest.json', root)))
const chapters = readdirSync(root).filter(n => /^chapter-/.test(n)).sort().map(n => JSON.parse(readFileSync(new URL(n, root))))
test('pinned book snapshot contains all 34 chapters and complete identifiable entries', () => {
  assert.equal(chapters.length, 34); assert.equal(filterEntries(chapters).length, manifest.count)
  assert.equal(manifest.count, 657)
  const entries = filterEntries(chapters); assert.equal(new Set(entries.map(e => e.id)).size, entries.length)
  for (const entry of entries) { assert.match(entry.markdown, /^### /); assert.match(entry.markdown, /- 来源：/); assert.match(entry.markdown, /- 备注：/); assert.ok(['A', 'B', 'C'].includes(entry.evidence)) }
})
test('author ratio uses upstream weights and is distinct from evidence', () => {
  assert.equal(ratio({ 钱: '0', 时间: '少', 毅力: '否', 收益: '大' }), '极高')
  assert.equal(ratio({ 钱: '少', 时间: '少', 毅力: '些', 收益: '大' }), '高')
  assert.equal(ratio({ 钱: '多', 时间: '多', 毅力: '是', 收益: '中' }), '一般')
  assert.equal(ratio({}), '未标注')
})
test('search includes original remarks and sources; filters compose without cross-benefit ranking', () => {
  assert.ok(filterEntries(chapters, { query: '可信范围' }).length > 0)
  const result = filterEntries(chapters, { evidence: 'A', benefit: '金钱', money: '0' })
  assert.ok(result.length > 0); assert.ok(result.every(e => e.evidence === 'A' && e.tags.口径 === '金钱' && e.tags.钱 === '0'))
  assert.equal(filterEntries(chapters, { query: '不存在的词abcdefgh' }).length, 0)
  assert.ok(filterEntries(chapters, { chapter: '13' }).every(e => e.chapter === 13))
})
test('source references pin revision and safely resolve relative book and document links', () => {
  assert.ok(sourceUrl(manifest.commit, '01-不要早死.md').includes(manifest.commit))
  const linked = resolveSourceLinks('[长文](../docs/结婚划不划算.md)', manifest.commit, '01-不要早死.md')
  assert.ok(linked.includes(`/blob/${manifest.commit}/docs/`))
})
