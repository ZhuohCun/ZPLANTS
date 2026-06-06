<template>
  <div class="auth-shell">
    <div class="auth-card">

      <div class="auth-title">ZPLANTS</div>
      <div class="auth-subtitle">An AI-Based Plants Recognition Software</div>
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" placeholder="Enter your username" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="Enter your password" />
        </el-form-item>
        <el-form-item>
          <div class="dual-action auth-actions">
            <el-button class="equal-btn" type="success" @click="submit">Sign In</el-button>
            <el-button class="equal-btn" plain @click="$router.push('/register')">Register</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { loginApi } from '@/api'
import { setToken, setUser } from '@/utils/auth'
import { getFirstAccessiblePath } from '@/utils/navigation'

export default {
  name: 'LoginView',
  data() {
    return {
      form: { username: '', password: '' },
      rules: {
        username: [{ required: true, message: 'Enter your username', trigger: 'blur' }],
        password: [{ required: true, message: 'Enter your password', trigger: 'blur' }]
      }
    }
  },
  methods: {
    submit() {
      this.$refs.formRef.validate(async valid => {
        if (!valid) return
        const res = await loginApi(this.form)
        setToken(res.data.token)
        setUser(res.data.userInfo)
        this.$router.replace(getFirstAccessiblePath(res.data.userInfo?.features || []))
      })
    }
  }
}
</script>

<style scoped>
.auth-hint { margin: 0.6rem 0 1rem; color: var(--text-subtle); line-height: 1.6; }
.auth-actions { width: 100%; }
</style>
