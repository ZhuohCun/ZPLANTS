<template>
  <div class="page-wrap">
    <template v-if="canView">
      <div class="card-panel detail-card">
        <div class="detail-hero">
          <img v-if="detail.imageUrl" :src="assetUrl(detail.imageUrl)" class="cover-image species-cover-image species-cover-image-detail" @error="setImageFallback" />
          <div class="detail-section detail-summary-card">
            <div class="info-row"><span class="label">Plant Species</span><span class="value">{{ detail.speciesName }}</span></div>
            <div class="info-row"><span class="label">Scientific Name</span><span class="value">{{ detail.scientificName || 'No information yet' }}</span></div>
            <div class="info-row"><span class="label">Light Needs</span><span class="value">{{ detail.lightRequirement || 'No information yet' }}</span></div>
          </div>
        </div>
        <div v-if="showCare" class="detail-divider"></div>
        <div v-if="showCare" class="detail-section"><span class="label">Care Notes</span><p class="value-block">{{ detail.carePoints || 'No information yet' }}</p></div>
        <div v-if="canViewDistribution" class="detail-divider"></div>
        <div v-if="canViewDistribution" class="detail-section"><span class="label">Locations</span><div class="distribution-box-wrap"><span v-for="item in detail.locations || []" :key="`${item.zone_id}-${item.location_id}`" class="distribution-box">{{ [item.zone_name || item.zoneName, item.location_name || item.locationName].filter(Boolean).join('-') }}</span><span v-if="!(detail.locations || []).length" class="distribution-box muted-box">No information yet</span></div></div>
        <div v-if="showCare" class="detail-divider"></div>
        <div v-if="showCare" class="detail-section"><span class="label">Care Rules</span><div class="distribution-box-wrap"><span v-for="rule in detail.care_rules || []" :key="rule.id || rule.methodName" class="distribution-box">{{ rule.methodName }} {{ formatCycleDays(rule.cycleDays) }}</span><span v-if="!(detail.care_rules || []).length" class="distribution-box muted-box">No information yet</span></div></div>
      </div>
      <div v-if="canViewPlants" class="card-panel top-gap-medium">
        <div class="section-head section-head-tight"><div class="section-title">Plant</div></div>
        <div v-if="detail.plants?.length" class="stack-list top-gap-small"><div v-for="item in detail.plants" :key="item.id" class="mini-card mini-card-column"><div class="list-title">{{ item.displayName || 'Unnamed Plant' }}</div><div class="distribution-box-wrap top-gap-small"><span class="distribution-box">{{ [item.zoneName, item.locationName].filter(Boolean).join('-') || 'No location set' }}</span></div></div></div>
        <div v-else class="empty-state">No information yet</div>
      </div>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { hasPermission } from '@/utils/auth'
import { speciesDetailApi } from '@/api'
import { backendAssetUrl, DEFAULT_COVER_URL } from '@/api/request'
import { formatEnglishDays } from '@/utils/textFormat'
export default {
  computed: { canView() { return hasPermission('species', 'view') }, canViewDistribution() { return hasPermission('species', 'view_distribution') }, canViewPlants() { return hasPermission('plant', 'view') }, showCare() { return hasPermission('care', 'view') } },
  data() { return { detail: {} } },
  created() { if (this.canView) this.loadData() },
  methods: { formatCycleDays(value) { return formatEnglishDays(value) }, setImageFallback(event) { event.target.src = DEFAULT_COVER_URL }, assetUrl(value) { return backendAssetUrl(value) }, async loadData() { if (!this.canView) { this.detail = {}; return } const res = await speciesDetailApi(this.$route.params.id); this.detail = res.data || {} } }
}
</script>

<style scoped>
.detail-hero { display: grid; grid-template-columns: minmax(0, 13rem) minmax(0, 1fr); gap: 1rem; align-items: stretch; }
.detail-summary-card { display: flex; flex-direction: column; justify-content: center; border-radius: 1rem; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); }
.species-cover-image-detail { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; object-position: center center; border-radius: 1rem; background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%); box-shadow: 0 0.55rem 1.35rem rgba(15, 23, 42, 0.08); }
@media (max-width: 640px) {
  .detail-hero { grid-template-columns: 1fr; justify-items: center; }
  .species-cover-image-detail { width: min(100%, 21rem); max-width: 21rem; margin: 0 auto; }
  .detail-summary-card { width: 100%; }
}
@media (max-width: 640px) and (orientation: portrait) {
  .species-cover-image-detail { width: min(100%, 22rem); max-width: 22rem; }
}
</style>
