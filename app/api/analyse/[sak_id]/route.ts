import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest, ctx: { params: Promise<{ sak_id: string }> }) {
  const { sak_id } = await ctx.params;
  const force = req.nextUrl.searchParams.get("force") === "true";

  const url = new URL(`/api/v1/analyse/${encodeURIComponent(sak_id)}`, BACKEND_URL);
  if (force) url.searchParams.set("force", "true");

  try {
    const upstream = await fetch(url, { signal: req.signal });
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: { "content-type": "application/json; charset=utf-8" },
    });
  } catch (err) {
    return Response.json(
      { error: "backend_unavailable", message: (err as Error).message },
      { status: 502 },
    );
  }
}
