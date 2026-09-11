import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
    server: {
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/ready': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/live': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
        }
    },
    plugins: [react()],
    base: '/',
    build: {
        outDir: 'dist',
        assetsDir: 'assets',
        sourcemap: true,
    }
})

