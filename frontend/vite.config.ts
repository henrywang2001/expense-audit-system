import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 安全网：万一后端仍返回 3xx，把绝对 Location 改写回代理源，
        // 避免浏览器跨源重定向时剥离 Authorization 头导致 401。
        autoRewrite: true,
        // 让重定向暴露在前端，便于发现路径写错，而不是被静默吞掉。
        followRedirects: false
      },
      // 发票等静态资源同源化（后端 main.py:140 挂载了 /uploads）。
      // 同源后 <img src="/uploads/xxx"> 开箱即用，无需手工拼域名前缀。
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
