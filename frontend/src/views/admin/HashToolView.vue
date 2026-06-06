<template>
  <div class="page-wrap">
    <div class="page-head-inline split-header">
      <div class="head-main-block">
        <div class="page-title compact-title">Password Hash</div>
        <div class="section-subtitle">Enter a password to calculate its hash.</div>
      </div>

    </div>
    <div class="card-panel">
      <el-form :model="form" label-position="top">
        <el-form-item label="Password"><el-input v-model="form.rawPassword" type="textarea" :rows="4" /></el-form-item>
        <div class="dual-action single-action-row">
          <el-button class="equal-btn" type="primary" @click="calculate">Calculate</el-button>
        </div>
        <el-form-item label="Password Hash"><el-input v-model="form.hashValue" type="textarea" :rows="6" readonly /></el-form-item>
      </el-form>
    </div>
  </div>
</template>
<script>
import { hashPasswordApi } from '@/api'
export default {
  data() {
    return { form: { rawPassword: '', hashValue: '' } }
  },
  methods: {
    async calculate() {
      const res = await hashPasswordApi({ rawPassword: this.form.rawPassword })
      this.form.hashValue = res.data?.hashValue || ''
    }
  }
}
</script>
