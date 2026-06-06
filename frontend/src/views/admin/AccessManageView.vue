<template>
  <div class="page-wrap">
    <div class="card-panel access-panel">
      <div class="section-head section-head-tight access-head">
        <div class="section-title">Role Permission Settings</div>
      </div>

      <div v-if="roleCards.length" class="permission-role-grid top-gap-small">
        <div v-for="role in roleCards" :key="role.roleCode" class="role-card role-card-polished">
          <div class="role-card-head sticky-role-head">
            <div class="role-card-main">
              <div class="role-card-title">{{ role.roleName }}</div>
            </div>
            <el-button class="header-mini-btn" type="primary" plain @click="toggleRole(role.roleCode)">{{ expandedRole === role.roleCode ? 'Collapse' : 'Expand' }}</el-button>
          </div>

          <div v-if="expandedRole === role.roleCode" class="feature-card-grid">
            <div v-for="feature in filteredModules(role)" :key="feature.moduleCode" class="feature-card feature-card-polished">
              <div class="feature-card-head feature-card-head-stacked">
                <div>
                  <div class="feature-title">{{ feature.moduleName }}</div>
                </div>
              </div>
              <div class="permission-toggle-grid permission-two-col">
                <div
                  v-for="perm in feature.permissions"
                  :key="perm.permissionCode"
                  class="permission-box permission-box-polished"
                  :class="{ active: isEnabled(perm.draftState), locked: perm.locked }"
                  @click="handlePermissionBoxClick(feature, perm)"
                >
                  <div class="permission-box-head">
                    <div>
                      <div class="permission-box-name">{{ perm.permissionName }}</div>
                      <div class="permission-box-desc">{{ perm.permissionGroupText }}</div>
                    </div>
                    <span class="permission-box-state" :class="stateClass(perm)"></span>
                  </div>
                  <div class="permission-switch-row">
                    <el-switch
                      :model-value="isEnabled(perm.draftState)"
                      :disabled="perm.locked"
                      active-text="On"
                      inactive-text="Off"
                      @change="value => onToggle(role.roleCode, feature.moduleCode, perm.permissionCode, value)"
                    />
                  </div>
                </div>
              </div>
            </div>
            <div class="dual-action full-width-actions">
              <el-button class="equal-btn" @click="resetRole(role.roleCode)">Reset</el-button>
              <el-button class="equal-btn" type="primary" @click="applyRole(role.roleCode)">Apply</el-button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No information yet</div>
    </div>
  </div>
</template>

<script>
import { hasPermission } from '@/utils/auth'
import { accessMatrixApi, updateAccessApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  computed: {
    canView() { return hasPermission('access', 'view') }
  },
  data() {
    return {
      roleCards: [],
      expandedRole: ''
    }
  },
  created() {
    if (!this.canView) {
      this.$router.replace('/home')
      return
    }
    this.loadData()
  },
  methods: {
    filteredModules(role) {
      return Array.isArray(role?.modules) ? role.modules : []
    },
    isEnabled(state) {
      return Number(state) === 2 || Number(state) === 3
    },
    stateClass(perm) {
      return { on: this.isEnabled(perm.draftState), locked: perm.locked }
    },
    toggleRole(code) {
      this.expandedRole = this.expandedRole === code ? '' : code
    },
    async loadData() {
      const res = await accessMatrixApi()
      const rows = res.data?.matrix || []
      const roleMap = {}
      rows.forEach(row => {
        if (!roleMap[row.roleCode]) roleMap[row.roleCode] = { roleCode: row.roleCode, roleName: row.roleName, modules: [] }
        roleMap[row.roleCode].modules.push({
          moduleCode: row.moduleCode,
          moduleName: row.moduleName,
          permissions: (row.permissions || []).map(perm => ({ ...perm, draftState: perm.state }))
        })
      })
      this.roleCards = Object.values(roleMap)
      this.expandedRole = ''
    },
    getBasicEnabled(feature) {
      return feature.permissions.some(perm => Number(perm.permissionGroup) === 0 && this.isEnabled(perm.draftState))
    },
    validateFeatureDraft(feature) {
      const basicEnabled = this.getBasicEnabled(feature)
      const otherEnabled = feature.permissions.some(item => Number(item.permissionGroup) !== 0 && this.isEnabled(item.draftState))
      if (otherEnabled && !basicEnabled) return 'Turn on the basic permission for this feature first.'
      const basic = feature.permissions.find(item => Number(item.permissionGroup) === 0)
      if (basic && !this.isEnabled(basic.draftState) && otherEnabled) return "Turn off the role permissions that depend on this one before turning this permission off."
      return ''
    },
    getOtherEnabled(feature, perm) {
      return feature.permissions.some(item => item.permissionCode !== perm.permissionCode && Number(item.permissionGroup) !== 0 && this.isEnabled(item.draftState))
    },
    getRejectMessage(feature, perm, nextEnabled) {
      if (Number(perm.permissionGroup) !== 0 && nextEnabled && !this.getBasicEnabled(feature)) {
        return 'Turn on the basic permission for this feature before enabling other permissions.'
      }
      if (Number(perm.permissionGroup) === 0 && !nextEnabled && this.getOtherEnabled(feature, perm)) {
        return "Turn off the role permissions that depend on this one before turning this permission off."
      }
      return ''
    },
    handlePermissionBoxClick(feature, perm) {
      if (perm.locked) ElMessage.info('This permission is currently always on or always off in the database and cannot be changed from this page')
    },
    async onToggle(roleCode, moduleCode, permissionCode, value) {
      const role = this.roleCards.find(item => item.roleCode === roleCode)
      const feature = role?.modules.find(item => item.moduleCode === moduleCode)
      const target = feature?.permissions.find(item => item.permissionCode === permissionCode)
      if (!target) return
      if (target.locked) {
        ElMessage.info('This permission is currently always on or always off in the database and cannot be changed from this page')
        return
      }
      const nextState = value ? 2 : 1
      const message = this.getRejectMessage(feature, target, value)
      if (message) {
        ElMessageBox.alert(message, 'Notice', { confirmButtonText: 'OK' })
        return
      }
      target.draftState = nextState
    },
    resetRole(roleCode) {
      const role = this.roleCards.find(item => item.roleCode === roleCode)
      if (!role) return
      role.modules.forEach(feature => feature.permissions.forEach(perm => { perm.draftState = perm.state }))
      ElMessage.success('Unapplied changes have been reset.')
    },
    async applyRole(roleCode) {
      const role = this.roleCards.find(item => item.roleCode === roleCode)
      if (!role) return
      const modules = []
      let changed = false
      for (const feature of this.filteredModules(role)) {
        const featureMessage = this.validateFeatureDraft(feature)
        if (featureMessage) {
          await ElMessageBox.alert(featureMessage, 'Notice', { confirmButtonText: 'OK' })
          return
        }
        const permissions = []
        for (const perm of feature.permissions) {
          if (Number(perm.draftState) !== Number(perm.state)) changed = true
          permissions.push({ permissionCode: perm.permissionCode, state: perm.draftState })
        }
        modules.push({ moduleCode: feature.moduleCode, permissions })
      }
      if (!changed) {
        ElMessage.info('There are no changes to apply.')
        return
      }
      await updateAccessApi({ roleCode, modules })
      await ElMessageBox.alert('Settings applied.', 'Notice', { confirmButtonText: 'OK' })
      await this.loadData()
    }
  }
}
</script>


<style scoped>
.permission-box-polished.locked {
  opacity: 0.64;
}
.permission-box-state.locked {
  border-color: var(--el-color-warning);
}
</style>
