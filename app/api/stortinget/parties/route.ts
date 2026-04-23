import type { NextRequest } from "next/server";

import { endpoints } from "@/lib/stortinget";
import { jsonFromFetchResult } from "@/lib/stortinget/route-helpers";
import { parseAllParties, type ApiParty } from "@/lib/stortinget/schemas";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const sesjonId = req.nextUrl.searchParams.get("sesjon");
  const bypass = req.nextUrl.searchParams.get("refresh") === "1";
  const result = sesjonId
    ? await endpoints.getPartiesForSession(sesjonId, { bypass, signal: req.signal })
    : await endpoints.getAllParties({ bypass, signal: req.signal });

  let parties: ApiParty[];
  try {
    parties = parseAllParties(result.data);
  } catch (err) {
    return Response.json(
      { error: "upstream_shape", message: (err as Error).message },
      { status: 502 },
    );
  }

  return jsonFromFetchResult({ ...result, data: parties });
}
