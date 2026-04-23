import "server-only";

import { classifyAge, type CacheEntry } from "./cache-store";
import { cacheDebug, getCacheStore, getRateLimiter, STORTINGET_BASE_URL } from "./config";

export type FetchSource = "fresh" | "stale" | "revalidated" | "miss";

export type FetchResult<T> = {
  data: T;
  source: FetchSource;
  cachedAt: number;
};

export type FetchOptions = {
  // Soft TTL: below this age the cache hit is treated as fresh. No refetch.
  ttlMs?: number;
  // Beyond ttlMs but within ttlMs+staleMs, serve stale and refresh in the
  // background. Beyond that, force a synchronous refetch.
  staleMs?: number;
  // Extra query string params merged onto the upstream URL.
  params?: Record<string, string | number | boolean | undefined>;
  // Upstream request signal (e.g. to propagate client aborts).
  signal?: AbortSignal;
  // Force a fresh fetch, bypassing any cached entry. Still writes on success.
  bypass?: boolean;
};

const DEFAULT_TTL_MS = 15 * 60 * 1000;
const DEFAULT_STALE_MS = 24 * 60 * 60 * 1000;

// Inflight dedup: collapse concurrent requests for the same key onto a single
// upstream fetch so we don't waste rate-limiter tokens on identical work.
const inflight = new Map<string, Promise<unknown>>();

function buildUrl(pathname: string, params: FetchOptions["params"]): string {
  const base = pathname.startsWith("http")
    ? pathname
    : `${STORTINGET_BASE_URL}/${pathname.replace(/^\/+/, "")}`;
  const url = new URL(base);
  if (!url.searchParams.has("format")) url.searchParams.set("format", "json");
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

async function fetchUpstream<T>(url: string, signal?: AbortSignal): Promise<T> {
  // `cache: 'no-store'` opts out of Next.js's own fetch cache — our store is
  // the single source of truth, and we don't want double-caching.
  const res = await fetch(url, {
    cache: "no-store",
    signal,
    headers: { accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`stortinget ${res.status} ${res.statusText} — ${url}`);
  }
  return (await res.json()) as T;
}

async function runAndStore<T>(key: string, url: string, ttlMs: number, staleMs: number, signal?: AbortSignal): Promise<T> {
  const existing = inflight.get(key) as Promise<T> | undefined;
  if (existing) return existing;

  const promise = (async () => {
    const limiter = getRateLimiter();
    await limiter.acquire();
    const value = await fetchUpstream<T>(url, signal);
    const entry: CacheEntry<T> = {
      key,
      value,
      storedAt: Date.now(),
      ttlMs,
      staleMs,
    };
    await getCacheStore().set(entry);
    return value;
  })().finally(() => {
    inflight.delete(key);
  });

  inflight.set(key, promise);
  return promise;
}

export async function fetchWithCache<T>(
  cacheKey: string,
  pathname: string,
  options: FetchOptions = {},
): Promise<FetchResult<T>> {
  const {
    ttlMs = DEFAULT_TTL_MS,
    staleMs = DEFAULT_STALE_MS,
    params,
    signal,
    bypass = false,
  } = options;

  const url = buildUrl(pathname, params);
  const store = getCacheStore();

  if (!bypass) {
    const entry = await store.get<T>(cacheKey);
    if (entry) {
      const age = classifyAge(entry);
      if (age === "fresh") {
        if (cacheDebug) console.log(`[stortinget] HIT  ${cacheKey}`);
        return { data: entry.value, source: "fresh", cachedAt: entry.storedAt };
      }
      if (age === "stale") {
        if (cacheDebug) console.log(`[stortinget] SWR  ${cacheKey}`);
        // Fire-and-forget refresh. Failures only log — the caller already has
        // usable data.
        void runAndStore<T>(cacheKey, url, ttlMs, staleMs).catch((err) => {
          console.error(`[stortinget] background refresh failed: ${cacheKey}`, err);
        });
        return { data: entry.value, source: "stale", cachedAt: entry.storedAt };
      }
      // expired → fall through to synchronous refetch below
    }
  }

  if (cacheDebug) console.log(`[stortinget] MISS ${cacheKey}`);
  const value = await runAndStore<T>(cacheKey, url, ttlMs, staleMs, signal);
  return {
    data: value,
    source: bypass ? "revalidated" : "miss",
    cachedAt: Date.now(),
  };
}
