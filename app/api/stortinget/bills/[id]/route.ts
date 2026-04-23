import type { NextRequest } from "next/server";

import { getMergedBillDetail } from "@/lib/stortinget/merge";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const bypass = req.nextUrl.searchParams.get("refresh") === "1";
  try {
    const merged = await getMergedBillDetail(id, { bypass, signal: req.signal });
    const age = Date.now() - merged.cachedAt;
    return new Response(
      JSON.stringify({
        data: merged.bill,
        meta: { source: merged.source, cachedAt: merged.cachedAt, ageMs: age },
      }),
      {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "cache-control": "private, no-store",
          "x-cache": merged.source,
          "x-cache-age-ms": String(age),
        },
      },
    );
  } catch (err) {
    return Response.json(
      { error: "merge_failed", message: (err as Error).message },
      { status: 502 },
    );
  }
}
