"use client";

import React from "react";
import {
  PARTIES,
  RECENT_VOTES,
  AGREEMENT_SERIES,
  COMMITTEES,
  BILLS,
  partyById,
  type Party,
} from "./data";
import { Page, MultiLine, PartyVoteBar, StatusChip } from "./components";

export function Votes() {
  const [focusParty, setFocusParty] = React.useState<string | null>(null);

  const matrix = PARTIES.map((a) =>
    PARTIES.map((b) => {
      if (a.id === b.id) return 1;
      const d = Math.sqrt(
        Math.pow(a.position.econ - b.position.econ, 2) +
          Math.pow(a.position.social - b.position.social, 2)
      );
      return Math.max(0, 1 - d / 2.2);
    })
  );

  return (
    <Page
      eyebrow="Analyse · 2025–2026"
      title="Stemmegivning"
      subtitle="Voteringsmønstre, koalisjonsanalyse og hvem som stemmer sammen."
    >
      <section className="card" style={{ padding: 24, marginBottom: 24 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 16,
          }}
        >
          <div>
            <div className="eyebrow">Enighet med regjeringen</div>
            <h3 style={{ fontSize: 18, marginTop: 4 }}>
              12 ukers rullerende gjennomsnitt · per parti
            </h3>
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {(["SV", "R", "MDG", "V", "KrF", "H", "FrP"] as const).map((id) => {
              const pp = partyById(id);
              return (
                <button
                  key={id}
                  onMouseEnter={() => setFocusParty(id)}
                  onMouseLeave={() => setFocusParty(null)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "4px 8px",
                    borderRadius: 4,
                    background: focusParty === id ? "var(--bg-elev)" : "transparent",
                    border: `1px solid ${
                      focusParty === id ? "var(--border-strong)" : "var(--border)"
                    }`,
                    cursor: "pointer",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  <span className="party-dot" style={{ background: pp.color }} />
                  {pp.short}
                </button>
              );
            })}
          </div>
        </div>
        <MultiLine
          series={(["SV", "R", "MDG", "V", "KrF", "H", "FrP"] as const).map((id) => {
            const pp = partyById(id);
            return { id, label: pp.short, color: pp.color, data: AGREEMENT_SERIES[id] };
          })}
          highlight={focusParty}
          height={320}
          width={1200}
        />
      </section>

      <section className="card" style={{ padding: 24, marginBottom: 24 }}>
        <div className="eyebrow" style={{ marginBottom: 4 }}>
          Enighetsmatrise
        </div>
        <h3 style={{ fontSize: 18, marginBottom: 18 }}>Hvor ofte stemmer partiene sammen</h3>
        <AgreementMatrix matrix={matrix} parties={PARTIES} />
      </section>

      <section className="card" style={{ overflow: "hidden" }}>
        <header style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
          <div className="eyebrow">Siste voteringer</div>
          <h3 style={{ fontSize: 18, marginTop: 4 }}>Partifordeling</h3>
        </header>
        {RECENT_VOTES.map((v, i) => (
          <div
            key={v.id}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 360px 120px",
              padding: "18px 20px",
              gap: 24,
              alignItems: "center",
              borderTop: i ? "1px solid var(--border)" : "none",
            }}
          >
            <div>
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 6 }}>
                <span className="mono" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
                  {v.date} · {v.time}
                </span>
                <StatusChip status={v.result === "vedtatt" ? "Vedtatt" : "Avvist"} />
              </div>
              <div style={{ fontSize: 14, fontWeight: 500 }}>{v.title}</div>
            </div>
            <PartyVoteBar vote={v} height={12} />
            <div style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 12 }}>
              <span style={{ color: "var(--pos)" }}>{v.tally.for}</span>
              <span style={{ color: "var(--fg-faint)", margin: "0 4px" }}>/</span>
              <span style={{ color: "var(--neg)" }}>{v.tally.against}</span>
            </div>
          </div>
        ))}
      </section>
    </Page>
  );
}

function AgreementMatrix({ matrix, parties }: { matrix: number[][]; parties: Party[] }) {
  const size = 44;
  const label = 56;
  const W = label + parties.length * size;
  const H = label + parties.length * size;
  return (
    <div style={{ overflow: "auto" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ display: "block" }}>
        {parties.map((p, i) => (
          <g key={"c" + p.id}>
            <rect x={label + i * size} y={label - 20} width={size} height={3} fill={p.color} />
            <text
              x={label + i * size + size / 2}
              y={label - 8}
              fontSize="11"
              fontFamily="var(--font-mono)"
              textAnchor="middle"
              fill="var(--fg-muted)"
            >
              {p.short}
            </text>
          </g>
        ))}
        {parties.map((p, i) => (
          <g key={"r" + p.id}>
            <rect x={label - 20} y={label + i * size} width={3} height={size} fill={p.color} />
            <text
              x={label - 8}
              y={label + i * size + size / 2 + 4}
              fontSize="11"
              fontFamily="var(--font-mono)"
              textAnchor="end"
              fill="var(--fg-muted)"
            >
              {p.short}
            </text>
          </g>
        ))}
        {matrix.map((row, i) =>
          row.map((v, j) => (
            <g key={i + "-" + j}>
              <rect
                x={label + j * size + 2}
                y={label + i * size + 2}
                width={size - 4}
                height={size - 4}
                rx="3"
                fill="var(--fg)"
                opacity={i === j ? 0.92 : Math.pow(v, 1.6) * 0.85}
              />
              <text
                x={label + j * size + size / 2}
                y={label + i * size + size / 2 + 4}
                fontSize="11"
                fontFamily="var(--font-mono)"
                textAnchor="middle"
                fill={v > 0.45 ? "var(--bg)" : "var(--fg-muted)"}
              >
                {i === j ? "·" : Math.round(v * 100)}
              </text>
            </g>
          ))
        )}
      </svg>
    </div>
  );
}

export function Committees() {
  return (
    <Page
      eyebrow={`${COMMITTEES.length} faste komitéer`}
      title="Komitéer"
      subtitle="Stortingets fagkomitéer behandler saker før de kommer til plenum."
    >
      <div className="card" style={{ overflow: "hidden" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "80px 1fr 200px 100px",
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
          <div>Kode</div>
          <div>Komité</div>
          <div>Leder</div>
          <div style={{ textAlign: "right" }}>Medlemmer</div>
        </div>
        {COMMITTEES.map((c, i) => {
          const bills = BILLS.filter((b) => b.committee === c.id).length;
          return (
            <div
              key={c.id}
              style={{
                display: "grid",
                gridTemplateColumns: "80px 1fr 200px 100px",
                padding: "16px 20px",
                gap: 16,
                alignItems: "center",
                borderTop: i ? "1px solid var(--border)" : "none",
              }}
            >
              <div className="mono" style={{ fontSize: 12, fontWeight: 600, color: "var(--fg)" }}>
                {c.short}
              </div>
              <div>
                <div style={{ fontSize: 14.5, fontWeight: 500 }}>{c.name}</div>
                <div style={{ fontSize: 12, color: "var(--fg-dim)", marginTop: 2 }}>
                  {bills} saker under behandling
                </div>
              </div>
              <div style={{ fontSize: 13, color: "var(--fg-muted)" }}>{c.chair}</div>
              <div style={{ textAlign: "right" }} className="mono num">
                {c.members}
              </div>
            </div>
          );
        })}
      </div>
    </Page>
  );
}
