import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
    host: true,
    allowedHosts: ['frontend', 'localhost'],
    hmr: {
      // When behind nginx proxy, use the nginx port so the HMR WebSocket
      // connects through the proxy instead of trying the internal port.
      clientPort: Number(process.env.VITE_HMR_PORT) || undefined,
    },
    watch: {
      // Use polling in Docker to avoid inotify issues; reduce CPU with longer interval
      usePolling: true,
      interval: 2000,
    },
    proxy: {
      '/api': {
        target: 'http://django:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://django:8001',
        ws: true,
        changeOrigin: true,
      },
      '/fhir': {
        target: 'http://django:8000',
        changeOrigin: true,
        secure: false,
      },
      // Agents FastAPI service — API calls only (not browser navigation)
      '/agents': {
        target: 'http://agents-api:8001',
        changeOrigin: true,
        secure: false,
        bypass(req) {
          // Browser navigation sends Accept: text/html — serve SPA index instead
          if (req.headers.accept?.includes('text/html')) {
            return '/index.html'
          }
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          query: ['@tanstack/react-query'],
          charts: ['recharts'],
          motion: ['framer-motion'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-tabs'],
        },
      },
    },
  },
})
