export const API_BASE = import.meta.env?.VITE_API_BASE || 'http://127.0.0.1:8000'

export async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (typeof options.body === 'string' && !Object.keys(headers).some(key => key.toLowerCase() === 'content-type')) headers['Content-Type'] = 'application/json'
  const token = localStorage.getItem('token')

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const controller = new AbortController()
  const externalAbort = () => controller.abort()
  options.signal?.addEventListener('abort', externalAbort, { once: true })
  if (options.signal?.aborted) controller.abort()
  let timedOut = false
  const timeout = setTimeout(() => { timedOut = true; controller.abort() }, 60000)
  let response, data
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal })
    data = response.status === 204 ? null : await response.json().catch((error) => {
      if (error.name === 'AbortError' || response.ok) throw error
      return {}
    })
  } catch (error) {
    const failure = new Error(controller.signal.aborted
      ? timedOut ? '服务响应超时，免费服务可能正在唤醒，请稍后重试。' : '请求已取消。'
      : response ? '服务返回了无法读取的数据，请稍后重试。' : '无法连接服务，请检查网络或稍后重试。')
    failure.name = controller.signal.aborted && !timedOut ? 'AbortError' : 'Error'
    failure.code = controller.signal.aborted ? timedOut ? 'TIMEOUT' : 'ABORTED' : response ? 'INVALID_RESPONSE' : 'NETWORK'
    throw failure
  } finally {
    clearTimeout(timeout)
    options.signal?.removeEventListener('abort', externalAbort)
  }

  if (!response.ok) {
    if (response.status === 401 && token && !path.startsWith('/api/auth/login')) {
      window.dispatchEvent(new Event('auth-invalidated'))
    }
    const fallback = response.status >= 500 ? '服务暂不可用，请稍后重试。' : response.status === 404 ? '内容不存在或已移除。' : response.status === 429 ? '操作过于频繁，请稍后重试。' : '输入信息不符合要求，请检查后重试'
    const detail = typeof data?.detail === 'string' ? data.detail : fallback
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
