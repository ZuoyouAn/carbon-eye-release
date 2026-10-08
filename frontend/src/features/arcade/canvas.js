// Original vector artwork: no copied sprites, models, textures, or remote assets.
export function createArcadeCanvas(container, painter) {
  const canvas = document.createElement('canvas'), context = canvas.getContext('2d')
  if (!context) throw Error('浏览器未提供 Canvas 2D，请换一个浏览器。')
  container.appendChild(canvas)
  let width = 1, height = 1, disposed = false, latest = null
  function render(...args) { if (disposed) return; latest = args; painter(context, width, height, ...args) }
  function resize() {
    if (disposed) return
    width = Math.max(1, container.clientWidth); height = Math.max(1, container.clientHeight)
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5)
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio)
    context.setTransform(ratio, 0, 0, ratio, 0, 0)
    if (latest) render(...latest)
  }
  const observer = new ResizeObserver(resize); observer.observe(container); resize()
  return { canvas, render, position(event) { const r = canvas.getBoundingClientRect(); return { x: (event.clientX - r.left) * width / r.width, y: (event.clientY - r.top) * height / r.height, width, height } }, dispose() { disposed = true; latest = null; observer.disconnect(); canvas.width = canvas.height = 1; canvas.remove() } }
}
function circle(c, x, y, r, fill, stroke) {
  c.beginPath(); c.arc(x, y, Math.max(.1, r), 0, Math.PI * 2)
  if (fill) { c.fillStyle = fill; c.fill() } if (stroke) { c.strokeStyle = stroke; c.stroke() }
}
function line(c, x, y, tx, ty, color, width = 2) { c.beginPath(); c.moveTo(x, y); c.lineTo(tx, ty); c.strokeStyle = color; c.lineWidth = width; c.stroke() }
export { paintSwarm } from './swarmScene.js'
export function winterTile(w, h, x, y) { const tile = Math.min(w / 14, h / 10); return { x: w / 2 + (x - y) * tile, y: h * .5 + (x + y - 6) * tile / 2, tile } }
export function pickWinterTile(position) {
  const { width: w, height: h, x, y } = position, tile = Math.min(w / 14, h / 10), dx = (x - w / 2) / tile, dy = (y - h * .5) / (tile / 2)
  return { x: Math.round((dx + dy) / 2 + 3), y: Math.round((dy - dx) / 2 + 3) }
}
function diamond(c, x, y, tile, color, stroke = '#c4d8e3') { c.beginPath(); c.moveTo(x, y - tile / 2); c.lineTo(x + tile, y); c.lineTo(x, y + tile / 2); c.lineTo(x - tile, y); c.closePath(); c.fillStyle = color; c.fill(); c.strokeStyle = stroke; c.lineWidth = 1; c.stroke() }
function block(c, x, y, tile, height, color, roof) {
  c.beginPath(); c.moveTo(x - tile * .7, y); c.lineTo(x, y + tile * .35); c.lineTo(x, y + tile * .35 - height); c.lineTo(x - tile * .7, y - height); c.closePath(); c.fillStyle = color; c.fill()
  c.beginPath(); c.moveTo(x, y + tile * .35); c.lineTo(x + tile * .7, y); c.lineTo(x + tile * .7, y - height); c.lineTo(x, y + tile * .35 - height); c.closePath(); c.fillStyle = roof; c.fill()
  diamond(c, x, y - height, tile * .7, '#f1f7fa', '#dae6ec')
}
export function paintWinter(c, w, h, s, target, selected = '', reduced = false) {
  c.clearRect(0, 0, w, h); c.fillStyle = s.storm ? '#dee8f0' : '#ebf3f7'; c.fillRect(0, 0, w, h)
  const tile = winterTile(w, h, 3, 3).tile
  for (let sum = 0; sum <= 12; sum++) for (let x = 0; x <= 6; x++) {
    const y = sum - x; if (y < 0 || y > 6) continue
    const at = winterTile(w, h, x, y), warm = s.powered && Math.hypot(x - 3, y - 3) <= s.radius
    diamond(c, at.x, at.y, tile, warm ? '#eee5d7' : (x + y) % 2 ? '#e3eef3' : '#e9f2f6')
    if (x === 3 && y === 3) {
      block(c, at.x, at.y - 1, tile, tile * .95, '#aa8d71', '#c6a88a'); block(c, at.x, at.y - tile * .8, tile * .3, tile * .9, '#9b8170', '#bba18b')
      circle(c, at.x, at.y - tile * .18, tile * .18, s.powered ? '#f6be63' : '#9ba4ad')
      if (s.powered && !reduced) for (let i = 0; i < 3; i++) { const phase = (s.elapsed * .22 + i / 3) % 1; c.globalAlpha = (1 - phase) * .28; circle(c, at.x + phase * 12, at.y - tile * 2 - phase * 35, 4 + phase * 9, '#91a3af'); c.globalAlpha = 1 }
    } else {
      const b = s.buildings.find(item => item.x === x && item.y === y)
      if (b) {
        const colors = { hut: ['#a58f7b', '#c3ae94'], sawmill: ['#9aa88f', '#bec4a7'], coal: ['#86909a', '#acb5bd'], kitchen: ['#b4a17e', '#d0bc99'], mine: ['#8f9caf', '#b0bed0'], clinic: ['#9dbbb4', '#c4dbd5'], workshop: ['#94aabd', '#b8ccdc'], outpost: ['#b29bac', '#d0b7c7'] }
        const [side, front] = colors[b.kind]; block(c, at.x, at.y, tile, tile * (.52 + b.level * .1), side, front)
        if (b.kind === 'clinic') { c.fillStyle = '#edfafa'; c.fillRect(at.x - 3, at.y - tile * .25 - 5, 6, 15); c.fillRect(at.x - 7, at.y - tile * .25, 14, 5) }
        else { c.fillStyle = warm ? '#edc37d' : '#d4e4ed'; c.fillRect(at.x + 3, at.y - tile * .28, tile * .17, tile * .16) }
        if (w > 500) { c.fillStyle = '#53697d'; c.font = '12px sans-serif'; c.textAlign = 'center'; c.fillText(`${b.level}级`, at.x, at.y + tile * .55) }
      }
    }
    if (target && target.x === x && target.y === y) { c.globalAlpha = .45; diamond(c, at.x, at.y, tile, selected ? (target.ok ? '#6bbba3' : '#d88d7c') : '#87b9e5'); c.globalAlpha = 1; diamond(c, at.x, at.y, tile, '#ffffff00', selected ? (target.ok ? '#369e83' : '#c67060') : '#4f95d0') }
  }
  const destinations = { wood: 'sawmill', coal: 'coal', food: 'kitchen', iron: 'mine', medic: 'clinic' }
  let person = 0
  for (const [job, count] of Object.entries(s.jobs)) for (let i = 0; i < count; i++) {
    const b = s.buildings.find(item => item.kind === destinations[job]), destination = b || { x: job === 'wood' ? 0 : 6, y: job === 'food' ? 6 : 0 }
    const phase = reduced ? .5 : ((s.elapsed * .07 + person++ * .17) % 2), t = phase <= 1 ? phase : 2 - phase
    const at = winterTile(w, h, 3 + (destination.x - 3) * t, 3 + (destination.y - 3) * t)
    circle(c, at.x + tile * .3, at.y + tile * .4, 3, '#587c91'); circle(c, at.x + tile * .3, at.y + tile * .4 - 5, 2.4, '#e8c5a3')
  }
  if (!reduced) for (let i = 0; i < (s.storm ? 70 : 25); i++) { const x = (i * 137 + s.elapsed * (s.storm ? 38 : 9)) % (w + 30) - 15, y = (i * 83 + s.elapsed * (s.storm ? 65 : 22)) % h; line(c, x, y, x - (s.storm ? 6 : 1), y + 4, '#ffffffb0', 1.4) }
  c.fillStyle = '#526c81'; c.font = '14px sans-serif'; c.textAlign = 'center'; c.fillText(s.storm ? '暴风雪中 · 燃料与口粮不能断' : '点选地块，围绕暖炉建设你的聚落', w / 2, h - 24)
}
