import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  root: __dirname,
  envDir: '../', // Look for .env files in parent directory
  server: {
    port: 3001
  },
  build: {
    outDir: '../public',
    emptyOutDir: false,
    rollupOptions: {
      output: {
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/[name].[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split('.') || []
          const ext = info[info.length - 1]
          if (/\.(css)$/.test(assetInfo.name || '')) {
            return `css/[name].[hash].${ext}`
          }
          return `assets/[name].[hash].[ext]`
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  publicDir: '../public'
}) 