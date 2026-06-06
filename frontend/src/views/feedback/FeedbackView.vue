<template>
  <div class="page-wrap feedback-page">
    <template v-if="canView">
    <el-tabs v-model="activeName" stretch>
      <el-tab-pane v-if="canSubmit" label="Send Feedback" name="submit">
        <div class="card-panel">
          <el-form :model="form" label-position="top">
            <el-form-item label="Feedback Type">
              <el-select v-model="form.typeCode" style="width:100%">
                <el-option v-for="item in feedbackTypes" :key="item.code" :label="item.name" :value="item.code" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="form.typeCode === 2" label="Linked Recognition Result">
              <el-select
                v-model="form.recognitionId"
                value-key="id"
                style="width:100%"
                clearable
                filterable
                placeholder="Choose a recognition result"
                @visible-change="handleRecognitionVisible"
              >
                <el-option v-for="item in mergedRecognitionOptions" :key="item.id" :label="item.label" :value="item.id" />
                <template #footer>
                  <div class="select-dropdown-footer" v-if="recognitionOptions.totalPages > 1">
                    <el-button class="pager-btn" plain size="small" :disabled="recognitionPage <= 1" @click.stop="changeRecognitionPage(recognitionPage - 1)">Previous</el-button>
                    <span class="pager-text">Page {{ recognitionPage }} of {{ recognitionOptions.totalPages }}</span>
                    <el-button class="pager-btn" plain size="small" :disabled="recognitionPage >= recognitionOptions.totalPages" @click.stop="changeRecognitionPage(recognitionPage + 1)">Next</el-button>
                  </div>
                </template>
              </el-select>
            </el-form-item>
            <el-form-item label="Feedback">
              <el-input v-model="form.content" type="textarea" :rows="6" maxlength="500" show-word-limit />
            </el-form-item>
            <div class="dual-action single-action-row">
              <el-button class="equal-btn" type="success" @click="submit">Send Feedback</el-button>
            </div>
          </el-form>
        </div>
      </el-tab-pane>

      <el-tab-pane label="Sent by Me" name="mine">
        <div class="card-panel">
          <div v-if="myList.list?.length" class="stack-list compact-list">
            <div v-for="item in myList.list" :key="item.id" class="mini-card mini-card-column">
              <div class="list-title-row"><span class="list-title">{{ item.type }}</span><span class="list-time">{{ item.createTime }}</span></div>
              <div class="list-desc">{{ item.content }}</div>
              <div class="list-desc">Status: {{ item.status }}</div>
              <div v-if="item.recognitionLabel" class="list-desc">Linked Result: {{ item.recognitionLabel }}</div>
              <div v-if="item.auditRemark" class="list-desc">Review Note: {{ item.auditRemark }}</div>
            </div>
          </div>
          <div v-else class="empty-state">No information yet</div>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="canAudit" label="Feedback Review" name="audit">
        <div class="card-panel">
          <div class="toolbar mobile-toolbar">
            <el-select v-model="auditQuery.status" placeholder="Status Filter" @change="applyAuditSearch">
              <el-option label="All" value="all" />
              <el-option label="Awaiting Review" :value="1" />
              <el-option label="Approved" :value="2" />
              <el-option label="Rejected" :value="3" />
            </el-select>
            <el-button class="equal-btn" type="success" @click="applyAuditSearch">Search</el-button>
          </div>
          <div v-if="auditList.list?.length" class="stack-list compact-list top-gap-small">
            <div v-for="item in auditList.list" :key="item.id" class="mini-card mini-card-column">
              <div class="list-title-row"><span class="list-title">{{ item.username }} · {{ item.type }}</span><span class="list-time">{{ item.createTime }}</span></div>
              <div class="list-desc">{{ item.content }}</div>
              <div v-if="item.recognitionLabel" class="list-desc">Linked Result: {{ item.recognitionLabel }}</div>
              <div class="list-desc">Current Status: {{ item.status }}</div>
              <div class="mini-actions" v-if="item.statusCode === 1">
                <el-button class="equal-btn" type="primary" plain @click="openAudit(item, 2)">Approve</el-button>
                <el-button class="equal-btn" type="danger" plain @click="openAudit(item, 3)">Reject</el-button>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">No information yet</div>
        </div>
      </el-tab-pane>
    </el-tabs>

      <el-dialog v-model="auditVisible" title="Review Feedback" destroy-on-close>
      <el-form :model="auditForm" label-position="top">
        <el-form-item label="Review Result"><el-select v-model="auditForm.auditStatus" style="width:100%"><el-option label="Approve" :value="2" /><el-option label="Reject" :value="3" /></el-select></el-form-item>
        <el-form-item label="Review Note"><el-input v-model="auditForm.auditRemark" type="textarea" :rows="4" maxlength="300" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <div class="dual-action">
          <el-button class="equal-btn" @click="auditVisible = false">Cancel</el-button>
          <el-button class="equal-btn" type="primary" @click="submitAudit">Confirm</el-button>
        </div>
      </template>
      </el-dialog>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>

<script>
import { submitFeedbackApi, myFeedbackApi, feedbackListApi, auditFeedbackApi, feedbackTypesApi, recognitionOptionsApi } from '@/api'
import { hasPermission } from '@/utils/auth'
import { ElMessage } from 'element-plus'

