/**
 * POST /api/investigate
 *
 * Dev-only proxy: forwards the complaint to FastAPI and returns the result.
 * This route is active only when running `npm run dev` (Next.js server mode).
 *
 * In production, `npm run build` (NEXT_STATIC=1) produces a static export.
 * Static exports do not include API routes — the client calls FastAPI
 * directly at the same origin (NEXT_PUBLIC_API_BASE is empty in production).
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.json();

  const upstream = await fetch(`${BACKEND}/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
