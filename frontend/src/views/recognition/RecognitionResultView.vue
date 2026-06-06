<template>
  <div class="page-wrap">
    <template v-if="canView">
    <div class="card-panel result-panel">
      <img :src="assetUrl(detail.imageUrl)" class="cover-image" @error="setImageFallback" />
      <div class="tag-list" style="margin-top:1rem"><el-tag type="success">{{ detail.speciesName || detail.plantName }}</el-tag><el-tag type="info">{{ detail.plantInfo?.scientificName }}</el-tag></div>
      <div class="result-meta">Recognized at: {{ detail.createTime }}</div>
    </div>
    <div class="card-panel detail-stack">
      <div class="page-title">Plant Information and Care Advice</div>
      <div class="info-row"><span class="label">Plant Species</span><span class="value">{{ detail.plantInfo?.speciesName || detail.plantInfo?.plantName }}</span></div>
      <div class="info-row"><span class="label">Scientific Name</span><span class="value">{{ detail.plantInfo?.scientificName }}</span></div>
      <div v-if="canViewDistribution" class="info-row"><span class="label">Campus Distribution</span><span class="value">{{ detail.plantInfo?.distribution || 'No information yet' }}</span></div>
      <div v-if="canViewCare" class="info-block"><span class="label">Care Rules</span><div class="distribution-box-wrap"><span v-for="rule in detail.plantInfo?.care_rules || []" :key="rule.id || rule.methodName" class="distribution-box">{{ rule.methodName }} {{ formatCycleDays(rule.cycleDays) }}</span><span v-if="!(detail.plantInfo?.care_rules || []).length" class="distribution-box muted-box">No information yet</span></div></div>
      <div v-if="canViewCare" class="info-block"><span class="label">Care Notes</span><p class="value-block">{{ detail.plantInfo?.carePoints || 'No information yet' }}</p></div>
      <div class="page-title" style="margin-top:1rem">Similar Candidates</div>
      <div class="stack-list compact-list"><div v-for="item in detail.topK || []" :key="item.rank || item.speciesId || item.plantId" class="mini-card"><span>{{ formatCandidate(item) }}</span></div></div>
      <div class="actions" style="margin-top:1rem"><el-button v-if="canSubmitFeedback" class="equal-btn" type="primary" @click="goFeedback">Send Result Feedback</el-button><el-button v-if="canViewRecords" class="equal-btn" @click="$router.push('/recognition/records')">View Recognition Records</el-button></div>
    </div>
    </template>
  </div>
</template>
<script>
import { hasPermission } from '@/utils/auth'
import { recognitionDetailApi } from '@/api'
import { backendAssetUrl, DEFAULT_COVER_URL } from '@/api/request'
import { formatEnglishDays } from '@/utils/textFormat'
export default {
  computed: { canView() { return hasPermission('recognition', 'capture') }, canViewRecords() { return hasPermission('recognition', 'view_records') }, canViewCare() { return hasPermission('care', 'view') }, canViewDistribution() { return hasPermission('species', 'view_distribution') }, canSubmitFeedback() { return hasPermission('feedback', 'submit') } }, data() { return { detail: {} } }, created() { if (this.canView) this.loadData() }, methods: {
    formatCycleDays(value) { return formatEnglishDays(value) }, formatConfidence(value) { return `${(Number(value || 0) * 100).toFixed(2)}%` }, formatCandidate(item) { const name = item?.speciesName || item?.plantName || 'Unknown Result'; return `${name} ${this.formatConfidence(item?.confidence)}` }, setImageFallback(event) { event.target.src = DEFAULT_COVER_URL }, assetUrl(value) { return backendAssetUrl(value) }, async loadData() { if (!this.canView) { this.detail = {}; return } const res = await recognitionDetailApi(this.$route.params.id); this.detail = res.data || {} }, goFeedback() { this.$router.push({ path: '/feedback', query: { recognitionId: this.detail.id, typeCode: 2 } }) } } }
</script>


