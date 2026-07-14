import { defineConfig } from 'vite' // 导入 Vite 配置方法。
import vue from '@vitejs/plugin-vue' // 导入 Vue 插件。

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
})
