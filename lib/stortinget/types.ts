// Shared types that cross the server/client boundary. Pure types — no
// runtime code — so safe to import from either side.

import type { Side } from "./party-augment";
import type { FetchSource } from "./fetcher";

export type { Side };

export type MergedParty = {
  id: string;
  name: string;
  short: string;
  color: string;
  seats: number;
  leader: string;
  side: Side;
  position: { econ: number; social: number };
};

export type MergedPartiesEnvelope = {
  data: MergedParty[];
  meta: {
    sources: { parties: FetchSource; representatives: FetchSource };
    cachedAt: number;
    ageMs: number;
  };
};

// Matches the existing Representative shape in components/dash/data.ts so
// downstream UI can accept the live data with no type-narrowing changes.
// `voteShare` is NaN when not available from the API (Stortinget doesn't
// expose attendance percentages via this endpoint).
export type MergedRepresentative = {
  id: string;
  name: string;
  party: string;
  fylke: string;
  born: number;
  committee: string;
  committeeNames: string[];
  gender: number | null;
  role: string;
  voteShare: number;
  isVara: boolean;
};

export type MergedRepsEnvelope = {
  data: MergedRepresentative[];
  meta: {
    source: FetchSource;
    cachedAt: number;
    ageMs: number;
  };
};

// Bills from `saker_liste`. Status/type are upstream numeric enums — we
// surface both the raw code and a best-effort Norwegian label. Consumers
// should treat `statusLabel === null` as "unknown code" and render the raw
// code rather than a fabricated string.
export type MergedBill = {
  id: string;
  title: string;
  shortTitle: string;
  reference: string;
  typeCode: number;
  typeLabel: string | null;
  statusCode: number;
  statusLabel: string | null;
  committeeId: string;
  committeeName: string;
  updatedAt: number;
  sessionId: string | null;
};

export type MergedBillsEnvelope = {
  data: MergedBill[];
  meta: {
    source: FetchSource;
    cachedAt: number;
    ageMs: number;
    sessionId: string;
  };
};

// Per-bill detail. Builds on MergedBill and adds the saksgang progression
// plus rapporteurs and keywords. `stageNumber` is derived from the last
// step with any real (non-placeholder) event; 0 means nothing has happened
// yet, 4 means the bill is ferdigbehandlet.
export type TimelineEvent = {
  id: string;
  label: string;
  date: number | null;
};

export type TimelineStep = {
  stepNumber: number;
  id: string;
  name: string;
  uaktuell: boolean;
  events: TimelineEvent[];
};

export type MergedBillDetail = MergedBill & {
  ferdigbehandlet: boolean;
  stageNumber: 0 | 1 | 2 | 3 | 4;
  sakNumber: number | null;
  proposers: Array<{ id: string; name: string; partyId: string | null; partyName: string | null }>;
  keywords: string[];
  saksgang: {
    id: string;
    name: string;
    steps: TimelineStep[];
  };
};

export type MergedBillDetailEnvelope = {
  data: MergedBillDetail;
  meta: {
    source: FetchSource;
    cachedAt: number;
    ageMs: number;
  };
};

// ── Prediksjon types (mirrors backend app/models/prediksjon.py) ──────────────

export type Konfidens = "hoy" | "middels" | "lav";

export type PrimaerSignal =
  | "fraksjon_xml"
  | "forslagsstiller_repr"
  | "regjeringsposisjon"
  | "historisk_moenster"
  | "llm_analyse"
  | "ikke_tilgjengelig";

export type Sakskategori =
  | "rutine"
  | "koalisjonssak"
  | "balansesak"
  | "personvotering"
  | "ukjent";

export type SamletUtfall =
  | "sannsynlig_bifalt"
  | "sannsynlig_forkastet"
  | "usikkert";

export type VoteringType = "tilrading" | "mindretallsforslag";

export type PartiPrediksjon = {
  parti: string;
  sannsynlighet_for: number;
  konfidens: Konfidens;
  primaersignal: PrimaerSignal;
  begrunnelse: string;
  historiske_saker: number[];
};

export type VoteringPrediksjon = {
  votering_type: VoteringType;
  tittel: string;
  forslagstekst?: string;
  forslagsstillere: string[];
  prediksjoner: PartiPrediksjon[];
  samlet_utfall: SamletUtfall;
};

export type Saksprediksjon = {
  sak_id: number;
  sakskategori: Sakskategori;
  voteringer: VoteringPrediksjon[];
  samlet_utfall: SamletUtfall;
  samlet_konfidens: Konfidens;
  signalkilder_brukt: string[];
  baseline_ville_gitt: string | null;
  prompt_versjon: string | null;
};

// ── Analyse types (mirrors backend app/models/analyse.py) ────────────────────

export type Forpliktelsesgrad =
  | "utrede"
  | "vurdere"
  | "legge_frem"
  | "komme_tilbake"
  | "sikre"
  | "gjennomfore";

export type Sikkerhetsnivaa = "hoy" | "middels" | "lav";

export type KoblingType = "reversering" | "opptrapping" | "nytt" | "videroforing";

export type SaksForslagspunkt = {
  nr: string;
  tekst: string;
  forpliktelsesgrad: Forpliktelsesgrad | null;
  begrunnelse_klassifisering: string | null;
};

export type SaksInnholdsanalyse = {
  problemforstaelse: string;
  losningsforslag: string;
  argumentasjonslinjer: string[];
};

export type SaksPolitiskDimensjon = {
  akse: string;
  plassering: string;
  sikkerhet: Sikkerhetsnivaa;
  begrunnelse: string;
};

export type SaksKoblingEksisterendePolitikk = {
  type: KoblingType;
  sikkerhet: Sikkerhetsnivaa;
  begrunnelse: string;
};

export type SaksPolitiskKontekst = {
  politiske_dimensjoner: SaksPolitiskDimensjon[];
  kobling_eksisterende_politikk: SaksKoblingEksisterendePolitikk | null;
};

export type Saksanalyse = {
  sak_id: number;
  pub_id: string;
  dok_type: string;
  tittel: string | null;
  sesjon: string | null;
  forslag: SaksForslagspunkt[];
  innholdsanalyse: SaksInnholdsanalyse | null;
  politisk_kontekst: SaksPolitiskKontekst | null;
};