export default {
  data() {
    return {
      activeName: 'mine',
      feedbackTypes: [],
      form: { typeCode: 1, recognitionId: '', content: '' },
      myList: { list: [] },
      auditQuery: { pageNum: 1, pageSize: 5, status: 'all' },
      auditList: { list: [] },
      auditVisible: false,
      currentFeedbackId: '',
      auditForm: { auditStatus: 2, auditRemark: '' },
      recognitionOptions: { list: [], totalPages: 1 },
      recognitionPage: 1,
      selectedRecognitionOption: null
    }
  },
  computed: {
    canView() { return hasPermission('feedback', 'view') },
    canSubmit() { return hasPermission('feedback', 'submit') },
    canAudit() { return hasPermission('feedback', 'audit') },
    mergedRecognitionOptions() {
      const base = [...(this.recognitionOptions.list || [])]
      if (this.selectedRecognitionOption && !base.some(item => item.id === this.selectedRecognitionOption.id)) {
        base.unshift(this.selectedRecognitionOption)
      }
      return base
    }
  },
  created() {
    this.activeName = this.canSubmit ? 'submit' : 'mine'
    if (!this.canView) return
    this.loadTypes()
    this.applyRoutePreset()
    this.refreshByTab()
  },
  watch: {
    activeName() { this.refreshByTab() },
    '$route.query': {
      deep: true,
      handler() { this.applyRoutePreset() }
    },
    'form.typeCode'(value) {
      if (Number(value) !== 2) {
        this.form.recognitionId = ''
        this.selectedRecognitionOption = null
      }
    },
    'form.recognitionId'(val) {
      const found = this.mergedRecognitionOptions.find(item => item.id === val)
      if (found) this.selectedRecognitionOption = found
    }
  },
  methods: {
    applyRoutePreset() {
      const { recognitionId, typeCode } = this.$route.query || {}
      if (typeCode) this.form.typeCode = Number(typeCode) || 1
      if (recognitionId) {
        this.form.recognitionId = Number(recognitionId) || recognitionId
        if (this.canSubmit) this.activeName = 'submit'
      }
    },
    refreshByTab() {
      if (!this.canView) return
      if (this.activeName === 'mine') this.loadMyList()
      if (this.activeName === 'audit' && this.canAudit) this.loadAuditList()
      if (this.activeName === 'submit' && this.canSubmit && Number(this.form.typeCode) === 2) this.loadRecognitionPage()
    },
    async loadTypes() {
      if (!this.canView) { this.feedbackTypes = []; return }
      const res = await feedbackTypesApi()
      this.feedbackTypes = res.data || []
    },
    async submit() {
      if (!this.canSubmit) {
        ElMessage.warning({ message: 'This account cannot use this feature.', offset: 104 })
        return
      }
      if (!this.form.content) {
        ElMessage.warning({ message: 'Enter your feedback.', offset: 104 })
        return
      }
      if (Number(this.form.typeCode) === 2 && !this.form.recognitionId) {
        ElMessage.warning({ message: 'Choose the related recognition result.', offset: 104 })
        return
      }
      await submitFeedbackApi(this.form)
      ElMessage.success({ message: 'Sent', offset: 104 })
      this.form = { typeCode: 1, recognitionId: '', content: '' }
      this.selectedRecognitionOption = null
      this.recognitionPage = 1
      this.recognitionOptions = { list: [], totalPages: 1 }
      await this.loadMyList()
      if (this.canAudit) await this.loadAuditList()
      this.activeName = 'mine'
    },
    async loadMyList() {
      if (!this.canView) { this.myList = { list: [] }; return }
      const res = await myFeedbackApi({ pageNum: 1, pageSize: 5 })
      this.myList = res.data || { list: [] }
    },
    async loadAuditList() {
      if (!this.canView) { this.auditList = { list: [] }; return }
      const res = await feedbackListApi(this.auditQuery)
      this.auditList = res.data || { list: [] }
    },
    applyAuditSearch() { this.auditQuery.pageNum = 1; this.loadAuditList() },
    openAudit(row, status) {
      this.currentFeedbackId = row.id
      this.auditForm = { auditStatus: status, auditRemark: '' }
      this.auditVisible = true
    },
    async submitAudit() {
      await auditFeedbackApi(this.currentFeedbackId, this.auditForm)
      this.auditVisible = false
      await this.loadAuditList()
    },
    async handleRecognitionVisible(visible) {
      if (visible) await this.loadRecognitionPage()
    },
    async loadRecognitionPage() {
      if (!this.canView) { this.recognitionOptions = { list: [], totalPages: 1 }; return }
      const res = await recognitionOptionsApi({ pageNum: this.recognitionPage, pageSize: 5 })
      this.recognitionOptions = res.data || { list: [], totalPages: 1 }
      const found = (this.recognitionOptions.list || []).find(item => item.id === this.form.recognitionId)
      if (found) this.selectedRecognitionOption = found
    },
    async changeRecognitionPage(page) {
      this.recognitionPage = page
      await this.loadRecognitionPage()
    }
  }
}
</script>

<style scoped>
.feedback-page { display: flex; flex-direction: column; gap: 1rem; }
.select-dropdown-footer {
  display: flex; align-items: center; justify-content: space-between; gap: 0.75rem;
  padding: 0.65rem 0.25rem 0.1rem; border-top: 1px solid rgba(148, 163, 184, 0.16);
}
.pager-btn { min-width: 5.2rem; }
.pager-text { color: var(--text-subtle); font-size: 0.86rem; }
.view-empty-card { min-height: 12rem; display: grid; place-items: center; }
</style>
