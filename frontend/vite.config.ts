import { defineConfig } from "vite";

export default defineConfig({
  build: {
    // Write compiled output directly into app/static/ so FastAPI serves it
    // with zero changes to the existing StaticFiles mount.
    outDir: "../app/static",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    // During dev, proxy all API routes to FastAPI on 8000.
    // The browser talks only to Vite (5173) — no CORS issues.
    proxy: {
      "/investigate": "http://localhost:8000",
      "/ingest":      "http://localhost:8000",
      "/health":      "http://localhost:8000",
    },
  },
});
