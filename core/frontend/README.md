# Atlas frontend

For the full Docker development and production-like workflows, see the [root Atlas guide](../../README.md) and canonical [Getting Started](https://sidorov-as.github.io/atlas/getting-started/). Configuration, gateway diagnosis, and recovery procedures live in [Operating Atlas](https://sidorov-as.github.io/atlas/operating-atlas/), rather than in this host-only guide.

## Host workflow

```shell
npm ci
npm run dev
```

The development server is available at http://localhost:5173 and proxies Django routes to `http://localhost:8000` by default. Use `VITE_BACKEND_URL` to point the proxy elsewhere. Run `npm run lint`, `npm test`, and `npm run build` before submitting frontend changes.
