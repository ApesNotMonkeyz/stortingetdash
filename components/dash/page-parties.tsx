"use client";

import React from "react";
import {
  PARTIES,
  REPRESENTATIVES,
  AGREEMENT_SERIES,
  partyById,
  type Party,
} from "./data";
import { Page, Hemicycle, MultiLine, type Nav, type Params } from "./components";

export function Parties({ onNav }: { onNav: Nav }) {
  const sorted = [...PARTIES].sort((a, b) => b.seats - a.seats);
  const total = PARTIES.reduce((s, p) => s + p.seats, 0);

  return (
    <Page
      eyebrow={`${PARTIES.length} partier · ${total} mandater`}
      title="Partier"
      subtitle="Alle partier representert i Stortinget. Mandatfordeling, ledere og ideologisk posisjonering."
    >
      <div className="card" style={{ padding: 24, marginBottom: 24 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 12,
          }}
        >
          <div>
            <div className="eyebrow">Politisk kompass</div>
            <h3 style={{ fontSize: 18, marginTop: 4 }}>Økonomisk vs. sosial posisjon</h3>
          </div>
          <div className="mono" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
            basert på voteringsmønstre
          </div>
        </div>
        <Compass parties={PARTIES} onNav={onNav} />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
          gap: 16,
        }}
      >
        {sorted.map((p) => (
          <button
            key={p.id}
            onClick={() => onNav("party", { id: p.id })}
            className="card"
            style={{
              padding: 0,
              textAlign: "left",
              cursor: "pointer",
              background: "var(--bg)",
              overflow: "hidden",
              borderColor: "var(--border)",
            }}
          >
            <div style={{ height: 6, background: p.color }} />
            <div style={{ padding: 20 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  marginBottom: 14,
                }}
              >
                <div>
                  <div
                    className="mono"
                    style={{
                      fontSize: 11,
                      color: "var(--fg-dim)",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    {p.short}
                  </div>
                  <h3 style={{ fontSize: 18, marginTop: 4, lineHeight: 1.2 }}>{p.name}</h3>
                </div>
                <div className="display num" style={{ fontSize: 36, color: p.color }}>
                  {p.seats}
                </div>
              </div>
              <div style={{ fontSize: 13, color: "var(--fg-muted)", marginBottom: 12 }}>
                {p.leader}
              </div>
              <div
                style={{
                  height: 4,
                  background: "var(--bg-sunk)",
                  borderRadius: 2,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: (p.seats / total) * 100 + "%",
                    background: p.color,
                  }}
                />
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginTop: 6,
                  fontFamily: "var(--font-mono)",
                  fontSize: 10.5,
                  color: "var(--fg-faint)",
                }}
              >
                <span>{((p.seats / total) * 100).toFixed(1)}% av mandater</span>
                <span>{p.side}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </Page>
  );
}

function Compass({ parties, onNav }: { parties: Party[]; onNav: Nav }) {
  const W = 900,
    H = 400;
  const pad = 48;
  const toX = (v: number) => pad + ((v + 1) / 2) * (W - pad * 2);
  const toY = (v: number) => pad + (1 - (v + 1) / 2) * (H - pad * 2);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block" }}>
      <line x1={pad} y1={H / 2} x2={W - pad} y2={H / 2} stroke="var(--border)" />
      <line x1={W / 2} y1={pad} x2={W / 2} y2={H - pad} stroke="var(--border)" />
      {[-0.5, 0.5].map((v) => (
        <g key={v}>
          <line x1={toX(v)} y1={pad} x2={toX(v)} y2={H - pad} stroke="var(--border)" strokeDasharray="2,4" />
          <line x1={pad} y1={toY(v)} x2={W - pad} y2={toY(v)} stroke="var(--border)" strokeDasharray="2,4" />
        </g>
      ))}
      <text x={pad} y={H / 2 - 10} fontSize="10.5" fill="var(--fg-dim)" fontFamily="var(--font-mono)">
        ← venstre
      </text>
      <text
        x={W - pad}
        y={H / 2 - 10}
        fontSize="10.5"
        fill="var(--fg-dim)"
        fontFamily="var(--font-mono)"
        textAnchor="end"
      >
        høyre →
      </text>
      <text x={W / 2 + 8} y={pad + 12} fontSize="10.5" fill="var(--fg-dim)" fontFamily="var(--font-mono)">
        ↑ liberal
      </text>
      <text x={W / 2 + 8} y={H - pad - 4} fontSize="10.5" fill="var(--fg-dim)" fontFamily="var(--font-mono)">
        ↓ konservativ
      </text>
      {parties.map((p) => {
        const r = 8 + Math.sqrt(p.seats) * 2.5;
        return (
          <g key={p.id} onClick={() => onNav("party", { id: p.id })} style={{ cursor: "pointer" }}>
            <circle cx={toX(p.position.econ)} cy={toY(p.position.social)} r={r} fill={p.color} opacity="0.85" />
            <text
              x={toX(p.position.econ)}
              y={toY(p.position.social) + 3}
              fontSize="10"
              fontFamily="var(--font-mono)"
              fontWeight="600"
              fill="white"
              textAnchor="middle"
              style={{ pointerEvents: "none" }}
            >
              {p.short}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function PartyDetail({ onNav, params }: { onNav: Nav; params: Params }) {
  const p = partyById(params.id);
  const reps = REPRESENTATIVES.filter((r) => r.party === p.id);
  const agreement = AGREEMENT_SERIES[p.id] ?? [];
  const lastAgreement = agreement[agreement.length - 1];

  return (
    <Page
      crumb={[{ label: "Partier", to: "parties" }, { label: p.short }]}
      onNav={onNav}
    >
      <div
        style={{
          position: "relative",
          background: `color-mix(in oklab, ${p.color} 8%, var(--bg))`,
          border: `1px solid color-mix(in oklab, ${p.color} 20%, var(--border))`,
          borderRadius: 12,
          padding: "36px 36px 32px",
          marginBottom: 24,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(180deg, ${p.color}08, transparent 60%)`,
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto",
            gap: 32,
            alignItems: "center",
            position: "relative",
          }}
        >
          <div>
            <div
              className="mono"
              style={{
                fontSize: 11,
                color: p.color,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                fontWeight: 600,
                marginBottom: 10,
              }}
            >
              {p.short}
            </div>
            <h1 className="display" style={{ fontSize: 68, lineHeight: 0.95 }}>
              {p.name}
            </h1>
            <p style={{ fontSize: 15, color: "var(--fg-muted)", marginTop: 14 }}>
              Ledet av {p.leader} ·{" "}
              {p.side === "left" ? "venstresiden" : p.side === "right" ? "høyresiden" : "sentrum"}
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="display num" style={{ fontSize: 120, lineHeight: 0.9, color: p.color }}>
              {p.seats}
            </div>
            <div className="eyebrow">Mandater</div>
          </div>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 1,
          background: "var(--border)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          overflow: "hidden",
          marginBottom: 24,
        }}
      >
        {[
          ["Representanter", reps.length],
          [
            "Enighet m/ reg.",
            lastAgreement != null ? (lastAgreement * 100).toFixed(0) + "%" : "—",
          ],
          ["Komitéledere", reps.filter((r) => r.role.includes("leder")).length],
          ["Kvinneandel", "47%"],
        ].map(([k, v], i) => (
          <div key={i} style={{ background: "var(--bg)", padding: "16px 20px" }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>
              {k}
            </div>
            <div className="display num" style={{ fontSize: 32 }}>
              {v}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section className="card" style={{ padding: 24 }}>
            <div className="eyebrow" style={{ marginBottom: 14 }}>
              Posisjon i salen
            </div>
            <Hemicycle parties={PARTIES} highlightId={p.id} size="md" />
          </section>
          {agreement.length > 0 && (
            <section className="card" style={{ padding: 24 }}>
              <div className="eyebrow" style={{ marginBottom: 4 }}>
                Enighet med regjeringen
              </div>
              <h3 style={{ fontSize: 16, marginBottom: 14 }}>12 uker</h3>
              <MultiLine
                series={[{ id: p.id, label: p.short, color: p.color, data: agreement }]}
                height={200}
              />
            </section>
          )}
        </div>

        <section className="card" style={{ overflow: "hidden" }}>
          <header style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
            <div className="eyebrow">Representanter</div>
            <h3 style={{ fontSize: 16, marginTop: 4 }}>
              {reps.length} fra {p.short}
            </h3>
          </header>
          {reps.map((r, i) => (
            <button
              key={r.id}
              onClick={() => onNav("rep", { id: r.id })}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 80px",
                padding: "12px 20px",
                gap: 12,
                width: "100%",
                textAlign: "left",
                background: "none",
                border: 0,
                borderTop: i ? "1px solid var(--border)" : "none",
                cursor: "pointer",
                color: "inherit",
                alignItems: "center",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elev)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{r.name}</div>
                <div style={{ fontSize: 12, color: "var(--fg-dim)" }}>
                  {r.fylke} · {r.role}
                </div>
              </div>
              <div
                className="mono num"
                style={{ fontSize: 12, color: "var(--fg-dim)", textAlign: "right" }}
              >
                {(r.voteShare * 100).toFixed(0)}%
              </div>
            </button>
          ))}
          {!reps.length && (
            <div style={{ padding: 20, color: "var(--fg-dim)", fontSize: 13 }}>
              Ingen representanter i datasettet.
            </div>
          )}
        </section>
      </div>
    </Page>
  );
}
