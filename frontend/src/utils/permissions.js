export const ROLE_OPTIONS = [
  { value: 'user', label: '低权限' },
  { value: 'elevated', label: '高权限' },
  { value: 'admin', label: '管理员' },
]

export function roleLabel(role) {
  return ROLE_OPTIONS.find((option) => option.value === role)?.label || '未授权'
}

export function mayPublish(user) {
  return Boolean(user && !user.is_muted && !user.is_deleted && ['elevated', 'admin'].includes(user.role))
}
