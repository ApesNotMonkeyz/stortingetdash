import "server-only";

import { promises as fs } from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

import type { CacheEntry, CacheStats, CacheStore } from "./cache-store";

export class FileCacheStore implements CacheStore {
  constructor(private readonly root: string) {}

  private pathFor(key: string): string {
    const hash = crypto.createHash("sha1").update(key).digest("hex");
    return path.join(this.root, hash.slice(0, 2), `${hash}.json`);
  }

  async get<T>(key: string): Promise<CacheEntry<T> | null> {
    const file = this.pathFor(key);
    try {
      const raw = await fs.readFile(file, "utf-8");
      return JSON.parse(raw) as CacheEntry<T>;
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
      throw err;
    }
  }

  async set<T>(entry: CacheEntry<T>): Promise<void> {
    const file = this.pathFor(entry.key);
    await fs.mkdir(path.dirname(file), { recursive: true });
    // Atomic write: write to a temp sibling then rename.
    const tmp = `${file}.tmp-${process.pid}-${Date.now()}`;
    await fs.writeFile(tmp, JSON.stringify(entry));
    await fs.rename(tmp, file);
  }

  async delete(key: string): Promise<void> {
    const file = this.pathFor(key);
    try {
      await fs.unlink(file);
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    }
  }

  async stats(): Promise<CacheStats> {
    let entries = 0;
    let bytes = 0;
    try {
      const shards = await fs.readdir(this.root);
      for (const shard of shards) {
        const shardPath = path.join(this.root, shard);
        let files: string[];
        try {
          files = await fs.readdir(shardPath);
        } catch {
          continue;
        }
        for (const file of files) {
          if (!file.endsWith(".json")) continue;
          const stat = await fs.stat(path.join(shardPath, file));
          entries += 1;
          bytes += stat.size;
        }
      }
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    }
    return { entries, bytes };
  }
}
