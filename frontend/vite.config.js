import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:8001',
      '/recent-contacts': 'http://127.0.0.1:8001',
      '/search': 'http://127.0.0.1:8001',
      '/search-stream': 'http://127.0.0.1:8001',
      '/ask': 'http://127.0.0.1:8001',
      '/summarize': 'http://127.0.0.1:8001',
      '/reply-suggest': 'http://127.0.0.1:8001',
    },
  },
  build: {
    outDir: '../static/react',
  },
});
