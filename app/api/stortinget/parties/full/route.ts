import type { NextRequest } from "next/server";

import { getMergedParties } from "@/lib/stortinget/merge";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const bypass = req.nextUrl.searchParams.get("refresh") === "1";
  try {
    const merged = await getMergedParties({ bypass, signal: req.signal });
    const age = Date.now() - merged.cachedAt;
    return new Response(
      JSON.stringify({
        data: merged.parties,
        meta: {
          sources: merged.sources,
          cachedAt: merged.cachedAt,
          ageMs: age,
        },
      }),
      {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "cache-control": "private, no-store",
          "x-cache": `${merged.sources.parties}/${merged.sources.representatives}`,
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
