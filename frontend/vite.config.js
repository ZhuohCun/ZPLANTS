import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)


const BACKEND_API_BASE_FROM_SOURCE = '127.0.0.1:5000/api'

const PASSWORD_RSA_PUBLIC_KEY_BASE64_FROM_SOURCE = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsKn/MIWmFlyrb50eMTWLdGb5Dp1QA38u7nuC0ian1trPLtkfGgXlH1HtumtfKkjQx3dpSS5T+eGee8x1IghesKE8/TqV1jKqcd4m94h37g5glahJ8ART3IlhFqqnM+nPcez25HOmiXsr8JqU1ekKlv3pfSJEgWjngmZRPo7BQNyBEOg9pw9DQAVV9faVBd9z5s8itND2w+R2WKaOgh7hx8+CbN68e44kzjVaajz2NpO+C1SAbWqmfCfZY3fZJ4+b4bvWlQRXNg+GkZDQtdvJKLsTfRtulnXi+pW1MiDKInmIWh5FF5IBdZ7fg8cNedHX5HCd64K9X/j0ujgb+po3swIDAQAB'

export default defineConfig({
  plugins: [vue()],
  define: {
    __BACKEND_API_BASE_FROM_SOURCE__: JSON.stringify(BACKEND_API_BASE_FROM_SOURCE),
    __PASSWORD_RSA_PUBLIC_KEY_BASE64_FROM_SOURCE__: JSON.stringify(PASSWORD_RSA_PUBLIC_KEY_BASE64_FROM_SOURCE)
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src")
    }
  },
  publicDir: "public",
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router'],
          element: ['element-plus', '@element-plus/icons-vue'],
          network: ['axios']
        }
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    strictPort: true,
    allowedHosts: true
  }
})
