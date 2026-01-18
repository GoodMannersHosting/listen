import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: '../static',
    emptyOutDir: false,
    cssCodeSplit: false, // Ensure single CSS file
    rollupOptions: {
      input: {
        main: './src/main.js'
      },
      output: {
        entryFileNames: 'app.js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          // Use fixed filename for CSS files to avoid hash changes
          // Check both name and source properties to detect CSS files
          const name = assetInfo.name || '';
          const source = assetInfo.source || '';
          const isCss = name.endsWith('.css') || 
                       (typeof source === 'string' && source.includes('css'));
          
          if (isCss) {
            // Return fixed filename without hash
            return 'assets/main.css';
          }
          // Keep hashing for other assets
          return 'assets/[name]-[hash][extname]';
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
