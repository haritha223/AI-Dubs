import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy all /translate and /static API calls to the FastAPI backend
      '/translate': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/config': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/outputs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
