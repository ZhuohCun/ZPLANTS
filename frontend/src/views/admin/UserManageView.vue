<template>
  <div class="page-wrap">
    <template v-if="canView">
    <div class="card-panel">
      <div class="toolbar mobile-toolbar toolbar-with-actions">
        <el-input v-model="query.keyword" @keyup.enter="applySearch" @clear="applySearch" placeholder="Search username, name, or email" clearable />
        <el-button class="equal-btn" type="success" @click="applySearch">Search</el-button>
        <el-button v-if="canCreate" class="equal-btn" type="primary" @click="openDialog()">Add User</el-button>
      </div>
      <div v-if="tableData.list?.length" class="stack-list top-gap-small">
        <div v-for="item in tableData.list" :key="item.id" class="list-card">
          <div class="list-card-body wide-body">
            <div class="list-title-row wrap-row"><span class="list-title">{{ item.username }}</span><span class="list-time">{{ item.roleName }}</span></div>
            <div class="list-desc">Name:{{ item.realName || 'No information yet' }} · Email:{{ item.email || 'No information yet' }}</div>
            <div class="list-desc">Status: {{ item.status }}</div>
            <div v-if="item.statusCode === 0" class="list-desc">Disable Reason: {{ item.disableReason || 'No information yet' }}</div>
            <div v-if="item.statusCode === 0" class="list-desc">Disabled By: {{ item.disabledByName || 'No information yet' }}</div>
            <div class="mini-actions top-gap-small">
              <el-button v-if="canUpdate" class="equal-btn" type="primary" plain @click="openDialog(item)">Edit</el-button>
              <el-button v-if="canDisable" class="equal-btn" :type="item.statusCode===1 ? 'warning' : 'success'" plain @click="toggleStatus(item)">{{ item.statusCode===1 ? 'Disable' : 'Enable' }}</el-button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No information yet</div>
      <div v-if="(tableData.total || 0) > (query.pageSize || 5)" class="pager-wrap"><el-pagination background layout="prev, pager, next" :current-page="query.pageNum" :page-size="query.pageSize" :total="tableData.total || 0" @current-change="changePage" /></div>
    </div>

    <el-dialog v-model="dialogVisible" :title="form.id ? 'Edit User' : 'Add User'" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="Username"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="Full Name"><el-input v-model="form.realName" /></el-form-item>
        <el-form-item label="Phone"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="Email"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="Role"><el-select v-model="form.role" style="width:100%"><el-option label="General User" value="user" /><el-option label="Grounds Maintenance" value="manager" /><el-option label="System Administrator" value="admin" /></el-select></el-form-item>
        <el-form-item label="Password"><el-input v-model="form.password" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer><div class="dual-action"><el-button class="equal-btn" @click="dialogVisible=false">Cancel</el-button><el-button class="equal-btn" type="primary" @click="submit">Save</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="disableVisible" title="Disable User" destroy-on-close>
      <el-form :model="disableForm" label-position="top">
        <el-form-item label="Disable Reason"><el-input v-model="disableForm.disableReason" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer><div class="dual-action"><el-button class="equal-btn" @click="disableVisible=false">Cancel</el-button><el-button class="equal-btn" type="warning" @click="confirmDisable">Disable User</el-button></div></template>
    </el-dialog>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { userListApi, createUserApi, updateUserApi } from '@/api'
import { getUser, clearAuth, hasPermission } from '@/utils/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  computed: {
    canView() { return hasPermission('users', 'view') },
    canCreate() { return hasPermission('users', 'update') },
    canUpdate() { return hasPermission('users', 'update') },
    canDisable() { return hasPermission('users', 'disable') }
  },
  data() {
    return {
      query: { keyword: '', pageNum: 1, pageSize: 5 },
      tableData: { list: [], total: 0 },
      dialogVisible: false,
      disableVisible: false,
      form: {},
      currentTarget: null,
      disableForm: { disableReason: '' }
    }
  },
  created() { if (this.canView) this.loadData() },
  methods: {
    async loadData() { if (!this.canView) { this.tableData = { list: [], total: 0 }; return } const res = await userListApi(this.query); this.tableData = res.data || { list: [], total: 0 } },
    applySearch() { this.query.pageNum = 1; this.loadData() },
    changePage(page) { this.query.pageNum = page; this.loadData() },
    openDialog(item) { this.form = item ? { ...item, password: '' } : { username: '', realName: '', phone: '', email: '', role: 'user', password: '' }; this.dialogVisible = true },
    async submit() {
      this.form.phone = String(this.form.phone || '').trim()
      this.form.phone = String(this.form.phone || '').replace(/[０-９]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 65248)).replace(/\D/g, '')
      this.form.email = String(this.form.email || '').trim()
      if (this.form.phone && !/^\d{11}$/.test(this.form.phone)) { ElMessage.warning('Enter an 11-digit phone number.'); return }
      if (this.form.email && !String(this.form.email).includes('@')) { ElMessage.warning('Enter a valid email address.'); return }
      if (!this.form.id && !this.form.password) { ElMessage.warning('Set a password when adding a new user.'); return }
      const current = getUser()
      const isSelf = Number(this.form.id) === Number(current.id)
      const before = this.tableData.list.find(item => Number(item.id) === Number(this.form.id)) || {}
      const changed = !this.form.id || ['username', 'realName', 'phone', 'email', 'role'].some(key => (this.form[key] || '') !== (before[key] || '')) || !!this.form.password
      if (this.form.id) await updateUserApi(this.form.id, this.form)
      else await createUserApi(this.form)
      this.dialogVisible = false
      if (isSelf && changed) {
        ElMessage.success('Your account information changed. Sign in again.')
        clearAuth()
        this.$router.replace('/login')
        return
      }
      this.loadData()
    },
    enabledAdminCountExcluding(userId) {
      return (this.tableData.list || []).filter(item => item.role === 'admin' && Number(item.statusCode) === 1 && Number(item.id) !== Number(userId)).length
    },
    async toggleStatus(item) {
      const current = getUser()
      if (item.statusCode === 1) {
        if (item.role === 'admin' && this.enabledAdminCountExcluding(item.id) <= 0) {
          ElMessage.warning('At least one enabled administrator account must remain.')
          return
        }
        this.currentTarget = item
        this.disableForm = { disableReason: '' }
        this.disableVisible = true
        return
      }
      await updateUserApi(item.id, { ...item, statusCode: 1, disableReason: '' })
      if (Number(item.id) === Number(current.id)) {
        ElMessage.success('Your account has been re-enabled. Sign in again.')
        clearAuth()
        this.$router.replace('/login')
        return
      }
      this.loadData()
    },
    async confirmDisable() {
      if (!this.disableForm.disableReason) {
        ElMessage.warning('Enter a reason for disabling the account.')
        return
      }
      const item = this.currentTarget
      const current = getUser()
      await updateUserApi(item.id, { ...item, statusCode: 0, disableReason: this.disableForm.disableReason })
      this.disableVisible = false
      if (Number(item.id) === Number(current.id)) {
        ElMessage.success('Your account has been disabled. Sign in again.')
        clearAuth()
        this.$router.replace('/login')
        return
      }
      this.loadData()
    }
  }
}
</script>

<style scoped>
.view-empty-card { min-height: 12rem; display: grid; place-items: center; }
</style>
