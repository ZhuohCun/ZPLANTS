<template>
  <div class="page-wrap">
    <section v-if="visibleStats.length" class="card-panel home-panel">
      <div class="section-head section-head-tight">
        <div class="section-title">Overview</div>
      </div>
      <div class="stats-grid compact-grid fixed-two-grid">
        <div v-for="item in visibleStats" :key="item.key" class="stat-card stat-card-balanced">
          <div class="stat-value">{{ item.value }}</div>
          <div class="stat-meta">{{ item.label }}</div>
        </div>
      </div>
    </section>

    <section class="card-panel home-panel">
      <div class="section-head section-head-tight">
        <div class="section-title">Quick Actions</div>
      </div>
      <div class="quick-action-grid">
        <button v-if="hasFeature('recognition')" class="quick-card quick-card-primary" @click="$router.push('/recognition/upload')">
          <div class="quick-card-title">Recognize Now</div>
          <div class="quick-card-desc">Upload a plant photo to get a recognition result.</div>
        </button>
        <button v-if="hasFeature('species')" class="quick-card" @click="$router.push('/species')">
          <div class="quick-card-title">Plant Species</div>
          <div class="quick-card-desc">{{ speciesEntryDesc }}</div>
        </button>
        <button v-if="hasPermission('care','view')" class="quick-card quick-card-alert" @click="$router.push('/care')">
          <div class="quick-card-title">Care Reminders</div>
          <div class="quick-card-desc">View and complete pending care reminders.</div>
        </button>
        <button v-if="hasFeature('feedback') && hasPermission('feedback','submit')" class="quick-card" @click="$router.push('/feedback')">
          <div class="quick-card-title">Send Feedback</div>
          <div class="quick-card-desc">Send suggestions or feedback on a recognition result.</div>
        </button>
      </div>
    </section>

    <section v-if="hasPermission('recognition', 'view_records')" class="card-panel home-panel home-feed-panel">
      <div class="section-head section-head-tight">
        <div class="section-title">Recent Recognition Records</div>
      </div>
      <div v-if="(stats.recentRecognitions || []).length" class="stack-list stack-list-compact home-record-container">
        <div
          v-for="item in stats.recentRecognitions"
          :key="item.id"
          class="list-card recognition-card home-record-card"
          @click="$router.push(`/recognition/result/${item.id}`)"
        >
          <img :src="assetUrl(item.imageUrl)" class="thumb-image" @error="setImageFallback" />
          <div class="list-card-body wide-body">
            <div class="list-title-row wrap-row">
              <span class="list-title">{{ item.speciesName || item.plantName }}</span>
              <span class="list-time">{{ item.createTime }}</span>
            </div>
            <div class="list-desc">The photo and result have been saved.</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No information yet</div>
    </section>

    <section v-if="hasPermission('care','view')" class="card-panel home-panel home-feed-panel">
      <div class="section-head section-head-tight">
        <div class="section-title">Pending Care</div>
      </div>
      <div v-if="(stats.pendingReminders || []).length" class="stack-list stack-list-compact home-reminder-container">
        <div v-for="item in stats.pendingReminders" :key="item.id" class="mini-card reminder-card home-reminder-card" @click="openReminder(item)">
          <div class="reminder-status-corner">Pending</div>
          <div class="reminder-card-body">
            <div class="list-title-row wrap-row reminder-head-row">
              <span class="list-title">{{ formatPlace(item) }}</span>
              <span class="list-time reminder-time">{{ item.createTime }}</span>
            </div>
            <div class="list-desc emphasis-desc">{{ item.speciesName }} · {{ item.reminderType }}</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No information yet</div>
    </section>
  </div>
</template>

<script>
import { dashboardApi } from '@/api'
import { backendAssetUrl, DEFAULT_COVER_URL } from '@/api/request'
import { hasFeature, hasPermission } from '@/utils/auth'

export default {
  name: 'HomeView',
  data() {
    return {
      stats: {}
    }
  },
  computed: {
    speciesEntryDesc() {
      return hasPermission('species', 'view_distribution') ? 'View plant species and campus distribution details.' : 'View species details'
    },
    visibleStats() {
      const cards = []
      if (hasFeature('species')) cards.push({ key: 'species', label: 'Plant Species', value: this.stats.speciesCount || 0 })
      if (hasFeature('plant')) cards.push({ key: 'plants', label: 'Plant Management', value: this.stats.plantCount || 0 })
      if (hasPermission('recognition', 'view_records')) cards.push({ key: 'recognitions', label: 'Recognition Count', value: this.stats.recognitionCount || 0 })
      if (hasPermission('care', 'view')) cards.push({ key: 'pending', label: 'Pending Care', value: this.stats.pendingReminderCount || 0 })
      return cards
    }
  },
  created() {
    this.loadData()
  },
  methods: {
    setImageFallback(event) { event.target.src = DEFAULT_COVER_URL },
    assetUrl(value) { return backendAssetUrl(value) },
    hasFeature,
    hasPermission,
    openReminder() {
      this.$router.push('/care')
    },
    formatPlace(item) {
      const zone = String(item?.zoneName || '').trim()
      const location = String(item?.locationName || '').trim()
      if (zone && location) return `${zone} - ${location}`
      return zone || location || 'No location information'
    },
    async loadData() {
      const res = await dashboardApi()
      this.stats = res.data || {}
    }
  }
}
</script>
