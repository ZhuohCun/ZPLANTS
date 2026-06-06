<template>
  <div class="auth-shell">
    <div class="auth-card">
      <div class="auth-title">Page Not Found</div>
      <div class="auth-subtitle">The page you opened is not available.</div>
      <el-button type="success" style="width: 100%" @click="$router.push('/home')">Back Home</el-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NotFoundView'
}
</script>
