import "server-only";

import { fetchWithCache, type FetchOptions, type FetchResult } from "./fetcher";

// Per-resource TTLs. Data that changes rarely (all-time party list) gets a
// long soft TTL; session-scoped data gets shorter freshness; vote tallies get
// near-live freshness. Tune as upstream update frequency becomes clearer.
const TTL = {
  day: 24 * 60 * 60 * 1000,
  hours6: 6 * 60 * 60 * 1000,
  hour: 60 * 60 * 1000,
  minutes15: 15 * 60 * 1000,
  minute: 60 * 1000,
};

const STALE = {
  week: 7 * 24 * 60 * 60 * 1000,
  day: 24 * 60 * 60 * 1000,
  hours6: 6 * 60 * 60 * 1000,
};

// Cache keys are stable, namespaced strings — never raw URLs — so we can
// rename the upstream path without invalidating entries.
const key = (parts: Array<string | number | undefined>) =>
  ["stortinget", ...parts.filter((p) => p !== undefined)].join(":");

type Opts = Pick<FetchOptions, "signal" | "bypass">;

// ---- Known endpoints ------------------------------------------------------
// Intentionally thin: each wraps a single upstream path. Response types are
// `unknown` until we pin down the schemas — callers should narrow at the
// boundary (zod etc.) before trusting the shape.

export function getAllParties<T = unknown>(opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["allepartier"]), "allepartier", {
    ttlMs: TTL.day,
    staleMs: STALE.week,
    ...opts,
  });
}

export function getPartiesForSession<T = unknown>(sesjonId: string, opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["partier", sesjonId]), "partier", {
    ttlMs: TTL.day,
    staleMs: STALE.week,
    params: { sesjonid: sesjonId },
    ...opts,
  });
}

export function getCurrentRepresentatives<T = unknown>(opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["dagensrepresentanter"]), "dagensrepresentanter", {
    ttlMs: TTL.hours6,
    staleMs: STALE.day,
    ...opts,
  });
}

export function getRepresentativesForSession<T = unknown>(sesjonId: string, opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["representanter", sesjonId]), "representanter", {
    ttlMs: TTL.hours6,
    staleMs: STALE.day,
    params: { SesjonID: sesjonId },
    ...opts,
  });
}

export function getCommittees<T = unknown>(sesjonId: string, opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["komiteer", sesjonId]), "komiteer", {
    ttlMs: TTL.day,
    staleMs: STALE.week,
    params: { sesjonid: sesjonId },
    ...opts,
  });
}

export function getBills<T = unknown>(sesjonId: string, opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["saker", sesjonId]), "saker", {
    ttlMs: TTL.hour,
    staleMs: STALE.hours6,
    params: { sesjonid: sesjonId },
    ...opts,
  });
}

export function getVotesForBill<T = unknown>(sakId: string | number, opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["voteringer", sakId]), "voteringer", {
    ttlMs: TTL.minutes15,
    staleMs: STALE.hours6,
    params: { sakid: sakId },
    ...opts,
  });
}

// Per-bill detail. Richer than the list entry — includes saksgang steps with
// their events, stikkord, proposers (for representant-forslag), and the
// ferdigbehandlet flag. TTL is slightly longer than the list since detail
// fields change less frequently (the list's sist_oppdatert moves any time
// there's activity, while individual fields like saksgang add events).
export function getBillDetail<T = unknown>(sakId: string | number, opts: Opts = {}): Promise<FetchResult<T>> {
  return fetchWithCache<T>(key(["sak", sakId]), "sak", {
    ttlMs: TTL.hour,
    staleMs: STALE.day,
    params: { sakid: sakId },
    ...opts,
  });
}
