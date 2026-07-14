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
    throw new Error(data.detail || `接口返回 ${response.status}`)
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
