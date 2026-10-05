import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import { defineConfig } from 'vitest/config'

const backendUrl = process.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // @asyncapi/react-component's Avro parser (avsc) assumes Node's Buffer/process/util
    // globals. Scoped to just what avsc needs so we don't pull in unrelated polyfills
    // (e.g. crypto-browserify, which drags in a low-severity-vulnerable elliptic).
    nodePolyfills({
      include: ['buffer', 'util', 'process'],
      globals: { Buffer: true, process: true, global: true },
    }),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // changeOrigin: false — keep the Host header as the browser sent it
      // (localhost:5173, already in DJANGO_ALLOWED_HOSTS). Vite's string
      // shorthand defaults changeOrigin to true, which rewrites Host to the
      // backend's Docker-internal hostname (e.g. "backend:8000") and trips
      // Django's DisallowedHost check on every proxied request.
      '/api/': { target: backendUrl, changeOrigin: false },
      '/auth/': { target: backendUrl, changeOrigin: false },
      '/_allauth': { target: backendUrl, changeOrigin: false },
      '/admin': { target: backendUrl, changeOrigin: false },
      // Django admin's own static assets (`/static/admin/...`), served by
      // Django's staticfiles app in development — otherwise falls through
      // to the SPA's history-fallback and Chrome silently rejects the
      // resulting `index.html` as a stylesheet, leaving `/admin/` unstyled.
      '/static/': { target: backendUrl, changeOrigin: false },
      // `/healthz/plugins/` is the first frontend-origin read of this ops health-check route
      // — previously only curled backend-internally by
      // `core/backend/docker/healthcheck.sh`, never proxied from the SPA's
      // own origin.
      '/healthz/': { target: backendUrl, changeOrigin: false },
    },
  },
  test: {
    // Also picks up `@atlas/plugin-api`'s, `@atlas/plugin-standard-catalog`'s,
    // `@atlas/plugin-apis`'s, `@atlas/plugin-c4`'s, `@atlas/plugin-database-schema`'s, and
    // `@atlas/plugin-flows`'s own tests — those packages live outside
    // this Vite root (`plugin-api/typescript`, `plugins/*/frontend/`), so vitest's default
    // `include` (relative to this config's directory) wouldn't find them.
    include: [
      'src/**/*.{test,spec}.{ts,tsx}',
      '../../plugin-api/typescript/src/**/*.{test,spec}.{ts,tsx}',
      '../../plugins/standard-catalog/frontend/src/**/*.{test,spec}.{ts,tsx}',
      '../../plugins/apis/frontend/src/**/*.{test,spec}.{ts,tsx}',
      '../../plugins/c4/frontend/src/**/*.{test,spec}.{ts,tsx}',
      '../../plugins/database-schema/frontend/src/**/*.{test,spec}.{ts,tsx}',
      '../../plugins/flows/frontend/src/**/*.{test,spec}.{ts,tsx}',
      '../../plugins/search/frontend/src/**/*.{test,spec}.{ts,tsx}',
    ],
    server: {
      deps: {
        inline: [/@gravity-ui/],
      },
    },
  },
})
