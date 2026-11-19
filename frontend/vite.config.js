import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// AS1 (sunum katmanı) hesaplama yapmaz; tüm veri AS2 (FastAPI orkestrasyon) üzerinden gelir.
// Geliştirme ortamında /api ile başlayan istekler FastAPI backend'ine yönlendirilir.
// fs.allow: ['..'] ile auris-data/base_network/midtown_east.osm doğrudan okunabilir.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    fs: {
      allow: ['..'],
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
