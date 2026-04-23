import "server-only";

import type { FetchResult } from "./fetcher";

// Small wrapper so every /api/stortinget/* handler emits the same shape and
// exposes cache metadata via headers. `X-Cache` lets the client (or a curl
// check) see whether a request was served from cache.
export function jsonFromFetchResult<T>(result: FetchResult<T>, init?: ResponseInit): Response {
  const age = Date.now() - result.cachedAt;
  const headers = new Headers(init?.headers);
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("x-cache", result.source);
  headers.set("x-cache-age-ms", String(age));
  // Tell browsers/proxies not to cache — our server cache is authoritative.
  headers.set("cache-control", "private, no-store");
  return new Response(JSON.stringify({
    data: result.data,
    meta: { source: result.source, cachedAt: result.cachedAt, ageMs: age },
  }), { ...init, headers });
}
