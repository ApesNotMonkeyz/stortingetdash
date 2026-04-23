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
import { useApiResource } from "@/lib/stortinget/client";
import type {
  MergedParty,
  MergedPartiesEnvelope,
  MergedRepresentative,
  MergedRepsEnvelope,
} from "@/lib/stortinget/types";

export function Parties({ onNav }: { onNav: Nav }) {
  const live = useApiResource<MergedParty[], MergedPartiesEnvelope["meta"]>(
    "/api/stortinget/parties/full",
  );
  // Serve mock during loading/error so the page never flashes empty. Once
  // merged data arrives we swap in live seat counts. MergedParty is
  // structurally compatible with Party, so downstream components need no
  // changes.
  const parties: Party[] = live.status === "ready"
    ? live.data.filter((p) => p.seats > 0)
    : PARTIES;
  const sorted = [...parties].sort((a, b) => b.seats - a.seats);
  const total = parties.reduce((s, p) => s + p.seats, 0);
  const sourceLabel =
    live.status === "ready"
      ? `live · ${live.meta.sources.parties}/${live.meta.sources.representatives}`
      : live.status === "loading"
        ? "laster …"
        : "mock";

  return (
    <Page
      eyebrow={`${parties.length} partier · ${total} mandater · ${sourceLabel}`}
      title="Partier"
      subtitle="Alle partier representert i Stortinget. Mandatfordeling, ledere og ideologisk posisjonering."
    >
      <div className="card" style={{ padding: 24, marginBottom: 24 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 16,
          }}
        >
          <div>
            <div className="eyebrow">Parlamentssammensetning</div>
            <h3 style={{ fontSize: 18, marginTop: 4 }}>{total} mandater · fra v. R → FrP</h3>
          </div>
          <div className="mono" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
            {sourceLabel}
          </div>
        </div>
        <Hemicycle parties={parties} size="lg" />
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "6px 16px",
            marginTop: 14,
            justifyContent: "center",
          }}
        >
          {sorted.map((p) => (
            <button
              key={p.id}
              onClick={() => onNav("party", { id: p.id })}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: "none",
                border: 0,
                cursor: "pointer",
                color: "inherit",
                fontSize: 12,
                padding: "2px 4px",
                borderRadius: 4,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elev)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <span
                style={{ width: 8, height: 8, borderRadius: "50%", background: p.color, flexShrink: 0 }}
              />
              <span style={{ fontFamily: "var(--font-mono)", color: "var(--fg-muted)" }}>
                {p.short}
              </span>
              <span className="mono num" style={{ color: "var(--fg-dim)" }}>{p.seats}</span>
            </button>
          ))}
        </div>
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


