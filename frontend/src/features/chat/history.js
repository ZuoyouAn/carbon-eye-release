export const HISTORY_LIMIT = 200

// Viewing history must never silently discard the reader's oldest visible rows.
export function mergeLatest(current, incoming, readingHistory = false) {
  if (!readingHistory) return { items: incoming.slice(-HISTORY_LIMIT), hasNew: false }
  const latest = new Map(incoming.map(item => [item.id, item]))
  const maximum = current.at(-1)?.id || 0
  return {
    items: current.slice(0, HISTORY_LIMIT).map(item => latest.get(item.id) || item),
    hasNew: incoming.some(item => item.id > maximum),
  }
}

export function prependHistory(current, older) {
  const rows = new Map(current.map(item => [item.id, item]))
  older.forEach(item => rows.set(item.id, item))
  return [...rows.values()].sort((a, b) => a.id - b.id).slice(0, HISTORY_LIMIT)
}

export function composerReason(room, user) {
  if (!user || user.is_muted || user.is_deleted || !['user', 'elevated', 'admin'].includes(user.role)) return '账号当前只能阅读'
  if (!room || room.status !== 'accepted') return '请先接受邀请'
  if (room.blocked || room.send_state === 'blocked') return '私聊已关闭'
  if (room.send_state === 'closed') return '对方已拒绝或退出，仅可阅读已有记录'
  if (room.send_state === 'pending') return '等待对方接受邀请后才能发送消息'
  if (room.send_state !== 'ready') return '正在确认会话状态，请稍后刷新'
  return ''
}
