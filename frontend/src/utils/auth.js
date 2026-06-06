const TOKEN_KEY = 'plant_token'
const USER_KEY = 'plant_user'

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user || {}))
  window.dispatchEvent(new CustomEvent('plant-user-updated', { detail: user || {} }))
}

export function getUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

export function removeUser() {
  localStorage.removeItem(USER_KEY)
  window.dispatchEvent(new CustomEvent('plant-user-updated', { detail: {} }))
}

export function clearAuth() {
  removeToken()
  removeUser()
}

function decodePayload(token) {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

export function isAuthenticated() {
  const token = getToken()
  if (!token) return false
  const payload = decodePayload(token)
  if (!payload || !payload.exp) return true
  return payload.exp * 1000 > Date.now()
}

export function getRole() {
  return getUser().role || ''
}

export function getFeatures() {
  return getUser().features || []
}

export function getPermissionMap() {
  return getUser().permissionMap || {}
}

export function getEditableFeatures() {
  return getUser().editableFeatures || []
}

export function hasAnyRole(roles = []) {
  if (!roles.length) return true
  return roles.includes(getRole())
}

export function hasFeature(code) {
  if (!code) return true
  return getFeatures().includes(code)
}

export function hasEditableFeature(code) {
  if (!code) return true
  return getEditableFeatures().includes(code)
}

export function hasPermission(feature, permission) {
  if (!feature || !permission) return true
  const permissionMap = getPermissionMap()
  return (permissionMap[feature] || []).includes(permission)
}
