<template>
  <div class="page-wrap">
    <template v-if="canView">
      <div class="card-panel">
        <div class="toolbar mobile-toolbar toolbar-with-actions">
          <el-select v-model="query.status" style="width:100%" @change="applySearch">
            <el-option label="Pending" value="1" />
            <el-option label="Completed" value="2" />
            <el-option label="Dismissed" value="3" />
            <el-option label="All" value="all" />
          </el-select>
          <el-select v-model="query.zoneId" style="width:100%" @change="applySearch">
            <el-option label="All Zones" value="all" />
            <el-option v-for="item in zoneOptions" :key="item.id" :label="item.zoneName" :value="String(item.id)" />
          </el-select>
          <el-button class="equal-btn" type="success" @click="applySearch">Search</el-button>
        </div>
        <div v-if="tableData.list?.length" class="stack-list top-gap-small">
          <div v-for="group in tableData.list" :key="group.locationId" class="list-card list-card-stacked">
            <div class="list-card-body wide-body">
              <div class="list-title-row wrap-row">
                <span class="list-title">{{ [group.zoneName, group.locationName].filter(Boolean).join(' · ') }}</span>
              </div>
              <div class="stack-list top-gap-small">
                <div v-for="item in group.items || []" :key="item.id" class="mini-card mini-card-column">
                  <div class="list-title-row wrap-row">
                    <span class="list-title">{{ item.displayName || item.speciesName }}</span>
                    <span class="list-time">{{ item.reminderType }}</span>
                  </div>
                  <div class="distribution-box-wrap top-gap-small">
                    <span class="distribution-box">{{ item.status }}</span>
                    <span class="distribution-box" v-if="item.ruleName">{{ item.ruleName }} {{ formatCycleDays(item.ruleCycleDays) }}</span>
                  </div>
                  <div v-if="item.statusCode !== 1 && item.processTime" class="list-desc top-gap-small">Completed At:{{ item.processTime }}</div>
                  <div v-if="item.statusCode !== 1 && item.processRemark" class="list-desc">Note:{{ item.processRemark }}</div>
                  <div class="mini-actions top-gap-small">
                    <el-button v-if="canProcess && item.statusCode === 1" class="equal-btn" type="primary" plain @click="openProcess(item, 2)">Complete</el-button>
                    <el-button v-if="canIgnore && item.statusCode === 1" class="equal-btn" type="warning" plain @click="openProcess(item, 3)">Dismiss</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">No information yet</div>
        <div v-if="(tableData.total || 0) > (query.pageSize || 5)" class="pager-wrap"><el-pagination background layout="prev, pager, next" :current-page="query.pageNum" :page-size="query.pageSize" :total="tableData.total || 0" @current-change="changePage" /></div>
      </div>
      <el-dialog v-model="dialogVisible" title="Complete Care Reminder" width="92%">
        <el-form :model="form" label-position="top">
          <el-form-item label="Note"><el-input v-model="form.processRemark" type="textarea" :rows="4" /></el-form-item>
        </el-form>
        <template #footer>
          <div class="dual-action spaced-action">
            <el-button class="equal-btn" @click="dialogVisible = false">Cancel</el-button>
            <el-button class="equal-btn" type="primary" @click="submitProcess">Confirm</el-button>
          </div>
        </template>
      </el-dialog>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { reminderListApi, processReminderApi, zoneListApi } from '@/api'
import { hasPermission } from '@/utils/auth'
import { formatEnglishDays } from '@/utils/textFormat'
export default {
  computed: {
    canView() { return hasPermission('care', 'view') },
    canProcess() { return hasPermission('care', 'process') },
    canIgnore() { return hasPermission('care', 'ignore') }
  },
  data() {
    return {
      query: { status: '1', zoneId: 'all', pageNum: 1, pageSize: 5 },
      zoneOptions: [],
      tableData: { list: [], total: 0 },
      dialogVisible: false,
      currentId: '',
      form: { processResult: 2, processRemark: '' }
    }
  },
  created() { if (!this.canView) return; this.loadZones(); this.loadData() },
  methods: {
    formatCycleDays(value) { return formatEnglishDays(value) },
    async loadZones() { if (!this.canView) { this.zoneOptions = []; return } const res = await zoneListApi(); this.zoneOptions = res.data || [] },
    async loadData() { if (!this.canView) { this.tableData = { list: [], total: 0 }; return } const res = await reminderListApi(this.query); this.tableData = res.data || { list: [], total: 0 } },
    applySearch() { this.query.pageNum = 1; this.loadData() },
    changePage(page) { this.query.pageNum = page; this.loadData() },
    openProcess(item, status) { this.currentId = item.id; this.form = { processResult: status, processRemark: '' }; this.dialogVisible = true },
    async submitProcess() { await processReminderApi(this.currentId, this.form); this.dialogVisible = false; this.loadData() }
  }
}
</script>
