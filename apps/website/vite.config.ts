// vite.config.ts — Pokédex/Optimizer V10
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  base: '/Defensive-Spread-Optimizer/',

  build: {
    rollupOptions: {
      input: {
        optimizer: fileURLToPath(
          new URL('./index.html', import.meta.url),
        ),
        pokedex: fileURLToPath(
          new URL('./pokedex/index.html', import.meta.url),
        ),
      },
    },
  },

  plugins: [
    react(),

    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: false,
      manifest: false,

      includeAssets: [
        'icons/optimizer-apple-touch-icon.png',
        'icons/optimizer-192x192.png',
        'icons/optimizer-512x512.png',
        'icons/pokedex-apple-touch-icon.png',
        'icons/pokedex-192x192.png',
        'icons/pokedex-512x512.png',
        'assets/sprites/missingno.png',
      ],

      workbox: {
        globPatterns: [
          '**/*.{js,css,html,ico,svg,png,woff2,json,webmanifest}',
        ],

        globIgnores: [
          'assets/sprites/home/**',
        ],

        maximumFileSizeToCacheInBytes:
          5 * 1024 * 1024,

        cleanupOutdatedCaches: true,
        clientsClaim: true,
        skipWaiting: true,

        runtimeCaching: [
          {
            urlPattern:
              /\/assets\/sprites\/home\/.*\.(?:png|webp)$/i,

            handler: 'CacheFirst',

            options: {
              cacheName: 'pokemon-home-sprites',

              expiration: {
                maxEntries: 500,
                maxAgeSeconds:
                  60 * 60 * 24 * 30,
              },

              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],
      },
    }),
  ],
})
