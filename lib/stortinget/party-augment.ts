// Curated UI metadata for parties. None of these fields are returned by the
// Stortinget API — they come from editorial decisions (color palette,
// short-name convention) or are sourced elsewhere (current leader). Keep this
// list short; anything we can derive from the API should be derived.
//
// Safe to import from client code: the file is pure data, no side effects.

export type Side = "left" | "right" | "center";

export type PartyAugment = {
  short: string;
  color: string;
  leader: string;
  side: Side;
  position: { econ: number; social: number };
};

// Keyed by Stortinget party id ("A", "H", "FrP", ...).
export const PARTY_AUGMENT: Record<string, PartyAugment> = {
  A:   { short: "Ap",  color: "var(--ap)",  leader: "Jonas Gahr Støre",       side: "left",   position: { econ: -0.4, social:  0.2 } },
  H:   { short: "H",   color: "var(--h)",   leader: "Erna Solberg",           side: "right",  position: { econ:  0.6, social:  0.1 } },
  FrP: { short: "FrP", color: "var(--frp)", leader: "Sylvi Listhaug",         side: "right",  position: { econ:  0.8, social: -0.5 } },
  Sp:  { short: "Sp",  color: "var(--sp)",  leader: "Trygve Slagsvold Vedum", side: "center", position: { econ: -0.1, social: -0.3 } },
  SV:  { short: "SV",  color: "var(--sv)",  leader: "Kirsti Bergstø",         side: "left",   position: { econ: -0.7, social:  0.6 } },
  R:   { short: "R",   color: "var(--r)",   leader: "Marie Sneve Martinussen",side: "left",   position: { econ: -0.9, social:  0.7 } },
  V:   { short: "V",   color: "var(--v)",   leader: "Guri Melby",             side: "center", position: { econ:  0.3, social:  0.5 } },
  KrF: { short: "KrF", color: "var(--krf)", leader: "Dag Inge Ulstein",       side: "center", position: { econ:  0.1, social: -0.6 } },
  MDG: { short: "MDG", color: "var(--mdg)", leader: "Arild Hermstad",         side: "left",   position: { econ: -0.3, social:  0.7 } },
  PF:  { short: "PF",  color: "var(--pf)",  leader: "Irene Ojala",            side: "center", position: { econ: -0.1, social:  0.0 } },
};

const FALLBACK: PartyAugment = {
  short: "?",
  color: "var(--fg-dim)",
  leader: "—",
  side: "center",
  position: { econ: 0, social: 0 },
};

export function augmentFor(partyId: string): PartyAugment {
  return PARTY_AUGMENT[partyId] ?? { ...FALLBACK, short: partyId };
}
