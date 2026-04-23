import "server-only";

import {
  getAllParties,
  getBillDetail,
  getBills,
  getCurrentRepresentatives,
} from "./endpoints";
import { augmentFor } from "./party-augment";
import type { FetchResult, FetchSource } from "./fetcher";
import {
  parseAllParties,
  parseBillDetail,
  parseBills,
  parseCurrentRepresentatives,
  type ApiBill,
  type ApiBillDetail,
  type ApiRepresentative,
} from "./schemas";
import type {
  MergedBill,
  MergedBillDetail,
  MergedParty,
  MergedRepresentative,
  TimelineEvent,
  TimelineStep,
} from "./types";

export type MergedPartiesResult = {
  parties: MergedParty[];
  sources: { parties: FetchSource; representatives: FetchSource };
  cachedAt: number;
};

// Composes two independently-cached upstream calls into a single object that
// matches the dashboard's existing `Party` shape. Called in parallel so the
// cold-start cost is one rate-limiter slot per resource, not two sequentially.
export async function getMergedParties(opts: { bypass?: boolean; signal?: AbortSignal } = {}): Promise<MergedPartiesResult> {
  const [partiesRes, repsRes] = await Promise.all([
    getAllParties(opts),
    getCurrentRepresentatives(opts),
  ]);

  const parties = parseAllParties(partiesRes.data);
  const reps = parseCurrentRepresentatives(repsRes.data);

  const seatsById = new Map<string, number>();
  for (const rep of reps) {
    seatsById.set(rep.parti.id, (seatsById.get(rep.parti.id) ?? 0) + 1);
  }

  // Include every party returned by the API, sorted: represented (has seats)
  // first, then by seat count desc, with unrepresented parties trailing for
  // historical context.
  const merged: MergedParty[] = parties
    .map((p) => {
      const aug = augmentFor(p.id);
      return {
        id: p.id,
        name: p.navn,
        short: aug.short,
        color: aug.color,
        seats: seatsById.get(p.id) ?? 0,
        leader: aug.leader,
        side: aug.side,
        position: aug.position,
      };
    })
    .sort((a, b) => b.seats - a.seats);

  return {
    parties: merged,
    sources: { parties: partiesRes.source, representatives: repsRes.source },
    cachedAt: Math.min(partiesRes.cachedAt, repsRes.cachedAt),
  };
}

