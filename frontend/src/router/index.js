import { createRouter, createWebHistory } from 'vue-router'
import { profileApi } from '@/api'
import { isAuthenticated, clearAuth, getUser, setUser, hasPermission } from '@/utils/auth'
import { getFirstAccessiblePath, normalizeFeatures } from '@/utils/navigation'

const routes = [
  { path: '/', name: 'root', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true, title: 'Sign In' } },
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true, title: 'Sign In' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { public: true, title: 'Register' } },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      { path: 'home', name: 'home', component: () => import('@/views/home/HomeView.vue'), meta: { title: 'Home', feature: 'home' } },
      { path: 'recognition/upload', name: 'recognition-upload', component: () => import('@/views/recognition/RecognitionUploadView.vue'), meta: { title: 'Plant Recognition', feature: 'recognition' } },
      { path: 'recognize', redirect: '/recognition/upload', meta: { public: false, title: 'Plant Recognition', feature: 'recognition' } },
      { path: 'recognition/result/:id', name: 'recognition-result', component: () => import('@/views/recognition/RecognitionResultView.vue'), meta: { title: 'Recognition Result', feature: 'recognition' } },
      { path: 'recognition/records', name: 'recognition-records', component: () => import('@/views/recognition/RecognitionRecordsView.vue'), meta: { title: 'Recognition Records', feature: 'recognition', permission: 'view_records' } },
      { path: 'species', name: 'species', component: () => import('@/views/species/SpeciesListView.vue'), meta: { title: 'Plant Species', feature: 'species' } },
      { path: 'species/:id', name: 'species-detail', component: () => import('@/views/species/SpeciesDetailView.vue'), meta: { title: 'Species Details', feature: 'species' } },
      { path: 'plants', name: 'plants', component: () => import('@/views/plants/PlantListView.vue'), meta: { title: 'Plant Management', feature: 'plant' } },
      { path: 'plants/:id', name: 'plant-detail', component: () => import('@/views/plants/PlantDetailView.vue'), meta: { title: 'Plant Details', feature: 'plant' } },
      { path: 'care', name: 'care', component: () => import('@/views/care/CareReminderView.vue'), meta: { title: 'Care Reminders', feature: 'care' } },
      { path: 'care/methods-manage', name: 'care-methods-manage', component: () => import('@/views/care/CareMethodManageView.vue'), meta: { title: 'Care Method Management', feature: 'care_method' } },
      { path: 'feedback', name: 'feedback', component: () => import('@/views/feedback/FeedbackView.vue'), meta: { title: 'Feedback Center', feature: 'feedback' } },
      { path: 'admin/users', name: 'admin-users', component: () => import('@/views/admin/UserManageView.vue'), meta: { title: 'User Management', feature: 'users' } },
      { path: 'admin/logs', name: 'admin-logs', component: () => import('@/views/admin/LogsView.vue'), meta: { title: 'Operation Logs', feature: 'logs' } },
      { path: 'admin/locations', name: 'admin-locations', component: () => import('@/views/admin/LocationManageView.vue'), meta: { title: 'Zone and Location Management', feature: 'zone_location' } },
      { path: 'admin/access', name: 'admin-access', component: () => import('@/views/admin/AccessManageView.vue'), meta: { title: 'Role Permission Management', feature: 'access' } },
      { path: 'admin/hash', name: 'admin-hash', component: () => import('@/views/admin/HashToolView.vue'), meta: { title: 'Password Hash', feature: 'hash_tool' } },
      { path: 'profile', name: 'profile', component: () => import('@/views/profile/ProfileView.vue'), meta: { title: 'Profile', feature: 'profile' } },
      { path: 'profile/detail', name: 'profile-detail', component: () => import('@/views/profile/ProfileDetailView.vue'), meta: { title: 'Account Details', feature: 'profile' } }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/error/NotFoundView.vue'), meta: { public: true, title: 'Page Not Found' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

let refreshingProfile = null

async function refreshProfile() {
  if (!refreshingProfile) {
    refreshingProfile = profileApi()
      .then(res => {
        const oldUser = getUser()
        const next = { ...oldUser, ...(res.data || {}) }
        setUser(next)
        return next
      })
      .finally(() => {
        refreshingProfile = null
      })
  }
  return refreshingProfile
}

router.beforeEach(async (to, from, next) => {
  document.title = `${to.meta?.title || 'Page'}`
  if (to.path === '/' || to.path === '/login' || to.meta?.public) {
    next()
    return
  }
  if (!isAuthenticated()) {
    next('/login')
    return
  }
  try {
    const profile = await refreshProfile()
    const feature = to.meta?.feature || ''
    const features = normalizeFeatures(profile?.features || [])
    const permission = to.meta?.permission || ''
    const permissionPassed = !permission || hasPermission(feature, permission)
    if ((!feature || features.includes(feature)) && permissionPassed) {
      next()
      return
    }
    next(getFirstAccessiblePath(features))
  } catch {
    clearAuth()
    next('/login')
  }
})

export default router
