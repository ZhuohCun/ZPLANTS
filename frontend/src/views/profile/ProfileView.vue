<template>
  <div class="page-wrap">
    <div class="card-panel">
      <div class="profile-hero split-header profile-hero-compact">
        <div class="head-main-block">
          <div class="section-title">{{ profile.realName || profile.username || 'Guest User' }}</div>
          <div class="profile-id">Account:{{ profile.username || 'No information yet' }}</div>
        </div>
        <div class="head-action-block profile-action-row">
          <el-button class="header-mini-btn" type="primary" @click="$router.push('/profile/detail')">Edit Details</el-button>
          <el-button class="header-mini-btn" plain @click="handleLogout">Sign Out</el-button>
        </div>
      </div>
      <div class="profile-meta-list top-gap-small">
        <div class="profile-meta-item">
          <div class="profile-meta-label">Email</div>
          <div class="profile-meta-value">{{ profile.email || 'No information yet' }}</div>
        </div>
        <div class="profile-meta-item">
          <div class="profile-meta-label">Phone</div>
          <div class="profile-meta-value">{{ profile.phone || 'No information yet' }}</div>
        </div>
      </div>
    </div>

    <div class="card-panel top-gap-medium">
      <div class="section-head section-head-tight">
        <div class="section-title">More Features</div>
      </div>
      <div v-if="menuItems.length" class="more-grid top-gap-small">
        <button v-for="item in menuItems" :key="item.path" class="quick-card quick-card-menu" @click="$router.push(item.path)">
          <div class="quick-card-title">{{ item.title }}</div>
          <div class="quick-card-desc">{{ item.desc }}</div>
        </button>
      </div>
      <div v-else class="empty-state">No information yet</div>
    </div>
  </div>
</template>

<script>
import { profileApi, logoutApi } from '@/api'
import { setUser, getUser, hasFeature, clearAuth } from '@/utils/auth'

export default {
  data() {
    return {
      profile: { username: '', realName: '', phone: '', email: '' },
      menuItems: []
    }
  },
  created() {
    this.loadData()
    const items = [
      { path: '/care', title: 'Care Reminders', desc: 'View and complete care reminders', feature: 'care' },
      { path: '/care/methods-manage', title: 'Care Method Management', desc: 'Maintain available care methods', feature: 'care_method' },
      { path: '/feedback', title: 'Feedback Center', desc: 'Submit feedback and view review results', feature: 'feedback' },
      { path: '/plants', title: 'Plant Management', desc: 'View and maintain campus plants', feature: 'plant' },
      { path: '/admin/users', title: 'User Management', desc: 'View users and adjust account status', feature: 'users' },
      { path: '/admin/logs', title: 'Operation Logs', desc: 'View recorded system activity', feature: 'logs' },
      { path: '/admin/locations', title: 'Zone and Location Management', desc: 'Maintain zones and locations', feature: 'zone_location' },
      { path: '/admin/access', title: 'Role Permissions', desc: 'Configure permissions by role', feature: 'access' },
      { path: '/admin/hash', title: 'Password Hash', desc: 'Calculate a password hash', feature: 'hash_tool' }
    ]
    this.menuItems = items.filter(item => hasFeature(item.feature))
  },
  methods: {
    async loadData() {
      const res = await profileApi()
      this.profile = { ...this.profile, ...(res.data || {}) }
      setUser({ ...getUser(), ...(res.data || {}) })
    },
    async handleLogout() {
      try {
        await logoutApi()
      } catch {}
      clearAuth()
      this.$router.replace('/login')
    }
  }
}
</script>
