// Next.js runs this once per server instance, before the first request is
// handled (see node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/instrumentation.md).
// We kick off a Stortinget cache warmup fire-and-forget so the first real
// user never pays the full cold-start latency. Warmup failures only log —
// they should not delay or crash the server.

export async function register(): Promise<void> {
  // instrumentation.ts also loads in the Edge runtime; keep our Node-only
  // modules out of that build.
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  if (process.env.STORTINGET_WARMUP === "0") return;

  const { runWarmup, startWarmupLoop } = await import("@/lib/stortinget/warmup");

  // Don't block server startup: warmup can happily race with the first
  // incoming request — fetcher's inflight-dedup will collapse them.
  void runWarmup().catch((err) => {
    console.error("[stortinget] initial warmup failed:", err);
  });

  const intervalMs = Number(process.env.STORTINGET_WARMUP_INTERVAL_MS ?? 0);
  if (intervalMs > 0) {
    startWarmupLoop(intervalMs);
    console.log(`[stortinget] warmup loop every ${intervalMs}ms`);
  }
}
