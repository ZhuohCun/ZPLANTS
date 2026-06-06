<template>
  <div class="mobile-shell">
    <header class="mobile-header-shell floating-shell">
      <div class="mobile-header-inner split-header floating-bar">
        <div class="header-main-block">
          <div class="mobile-brand brand-wrap-wide">
            <img class="brand-mark brand-logo-img" src="/ynu-logo.png" alt="Yunnan University emblem" />
            <div class="brand-text">
              <div class="brand-title">{{ pageTitle }}</div>
              <div class="brand-subtitle">{{ welcomeText }}</div>
            </div>
          </div>
        </div>
        <div class="header-action-block header-action-ghost">
          <el-button v-if="showBackButton" class="header-action header-action-compact" size="small" plain @click="handleBack">Back</el-button>
        </div>
      </div>
    </header>
    <main class="mobile-content-shell">
      <div class="mobile-content-inner top-safe-space">
        <router-view />
      </div>
    </main>
    <nav class="mobile-nav-shell floating-shell">
      <div class="mobile-nav-inner floating-bar floating-nav" :style="navGridStyle">
        <button
          v-for="item in navs"
          :key="item.path"
          class="nav-button"
          :class="{ active: isActive(item.path) }"
          @click="go(item.path)"
        >
          <span class="nav-icon-wrap"><el-icon><component :is="item.icon" /></el-icon></span>
          <span>{{ item.label }}</span>
        </button>
      </div>
    </nav>
  </div>
</template>

<script>
import { getUser } from '@/utils/auth'
import { getVisibleNavItems, navItems } from '@/utils/navigation'

export default {
  name: 'MainLayout',
  data() {
    return {
      user: getUser(),
      navs: getVisibleNavItems()
    }
  },
  created() {
    this.handleUserUpdated = event => {
      this.user = event?.detail || getUser()
      this.navs = getVisibleNavItems()
    }
    window.addEventListener('plant-user-updated', this.handleUserUpdated)
  },
  beforeUnmount() {
    window.removeEventListener('plant-user-updated', this.handleUserUpdated)
  },
  computed: {
    pageTitle() {
      return `${this.$route.meta?.title || 'Page'}`
    },
    isTabPage() {
      return navItems.some(item => this.$route.path === item.path)
    },
    showBackButton() {
      return !this.isTabPage
    },
    navGridStyle() {
      const columnCount = Math.max(this.navs.length, 1)
      return {
        gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))`
      }
    },
    welcomeText() {
      const name = this.user.realName || this.user.username || 'Guest User'
      return this.user.role === 'admin' ? `Welcome ${name} (System Administrator)` : `Welcome ${name}`
    }
  },
  watch: {
    '$route.fullPath'() {
      this.user = getUser()
      this.navs = getVisibleNavItems()
    }
  },
  methods: {
    isActive(path) {
      return this.$route.path === path || this.$route.path.startsWith(path + '/')
    },
    go(path) {
      if (this.$route.path !== path) {
        this.$router.push(path)
      }
    },
    handleBack() {
      if (window.history.length > 1) {
        this.$router.back()
        return
      }
      this.$router.push('/profile')
    }
  }
}
</script>
