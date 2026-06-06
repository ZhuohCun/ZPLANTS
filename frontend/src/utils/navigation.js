import { House, Camera, Collection, Tickets, User } from '@element-plus/icons-vue'
import { getFeatures, hasPermission } from '@/utils/auth'


export const navItems = [
  { path: '/home', label: 'Home', icon: House, feature: 'home' },
  { path: '/recognition/upload', label: 'Recognition', icon: Camera, feature: 'recognition' },
  { path: '/species', label: 'Species', icon: Collection, feature: 'species' },
  { path: '/recognition/records', label: 'Records', icon: Tickets, feature: 'recognition', permission: 'view_records' },
  { path: '/profile', label: 'Profile', icon: User, feature: 'profile' }
]

export function normalizeFeatures(features = getFeatures()) {
  const result = new Set()
  ;(features || []).forEach(item => { if (item) result.add(item) })
  return Array.from(result)
}

export function getVisibleNavItems() {
  const features = normalizeFeatures()
  return navItems.filter(item => (!item.feature || features.includes(item.feature)) && (!item.permission || hasPermission(item.feature, item.permission)))
}

export function getFirstAccessiblePath(features = getFeatures()) {
  const enabled = normalizeFeatures(features)
  const found = navItems.find(item => (!item.feature || enabled.includes(item.feature)) && (!item.permission || hasPermission(item.feature, item.permission)))
  return found ? found.path : '/profile'
}
