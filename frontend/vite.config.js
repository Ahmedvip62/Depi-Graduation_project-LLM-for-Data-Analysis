import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Static SPA build. `base: './'` so the built assets resolve with relative
// paths and the notebook can serve `dist/` from any sub-path.
// In dev, the `/api` proxy forwards to the FastAPI backend on :8000 (stripping
// the `/api` prefix). In production the frontend calls `${VITE_API_BASE}/api/...`
// (default '' so a reverse proxy can map `/api` -> backend).
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      // Split heavy vendored libs into their own chunks so the main app bundle
      // stays small and Plotly (the biggest ~3MB) loads lazily with ChartCard
      // rather than blocking the first paint of the intake/dashboard.
      output: {
        manualChunks: {
          plotly: ['plotly.js-dist-min', 'react-plotly.js'],
          markdown: ['react-markdown', 'remark-gfm'],
          vendor: ['react', 'react-dom', 'lucide-react'],
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
