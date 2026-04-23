"use client";

import { useEffect, useState } from "react";

import type { FetchSource } from "./fetcher";

export type DefaultMeta = { source: FetchSource; cachedAt: number; ageMs: number };

export type ApiEnvelope<T, M = DefaultMeta> = {
  data: T;
  meta: M;
};

export type ResourceState<T, M = DefaultMeta> =
  | { status: "loading"; data: null; error: null; meta: null }
  | { status: "ready"; data: T; error: null; meta: M }
  | { status: "error"; data: null; error: Error; meta: null };

type TrackedState<T, M> = {
  url: string;
  resource: ResourceState<T, M>;
};

const loadingState = <T, M>(): ResourceState<T, M> => ({
  status: "loading",
  data: null,
  error: null,
  meta: null,
});

async function fetchEnvelope<T, M>(url: string, signal: AbortSignal): Promise<ApiEnvelope<T, M>> {
  const res = await fetch(url, { signal, cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<ApiEnvelope<T, M>>;
}

// Minimal fetch-on-mount hook. Not a replacement for SWR/react-query, just
// enough for the first live panel. Swap in a proper library once we have
// more than one or two live views.
//
// Pass `null` as the URL to skip fetching entirely (stays in "loading" state,
// which callers treat as "no live data" and fall back to mock content).
export function useApiResource<T, M = DefaultMeta>(url: string | null): ResourceState<T, M> {
  const key = url ?? "__null__";
  const [tracked, setTracked] = useState<TrackedState<T, M>>(() => ({
    url: key,
    resource: loadingState<T, M>(),
  }));

  // React 19 pattern for derived state from props: reset during render when
  // the input changes, rather than from an effect body.
  if (tracked.url !== key) {
    setTracked({ url: key, resource: loadingState<T, M>() });
  }

  useEffect(() => {
    if (url === null) return;
    const controller = new AbortController();
    fetchEnvelope<T, M>(url, controller.signal)
      .then((env) => {
        if (controller.signal.aborted) return;
        setTracked({
          url: key,
          resource: { status: "ready", data: env.data, error: null, meta: env.meta },
        });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const error = err instanceof Error ? err : new Error(String(err));
        if (error.name === "AbortError") return;
        setTracked({ url: key, resource: { status: "error", data: null, error, meta: null } });
      });
    return () => controller.abort();
  }, [url, key]);

  return tracked.url === key ? tracked.resource : loadingState<T, M>();
}
