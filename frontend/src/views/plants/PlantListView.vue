<template>
  <div class="page-wrap">
    <template v-if="canView">
      <div class="card-panel">
        <div class="toolbar mobile-toolbar toolbar-with-actions">
          <el-input v-model="query.keyword" @keyup.enter="applySearch" @clear="applySearch" placeholder="Search species, zone, or location" clearable />
          <el-select v-model="query.zoneId" style="width:100%" @change="applySearch"><el-option label="All Zones" value="all" /><el-option v-for="item in zoneOptions" :key="item.id" :label="item.zoneName" :value="item.id" /></el-select>
          <el-select v-model="query.speciesId" style="width:100%" @change="applySearch"><el-option label="All Species" value="all" /><el-option v-for="item in speciesOptions" :key="item.id" :label="item.speciesName" :value="item.id" /></el-select>
          <el-button class="equal-btn" type="success" @click="applySearch">Search</el-button>
          <el-button v-if="canCreate" class="equal-btn" type="primary" @click="openDialog()">Add Plant</el-button>
        </div>
        <div v-if="tableData.list?.length" class="stack-list top-gap-small">
          <div v-for="item in tableData.list" :key="item.id" class="list-card list-card-stacked">
            <div class="list-card-body wide-body">
              <div class="list-title-row wrap-row">
                <span class="list-title">{{ item.displayName || 'Unnamed Plant' }}</span>
                <span class="list-time">{{ item.speciesName || 'No information yet' }}</span>
              </div>
              <div v-if="canViewDistribution" class="list-desc">Locations</div>
              <div class="distribution-box-wrap top-gap-small">
                <span v-for="part in item.locations || []" :key="`${part.zoneId || part.zone_id}-${part.locationId || part.location_id}`" class="distribution-box">{{ [part.zoneName || part.zone_name, part.locationName || part.location_name].filter(Boolean).join('-') }}</span>
                <span v-if="!(item.locations || []).length" class="distribution-box muted-box">No location set</span>
              </div>
              <div v-if="canViewCare" class="section-caption top-gap-small">Care Rules</div>
              <div v-if="canViewCare" class="distribution-box-wrap">
                <span v-for="rule in item.care_rules || []" :key="`${item.id}-${rule.id || rule.methodName}`" class="distribution-box">{{ rule.methodName }} {{ formatCycleDays(rule.cycleDays) }}</span>
                <span v-if="!(item.care_rules || []).length" class="distribution-box muted-box">No information yet</span>
              </div>
              <div class="mini-actions top-gap-small" :class="actionClass()">
                <el-button class="equal-btn" type="success" plain @click="goDetail(item.id)">View Details</el-button>
                <el-button v-if="canUpdate" class="equal-btn" type="primary" plain @click="openDialog(item)">Edit</el-button>
                <el-button v-if="canDelete" class="equal-btn" type="danger" plain @click="remove(item)">Delete</el-button>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">No information yet</div>
        <div v-if="(tableData.total || 0) > (query.pageSize || 5)" class="pager-wrap"><el-pagination background layout="prev, pager, next" :current-page="query.pageNum" :page-size="query.pageSize" :total="tableData.total || 0" @current-change="changePage" /></div>
      </div>
      <el-dialog v-model="dialogVisible" :title="form.id ? 'Edit Plant' : 'Add Plant'" destroy-on-close>
        <el-form :model="form" label-position="top">
          <el-form-item label="Plant Species"><el-select v-model="form.speciesId" style="width:100%"><el-option v-for="item in speciesOptions" :key="item.id" :label="item.speciesName" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="Zone"><el-select v-model="form.zoneId" style="width:100%" @change="handleZoneChange"><el-option v-for="item in zoneOptions" :key="item.id" :label="item.zoneName" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="Location"><el-select v-model="form.locationId" style="width:100%"><el-option v-for="item in locationOptions" :key="item.id" :label="item.locationName" :value="item.id" /></el-select></el-form-item>
        </el-form>
        <template #footer><div class="dual-action spaced-action"><el-button class="equal-btn" @click="dialogVisible = false">Cancel</el-button><el-button class="equal-btn" type="primary" @click="submit">Save</el-button></div></template>
      </el-dialog>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { plantListApi, plantDetailApi, createPlantApi, updatePlantApi, deletePlantApi, speciesListApi, locationHierarchyApi } from '@/api'
