// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  compatibilityDate: '2024-04-03',
  css: ['~/src/assets/css/main.css'],
  dir: {
    pages: 'src/pages',
    components: 'src/components',
    middleware: 'src/middleware'
  },
  devServer: {
    port: 3001
  },
  nitro: {
    port: 3001,
    routeRules: {
      '/processes/**': {
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      }
    },
    // Disable static asset caching in dev mode
    devStorage: {
      cache: {
        driver: 'memory'
      }
    }
  },
  // Disable service worker and aggressive caching in dev
  app: {
    head: {
      meta: [
        { 'http-equiv': 'Cache-Control', content: 'no-cache, no-store, must-revalidate' },
        { 'http-equiv': 'Pragma', content: 'no-cache' },
        { 'http-equiv': 'Expires', content: '0' }
      ]
    }
  },
  vite: {
    server: {
      hmr: {
        port: 24679
      }
    },
    optimizeDeps: {
      include: ['@vue-flow/core'],
      esbuildOptions: {
        target: 'esnext'
      }
    },
    clearScreen: false
  },
  ssr: false,
  experimental: {
    payloadExtraction: false
  }
})
