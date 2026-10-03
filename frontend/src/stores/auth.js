import { computed, reactive } from 'vue'
import { apiRequest, postJson, putJson } from '../api/client'
import { mayPublish } from '../utils/permissions'

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('currentUser') || 'null')
  } catch {
    return null
  }
}

export const authState = reactive({
  token: localStorage.getItem('token') || '',
  user: readStoredUser(),
  ready: false,
})

export const isLoggedIn = computed(() => Boolean(authState.user && authState.token))
export const isAdmin = computed(() => isLoggedIn.value && authState.user?.role === 'admin' && !authState.user.is_muted && !authState.user.is_deleted)
export const isMuted = computed(() => Boolean(authState.user?.is_muted))
export const canPublish = computed(() => isLoggedIn.value && mayPublish(authState.user))

export function saveAuth(token, user) {
  authState.token = token
  authState.user = user
  localStorage.setItem('token', token)
  localStorage.setItem('currentUser', JSON.stringify(user))
}

export function clearAuth() {
  authState.token = ''
  authState.user = null
  localStorage.removeItem('token')
  localStorage.removeItem('currentUser')
}

window.addEventListener('auth-invalidated', clearAuth)

export async function refreshMe() {
  if (!authState.token) {
    authState.ready = true
    return null
  }

  try {
    const data = await apiRequest('/api/auth/me')
    saveAuth(authState.token, data.user)
    return data.user
  } catch {
    clearAuth()
    return null
  } finally {
    authState.ready = true
  }
}

export async function login(form) {
  const data = await postJson('/api/auth/login', form)
  saveAuth(data.token, data.user)
  return data
}

export async function register(form) {
  return postJson('/api/auth/register', form)
}

export async function logout() {
  try {
    await postJson('/api/auth/logout', {})
  } finally {
    clearAuth()
  }
}

export async function changePassword(form) {
  const result = await putJson('/api/me/password', form)
  clearAuth()
  return result
}
