import { defineConfig } from 'vite' // 导入 Vite 配置方法。
import vue from '@vitejs/plugin-vue' // 导入 Vue 插件。
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// Serve PDF.js's own CMaps/fonts locally: no document fonts sent to third parties.
const pdfRoot = resolve(dirname(fileURLToPath(import.meta.url)), 'node_modules/pdfjs-dist')
function documentAssets() {
  return { name: 'local-document-assets', generateBundle() {
    for (const folder of ['cmaps','standard_fonts']) for (const name of readdirSync(resolve(pdfRoot,folder))) this.emitFile({type:'asset',fileName:`document-assets/${folder}/${name}`,source:readFileSync(resolve(pdfRoot,folder,name))})
    this.emitFile({type:'asset',fileName:'document-assets/PDFJS-LICENSE',source:readFileSync(resolve(pdfRoot,'LICENSE'))})
  }, configureServer(server) { server.middlewares.use((req,res,next)=>{const match=(req.url||'').match(/^\/document-assets\/(cmaps|standard_fonts)\/([\w.-]+)$/);if(!match)return next();try{res.setHeader('Content-Type','application/octet-stream');res.end(readFileSync(resolve(pdfRoot,match[1],match[2])))}catch{res.statusCode=404;res.end()}}) } }
}

export default defineConfig({
  plugins: [vue(), documentAssets()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
})
