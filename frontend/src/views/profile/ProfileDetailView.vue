<template>
  <div class="page-wrap">
    <div class="card-panel">
      <div class="section-head section-head-tight split-header">
        <div class="head-main-block">
          <div class="section-title">Account Details</div>
          <div class="section-subtitle">Select Edit Details to update your account information.</div>
        </div>
        <div class="head-action-block">
          <template v-if="!editing">
            <el-button v-if="canEditProfile" class="header-mini-btn" type="primary" @click="startEdit">Edit Details</el-button>
          </template>
          <template v-else>
            <div class="profile-detail-actions">
              <el-button class="header-mini-btn" plain @click="cancelEdit">Cancel</el-button>
              <el-button class="header-mini-btn" type="primary" @click="saveProfile">Save</el-button>
            </div>
          </template>
        </div>
      </div>
      <el-form :model="profile" label-position="top" class="top-gap-small">
        <el-form-item label="Username"><el-input v-model="profile.username" disabled /></el-form-item>
        <el-form-item label="Full Name"><el-input v-model="profile.realName" :disabled="!editing" /></el-form-item>
        <el-form-item label="Phone"><el-input v-model="profile.phone" :disabled="!editing" /></el-form-item>
        <el-form-item label="Email"><el-input v-model="profile.email" :disabled="!editing" /></el-form-item>
      </el-form>
    </div>

    <div class="card-panel top-gap-medium">
      <div class="section-head section-head-tight split-header">
        <div class="head-main-block">
          <div class="section-title">Change Password</div>
          <div class="section-subtitle">Select Edit before making changes, then save them.</div>
        </div>
        <div class="head-action-block">
          <template v-if="!passwordEditing">
            <el-button v-if="canEditProfile" class="header-mini-btn" type="primary" @click="passwordEditing = true">Edit</el-button>
          </template>
          <template v-else>
            <div class="profile-detail-actions">
              <el-button class="header-mini-btn" plain @click="resetPasswordForm">Cancel</el-button>
              <el-button class="header-mini-btn" type="primary" @click="savePassword">Save</el-button>
            </div>
          </template>
        </div>
      </div>
      <el-form :model="passwordForm" label-position="top" class="top-gap-small">
        <el-form-item label="Current Password"><el-input v-model="passwordForm.oldPassword" type="password" show-password :disabled="!passwordEditing" /></el-form-item>
        <el-form-item label="New Password"><el-input v-model="passwordForm.newPassword" type="password" show-password :disabled="!passwordEditing" /></el-form-item>
        <el-form-item label="Confirm New Password"><el-input v-model="passwordForm.confirmPassword" type="password" show-password :disabled="!passwordEditing" /></el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { profileApi, updateProfileApi, updatePasswordApi } from '@/api'
import { setUser, getUser, clearAuth, hasPermission } from '@/utils/auth'
import { ElMessage } from 'element-plus'

export default {
  computed: { canEditProfile() { return hasPermission('profile', 'update_profile') } },
  data() {
    return {
      profile: { username: '', realName: '', phone: '', email: '' },
      sourceProfile: {},
      editing: false,
      passwordEditing: false,
      passwordForm: { oldPassword: '', newPassword: '', confirmPassword: '' }
    }
  },
  created() {
    this.loadProfile()
  },
  methods: {
    startEdit() {
      this.editing = true
    },
    cancelEdit() {
      this.editing = false
      this.profile = { ...this.sourceProfile }
      this.resetPasswordForm()
    },
    async loadProfile() {
      const res = await profileApi()
      this.profile = { ...(res.data || {}) }
      this.sourceProfile = { ...this.profile }
      setUser({ ...getUser(), ...(res.data || {}) })
    },
    async saveProfile() {
      this.profile.phone = String(this.profile.phone || '').trim()
      this.profile.phone = String(this.profile.phone || '').replace(/[０-９]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 65248)).replace(/\D/g, '')
      this.profile.email = String(this.profile.email || '').trim()
      if (!/^\d{11}$/.test(this.profile.phone || '')) { ElMessage.warning('Enter an 11-digit phone number.'); return }
      if (this.profile.email && !String(this.profile.email).includes('@')) { ElMessage.warning('Enter a valid email address.'); return }
      const changed = ['realName', 'phone', 'email'].some(key => (this.profile[key] || '') !== (this.sourceProfile[key] || ''))
      if (!changed) {
        this.editing = false
        return
      }
      const res = await updateProfileApi(this.profile)
      this.profile = { ...(res.data || this.profile) }
      this.sourceProfile = { ...this.profile }
      setUser({ ...getUser(), ...(res.data || {}) })
      this.editing = false
      ElMessage.success('Details updated.')
    },
    resetPasswordForm() {
      this.passwordEditing = false
      this.passwordForm = { oldPassword: '', newPassword: '', confirmPassword: '' }
    },
    async savePassword() {
      await updatePasswordApi(this.passwordForm)
      this.resetPasswordForm()
      ElMessage.success('Password updated. Sign in again.')
      clearAuth()
      this.$router.replace('/login')
    }
  }
}
</script>
