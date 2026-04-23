import type { NextRequest } from "next/server";

import { endpoints } from "@/lib/stortinget";
import { jsonFromFetchResult } from "@/lib/stortinget/route-helpers";
import { parseCurrentRepresentatives, type ApiRepresentative } from "@/lib/stortinget/schemas";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const sesjonId = req.nextUrl.searchParams.get("sesjon");
  const bypass = req.nextUrl.searchParams.get("refresh") === "1";

  // Session-scoped lookup not yet validated — it returns a different envelope
  // shape (`representanter_liste`). Pass the raw payload until we add a
  // schema for it.
  if (sesjonId) {
    const result = await endpoints.getRepresentativesForSession(sesjonId, { bypass, signal: req.signal });
    return jsonFromFetchResult(result);
  }

  const result = await endpoints.getCurrentRepresentatives({ bypass, signal: req.signal });
  let reps: ApiRepresentative[];
  try {
    reps = parseCurrentRepresentatives(result.data);
  } catch (err) {
    return Response.json(
      { error: "upstream_shape", message: (err as Error).message },
      { status: 502 },
    );
  }
  return jsonFromFetchResult({ ...result, data: reps });
}
