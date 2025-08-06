import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
}));

// Add this for debugging, it will log the key in the terminal where vite is running
console.log("VITE_AMAP_JS_API_KEY in vite.config.js:", process.env.VITE_AMAP_JS_API_KEY); 