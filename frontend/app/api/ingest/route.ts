/**
 * POST /api/ingest[?overwrite=true]
 *
 * Dev-only proxy: triggers document ingestion on the FastAPI backend.
 * Active only in `npm run dev`; excluded from the static export build.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const { searchParams } = new URL(request.url);
  const overwrite = searchParams.get("overwrite");
  const upstreamUrl =
    overwrite === "true"
      ? `${BACKEND}/ingest?overwrite=true`
      : `${BACKEND}/ingest`;

  const upstream = await fetch(upstreamUrl, { method: "POST" });
  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
