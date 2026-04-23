import "server-only";

import type { CacheEntry, CacheStats, CacheStore } from "./cache-store";

export class MemoryCacheStore implements CacheStore {
  private readonly map = new Map<string, CacheEntry<unknown>>();

  async get<T>(key: string): Promise<CacheEntry<T> | null> {
    return (this.map.get(key) as CacheEntry<T> | undefined) ?? null;
  }

  async set<T>(entry: CacheEntry<T>): Promise<void> {
    this.map.set(entry.key, entry as CacheEntry<unknown>);
  }

  async delete(key: string): Promise<void> {
    this.map.delete(key);
  }

  async stats(): Promise<CacheStats> {
    let bytes = 0;
    for (const entry of this.map.values()) {
      bytes += JSON.stringify(entry.value).length;
    }
    return { entries: this.map.size, bytes };
  }
}
