import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/dashboard': 'http://localhost:3000',
      '/webhook': 'http://localhost:3000',
      '/tasks': 'http://localhost:3000',
      '/channels': 'http://localhost:3000',
      '/history': 'http://localhost:3000',
      '/sessions': 'http://localhost:3000',
      '/heartbeat': 'http://localhost:3000',
      '/health': 'http://localhost:3000',
    },
  },
  base: '/ui/',
  build: {
    outDir: 'dist',
  },
})
