// Keep entry-point assets small; feature chunks have separate on-demand budgets.
import { readFileSync, statSync } from 'node:fs'
import { dirname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const dist = resolve(dirname(fileURLToPath(import.meta.url)), '../dist')
const html = readFileSync(resolve(dist, 'index.html'), 'utf8')
function assets(pattern, attribute) {
  return [...html.matchAll(pattern)].map(([tag]) => {
    const value = tag.match(new RegExp(`${attribute}="([^"]+)"`))?.[1]
    if (!value || !value.startsWith('/assets/')) throw new Error('Unexpected entry asset URL')
    const path = resolve(dist, value.slice(1))
    if (!path.startsWith(dist + sep)) throw new Error('Entry asset outside dist')
    return path
  })
}
const css = assets(/<link\b[^>]*\brel="stylesheet"[^>]*>/g, 'href')
const js = assets(/<script\b[^>]*\bsrc="[^"]+"[^>]*>/g, 'src')
if (!css.length || !js.length) throw new Error('Missing production entry assets')
const bytes = files => files.reduce((sum, path) => sum + statSync(path).size, 0)
const compressed = files => files.reduce((sum, path) => sum + gzipSync(readFileSync(path)).length, 0)
const budgets = { css: 100 * 1024, js: 220 * 1024 }
if (bytes(css) > budgets.css || bytes(js) > budgets.js) throw new Error('Homepage asset budget exceeded')
console.log(JSON.stringify({ status: 'passed', entry_css_bytes: bytes(css), entry_css_gzip_bytes: compressed(css), entry_js_bytes: bytes(js), budgets }))