// Stortinget serializes dates as the legacy .NET `/Date(ms+tz)/` literal.
// We only need the year, so pull the epoch millis and hand it to Date.
function birthYear(foedselsdato: string | undefined | null): number {
  if (!foedselsdato) return Number.NaN;
  const match = /\/Date\((-?\d+)/.exec(foedselsdato);
  if (!match) return Number.NaN;
  return new Date(Number(match[1])).getUTCFullYear();
}

function shapeRep(api: ApiRepresentative): MergedRepresentative {
  const committees = api.komiteer_liste ?? [];
  return {
    id: api.id,
    name: `${api.fornavn} ${api.etternavn}`.trim(),
    party: api.parti.id,
    fylke: api.fylke.navn,
    born: birthYear(api.foedselsdato ?? null),
    committee: committees[0]?.navn ?? "",
    committeeNames: committees.map((c) => c.navn),
    gender: api.kjoenn ?? null,
    role: api.vara_representant ? "Vara" : "Representant",
    voteShare: Number.NaN,
    isVara: api.vara_representant,
  };
}

export type MergedRepsResult = {
  reps: MergedRepresentative[];
  source: FetchSource;
  cachedAt: number;
};

export async function getMergedReps(opts: { bypass?: boolean; signal?: AbortSignal } = {}): Promise<MergedRepsResult> {
  const result: FetchResult<unknown> = await getCurrentRepresentatives(opts);
  const reps = parseCurrentRepresentatives(result.data).map(shapeRep);
  // Sort alphabetically by surname — matches the default UI sort and keeps
  // the API response stable across refreshes regardless of upstream order.
  reps.sort((a, b) => a.name.localeCompare(b.name, "nb"));
  return { reps, source: result.source, cachedAt: result.cachedAt };
}

// Stortinget's `saker` endpoint uses numeric enums for `type` and `status`
// that aren't labeled in the response and aren't self-consistent (observed:
// "Prop. 90 S" and a Dokument-8 representantforslag both come back as
// type=2). Until the mapping is pinned down, we leave both unlabeled and
// derive a human hint from the `henvisning` prefix in the UI instead.
const TYPE_LABELS: Record<number, string> = {};
const STATUS_LABELS: Record<number, string> = {};

function parseDotNetDate(raw: string | null | undefined): number {
  if (!raw) return 0;
  const match = /\/Date\((-?\d+)/.exec(raw);
  return match ? Number(match[1]) : 0;
}

// Derive a human document-class label from the henvisning prefix, which is
// authored by the clerks and reliable (unlike the numeric `type` field).
// Known patterns: "Prop. 142 L", "Meld. St. 14", "Dokument 8:123 S",
// "Dokument 9", "Innst. 42 S". Falls back to an empty string — the UI then
// renders nothing rather than a wrong guess.
function classifyReference(henvisning: string): string {
  const s = henvisning.trim();
  if (!s) return "";
  if (/^Prop\./i.test(s)) return "Proposisjon";
  if (/^Meld\./i.test(s)) return "Melding";
  if (/^Innst\./i.test(s)) return "Innstilling";
  if (/^Dokument\s+8[:\s]/i.test(s)) return "Representantforslag";
  if (/^Dokument\s+\d/i.test(s)) return "Dokument";
  return "";
}

function shapeBill(api: ApiBill): MergedBill {
  const reference = api.henvisning ?? "";
  const derived = classifyReference(reference);
  return {
    id: String(api.id),
    title: api.tittel,
    shortTitle: api.korttittel ?? api.tittel,
    reference,
    typeCode: api.type,
    typeLabel: TYPE_LABELS[api.type] ?? (derived || null),
    statusCode: api.status,
    statusLabel: STATUS_LABELS[api.status] ?? null,
    committeeId: api.komite?.id ?? "",
    committeeName: api.komite?.navn ?? "",
    updatedAt: parseDotNetDate(api.sist_oppdatert_dato),
    sessionId: api.behandlet_sesjon_id ?? null,
  };
}

export type MergedBillsResult = {
  bills: MergedBill[];
  source: FetchSource;
  cachedAt: number;
  sessionId: string;
};

export async function getMergedBills(
  sessionId: string,
  opts: { bypass?: boolean; signal?: AbortSignal } = {},
): Promise<MergedBillsResult> {
  const result: FetchResult<unknown> = await getBills(sessionId, opts);
  const bills = parseBills(result.data).map(shapeBill);
  // Sort by most-recently-updated first so the list surfaces active work at
  // the top, matching the existing UI's implicit "on dagsorden" behaviour.
  bills.sort((a, b) => b.updatedAt - a.updatedAt);
  return { bills, source: result.source, cachedAt: result.cachedAt, sessionId };
}

// Known saksgang event codes mapped to human labels. Unknown codes fall
// through to the raw id so the UI still renders something identifiable.
const EVENT_LABELS: Record<string, string> = {
  FRADEP: "Mottatt fra departementet",
  SAK: "Registrert som sak",
  FREMMET: "Fremmet",
  FREMSATT: "Fremsatt",
  REFS: "Referert",
  SENDT: "Sendt til komité",
  KOMITE: "Komitébehandling",
  HOER: "Høring",
  HOERFRIST: "Høringsfrist",
  ORDFORER: "Saksordfører utnevnt",
  AVGFRIST: "Avgivelsesfrist",
  AVG: "Innstilling avgitt",
  PLBEH: "Plenumsbehandling",
  PLBEHS: "Plenumsbehandling",
  BEHANDLET: "Ferdigbehandlet",
};

// Parse Stortinget's "dd.MM.yyyy HH:mm:ss" date strings. Upstream uses
// "01.01.0001 00:00:00" as a sentinel for "no date yet" — we return null so
// the UI can collapse placeholder events.
function parseNorwegianDate(raw: string): number | null {
  if (!raw || raw.startsWith("01.01.0001")) return null;
  const match = /^(\d{2})\.(\d{2})\.(\d{4})/.exec(raw);
  if (!match) return null;
  const [, dd, mm, yyyy] = match;
  const ts = Date.UTC(Number(yyyy), Number(mm) - 1, Number(dd));
  return Number.isFinite(ts) ? ts : null;
}

function shapeEvent(e: ApiBillDetail["saksgang"]["saksgang_steg_liste"][number]["saksgang_hendelse_liste"][number]): TimelineEvent {
  return {
    id: e.id,
    label: EVENT_LABELS[e.id] ?? e.id,
    date: parseNorwegianDate(e.dato ?? ""),
  };
}

function shapeStep(s: ApiBillDetail["saksgang"]["saksgang_steg_liste"][number]): TimelineStep {
  return {
    stepNumber: s.steg_nummer,
    id: s.id,
    name: s.navn,
    uaktuell: s.uaktuell,
    events: (s.saksgang_hendelse_liste ?? []).map(shapeEvent),
  };
}

// Stage 0..4: 0 = nothing real yet, 4 = ferdigbehandlet. For intermediate
// values we look at the highest-numbered step with at least one real-dated
// event — that reflects actual progress rather than the API's static step
// scaffold, which is present from day one.
function deriveStage(detail: ApiBillDetail, steps: TimelineStep[]): MergedBillDetail["stageNumber"] {
  if (detail.ferdigbehandlet) return 4;
  let lastActive = 0;
  for (const step of steps) {
    if (step.events.some((e) => e.date !== null)) lastActive = step.stepNumber;
  }
  return Math.min(lastActive, 3) as MergedBillDetail["stageNumber"];
}

function shapeDetail(api: ApiBillDetail): MergedBillDetail {
  const reference = api.henvisning ?? "";
  const derived = classifyReference(reference);
  const steps = api.saksgang.saksgang_steg_liste.map(shapeStep);
  return {
    id: String(api.id),
    title: api.tittel,
    shortTitle: api.korttittel ?? api.tittel,
    reference,
    typeCode: api.type,
    typeLabel: TYPE_LABELS[api.type] ?? (derived || null),
    statusCode: api.status,
    statusLabel: STATUS_LABELS[api.status] ?? null,
    committeeId: api.komite?.id ?? "",
    committeeName: api.komite?.navn ?? "",
    // The list's `sist_oppdatert_dato` isn't on the detail envelope — we
    // approximate by using the latest dated event in saksgang.
    updatedAt: steps
      .flatMap((s) => s.events.map((e) => e.date ?? 0))
      .reduce((a, b) => Math.max(a, b), 0),
    sessionId: api.sak_sesjon ?? null,
    ferdigbehandlet: api.ferdigbehandlet,
    stageNumber: deriveStage(api, steps),
    sakNumber: api.sak_nummer ?? null,
    proposers: (api.sak_opphav?.forslagstiller_liste ?? []).map((f) => ({
      id: f.id,
      name: `${f.fornavn} ${f.etternavn}`.trim(),
      partyId: f.parti?.id ?? null,
      partyName: f.parti?.navn ?? null,
    })),
    keywords: (api.stikkord_liste ?? []).map((s) => s.navn),
    saksgang: {
      id: api.saksgang.id,
      name: api.saksgang.navn,
      steps,
    },
  };
}

export type MergedBillDetailResult = {
  bill: MergedBillDetail;
  source: FetchSource;
  cachedAt: number;
};

export async function getMergedBillDetail(
  sakId: string,
  opts: { bypass?: boolean; signal?: AbortSignal } = {},
): Promise<MergedBillDetailResult> {
  const result: FetchResult<unknown> = await getBillDetail(sakId, opts);
  const bill = shapeDetail(parseBillDetail(result.data));
  return { bill, source: result.source, cachedAt: result.cachedAt };
}
