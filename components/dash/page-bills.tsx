"use client";

import React from "react";
import { BILLS, PARTIES, RECENT_VOTES, billById, committeeById, partyById } from "./data";
import { Page, StatusChip, StageBar, PartyTag, type Nav, type Params } from "./components";
import { useApiResource } from "@/lib/stortinget/client";
import type {
  MergedBill,
  MergedBillDetail,
  MergedBillDetailEnvelope,
  MergedBillsEnvelope,
  Saksanalyse,
  Forpliktelsesgrad,
  Sikkerhetsnivaa,
  Saksprediksjon,
  PartiPrediksjon,
  VoteringPrediksjon,
  Konfidens,
} from "@/lib/stortinget/types";

export function Bills({
  onNav,
  layoutVariant,
}: {
  onNav: Nav;
  layoutVariant: "table" | "cards";
}) {
  // Re-mount via key so that changing the layout variant from the tweak
  // panel resets any local view override the user had set.
  return <BillsInner key={layoutVariant} onNav={onNav} layoutVariant={layoutVariant} />;
}

// Flags a section that hasn't been wired to a live source yet. Used on the
// bill detail page so readers don't conflate the sample AI summary / expected
// vote split with data actually served from Stortinget.
function PreliminaryBadge() {
  return (
    <span
      className="chip"
      style={{
        fontSize: 10,
        color: "var(--warn)",
        background: "color-mix(in oklab, var(--warn) 10%, transparent)",
        borderColor: "color-mix(in oklab, var(--warn) 25%, transparent)",
      }}
    >
      foreløpig · mock
    </span>
  );
}

// ── Analyse panel ─────────────────────────────────────────────────────────────

const FORPLIKTELSE_LABELS: Record<Forpliktelsesgrad, string> = {
  utrede: "Utrede",
  vurdere: "Vurdere",
  legge_frem: "Legge frem",
  komme_tilbake: "Komme tilbake",
  sikre: "Sikre",
  gjennomfore: "Gjennomføre",
};

const FORPLIKTELSE_COLORS: Record<Forpliktelsesgrad, string> = {
  utrede: "var(--fg-dim)",
  vurdere: "var(--fg-dim)",
  legge_frem: "var(--warn)",
  komme_tilbake: "var(--warn)",
  sikre: "var(--pos)",
  gjennomfore: "var(--pos)",
};

const SIKKERHET_LABELS: Record<Sikkerhetsnivaa, string> = {
  hoy: "Høy",
  middels: "Middels",
  lav: "Lav",
};

