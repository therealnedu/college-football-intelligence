# CFIP frontend

Next.js UI for phase 1. Setup, ports, and the fixture-versus-live distinction are in the repository root [README](../README.md).

```bash
npm ci
npm test
npm run dev
```

The dev server listens on port 43123 and proxies `/cfip-api` to the API on port 43124.
