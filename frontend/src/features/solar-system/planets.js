// Facts: NASA About the Planets, reviewed 2026-10-05.
// visualRadius/orbit/period are illustration parameters, NOT physical measurements.
export const NASA_SOURCE = 'https://science.nasa.gov/solar-system/planets/'
export const PLANETS = Object.freeze([
  { id: 'mercury', name: '水星', english: 'Mercury', type: '类地行星', order: 1, color: '#a2a1a0', radius: .27, orbit: 4.1, period: 8, note: '最靠近太阳，也是八颗行星中最小的一颗。' },
  { id: 'venus', name: '金星', english: 'Venus', type: '类地行星', order: 2, color: '#d9b887', radius: .47, orbit: 6.2, period: 12, note: '从太阳向外数的第二颗行星，大小在八颗行星中排第六。' },
  { id: 'earth', name: '地球', english: 'Earth', type: '类地行星', order: 3, color: '#579ec7', radius: .5, orbit: 8.4, period: 17, note: '我们的家园，距离太阳第三近，大小排名第五。' },
  { id: 'mars', name: '火星', english: 'Mars', type: '类地行星', order: 4, color: '#c37e61', radius: .35, orbit: 10.5, period: 23, note: '从太阳向外数的第四颗行星，大小排名第七。' },
  { id: 'jupiter', name: '木星', english: 'Jupiter', type: '气态巨行星', order: 5, color: '#c3a080', radius: 1.05, orbit: 14, period: 31, note: '太阳系最大的行星，位于从太阳向外数的第五位。' },
  { id: 'saturn', name: '土星', english: 'Saturn', type: '气态巨行星', order: 6, color: '#cab98f', radius: .85, orbit: 18, period: 39, note: '大小仅次于木星，位于从太阳向外数的第六位。环是它醒目的轮廓。' },
  { id: 'uranus', name: '天王星', english: 'Uranus', type: '冰巨行星', order: 7, color: '#91c6c9', radius: .7, orbit: 22, period: 48, note: '大小排名第三，位于从太阳向外数的第七位。' },
  { id: 'neptune', name: '海王星', english: 'Neptune', type: '冰巨行星', order: 8, color: '#5c85c4', radius: .68, orbit: 26, period: 58, note: '八颗行星中最远离太阳的一颗，大小排名第四。' },
])
export function positionAt(planet, seconds) {
  const t = Number.isFinite(seconds) ? seconds : 0
  const angle = (t / planet.period * Math.PI * 2 + planet.order * .71) % (Math.PI * 2)
  return { x: Math.cos(angle) * planet.orbit, z: Math.sin(angle) * planet.orbit }
}
