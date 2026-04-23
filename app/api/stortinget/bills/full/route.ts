import type { NextRequest } from "next/server";

import { getMergedBills } from "@/lib/stortinget/merge";

export const dynamic = "force-dynamic";

// Current Stortinget session. We default to this so the dashboard has a
// sensible live endpoint with no params; callers can override via ?sesjonid=.
const DEFAULT_SESSION = "2025-2026";

export async function GET(req: NextRequest) {
  const bypass = req.nextUrl.searchParams.get("refresh") === "1";
  const sessionId = req.nextUrl.searchParams.get("sesjonid") ?? DEFAULT_SESSION;
  try {
    const merged = await getMergedBills(sessionId, { bypass, signal: req.signal });
    const age = Date.now() - merged.cachedAt;
    return new Response(
      JSON.stringify({
        data: merged.bills,
        meta: {
          source: merged.source,
          cachedAt: merged.cachedAt,
          ageMs: age,
          sessionId: merged.sessionId,
        },
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
