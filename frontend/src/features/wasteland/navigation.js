import { WORLD } from './expedition.js'
export function mapPoint(point) {
  const coordinate = value => (Math.max(-WORLD.bound, Math.min(WORLD.bound, Number.isFinite(value) ? value : 0)) / WORLD.bound + 1) * 50
  return { x: coordinate(point.x), y: coordinate(point.z) }
}
export function expeditionObjective(state) {
  const p = state.player
  let target, kind, label
  if (state.repaired) { target = WORLD.exit; kind = 'exit'; label = '前往绿色撤离坪' }
  else if (p.scrap >= 4 && p.cells >= 2) { target = WORLD.beacon; kind = 'repair'; label = '修复北侧信标' }
  else {
    kind = p.scrap < 4 ? 'scrap' : 'cell'
    target = state.loot.filter(item => !item.taken && item.kind === kind).sort((a, b) => Math.hypot(a.x - p.x, a.z - p.z) - Math.hypot(b.x - p.x, b.z - p.z))[0]
    label = kind === 'scrap' ? '寻找下一个零件' : '寻找下一块电芯'
  }
  if (!target) return null
  return { ...target, kind, label, distance: Math.hypot(target.x - p.x, target.z - p.z) }
}
