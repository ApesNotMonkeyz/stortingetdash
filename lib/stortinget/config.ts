import "server-only";

import path from "node:path";

import type { CacheStore } from "./cache-store";
import { FileCacheStore } from "./file-store";
import { MemoryCacheStore } from "./memory-store";
import { TokenBucket } from "./rate-limiter";

export const STORTINGET_BASE_URL = "https://data.stortinget.no/eksport";

// Global singletons, scoped to the Node process. On a long-running server this
// gives us a shared cache + rate limiter across all requests.
const g = globalThis as typeof globalThis & {
  __stortingetCacheStore?: CacheStore;
  __stortingetLimiter?: TokenBucket;
};

function createStore(): CacheStore {
  const driver = process.env.STORTINGET_CACHE_DRIVER ?? "file";
  if (driver === "memory") return new MemoryCacheStore();
  const root = process.env.STORTINGET_CACHE_DIR
    ?? path.join(process.cwd(), ".cache", "stortinget");
  return new FileCacheStore(root);
}

export function getCacheStore(): CacheStore {
  if (!g.__stortingetCacheStore) {
    g.__stortingetCacheStore = createStore();
  }
  return g.__stortingetCacheStore;
}

export function getRateLimiter(): TokenBucket {
  if (!g.__stortingetLimiter) {
    const perMinute = Number(process.env.STORTINGET_RATE_PER_MINUTE ?? 90);
    g.__stortingetLimiter = new TokenBucket({
      capacity: perMinute,
      refillPerMinute: perMinute,
    });
  }
  return g.__stortingetLimiter;
}

export const cacheDebug = process.env.STORTINGET_CACHE_DEBUG === "1";
