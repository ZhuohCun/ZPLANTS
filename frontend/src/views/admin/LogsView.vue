<template>
  <div class="page-wrap">
    <template v-if="canView">
    <div class="card-panel">
      <div class="toolbar mobile-toolbar toolbar-full-row"><el-input v-model="query.keyword" @keyup.enter="applySearch" @clear="applySearch" placeholder="Search username, module, or IP" clearable /><el-button class="equal-btn" type="success" @click="applySearch">Search</el-button></div>
      <div v-if="tableData.list?.length" class="stack-list top-gap-small">
        <div v-for="item in tableData.list" :key="item.id" class="mini-card mini-card-column">
          <div class="list-title-row wrap-row"><span class="list-title">{{ item.operationModule }} · {{ item.operationName }}</span><span class="list-time">{{ item.createTime }}</span></div>
          <div class="list-desc">Operator:{{ item.realName || item.username || 'Guest User' }}</div>
          <div class="list-desc">Address:{{ item.requestUrl }} {{ item.requestMethod }}</div>
          <div class="list-desc">IP: {{ item.ip }} {{ item.ipLocation }}</div>
        </div>
      </div>
      <div v-else class="empty-state">No information yet</div>
      <div v-if="(tableData.total || 0) > (query.pageSize || 5)" class="pager-wrap"><el-pagination background layout="prev, pager, next" :current-page="query.pageNum" :page-size="query.pageSize" :total="tableData.total || 0" @current-change="changePage" /></div>
    </div>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { hasPermission } from '@/utils/auth'
import { logListApi } from '@/api'
export default {
  computed: {
    canView() { return hasPermission('logs', 'view') }
  }, data() { return { query: { keyword: '', pageNum: 1, pageSize: 10 }, tableData: { list: [], total: 0 } } }, created() { this.loadData() }, methods: { async loadData() { const res = await logListApi(this.query); this.tableData = res.data || { list: [], total: 0 } }, applySearch() { this.query.pageNum = 1; this.loadData() },
    changePage(page) { this.query.pageNum = page; this.loadData() } } }
</script>

<style scoped>
.view-empty-card { min-height: 12rem; display: grid; place-items: center; }
</style>
