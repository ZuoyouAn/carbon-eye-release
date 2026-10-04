// Original procedural illustration, not a photographed texture or geographic map.
export function surfaceTint(id, x, y, z) {
  const wave = Math.sin(x * 14 + z * 7) * Math.sin(y * 11 - z * 9)
  if (id === 'earth') {
    const land = Math.sin(x * 5 + z * 3) + Math.cos(z * 7 - y * 4) + Math.sin(y * 8 + x * 2) > .85
    if (Math.abs(y) > .88) return { color: '#e6eef0', shade: 1 }
    return { color: land ? '#83a577' : '#579ec7', shade: .95 + wave * .06 }
  }
  if (id === 'jupiter' || id === 'saturn') return { color: null, shade: .78 + (Math.sin(y * 32 + Math.sin(x * 6 + z * 4) * .7) + 1) * .15 }
  return { color: null, shade: .87 + wave * .12 }
}
export function sceneTime(value) { return Math.min(600, Math.max(0, Number.isFinite(Number(value)) ? Number(value) : 0)) }
