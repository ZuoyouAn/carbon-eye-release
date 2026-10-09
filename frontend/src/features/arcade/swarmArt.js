export const SWARM_ART_URL = '/game-art/starfall-units.webp'
export const SWARM_GROUND_URL = '/game-art/starfall-ground.webp'
export const ART_CELLS = Object.freeze({ ranger: 0, guardian: 1, mage: 2, walker: 3, runner: 4, tank: 5, boss: 6, crystal: 7 })

export function spriteFrame(width, height, id) {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0 || !(id in ART_CELLS)) return null
  const cell = ART_CELLS[id]
  return { x: cell % 4 * width / 4, y: Math.floor(cell / 4) * height / 2, width: width / 4, height: height / 2 }
}
// View-owned image; no background requests or redraw callbacks after the view is disposed.
export function loadSwarmArt(ImageClass = globalThis.Image, url = SWARM_ART_URL) {
  const image = new ImageClass()
  let disposed = false, settled = false, resolve
  const ready = new Promise(done => { resolve = done })
  function finish(value) { if (settled) return; settled = true; image.onload = image.onerror = null; resolve(value) }
  image.onload = () => finish(!disposed && image.naturalWidth > 0 ? image : null)
  image.onerror = () => finish(null)
  image.src = url
  return { ready, dispose() { disposed = true; finish(null) } }
}