export function PartyDetail({ onNav, params }: { onNav: Nav; params: Params }) {
  const liveParties = useApiResource<MergedParty[], MergedPartiesEnvelope["meta"]>(
    "/api/stortinget/parties/full",
  );
  const liveReps = useApiResource<MergedRepresentative[], MergedRepsEnvelope["meta"]>(
    "/api/stortinget/representatives/full",
  );

  const mockParty = partyById(params.id);
  const liveParty = liveParties.status === "ready"
    ? liveParties.data.find((p) => p.id === params.id)
    : undefined;
  const p: Party = liveParty ?? mockParty;

  const agreement = AGREEMENT_SERIES[p.id] ?? [];
  const lastAgreement = agreement[agreement.length - 1];

  const partyReps: MergedRepresentative[] =
    liveReps.status === "ready"
      ? liveReps.data.filter((r) => r.party === params.id)
      : [];
  const isLiveReps = liveReps.status === "ready";

  // Committee breakdown — count seats per committee across all party reps.
  const committeeMap = new Map<string, number>();
  for (const rep of partyReps) {
    for (const c of rep.committeeNames) {
      committeeMap.set(c, (committeeMap.get(c) ?? 0) + 1);
    }
  }
  const committeeBreakdown = [...committeeMap.entries()].sort((a, b) => b[1] - a[1]);

  // Demographics from live data. kjoenn: 1=mann, 2=kvinne (ISO 5218).
  const currentYear = new Date().getFullYear();
  const femaleCount = partyReps.filter((r) => r.gender === 2).length;
  const genderTotal = partyReps.filter((r) => r.gender != null).length;
  const femaleShare = genderTotal > 0 ? femaleCount / genderTotal : null;
  const bornYears = partyReps.map((r) => r.born).filter((y) => Number.isFinite(y));
  const avgAge =
    bornYears.length > 0
      ? Math.round(bornYears.reduce((s, y) => s + (currentYear - y), 0) / bornYears.length)
      : null;
  const varaCount = partyReps.filter((r) => r.isVara).length;

  // Stat row — use live values when available, mock otherwise.
  const mockReps = REPRESENTATIVES.filter((r) => r.party === p.id);
  const statRows: [string, string | number][] = isLiveReps
    ? [
        ["Representanter (fast)", partyReps.filter((r) => !r.isVara).length],
        ["Vara", varaCount],
        ["Gjennomsnittsalder", avgAge != null ? `${avgAge} år` : "—"],
        ["Kvinneandel", femaleShare != null ? `${(femaleShare * 100).toFixed(0)}%` : "—"],
      ]
    : [
        ["Representanter", mockReps.length],
        [
          "Enighet m/ reg.",
          lastAgreement != null ? (lastAgreement * 100).toFixed(0) + "%" : "—",
        ],
        ["Komitéledere", mockReps.filter((r) => r.role.includes("leder")).length],
        ["Kvinneandel", "47%"],
      ];

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
        {statRows.map(([k, v], i) => (
          <div key={i} style={{ background: "var(--bg)", padding: "16px 20px" }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>{k}</div>
            <div className="display num" style={{ fontSize: 32 }}>{v}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section className="card" style={{ padding: 24 }}>
            <div className="eyebrow" style={{ marginBottom: 14 }}>
              Posisjon i salen
            </div>
            <Hemicycle
              parties={
                liveParties.status === "ready"
                  ? liveParties.data.filter((q) => q.seats > 0)
                  : PARTIES
              }
              highlightId={p.id}
              size="md"
            />
          </section>

          {isLiveReps && committeeBreakdown.length > 0 && (
            <section className="card" style={{ overflow: "hidden" }}>
              <header style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
                <div className="eyebrow">Komitérepresentasjon</div>
                <h3 style={{ fontSize: 16, marginTop: 4 }}>
                  {committeeBreakdown.length} komiteer
                </h3>
              </header>
              {committeeBreakdown.map(([name, count], i) => (
                <div
                  key={name}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr auto",
                    padding: "10px 20px",
                    gap: 12,
                    borderTop: i ? "1px solid var(--border)" : "none",
                    alignItems: "center",
                    fontSize: 13,
                  }}
                >
                  <span>{name}</span>
                  <span
                    className="mono"
                    style={{
                      fontSize: 12,
                      color: "var(--fg-dim)",
                      background: "var(--bg-elev)",
                      padding: "2px 8px",
                      borderRadius: 4,
                    }}
                  >
                    {count} pl.
                  </span>
                </div>
              ))}
            </section>
          )}

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
              {isLiveReps ? partyReps.length : mockReps.length} fra {p.short}
              {!isLiveReps && <span style={{ color: "var(--fg-dim)", fontWeight: 400 }}> · mock</span>}
            </h3>
          </header>
          {(isLiveReps ? partyReps : mockReps).map((r, i) => (
            <button
              key={r.id}
              onClick={() => onNav("rep", { id: r.id })}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto",
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
              {!isLiveReps && (
                <div className="mono num" style={{ fontSize: 12, color: "var(--fg-dim)", textAlign: "right" }}>
                  {((r as typeof mockReps[number]).voteShare * 100).toFixed(0)}%
                </div>
              )}
            </button>
          ))}
          {isLiveReps && !partyReps.length && (
            <div style={{ padding: 20, color: "var(--fg-dim)", fontSize: 13 }}>
              Ingen representanter funnet.
            </div>
          )}
        </section>
      </div>
    </Page>
  );
}
