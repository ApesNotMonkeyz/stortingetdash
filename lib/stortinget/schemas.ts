// Safe to import from both server and client — zod runs anywhere and the
// client uses `ApiParty` as a type (and can optionally re-validate).
import { z } from "zod";

// Stortinget wraps every response with boilerplate fields we don't need at
// the app boundary. We strip them here so callers see only the domain data.
const Envelope = z.object({
  versjon: z.string().optional(),
  respons_dato_tid: z.string().optional(),
});

// ---- allepartier ---------------------------------------------------------
// Shape observed live: { partier_liste: [{ id, navn, representert_parti }] }
export const PartySchema = Envelope.extend({
  id: z.string(),
  navn: z.string(),
  representert_parti: z.boolean(),
});
export type ApiParty = z.infer<typeof PartySchema>;

export const AllPartiesResponseSchema = Envelope.extend({
  partier_liste: z.array(PartySchema),
});
export type AllPartiesResponse = z.infer<typeof AllPartiesResponseSchema>;

// Helper that validates + narrows to the list we care about. Throws on
// unexpected shape — callers should surface that as a 502 upstream error.
export function parseAllParties(raw: unknown): ApiParty[] {
  return AllPartiesResponseSchema.parse(raw).partier_liste;
}

// ---- dagensrepresentanter ------------------------------------------------
// We only validate the fields we actually use. Unknown fields are allowed
// through on the raw object but stripped from the parsed result.
const CommitteeRefSchema = Envelope.extend({
  id: z.string(),
  navn: z.string(),
});

const FylkeSchema = Envelope.extend({
  id: z.string(),
  navn: z.string(),
  historisk_fylke: z.boolean().optional(),
});

export const RepresentativeSchema = Envelope.extend({
  id: z.string(),
  fornavn: z.string(),
  etternavn: z.string(),
  kjoenn: z.number().int().optional(),
  // .NET date literal — parsed on the fly by consumers (we only need the year).
  foedselsdato: z.string().nullable().optional(),
  fylke: FylkeSchema,
  parti: PartySchema,
  vara_representant: z.boolean(),
  komiteer_liste: z.array(CommitteeRefSchema).optional().default([]),
});
export type ApiRepresentative = z.infer<typeof RepresentativeSchema>;

export const CurrentRepresentativesResponseSchema = Envelope.extend({
  dagensrepresentanter_liste: z.array(RepresentativeSchema),
});

export function parseCurrentRepresentatives(raw: unknown): ApiRepresentative[] {
  return CurrentRepresentativesResponseSchema.parse(raw).dagensrepresentanter_liste;
}

// ---- saker (bills) -------------------------------------------------------
// Upstream uses numeric enums for `status`, `type`, and `dokumentgruppe`.
// We keep them as numbers here and map to labels at the merge layer where we
// can also expose the raw code when the label is uncertain.
const SakKomiteSchema = Envelope.extend({
  id: z.string(),
  navn: z.string(),
});

export const BillSchema = Envelope.extend({
  id: z.number(),
  tittel: z.string(),
  korttittel: z.string().nullable().optional(),
  henvisning: z.string().nullable().optional(),
  status: z.number().int(),
  type: z.number().int(),
  dokumentgruppe: z.number().int().optional(),
  komite: SakKomiteSchema.nullable().optional(),
  sist_oppdatert_dato: z.string().nullable().optional(),
  behandlet_sesjon_id: z.string().nullable().optional(),
});
export type ApiBill = z.infer<typeof BillSchema>;

export const BillsResponseSchema = Envelope.extend({
  saker_liste: z.array(BillSchema),
});

export function parseBills(raw: unknown): ApiBill[] {
  return BillsResponseSchema.parse(raw).saker_liste;
}

// ---- sak (single bill detail) -------------------------------------------
// The detail endpoint reuses many of the list's fields but adds saksgang
// progression, proposers (for Dokument 8-forslag), and stikkord. We only
// validate the parts the UI renders.
const SaksgangEventSchema = Envelope.extend({
  id: z.string(),
  dato: z.string().nullable().optional(),
  stegnummer: z.string().optional(),
  sorterings_nummer: z.number().optional(),
});

const SaksgangStepSchema = Envelope.extend({
  id: z.string(),
  navn: z.string(),
  steg_nummer: z.number().int(),
  uaktuell: z.boolean(),
  saksgang_hendelse_liste: z.array(SaksgangEventSchema).nullish().transform((v) => v ?? []),
});

const SaksgangSchema = Envelope.extend({
  id: z.string(),
  navn: z.string(),
  saksgang_steg_liste: z.array(SaksgangStepSchema),
});

const ForslagstillerSchema = Envelope.extend({
  id: z.string(),
  fornavn: z.string(),
  etternavn: z.string(),
  parti: PartySchema.nullable().optional(),
});

const SakOpphavSchema = Envelope.extend({
  forslagstiller_liste: z.array(ForslagstillerSchema).default([]),
});

const StikkordSchema = Envelope.extend({
  id: z.number().int().optional(),
  navn: z.string(),
});

export const BillDetailSchema = Envelope.extend({
  id: z.number(),
  tittel: z.string(),
  korttittel: z.string().nullable().optional(),
  henvisning: z.string().nullable().optional(),
  status: z.number().int(),
  type: z.number().int(),
  dokumentgruppe: z.number().int().optional(),
  komite: SakKomiteSchema.nullable().optional(),
  ferdigbehandlet: z.boolean(),
  sak_nummer: z.number().int().optional(),
  sak_sesjon: z.string().nullable().optional(),
  saksgang: SaksgangSchema,
  sak_opphav: SakOpphavSchema.nullable().optional(),
  stikkord_liste: z.array(StikkordSchema).optional().default([]),
});
export type ApiBillDetail = z.infer<typeof BillDetailSchema>;

export function parseBillDetail(raw: unknown): ApiBillDetail {
  return BillDetailSchema.parse(raw);
}
