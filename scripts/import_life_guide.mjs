// Reads a reviewed, pinned upstream checkout. Emits patches, never writes source files.
// node scripts/import_life_guide.mjs outputs/life-guide-upstream manifest|01..34|license
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
const root = resolve(process.argv[2] || ''), selection = process.argv[3]
const commit = execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
if (commit !== 'b4048d14960fec19c0367f8c0e6891f2b038c7ef') throw new Error('Upstream revision changed; review source and license before updating.')
const source = 'https://github.com/eternity4719/HowToLiveBetter'
const chapters = readdirSync(resolve(root, 'book')).filter(n => /^\d{2}-.+\.md$/.test(n)).sort().map(file => {
  const raw = readFileSync(resolve(root, 'book', file), 'utf8').replace(/\r\n/g, '\n')
  const number = Number(file.slice(0, 2)), title = raw.match(/^#\s+(.+)$/m)?.[1] || file.slice(3, -3)
  const headings = [...raw.matchAll(/^###\s+(\d+)[.．、]\s*(.+)$/gm)]
  if (!headings.length) throw new Error(`Missing entries: ${file}`)
  const entries = headings.map((heading, i) => {
    const markdown = raw.slice(heading.index, headings[i + 1]?.index ?? raw.length).trim()
    const field = name => markdown.match(new RegExp(`^- ${name}：\\s*(.*)$`, 'm'))?.[1] || ''
    const tags = Object.fromEntries([...(markdown.match(/<!--\s*成本标签:\s*(.*?)\s*-->/)?.[1] || '').matchAll(/([^\s=]+)=([^\s]+)/g)].map(m => [m[1], m[2]]))
    return { id: `${number}-${heading[1]}`, number: Number(heading[1]), title: heading[2], summary: field('说人话'), evidence: field('证据等级').slice(0, 1), tags, markdown }
  })
  if (new Set(entries.map(e => e.id)).size !== entries.length) throw new Error('Duplicate entry ID')
  return { number, title, file, intro: raw.slice(0, headings[0].index).trim(), hash: createHash('sha256').update(raw).digest('hex'), entries }
})
function patch(path, content) { process.stdout.write(`*** Begin Patch\n*** Add File: ${path}\n${content.split('\n').map(line => '+' + line).join('\n')}\n*** End Patch\n`) }
if (selection === 'manifest') {
  const manifest = { title: '高性价比人生指南', author: 'eternity4719 / HowToLiveBetter contributors', source, commit, syncedAt: '2026-10-05', license: 'CC BY 4.0', licenseUrl: 'https://creativecommons.org/licenses/by/4.0/', changes: '正文未改写；拆分为章节 JSON，新增 Space 阅读和检索界面。', count: chapters.reduce((n, chapter) => n + chapter.entries.length, 0), chapters: chapters.map(({ entries, intro, ...chapter }) => ({ ...chapter, count: entries.length, url: `/life-guide/chapter-${String(chapter.number).padStart(2, '0')}.json` })) }
  patch('frontend/public/life-guide/manifest.json', JSON.stringify(manifest, null, 2))
} else if (selection === 'license') {
  patch('frontend/public/life-guide/LICENSE.txt', readFileSync(resolve(root, 'LICENSE'), 'utf8').replace(/\r\n/g, '\n'))
} else {
  const chapter = chapters.find(c => c.number === Number(selection))
  if (!chapter) throw new Error('Unknown chapter')
  patch(`frontend/public/life-guide/chapter-${String(chapter.number).padStart(2, '0')}.json`, JSON.stringify(chapter))
}
