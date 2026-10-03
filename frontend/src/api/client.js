export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export async function apiRequest(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const token = localStorage.getItem('token')

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    if (response.status === 401 && token && !path.startsWith('/api/auth/login')) {
      window.dispatchEvent(new Event('auth-invalidated'))
    }
    const detail = typeof data.detail === 'string' ? data.detail : '输入信息不符合要求，请检查后重试'
    const error = new Error(detail || `接口返回 ${response.status}`)
    error.status = response.status
    throw error
  }

  return data
}

export function postJson(path, body) {
  return apiRequest(path, { method: 'POST', body: JSON.stringify(body) })
}

export function putJson(path, body) {
  return apiRequest(path, { method: 'PUT', body: JSON.stringify(body) })
}

export function deleteRequest(path) {
  return apiRequest(path, { method: 'DELETE' })
}
