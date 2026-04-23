import "server-only";

import { getAllParties, getCurrentRepresentatives } from "./endpoints";
import type { FetchResult } from "./fetcher";

// Endpoints the dashboard's main pages depend on. Adding here is cheap: each
// entry is one potential rate-limiter slot at cold start, and they go
// through `fetchWithCache` which no-ops on fresh hits.
const WARMUP_TASKS: Array<{ label: string; run: () => Promise<FetchResult<unknown>> }> = [
  { label: "allepartier",          run: () => getAllParties() },
  { label: "dagensrepresentanter", run: () => getCurrentRepresentatives() },
];

export async function runWarmup(): Promise<void> {
  const started = Date.now();
  const results = await Promise.allSettled(WARMUP_TASKS.map((t) => t.run()));
  for (let i = 0; i < WARMUP_TASKS.length; i += 1) {
    const task = WARMUP_TASKS[i];
    const result = results[i];
    if (result.status === "fulfilled") {
      console.log(`[stortinget] warmup ${task.label}: ${result.value.source}`);
    } else {
      console.error(`[stortinget] warmup ${task.label} failed:`, result.reason);
    }
  }
  console.log(`[stortinget] warmup complete in ${Date.now() - started}ms`);
}

// Store the interval handle on globalThis so HMR / repeated `register()`
// calls don't spawn duplicate timers.
const g = globalThis as typeof globalThis & {
  __stortingetWarmupTimer?: ReturnType<typeof setInterval>;
};

export function startWarmupLoop(intervalMs: number): void {
  if (g.__stortingetWarmupTimer) clearInterval(g.__stortingetWarmupTimer);
  const timer = setInterval(() => {
    void runWarmup().catch((err) => {
      console.error("[stortinget] warmup loop error:", err);
    });
  }, intervalMs);
  // Don't prevent Node from exiting if only this timer is pending.
  timer.unref?.();
  g.__stortingetWarmupTimer = timer;
}

export function stopWarmupLoop(): void {
  if (g.__stortingetWarmupTimer) {
    clearInterval(g.__stortingetWarmupTimer);
    g.__stortingetWarmupTimer = undefined;
  }
}
