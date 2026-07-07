import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy na backend Django (dev: http://127.0.0.1:8000) — dzięki temu
// zapytania /api/* są same-origin i działa SessionAuthentication.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // /admin i /static przez proxy, żeby zalogować się do Django
      // i uzyskać cookie sesji na tym samym originie co front.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/admin': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