import { hasPermission } from '@/utils/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatEnglishDays } from '@/utils/textFormat'
export default {
  data() {
    return { query: { keyword: '', zoneId: 'all', speciesId: 'all', pageNum: 1, pageSize: 5 }, tableData: { list: [], total: 0 }, dialogVisible: false, form: { speciesId: '', zoneId: '', locationId: '' }, speciesOptions: [], zoneOptions: [], hierarchy: [], locationOptions: [] }
  },
  computed: {
    canView() { return hasPermission('plant', 'view') },
    canViewDistribution() { return hasPermission('species', 'view_distribution') },
    canViewCare() { return hasPermission('care', 'view') },
    canCreate() { return hasPermission('plant', 'create') },
    canUpdate() { return hasPermission('plant', 'update') },
    canDelete() { return hasPermission('plant', 'delete') }
  },
  created() { if (!this.canView) return; this.loadData(); this.loadBasic() },
  methods: {
    formatCycleDays(value) { return formatEnglishDays(value) },
    actionClass() {
      const count = 1 + (this.canUpdate ? 1 : 0) + (this.canDelete ? 1 : 0)
      return `action-count-${count}`
    },
    async loadBasic() {
      if (!this.canView) { this.speciesOptions = []; this.hierarchy = []; this.zoneOptions = []; return }
      this.speciesOptions = (await speciesListApi({ pageNum: 1, pageSize: 500, silentView: 1 })).data?.list || []
      this.hierarchy = (await locationHierarchyApi()).data || []
      this.zoneOptions = this.hierarchy.map(v => ({ id: v.id, zoneName: v.zoneName }))
    },
    async loadData() { if (!this.canView) { this.tableData = { list: [], total: 0 }; return } const res = await plantListApi(this.query); this.tableData = res.data || { list: [], total: 0 } },
    applySearch() { this.query.pageNum = 1; this.loadData() },
    changePage(page) { this.query.pageNum = page; this.loadData() },
    goDetail(id) { this.$router.push(`/plants/${id}`) },
    handleZoneChange(value, preserveLocationId = '') { const target = this.hierarchy.find(v => Number(v.id) === Number(value)); this.locationOptions = target?.locations || []; this.form.locationId = preserveLocationId || '' },
    async openDialog(item) {
      if (!this.hierarchy.length) await this.loadBasic()
      if (!item) { this.form = { speciesId: '', zoneId: '', locationId: '' }; this.locationOptions = []; this.dialogVisible = true; return }
      const res = await plantDetailApi(item.id)
      const detail = res.data || {}
      const firstLocation = (detail.locations || [])[0] || {}
      const firstZoneId = firstLocation.zoneId || firstLocation.zone_id || ''
      const firstLocationId = firstLocation.locationId || firstLocation.location_id || ''
      this.form = { id: item.id, speciesId: detail.speciesId, zoneId: firstZoneId, locationId: firstLocationId }
      this.handleZoneChange(firstZoneId, firstLocationId)
      this.dialogVisible = true
    },
    async submit() {
      if (!this.form.speciesId || !this.form.locationId) { ElMessage.warning('Choose a plant species and a location.'); return }
      const payload = { speciesId: Number(this.form.speciesId), locationIds: [Number(this.form.locationId)] }
      if (this.form.id) await updatePlantApi(this.form.id, payload)
      else await createPlantApi(payload)
      this.dialogVisible = false
      this.loadData()
    },
    async remove(item) {
      await ElMessageBox.confirm(`Delete plant "${item.displayName || item.speciesName || item.id}"?`, 'Notice', { type: 'warning' })
      await deletePlantApi(item.id)
      this.loadData()
    }
  }
}
</script>

