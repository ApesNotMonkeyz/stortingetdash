import "server-only";

export type CacheEntry<T> = {
  key: string;
  value: T;
  storedAt: number;
  ttlMs: number;
  staleMs: number;
  etag?: string;
};

export type CacheAge = "fresh" | "stale" | "expired";

export function classifyAge(entry: Pick<CacheEntry<unknown>, "storedAt" | "ttlMs" | "staleMs">, now = Date.now()): CacheAge {
  const age = now - entry.storedAt;
  if (age < entry.ttlMs) return "fresh";
  if (age < entry.ttlMs + entry.staleMs) return "stale";
  return "expired";
}

export type CacheStats = {
  entries: number;
  bytes: number;
};

export interface CacheStore {
  get<T>(key: string): Promise<CacheEntry<T> | null>;
  set<T>(entry: CacheEntry<T>): Promise<void>;
  delete(key: string): Promise<void>;
  stats(): Promise<CacheStats>;
}
