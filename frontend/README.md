# CFIP frontend

Next.js UI. Setup, ports, and the fixture-versus-live distinction are in the repository root [README](../README.md).

```bash
npm ci
npm test
npm run dev
```

The dev server listens on port 43123 and proxies `/cfip-api` to the API on port 43124.

The public demo is a static export. It reads a snapshot file produced by `python -m app.ingest` and does not proxy to FastAPI. The Pages workflow sets `CFIP_STATIC_EXPORT=true`, `NEXT_PUBLIC_DATA_SOURCE=snapshot`, and `NEXT_PUBLIC_BASE_PATH=/college-football-intelligence`. The page labels fixture data and live data differently. Two-team comparison is not in this UI.
