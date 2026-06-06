<template>
  <div class="auth-shell">
    <div class="auth-card">
      <div class="auth-title">Create Account</div>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="Username" prop="username"><el-input v-model="form.username" placeholder="Enter your username" /></el-form-item>
        <el-form-item label="Full Name" prop="realName"><el-input v-model="form.realName" placeholder="Enter your full name" /></el-form-item>
        <el-form-item label="Phone" prop="phone" required><el-input v-model="form.phone" placeholder="Enter an 11-digit phone number" /></el-form-item>
        <el-form-item label="Email" prop="email" required><el-input v-model="form.email" placeholder="Enter your email" /></el-form-item>
        <el-form-item label="Password" prop="password"><el-input v-model="form.password" type="password" show-password placeholder="Enter your password" /></el-form-item>
        <el-form-item label="Confirm Password" prop="confirmPassword"><el-input v-model="form.confirmPassword" type="password" show-password placeholder="Enter the password again" /></el-form-item>
        <el-form-item>
          <div class="dual-action auth-actions">
            <el-button class="equal-btn" type="primary" @click="submit">Register</el-button>
            <el-button class="equal-btn" plain @click="$router.replace('/login')">Back to Sign In</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { registerApi } from '@/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'RegisterView',
  data() {
    return {
      form: { username: '', realName: '', phone: '', email: '', password: '', confirmPassword: '' },
      rules: {
        username: [{ required: true, message: 'Enter your username', trigger: 'blur' }],
        realName: [{ required: true, message: 'Enter your full name', trigger: 'blur' }],
        phone: [{ required: true, message: 'Enter your phone number', trigger: 'blur' }],
        email: [{ required: true, message: 'Enter your email', trigger: 'blur' }],
        password: [{ required: true, message: 'Enter your password', trigger: 'blur' }],
        confirmPassword: [{ required: true, message: 'Enter the password again', trigger: 'blur' }]
      }
    }
  },
  methods: {
    submit() {
      this.$refs.formRef.validate(async valid => {
        if (!valid) return
        await registerApi(this.form)
        ElMessage.success('Your account has been created. Return to sign in.')
        this.$router.replace('/login')
      })
    }
  }
}
</script>

<style scoped>
.auth-actions { width: 100%; }
</style>
