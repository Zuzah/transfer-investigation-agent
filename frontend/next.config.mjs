/**
 * Next.js 14 config.
 *
 * When NEXT_STATIC=1 (set by `npm run build`), produce a static HTML export
 * that FastAPI can serve from app/static/ with no changes.
 *
 * During development (`npm run dev`), the dev server proxies all API paths
 * to FastAPI at localhost:8000 via rewrites. This replaces the Vite proxy
 * that was used before the Next.js migration.
 *
 * @type {import('next').NextConfig}
 */
const isStaticBuild = process.env.NEXT_STATIC === "1";

const nextConfig = {
  ...(isStaticBuild && {
    output: "export",
    distDir: "../app/static",
  }),
  // Required for static export (Next.js Image Optimization needs a server).
  images: {
    unoptimized: true,
  },
  // Proxy API calls to FastAPI in dev mode.
  // In production the static export is served by FastAPI on the same origin,
  // so no proxying is needed there.
  ...(!isStaticBuild && {
    async rewrites() {
      return [
        { source: "/investigate",      destination: "http://localhost:8000/investigate" },
        { source: "/ingest",           destination: "http://localhost:8000/ingest" },
        { source: "/health",           destination: "http://localhost:8000/health" },
        { source: "/cases",            destination: "http://localhost:8000/cases" },
        { source: "/cases/:path*",     destination: "http://localhost:8000/cases/:path*" },
        { source: "/admin/reset",      destination: "http://localhost:8000/admin/reset" },
      ];
    },
  }),
};

export default nextConfig;
