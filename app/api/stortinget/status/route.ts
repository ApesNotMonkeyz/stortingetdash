import { getCacheStore, getRateLimiter } from "@/lib/stortinget";

export const dynamic = "force-dynamic";

export async function GET() {
  const [cache, bucket] = await Promise.all([
    getCacheStore().stats(),
    Promise.resolve(getRateLimiter().snapshot()),
  ]);
  return Response.json({
    cache,
    rateLimiter: bucket,
  });
}
