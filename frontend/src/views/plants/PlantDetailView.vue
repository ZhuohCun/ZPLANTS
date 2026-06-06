<template>
  <div class="page-wrap">
    <template v-if="canView">
      <div class="card-panel detail-card plant-detail-shell">
        <div class="detail-section">
          <div class="info-row"><span class="label">Plant Name</span><span class="value">{{ detail.displayName || 'No information yet' }}</span></div>
          <div class="info-row"><span class="label">Plant Species</span><span class="value">{{ detail.speciesName || 'No information yet' }}</span></div>
          <div class="info-row"><span class="label">Scientific Name</span><span class="value">{{ detail.scientificName || 'No information yet' }}</span></div>
          <div class="info-row"><span class="label">Light Needs</span><span class="value">{{ detail.lightRequirement || 'No information yet' }}</span></div>
        </div>
        <div v-if="showCare" class="detail-divider"></div>
        <div v-if="showCare" class="detail-section">
          <span class="label">Care Notes</span>
          <p class="value-block">{{ detail.carePoints || 'No information yet' }}</p>
        </div>
        <div v-if="canViewDistribution" class="detail-divider"></div>
        <div v-if="canViewDistribution" class="detail-section">
          <span class="label">Locations</span>
          <div class="distribution-box-wrap">
            <span v-for="item in detail.locations || []" :key="`${item.zone_id}-${item.location_id}`" class="distribution-box">{{ [item.zone_name, item.location_name].filter(Boolean).join('-') }}</span>
            <span v-if="!(detail.locations || []).length" class="distribution-box muted-box">No information yet</span>
          </div>
        </div>
        <div v-if="showCare" class="detail-divider"></div>
        <div v-if="showCare" class="detail-section">
          <span class="label">Care Rules</span>
          <div class="distribution-box-wrap">
            <span v-for="rule in detail.care_rules || []" :key="rule.id || rule.methodName" class="distribution-box">{{ rule.methodName }} {{ formatCycleDays(rule.cycleDays) }}</span>
            <span v-if="!(detail.care_rules || []).length" class="distribution-box muted-box">No information yet</span>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { hasPermission } from '@/utils/auth'
import { plantDetailApi } from '@/api'
import { formatEnglishDays } from '@/utils/textFormat'
export default {
  computed: { canView() { return hasPermission('plant', 'view') }, canViewDistribution() { return hasPermission('species', 'view_distribution') }, showCare() { return hasPermission('care', 'view') } },
  data() { return { detail: {} } },
  created() { if (this.canView) this.loadData() },
  methods: {
    formatCycleDays(value) { return formatEnglishDays(value) },
    async loadData() { if (!this.canView) { this.detail = {}; return } const res = await plantDetailApi(this.$route.params.id); this.detail = res.data || {} }
  }
}
</script>
