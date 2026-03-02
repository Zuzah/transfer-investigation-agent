/**
 * Next.js 14 config.
 *
 * When NEXT_STATIC=1 (set by `npm run build`), produce a static HTML export
 * that FastAPI can serve from app/static/ with no changes.
 *
 * During development (`npm run dev`), output/distDir are not set so Next.js
 * runs as a full server — API routes in app/api/ work normally and proxy
 * requests to FastAPI at localhost:8000.
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
};

export default nextConfig;
