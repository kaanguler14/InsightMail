import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/recent-contacts': 'http://127.0.0.1:8000',
      '/search': 'http://127.0.0.1:8000',
      '/search-stream': 'http://127.0.0.1:8000',
      '/ask': 'http://127.0.0.1:8000',
      '/summarize': 'http://127.0.0.1:8000',
      '/reply-suggest': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: '../static/react',
  },
});