function ForpliktelseBadge({ grad }: { grad: Forpliktelsesgrad }) {
  const color = FORPLIKTELSE_COLORS[grad];
  return (
    <span
      className="chip"
      style={{
        fontSize: 10,
        color,
        background: `color-mix(in oklab, ${color} 12%, transparent)`,
        borderColor: `color-mix(in oklab, ${color} 28%, transparent)`,
        fontFamily: "var(--font-mono)",
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      {FORPLIKTELSE_LABELS[grad]}
    </span>
  );
}

function AnalyseVisning({ analyse }: { analyse: Saksanalyse }) {
  const inn = analyse.innholdsanalyse;
  const kont = analyse.politisk_kontekst;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {inn && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 10 }}>Sammendrag</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: 13.5 }}>
              <span style={{ color: "var(--fg-dim)", fontSize: 11, fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 3 }}>
                Problem
              </span>
              {inn.problemforstaelse}
            </div>
            <div style={{ fontSize: 13.5 }}>
              <span style={{ color: "var(--fg-dim)", fontSize: 11, fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 3 }}>
                Løsning
              </span>
              {inn.losningsforslag}
            </div>
            {inn.argumentasjonslinjer.length > 0 && (
              <div>
                <span style={{ color: "var(--fg-dim)", fontSize: 11, fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>
                  Argumenter
                </span>
                <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 5 }}>
                  {inn.argumentasjonslinjer.map((a, i) => (
                    <li key={i} style={{ display: "flex", gap: 10, fontSize: 13 }}>
                      <span className="mono" style={{ color: "var(--fg-faint)", minWidth: 20 }}>{String(i + 1).padStart(2, "0")}</span>
                      <span style={{ color: "var(--fg-muted)" }}>{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {analyse.forslag.length > 0 && (
        <div>
          <hr style={{ margin: "0 0 14px" }} />
          <div className="eyebrow" style={{ marginBottom: 10 }}>Forslagspunkter</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {analyse.forslag.map((f) => (
              <div
                key={f.nr}
                style={{
                  padding: "10px 12px",
                  background: "var(--bg-elev)",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--fg-faint)" }}>
                    §{f.nr}
                  </span>
                  {f.forpliktelsesgrad && <ForpliktelseBadge grad={f.forpliktelsesgrad} />}
                </div>
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: "var(--fg)" }}>
                  {f.tekst}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {kont && (kont.politiske_dimensjoner.length > 0 || kont.kobling_eksisterende_politikk) && (
        <div>
          <hr style={{ margin: "0 0 14px" }} />
          <div className="eyebrow" style={{ marginBottom: 10 }}>Politisk kontekst</div>
          {kont.politiske_dimensjoner.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
              {kont.politiske_dimensjoner.map((d, i) => (
                <div
                  key={i}
                  style={{
                    padding: "8px 12px",
                    background: "var(--bg-elev)",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    fontSize: 13,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                    <span style={{ fontWeight: 500 }}>{d.akse}</span>
                    <span style={{ color: "var(--fg-dim)", fontSize: 11 }}>→</span>
                    <span style={{ color: "var(--fg-muted)" }}>{d.plassering}</span>
                    <span
                      className="chip"
                      style={{ fontSize: 10, marginLeft: "auto", fontFamily: "var(--font-mono)" }}
                    >
                      {SIKKERHET_LABELS[d.sikkerhet]}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--fg-dim)", lineHeight: 1.4 }}>
                    {d.begrunnelse}
                  </div>
                </div>
              ))}
            </div>
          )}
          {kont.kobling_eksisterende_politikk && (
            <div
              style={{
                padding: "8px 12px",
                background: "var(--bg-elev)",
                borderRadius: 6,
                border: "1px solid var(--border)",
                fontSize: 13,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                <span style={{ color: "var(--fg-dim)", fontSize: 11, fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Kobling
                </span>
                <span className="chip" style={{ fontSize: 11, fontFamily: "var(--font-mono)" }}>
                  {kont.kobling_eksisterende_politikk.type}
                </span>
                <span
                  className="chip"
                  style={{ fontSize: 10, marginLeft: "auto", fontFamily: "var(--font-mono)" }}
                >
                  {SIKKERHET_LABELS[kont.kobling_eksisterende_politikk.sikkerhet]}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--fg-dim)", lineHeight: 1.4 }}>
                {kont.kobling_eksisterende_politikk.begrunnelse}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

type AnalysePanelState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; analyse: Saksanalyse }
  | { kind: "error"; message: string };

function AnalysePanel({ sakId }: { sakId: string }) {
  const [state, setState] = React.useState<AnalysePanelState>({ kind: "idle" });

  async function hentAnalyse(force = false) {
    setState({ kind: "loading" });
    try {
      const url = `/api/analyse/${encodeURIComponent(sakId)}${force ? "?force=true" : ""}`;
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setState({ kind: "error", message: body.detail ?? body.message ?? `HTTP ${res.status}` });
        return;
      }
      const analyse: Saksanalyse = await res.json();
      setState({ kind: "ready", analyse });
    } catch (err) {
      setState({ kind: "error", message: (err as Error).message });
    }
  }

  return (
    <section className="card" style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: state.kind === "idle" ? 0 : 14 }}>
        <span
          style={{
            width: 22,
            height: 22,
            borderRadius: 4,
            background: "var(--fg)",
            color: "var(--bg)",
            display: "grid",
            placeItems: "center",
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            fontWeight: 600,
          }}
        >
          A
        </span>
        <div className="eyebrow">AI-analyse</div>
        {state.kind === "idle" && (
          <button
            className="btn"
            onClick={() => hentAnalyse()}
            style={{ marginLeft: "auto", height: 28, padding: "0 12px", fontSize: 12, cursor: "pointer" }}
          >
            Hent analyse
          </button>
        )}
        {state.kind === "ready" && (
          <button
            className="btn"
            onClick={() => setState({ kind: "idle" })}
            style={{ marginLeft: "auto", height: 28, padding: "0 12px", fontSize: 12, cursor: "pointer" }}
          >
            Lukk
          </button>
        )}
        {state.kind === "error" && (
          <button
            className="btn"
            onClick={() => hentAnalyse()}
            style={{ marginLeft: "auto", height: 28, padding: "0 12px", fontSize: 12, cursor: "pointer" }}
          >
            Prøv igjen
          </button>
        )}
      </div>

      {state.kind === "loading" && (
        <div>
          <div style={{ fontSize: 13, color: "var(--fg-dim)", marginBottom: 12 }}>
            Kjører analysepipeline — dette tar typisk 20–40 sekunder…
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[80, 60, 90, 50].map((w, i) => (
              <div
                key={i}
                style={{
                  height: 12,
                  width: `${w}%`,
                  borderRadius: 4,
                  background: "var(--border)",
                  opacity: 0.6,
                }}
              />
            ))}
          </div>
        </div>
      )}

      {state.kind === "error" && (
        <div
          style={{
            padding: "12px 14px",
            borderRadius: 6,
            background: "color-mix(in oklab, var(--neg) 10%, transparent)",
            border: "1px solid color-mix(in oklab, var(--neg) 25%, transparent)",
            color: "var(--neg)",
            fontSize: 13,
            lineHeight: 1.5,
          }}
        >
          {state.message}
        </div>
      )}

      {state.kind === "ready" && <AnalyseVisning analyse={state.analyse} />}
    </section>
  );
}

// ── Prediksjon panel ──────────────────────────────────────────────────────────

type PrediksjonsState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; data: Saksprediksjon }
  | { kind: "error"; message: string };

const HEMICYCLE_ORDER = ["R", "SV", "A", "MDG", "Sp", "V", "KrF", "H", "FrP"];

const UTFALL_LABELS: Record<string, string> = {
  sannsynlig_bifalt: "Vedtas trolig",
  sannsynlig_forkastet: "Forkastes trolig",
  usikkert: "Usikkert utfall",
};

const KATEGORI_LABELS: Record<string, string> = {
  rutine: "Rutinesak",
  koalisjonssak: "Koalisjonssak",
  balansesak: "Balansesak",
  personvotering: "Personvotering",
  ukjent: "Ukjent kategori",
};

const SIGNAL_LABELS: Record<string, string> = {
  fraksjon_xml: "Fraksjon",
  forslagsstiller_repr: "Forslagsstiller",
  regjeringsposisjon: "Regjeringsposisjon",
  historisk_moenster: "Historikk",
  llm_analyse: "LLM",
  ikke_tilgjengelig: "—",
};

function KonfidensBar({ pred }: { pred: PartiPrediksjon }) {
  const party = partyById(pred.parti);
  const pct = Math.round(pred.sannsynlighet_for * 100);
  const opacity = pred.konfidens === "hoy" ? 1 : pred.konfidens === "middels" ? 0.55 : 0.3;

  const barColor =
    pred.sannsynlighet_for >= 0.6
      ? party.color
      : pred.sannsynlighet_for <= 0.4
        ? "var(--neg)"
        : "var(--fg-dim)";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, height: 28 }}>
      <span
        style={{
          width: 28,
          flexShrink: 0,
          fontSize: 12,
          fontWeight: 600,
          color: party.color,
          fontFamily: "var(--font-mono)",
        }}
      >
        {pred.parti}
      </span>
      <div
        style={{
          flex: 1,
          height: 6,
          borderRadius: 3,
          background: "var(--border)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            height: "100%",
            width: `${pct}%`,
            background: barColor,
            opacity,
            borderRadius: 3,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span
        style={{
          width: 32,
          flexShrink: 0,
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          color: "var(--fg-dim)",
          textAlign: "right",
          opacity,
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

function sortByHemicycle(preds: PartiPrediksjon[]): PartiPrediksjon[] {
  return [...preds].sort((a, b) => {
    const ai = HEMICYCLE_ORDER.indexOf(a.parti);
    const bi = HEMICYCLE_ORDER.indexOf(b.parti);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
}

function VoteringBars({
  prediksjoner,
  expandedParti,
  onToggle,
}: {
  prediksjoner: PartiPrediksjon[];
  expandedParti: string | null;
  onToggle: (parti: string) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {sortByHemicycle(prediksjoner).map((pred) => (
        <div key={pred.parti}>
          <button
            onClick={() => onToggle(pred.parti)}
            style={{ width: "100%", background: "none", border: "none", padding: "2px 0", cursor: "pointer", textAlign: "left" }}
          >
            <KonfidensBar pred={pred} />
          </button>
          {expandedParti === pred.parti && (
            <div
              style={{
                margin: "4px 0 8px 36px",
                fontSize: 12,
                lineHeight: 1.6,
                color: "var(--fg-dim)",
                padding: "8px 10px",
                borderRadius: 5,
                background: "color-mix(in oklab, var(--fg) 4%, transparent)",
                border: "1px solid var(--border)",
              }}
            >
              <span style={{ fontSize: 10, color: "var(--fg-dim)", marginBottom: 4, display: "block" }}>
                Signal: {SIGNAL_LABELS[pred.primaersignal] ?? pred.primaersignal}
                {" · "}Konfidens: {pred.konfidens}
              </span>
              {pred.begrunnelse}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Mindretallsforslag({
  vot,
  index,
  expanded,
  onToggle,
}: {
  vot: VoteringPrediksjon;
  index: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  const [tekstUtvidet, setTekstUtvidet] = React.useState(false);
  const tekst = vot.forslagstekst ?? "";
  const TEKST_GRENSE = 220;
  const tekst_trimmet = tekst.length > TEKST_GRENSE && !tekstUtvidet
    ? tekst.slice(0, TEKST_GRENSE) + "…"
    : tekst;

  return (
    <div style={{ marginBottom: 8, paddingBottom: 8, borderBottom: "1px solid color-mix(in oklab, var(--border) 60%, transparent)" }}>
      <button
        onClick={onToggle}
        style={{ width: "100%", background: "none", border: "none", padding: "4px 0", cursor: "pointer", textAlign: "left", display: "flex", alignItems: "flex-start", gap: 6 }}
      >
        <span style={{ fontSize: 12, color: "var(--fg)", fontWeight: 500, flex: 1 }}>
          {vot.tittel}
        </span>
        <span style={{ fontSize: 10, color: "var(--fg-dim)", flexShrink: 0, paddingTop: 1 }}>
          {UTFALL_LABELS[vot.samlet_utfall] ?? vot.samlet_utfall}
        </span>
        <span style={{ fontSize: 10, color: "var(--fg-dim)", flexShrink: 0, paddingTop: 1, marginLeft: 4 }}>
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && (
        <div style={{ marginTop: 6 }}>
          {/* Forslagsstillere */}
          {vot.forslagsstillere.length > 0 && (
            <div style={{ display: "flex", gap: 4, marginBottom: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 10, color: "var(--fg-dim)", alignSelf: "center" }}>Fremmet av:</span>
              {vot.forslagsstillere.map((p) => {
                const party = partyById(p);
                return (
                  <span
                    key={p}
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: party.color,
                      padding: "1px 6px",
                      borderRadius: 3,
                      background: `color-mix(in oklab, ${party.color} 12%, transparent)`,
                      border: `1px solid color-mix(in oklab, ${party.color} 28%, transparent)`,
                    }}
                  >
                    {p}
                  </span>
                );
              })}
            </div>
          )}

          {/* Forslagstekst */}
          {tekst && (
            <div style={{ marginBottom: 10 }}>
              <p
                style={{
                  fontSize: 11,
                  lineHeight: 1.6,
                  color: "var(--fg-dim)",
                  margin: 0,
                  padding: "8px 10px",
                  borderRadius: 4,
                  background: "color-mix(in oklab, var(--fg) 3%, transparent)",
                  border: "1px solid var(--border)",
                  whiteSpace: "pre-wrap",
                }}
              >
                {tekst_trimmet}
              </p>
              {tekst.length > TEKST_GRENSE && (
                <button
                  onClick={(e) => { e.stopPropagation(); setTekstUtvidet(!tekstUtvidet); }}
                  style={{ fontSize: 11, color: "var(--fg-dim)", background: "none", border: "none", cursor: "pointer", padding: "2px 0", marginTop: 2 }}
                >
                  {tekstUtvidet ? "Vis mindre" : "Vis mer"}
                </button>
              )}
            </div>
          )}

          {/* Party bars */}
          <VoteringBars
            prediksjoner={vot.prediksjoner}
            expandedParti={null}
            onToggle={() => {}}
          />
          <div style={{ display: "flex", justifyContent: "space-between", marginLeft: 36, marginRight: 40, marginTop: 4 }}>
            <span style={{ fontSize: 10, color: "var(--fg-dim)" }}>MOT</span>
            <span style={{ fontSize: 10, color: "var(--fg-dim)" }}>FOR</span>
          </div>
        </div>
      )}
    </div>
  );
}

function PrediksjonsVisning({ data }: { data: Saksprediksjon }) {
  const [expandedParti, setExpandedParti] = React.useState<string | null>(null);
  const [expandedVotering, setExpandedVotering] = React.useState<number | null>(null);

  const voteringer = data.voteringer ?? [];
  const tilraading = voteringer[0];
  const mindretallsVoteringer = voteringer.slice(1);

  const utfallColor =
    data.samlet_utfall === "sannsynlig_bifalt"
      ? "var(--pos)"
      : data.samlet_utfall === "sannsynlig_forkastet"
        ? "var(--neg)"
        : "var(--warn)";

  return (
    <div>
      {/* Header row: utfall + kategori */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: utfallColor,
            padding: "3px 8px",
            borderRadius: 4,
            background: `color-mix(in oklab, ${utfallColor} 12%, transparent)`,
            border: `1px solid color-mix(in oklab, ${utfallColor} 28%, transparent)`,
          }}
        >
          {UTFALL_LABELS[data.samlet_utfall] ?? data.samlet_utfall}
        </span>
        <span className="chip" style={{ fontSize: 11 }}>
          {KATEGORI_LABELS[data.sakskategori] ?? data.sakskategori}
        </span>
        <span className="chip" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
          Konfidens: {data.samlet_konfidens}
        </span>
      </div>

      {/* Tilrådingen — party bars */}
      {tilraading && (
        <>
          <VoteringBars
            prediksjoner={tilraading.prediksjoner}
            expandedParti={expandedParti}
            onToggle={(p) => setExpandedParti(expandedParti === p ? null : p)}
          />
          <div style={{ display: "flex", justifyContent: "space-between", marginLeft: 36, marginRight: 40, marginTop: 4, marginBottom: 12 }}>
            <span style={{ fontSize: 10, color: "var(--fg-dim)" }}>MOT</span>
            <span style={{ fontSize: 10, color: "var(--fg-dim)" }}>FOR</span>
          </div>
        </>
      )}

      {/* Mindretallsforslag */}
      {mindretallsVoteringer.length > 0 && (
        <div style={{ marginTop: 8, borderTop: "1px solid var(--border)", paddingTop: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--fg-dim)", letterSpacing: "0.06em", marginBottom: 6 }}>
            MINDRETALLSFORSLAG
          </div>
          {mindretallsVoteringer.map((vot, i) => (
            <Mindretallsforslag
              key={i}
              vot={vot}
              index={i}
              expanded={expandedVotering === i}
              onToggle={() => setExpandedVotering(expandedVotering === i ? null : i)}
            />
          ))}
        </div>
      )}

      {/* Baseline note */}
      {data.baseline_ville_gitt && (
        <p style={{ fontSize: 11, color: "var(--fg-dim)", marginTop: 12, marginBottom: 0, lineHeight: 1.5 }}>
          {data.baseline_ville_gitt}
        </p>
      )}
    </div>
  );
}

function PrediksjonsPanel({ sakId }: { sakId: string }) {
  const [state, setState] = React.useState<PrediksjonsState>({ kind: "idle" });

  async function hentPrediksjon(force = false) {
    setState({ kind: "loading" });
    try {
      const url = `/api/prediksjon/${encodeURIComponent(sakId)}${force ? "?force=true" : ""}`;
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setState({ kind: "error", message: body.detail ?? body.message ?? `HTTP ${res.status}` });
        return;
      }
      const data: Saksprediksjon = await res.json();
      setState({ kind: "ready", data });
    } catch (err) {
      setState({ kind: "error", message: (err as Error).message });
    }
  }

  return (
    <section className="card" style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: state.kind === "idle" ? 0 : 14 }}>
        <span
          style={{
            width: 22,
            height: 22,
            borderRadius: 4,
            background: "var(--fg)",
            color: "var(--bg)",
            display: "grid",
            placeItems: "center",
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            fontWeight: 600,
          }}
        >
          P
        </span>
        <div className="eyebrow">Partistandpunkt</div>
        {state.kind === "idle" && (
          <button
            className="btn"
            onClick={() => hentPrediksjon()}
            style={{ marginLeft: "auto", height: 28, padding: "0 12px", fontSize: 12, cursor: "pointer" }}
          >
            Analyser
          </button>
        )}
        {state.kind === "ready" && (
          <button
            className="btn"
            onClick={() => setState({ kind: "idle" })}
            style={{ marginLeft: "auto", height: 28, padding: "0 12px", fontSize: 12, cursor: "pointer" }}
          >
            Lukk
          </button>
        )}
        {state.kind === "error" && (
          <button
            className="btn"
            onClick={() => hentPrediksjon()}
            style={{ marginLeft: "auto", height: 28, padding: "0 12px", fontSize: 12, cursor: "pointer" }}
          >
            Prøv igjen
          </button>
        )}
      </div>

      {state.kind === "loading" && (
        <div>
          <div style={{ fontSize: 13, color: "var(--fg-dim)", marginBottom: 12 }}>
            Analyserer partistandpunkter…
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {[70, 85, 55, 90, 60, 75, 50, 80, 65].map((w, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <div style={{ width: 28, height: 10, borderRadius: 3, background: "var(--border)", opacity: 0.5 }} />
                <div style={{ flex: 1, height: 6, borderRadius: 3, background: "var(--border)", opacity: 0.4 }}>
                  <div style={{ width: `${w}%`, height: "100%", background: "var(--border)", borderRadius: 3 }} />
                </div>
                <div style={{ width: 28, height: 8, borderRadius: 3, background: "var(--border)", opacity: 0.4 }} />
              </div>
            ))}
          </div>
        </div>
      )}

      {state.kind === "error" && (
        <div
          style={{
            padding: "12px 14px",
            borderRadius: 6,
            background: "color-mix(in oklab, var(--neg) 10%, transparent)",
            border: "1px solid color-mix(in oklab, var(--neg) 25%, transparent)",
            color: "var(--neg)",
            fontSize: 13,
            lineHeight: 1.5,
          }}
        >
          {state.message}
        </div>
      )}

      {state.kind === "ready" && <PrediksjonsVisning data={state.data} />}
    </section>
  );
}

// Normalised row shape — lets the same JSX render both mock and live rows
// without branching in the table/card markup.
type BillRow = {
  key: string;
  routeId: string;
  reference: string;
  title: string;
  category: string;
  committeeShort: string;
  date: string;
  status: string | null;
  stage: number;
};

function formatDate(epochMs: number): string {
  if (!epochMs) return "";
  const d = new Date(epochMs);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

function mockRow(b: (typeof BILLS)[number]): BillRow {
  return {
    key: b.id,
    routeId: b.id,
    reference: b.id,
    title: b.title,
    category: b.category,
    committeeShort: committeeById(b.committee).short,
    date: b.date,
    status: b.status,
    stage: b.stage,
  };
}

function liveRow(b: MergedBill): BillRow {
  return {
    key: b.id,
    routeId: b.id,
    // The human-facing `Prop. X S (YYYY-YYYY)` citation; fall back to the
    // numeric id if upstream ever omits it.
    reference: b.reference || b.id,
    title: b.shortTitle,
    category: b.typeLabel ?? "",
    committeeShort: b.committeeId,
    date: formatDate(b.updatedAt),
    // Status codes aren't labeled yet (see merge.ts). Pass null so the chip
    // is skipped entirely rather than fabricating a label.
    status: b.statusLabel,
    stage: 0,
  };
}

function BillsInner({
  onNav,
  layoutVariant,
}: {
  onNav: Nav;
  layoutVariant: "table" | "cards";
}) {
  const [query, setQuery] = React.useState("");
  const [cat, setCat] = React.useState("alle");
  const [status, setStatus] = React.useState("alle");
  const [view, setView] = React.useState<"table" | "cards">(layoutVariant);

  const live = useApiResource<MergedBill[], MergedBillsEnvelope["meta"]>(
    "/api/stortinget/bills/full",
  );
  const isLive = live.status === "ready";
  const rows: BillRow[] = isLive ? live.data.map(liveRow) : BILLS.map(mockRow);

  const filtered = rows.filter((b) => {
    const q = query.toLowerCase();
    if (
      query &&
      !(b.title.toLowerCase().includes(q) || b.reference.toLowerCase().includes(q))
    )
      return false;
    if (cat !== "alle" && b.category !== cat) return false;
    if (status !== "alle" && b.status !== status) return false;
    return true;
  });

  const cats = [
    "alle",
    ...Array.from(new Set(rows.map((b) => b.category).filter(Boolean))),
  ];
  // Only offer status filters that actually appear in the current dataset;
  // live rows have status=null, so the select collapses to just "alle" until
  // we have a reliable status mapping.
  const statuses = [
    "alle",
    ...Array.from(new Set(rows.map((b) => b.status).filter((s): s is string => !!s))),
  ];

  const sourceLabel = isLive ? `live · ${live.meta.source}` : "mock";

  return (
    <Page
      eyebrow={`${rows.length} saker i sesjonen · ${sourceLabel}`}
      title="Saker"
      subtitle="Proposisjoner, innstillinger og representantforslag under behandling eller ferdigbehandlet i inneværende sesjon."
    >
      <div
        className="card"
        style={{
          padding: 16,
          display: "grid",
          gridTemplateColumns: "1fr auto auto auto",
          gap: 10,
          marginBottom: 20,
          alignItems: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "0 12px",
            height: 36,
            background: "var(--bg-elev)",
            borderRadius: 6,
            border: "1px solid var(--border)",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ color: "var(--fg-dim)" }}>
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" />
            <path d="M9.5 9.5L12 12" stroke="currentColor" strokeLinecap="round" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Søk i saker, ID, nøkkelord…"
            style={{
              flex: 1,
              background: "transparent",
              border: 0,
              outline: "none",
              color: "var(--fg)",
              fontSize: 14,
              fontFamily: "inherit",
            }}
          />
        </div>
        <select
          value={cat}
          onChange={(e) => setCat(e.target.value)}
          className="btn"
          style={{ height: 36, padding: "0 10px" }}
        >
          {cats.map((c) => (
            <option key={c} value={c}>
              {c === "alle" ? "Alle kategorier" : c}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="btn"
          style={{ height: 36, padding: "0 10px" }}
        >
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s === "alle" ? "Alle statuser" : s}
            </option>
          ))}
        </select>
        <div
          style={{
            display: "flex",
            background: "var(--bg-elev)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: 2,
            height: 36,
          }}
        >
          {(["table", "cards"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                padding: "0 12px",
                border: 0,
                cursor: "pointer",
                background: view === v ? "var(--bg)" : "transparent",
                color: view === v ? "var(--fg)" : "var(--fg-dim)",
                borderRadius: 4,
                fontSize: 12,
                fontFamily: "var(--font-mono)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              {v === "table" ? "Tabell" : "Kort"}
            </button>
          ))}
        </div>
      </div>

      {view === "table" ? (
        <div className="card" style={{ overflow: "hidden" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "130px minmax(0, 1fr) 140px 110px",
              padding: "10px 20px",
              gap: 16,
              borderBottom: "1px solid var(--border)",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--fg-dim)",
            }}
          >
            <div>Sak-ID</div>
            <div>Tittel</div>
            <div>Status</div>
            <div style={{ textAlign: "right" }}>Dato</div>
          </div>
          {filtered.map((b, i) => (
            <button
              key={b.key}
              onClick={() => onNav("bill", { id: b.routeId })}
              style={{
                display: "grid",
                gridTemplateColumns: "130px minmax(0, 1fr) 140px 110px",
                padding: "14px 20px",
                gap: 16,
                alignItems: "center",
                width: "100%",
                textAlign: "left",
                background: "none",
                border: 0,
                borderTop: i ? "1px solid var(--border)" : "none",
                cursor: "pointer",
                color: "inherit",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elev)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <div className="mono" style={{ fontSize: 12, color: "var(--fg-dim)" }}>
                {b.reference}
              </div>
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 500,
                    lineHeight: 1.35,
                    overflow: "hidden",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                  }}
                >
                  {b.title}
                </div>
                <div style={{ fontSize: 11.5, color: "var(--fg-dim)", marginTop: 3 }}>
                  {[b.category, b.committeeShort].filter(Boolean).join(" · ") || "—"}
                </div>
              </div>
              <div>{b.status ? <StatusChip status={b.status} /> : null}</div>
              <div
                className="mono"
                style={{ fontSize: 11, color: "var(--fg-dim)", textAlign: "right" }}
              >
                {b.date}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: 16,
          }}
        >
          {filtered.map((b) => (
            <button
              key={b.key}
              onClick={() => onNav("bill", { id: b.routeId })}
              className="card"
              style={{
                padding: 20,
                textAlign: "left",
                cursor: "pointer",
                background: "var(--bg)",
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--border-strong)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
              }}
            >
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <span className="mono" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
                  {b.reference}
                </span>
                {b.status ? <StatusChip status={b.status} /> : null}
              </div>
              <h3 style={{ fontSize: 16, lineHeight: 1.3 }}>{b.title}</h3>
              <div style={{ color: "var(--fg-dim)", fontSize: 12.5 }}>
                {b.category}
                {b.committeeShort ? ` · ${b.committeeShort}` : ""}
              </div>
              {b.stage > 0 ? <StageBar stage={b.stage} status={b.status ?? ""} /> : null}
            </button>
          ))}
        </div>
      )}
      {!filtered.length && (
        <div style={{ padding: 60, textAlign: "center", color: "var(--fg-dim)" }}>
          Ingen saker matcher filtrene.
        </div>
      )}
    </Page>
  );
}

export function BillDetail({ onNav, params }: { onNav: Nav; params: Params }) {
  // Per-bill detail endpoint — gives us saksgang, proposers, keywords, and a
  // derived stageNumber. Mock bills use reference strings (e.g. "Prop. 142 L
  // (2025-2026)") as their id, which are not valid Stortinget sak IDs. Skip
  // the API call for those to avoid 502s; they fall back to mock data below.
  const isNumericId = /^\d+$/.test(params.id);
  const detail = useApiResource<MergedBillDetail, MergedBillDetailEnvelope["meta"]>(
    isNumericId ? `/api/stortinget/bills/${encodeURIComponent(params.id)}` : null,
  );
  const liveDetail = detail.status === "ready" ? detail.data : undefined;

  // When live data matches, we adopt those fields; otherwise we stay on the
  // mock record (keyed by the mock's string id). The AI summary and expected
  // vote split remain mock and are badged "foreløpig" so readers know.
  const mockBill = billById(params.id) ?? BILLS[0];
  const bill = mockBill;
  const isLive = !!liveDetail;

  const displayReference = liveDetail ? liveDetail.reference || liveDetail.id : bill.id;
  const displayTitle = liveDetail ? liveDetail.shortTitle : bill.title;
  const displayCategory = liveDetail ? liveDetail.typeLabel ?? "" : bill.category;
  const displayCommitteeName = liveDetail ? liveDetail.committeeName : committeeById(bill.committee).name;
  const displayUpdated = liveDetail
    ? formatDate(liveDetail.updatedAt)
    : bill.date;
  const committee = committeeById(bill.committee);
  const vote = RECENT_VOTES.find((v) => v.bill === bill.id);

  const expected = bill.expectedSupport;
  const supportParty = (id: string) => {
    if (expected.for.includes(id)) return "for";
    if (expected.against.includes(id)) return "mot";
    if (expected.split.includes(id)) return "split";
    return "ukjent";
  };

  // Mock timeline — only used when we're showing a mock bill.
  const mockTimeline = [
    { date: bill.date, label: "Fremmet", desc: `Fremmet av ${bill.proposer}`, future: false },
    { date: "2026-03-05", label: "Til komité", desc: `Henvist ${committee.name}`, future: false },
    { date: "2026-03-22", label: "Høring", desc: "14 høringsinstanser", future: false },
    { date: "2026-04-08", label: "Komitéinnstilling", desc: "Flertall / mindretall avgitt", future: false },
    {
      date: bill.stage >= 3 ? "2026-04-20" : null,
      label: "Votering",
      desc: "Plenum",
      future: bill.stage < 4,
    },
  ].filter((t) => t.date) as { date: string; label: string; desc: string; future: boolean }[];

  // Live timeline derived from the saksgang steps. Each active step becomes one
  // entry; its date is the latest dated event within that step. Steps with no
  // dated events are shown as upcoming (future: true).
  const liveTimeline = liveDetail
    ? liveDetail.saksgang.steps
        .filter((s) => !s.uaktuell)
        .map((s) => {
          const datedEvents = s.events.filter((e) => e.date !== null);
          const latestDate = datedEvents.reduce<number | null>(
            (best, e) => (e.date !== null && (best === null || e.date > best) ? e.date : best),
            null,
          );
          const desc = datedEvents.map((e) => e.label).join(" · ");
          return {
            date: latestDate ? formatDate(latestDate) : null,
            label: s.name,
            desc,
            future: datedEvents.length === 0,
          };
        })
    : null;

  const timeline = isLive ? liveTimeline! : mockTimeline;

  return (
    <Page
      crumb={[{ label: "Saker", to: "bills" }, { label: displayReference }]}
      onNav={onNav}
    >
      <div style={{ marginBottom: 28 }}>
        <div
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            marginBottom: 16,
            flexWrap: "wrap",
          }}
        >
          <span className="mono" style={{ fontSize: 12, color: "var(--fg-dim)" }}>
            {displayReference}
          </span>
          {isLive
            ? liveDetail!.statusLabel
              ? <StatusChip status={liveDetail!.statusLabel} />
              : null
            : <StatusChip status={bill.status} />}
          {displayCategory ? <span className="chip">{displayCategory}</span> : null}
          {displayCommitteeName ? <span className="chip">{displayCommitteeName}</span> : null}
          {isLive && liveDetail!.keywords.slice(0, 4).map((kw) => (
            <span key={kw} className="chip" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
              {kw}
            </span>
          ))}
        </div>
        <h1 className="display" style={{ fontSize: 44, lineHeight: 1.05, maxWidth: 1000 }}>
          {displayTitle}
        </h1>
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <div className="eyebrow" style={{ marginBottom: 16 }}>
          Saksgang
        </div>
        <StageBar
          stage={isLive ? liveDetail!.stageNumber : bill.stage}
          status={isLive ? (liveDetail!.statusLabel ?? "") : bill.status}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {isLive ? (
            <>
              <AnalysePanel sakId={liveDetail!.id} />
              <PrediksjonsPanel sakId={liveDetail!.id} />
            </>
          ) : (
            <section className="card" style={{ padding: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 4,
                    background: "var(--fg)",
                    color: "var(--bg)",
                    display: "grid",
                    placeItems: "center",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                  }}
                >
                  A
                </span>
                <div className="eyebrow">AI-sammendrag</div>
                <PreliminaryBadge />
              </div>
              <p
                style={{
                  fontSize: 15.5,
                  lineHeight: 1.65,
                  color: "var(--fg)",
                  margin: 0,
                  fontFamily: "var(--font-display)",
                  fontWeight: 400,
                }}
              >
                {bill.aiSummary}
              </p>
              <hr style={{ margin: "18px 0" }} />
              <div className="eyebrow" style={{ marginBottom: 10 }}>
                Hovedpunkter
              </div>
              <ul
                style={{
                  margin: 0,
                  padding: 0,
                  listStyle: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                }}
              >
                {bill.aiKeyPoints.map((k, i) => (
                  <li key={i} style={{ display: "flex", gap: 10, fontSize: 14 }}>
                    <span className="mono" style={{ color: "var(--fg-faint)", minWidth: 24 }}>
                      0{i + 1}
                    </span>
                    <span style={{ color: "var(--fg-muted)" }}>{k}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {!isLive && <section className="card" style={{ padding: 24 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 4,
              }}
            >
              <div className="eyebrow">
                {vote ? "Avstemningsresultat" : "Forventet stemmegivning"}
              </div>
              <PreliminaryBadge />
            </div>
            <h3 style={{ fontSize: 18, marginBottom: 16 }}>
              {vote
                ? `${vote.tally.for} for · ${vote.tally.against} mot`
                : "Basert på komitéinnstilling og tidligere votering"}
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 16,
              }}
            >
              {([
                ["for", "Støtter", "var(--pos)"],
                ["split", "Splittet", "var(--warn)"],
                ["mot", "Går mot", "var(--neg)"],
              ] as const).map(([key, label, color]) => {
                const parties = PARTIES.filter((p) => supportParty(p.id) === key);
                const seats = parties.reduce((s, p) => s + p.seats, 0);
                return (
                  <div
                    key={key}
                    style={{ background: "var(--bg-elev)", padding: 16, borderRadius: 8 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: 10,
                      }}
                    >
                      <div className="eyebrow" style={{ color }}>
                        {label}
                      </div>
                      <div className="mono num" style={{ color: "var(--fg-dim)" }}>
                        {seats} mand.
                      </div>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {parties.map((p) => (
                        <PartyTag key={p.id} id={p.id} />
                      ))}
                      {!parties.length && (
                        <span style={{ color: "var(--fg-faint)", fontSize: 12 }}>—</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>}

          {isLive && liveDetail!.proposers.length > 0 && (
            <section className="card" style={{ padding: 24 }}>
              <div className="eyebrow" style={{ marginBottom: 14 }}>Forslagsstillere</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {liveDetail!.proposers.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 0",
                      borderTop: "1px solid var(--border)",
                      fontSize: 13,
                    }}
                  >
                    <span>{p.name}</span>
                    {p.partyName && (
                      <span
                        style={{
                          fontSize: 11,
                          color: "var(--fg-dim)",
                          fontFamily: "var(--font-mono)",
                        }}
                      >
                        {p.partyName}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section className="card" style={{ padding: 20 }}>
            <div className="eyebrow" style={{ marginBottom: 10 }}>
              Metadata
            </div>
            {(isLive
              ? [
                  ["Henvisning", displayReference],
                  ["Type", displayCategory || "—"],
                  ["Komité", displayCommitteeName || "—"],
                  ["Sist oppdatert", displayUpdated],
                  ["Sesjon", liveDetail!.sessionId ?? "—"],
                  ["Sak nr.", liveDetail!.sakNumber != null ? String(liveDetail!.sakNumber) : "—"],
                  ["Status (kode)", String(liveDetail!.statusCode)],
                  ["Ferdigbehandlet", liveDetail!.ferdigbehandlet ? "Ja" : "Nei"],
                ]
              : [
                  ["Saks-ID", bill.id],
                  ["Fremmet av", bill.proposer],
                  ["Dato fremmet", bill.date],
                  ["Komité", committee.name],
                  ["Kategori", bill.category],
                  ["Debatter", `${bill.debates} holdt`],
                  ["Endringer", `${bill.amendments} forslag`],
                ]
            ).map(([k, v]) => (
              <div
                key={k}
                style={{
                  display: "grid",
                  gridTemplateColumns: "110px 1fr",
                  gap: 10,
                  padding: "8px 0",
                  borderTop: "1px solid var(--border)",
                  fontSize: 13,
                }}
              >
                <div style={{ color: "var(--fg-dim)" }}>{k}</div>
                <div>{v}</div>
              </div>
            ))}
          </section>

          <section className="card" style={{ padding: 20 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 14,
              }}
            >
              <div className="eyebrow">Tidslinje</div>
              {!isLive && <PreliminaryBadge />}
            </div>
            <div style={{ position: "relative", paddingLeft: 18 }}>
              <div
                style={{
                  position: "absolute",
                  left: 5,
                  top: 4,
                  bottom: 4,
                  width: 1,
                  background: "var(--border)",
                }}
              />
              {timeline.map((t, i) => (
                <div key={i} style={{ marginBottom: 14, position: "relative" }}>
                  <div
                    style={{
                      position: "absolute",
                      left: -18,
                      top: 5,
                      width: 11,
                      height: 11,
                      borderRadius: "50%",
                      background: t.future ? "var(--bg)" : "var(--fg)",
                      border: `2px solid ${t.future ? "var(--border-strong)" : "var(--fg)"}`,
                    }}
                  />
                  <div
                    className="mono"
                    style={{
                      fontSize: 10.5,
                      color: "var(--fg-dim)",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    {t.date ?? "Planlagt"}
                  </div>
                  <div style={{ fontSize: 13.5, fontWeight: 500 }}>{t.label}</div>
                  {t.desc && (
                    <div style={{ fontSize: 12.5, color: "var(--fg-dim)" }}>{t.desc}</div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {isLive && liveDetail!.keywords.length > 0 && (
            <section className="card" style={{ padding: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 12 }}>Stikkord</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {liveDetail!.keywords.map((kw) => (
                  <span key={kw} className="chip" style={{ fontSize: 12 }}>
                    {kw}
                  </span>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </Page>
  );
}
