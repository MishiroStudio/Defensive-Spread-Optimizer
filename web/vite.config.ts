import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),

    VitePWA({
      registerType: 'autoUpdate',

      includeAssets: [
        'icons/apple-touch-icon.png',
        'assets/sprites/missingno.png',
        'data/pokemon.json',
      ],

      manifest: {
        id: '/',
        name: 'Defensive Spread Optimizer',
        short_name: 'Spread Optimizer',
        description:
          'Find the bulkiest defensive spread for your Pokémon.',

        start_url: '/',
        scope: '/',

        display: 'standalone',
        orientation: 'portrait',

        background_color: '#f8fafc',
        theme_color: '#f28c28',

        icons: [
          {
            src: 'icons/pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'icons/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'icons/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },

      workbox: {
        globPatterns: [
          '**/*.{js,css,html,ico,svg,png,woff2,json}',
        ],

        globIgnores: [
          'assets/sprites/home/**',
        ],

        runtimeCaching: [
          {
            urlPattern:
              /\/assets\/sprites\/home\/.*\.(?:png|webp)$/i,

            handler: 'CacheFirst',

            options: {
              cacheName: 'pokemon-sprites',

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