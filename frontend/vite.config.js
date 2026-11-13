import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// AS1 (sunum katmanı) hesaplama yapmaz; tüm veri AS2 (FastAPI orkestrasyon) üzerinden gelir.
// Geliştirme ortamında /api ile başlayan istekler FastAPI backend'ine yönlendirilir.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
