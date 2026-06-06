<template>
  <div class="page-wrap">
    <template v-if="canView">
    <div class="card-panel">
      <div class="toolbar mobile-toolbar toolbar-with-actions">
        <el-input v-model="query.speciesName" @keyup.enter="applySearch" @clear="applySearch" placeholder="Search by plant species" clearable />
        <el-button class="equal-btn" type="success" @click="applySearch">Search</el-button>
      </div>
      <div v-if="tableData.list?.length" class="stack-list top-gap-small">
        <div v-for="item in tableData.list" :key="item.id" class="list-card" @click="goDetail(item.id)">
          <img :src="assetUrl(item.imageUrl)" class="thumb-image" @error="setImageFallback" />
          <div class="list-card-body">
            <div class="list-title-row wrap-row">
              <span class="list-title">{{ item.speciesName || item.plantName }}</span>
              <span class="list-time">{{ item.createTime }}</span>
            </div>
            <div class="list-desc">The photo and result have been saved.</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No information yet</div>
      <div v-if="(tableData.total || 0) > (query.pageSize || 5)" class="pager-wrap"><el-pagination background layout="prev, pager, next" :current-page="query.pageNum" :page-size="query.pageSize" :total="tableData.total || 0" @current-change="changePage" /></div>
    </div>
    </template>
  </div>
</template>
<script>
import { hasPermission } from '@/utils/auth'
import { recognitionListApi } from '@/api'
import { backendAssetUrl, DEFAULT_COVER_URL } from '@/api/request'
export default {
  computed: {
    canView() { return hasPermission('recognition', 'view_records') }
  },
  data() {
    return { query: { speciesName: '', pageNum: 1, pageSize: 5 }, tableData: { list: [], total: 0 } }
  },
  created() { if (this.canView) this.loadData() },
  methods: {
    setImageFallback(event) { event.target.src = DEFAULT_COVER_URL },
    assetUrl(value) { return backendAssetUrl(value) },
    async loadData() { if (!this.canView) { this.tableData = { list: [], total: 0 }; return } const res = await recognitionListApi(this.query); this.tableData = res.data || { list: [], total: 0 } },
    applySearch() { this.query.pageNum = 1; this.loadData() },
    changePage(page) { this.query.pageNum = page; this.loadData() },
    goDetail(id) { this.$router.push(`/recognition/result/${id}`) }
  }
}
</script>


