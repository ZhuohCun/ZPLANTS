<template>
  <div class="page-wrap">
    <template v-if="canView">
      <div class="card-panel">
        <div class="section-head section-head-tight">
          <div>
            <div class="section-title">Care Method Management</div>
          </div>
        </div>
        <div class="toolbar mobile-toolbar toolbar-with-actions top-gap-small">
          <el-input v-model="query.keyword" @keyup.enter="applySearch" @clear="applySearch" placeholder="Enter a care method name" clearable />
          <el-button class="equal-btn" type="success" @click="applySearch">Search</el-button>
          <el-button v-if="canCreate" class="equal-btn" type="primary" @click="openDialog()">Add Method</el-button>
        </div>
        <div v-if="tableData.list?.length" class="stack-list top-gap-small">
          <div v-for="item in tableData.list" :key="item.id" class="mini-card mini-card-column">
            <div class="list-title-row wrap-row">
              <span class="list-title">{{ item.methodName }}</span>
            </div>
            <div class="mini-actions top-gap-small">
              <el-button v-if="canUpdate" class="equal-btn" type="primary" plain @click="openDialog(item)">Edit</el-button>
              <el-button v-if="canDelete" class="equal-btn" type="danger" plain @click="remove(item)">Delete</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">No information yet</div>
        <div v-if="(tableData.total || 0) > (query.pageSize || 5)" class="pager-wrap">
          <el-pagination background layout="prev, pager, next" :current-page="query.pageNum" :page-size="query.pageSize" :total="tableData.total || 0" @current-change="changePage" />
        </div>
      </div>

      <el-dialog v-model="dialogVisible" :title="form.id ? 'Edit Care Method' : 'Add Care Method'" width="92%">
        <el-form :model="form" label-position="top">
          <el-form-item label="Care Method Name"><el-input v-model="form.methodName" /></el-form-item>
        </el-form>
        <template #footer>
          <div class="dialog-footer dual-action spaced-action">
            <el-button class="equal-btn" @click="dialogVisible = false">Cancel</el-button>
            <el-button class="equal-btn" type="primary" @click="submit">Save</el-button>
          </div>
        </template>
      </el-dialog>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { careMethodListApi, createCareMethodApi, updateCareMethodApi, deleteCareMethodApi } from '@/api'
import { hasPermission } from '@/utils/auth'
import { ElMessageBox } from 'element-plus'

export default {
  data() {
    return {
      query: { keyword: '', pageNum: 1, pageSize: 5 },
      tableData: { list: [], total: 0 },
      dialogVisible: false,
      form: { methodName: '' }
    }
  },
  computed: {
    canView() { return hasPermission('care_method', 'view') },
    canCreate() { return hasPermission('care_method', 'create') },
    canUpdate() { return hasPermission('care_method', 'update') },
    canDelete() { return hasPermission('care_method', 'delete') }
  },
  created() { if (this.canView) this.loadData() },
  methods: {
    async loadData() { if (!this.canView) { this.tableData = { list: [], total: 0 }; return } const res = await careMethodListApi({ silentView: 1, ...this.query }); this.tableData = res.data || { list: [], total: 0 } },
    applySearch() { this.query.pageNum = 1; this.loadData() },
    changePage(page) { this.query.pageNum = page; this.loadData() },
    openDialog(item) { this.form = item ? { id: item.id, methodName: item.methodName } : { methodName: '' }; this.dialogVisible = true },
    async submit() { if (this.form.id) await updateCareMethodApi(this.form.id, { methodName: this.form.methodName }); else await createCareMethodApi({ methodName: this.form.methodName }); this.dialogVisible = false; this.loadData() },
    async remove(item) { await ElMessageBox.confirm(`Delete care method "${item.methodName}"?`, 'Notice', { type: 'warning' }); await deleteCareMethodApi(item.id); this.loadData() }
  }
}
</script>
