import { computed, reactive } from 'vue'
import { apiRequest, postJson, putJson } from '../api/client'

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
export const isAdmin = computed(() => authState.user?.role === 'admin')
export const isMuted = computed(() => Boolean(authState.user?.is_muted))
export const canPublish = computed(() => Boolean(authState.user && !authState.user.is_muted))

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
  return putJson('/api/me/password', form)
}
