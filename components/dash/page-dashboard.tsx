"use client";

import React from "react";
import {
  PARTIES,
  BILLS,
  RECENT_VOTES,
  SCHEDULE,
  AGREEMENT_SERIES,
  partyById,
} from "./data";
import {
  Page,
  Sparkline,
  StatusChip,
  StageBar,
  MultiLine,
  PartyVoteBar,
  Hemicycle,
  type Nav,
} from "./components";

export function Dashboard({
  onNav,
  layoutVariant,
}: {
  onNav: Nav;
  layoutVariant: "classic" | "feed";
}) {
  return (
    <Page
      eyebrow="Sesjon 2025–2026 · Uke 16"
      title="Oversikt"
      subtitle="Et overblikk over pågående saker, siste voteringer, og hvordan salen beveger seg."
      actions={
        <>
          <button className="btn">Last ned ukerapport</button>
          <button className="btn primary">Ny analyse</button>
        </>
      }
    >
      {/* KPI strip */}
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
          { k: "Aktive saker", v: "127", trend: [102, 108, 112, 119, 123, 127], note: "+4 denne uken" },
          { k: "Voteringer siste 30 d.", v: "52", trend: [38, 42, 46, 49, 51, 52], note: "3 i dag" },
          { k: "Enstemmige vedtak", v: "61%", trend: [58, 59, 60, 60, 61, 61], note: "↑ 3 pp mot fjor" },
          { k: "Gjennomsnittlig opposisjonsavvik", v: "0.34", trend: [0.41, 0.39, 0.37, 0.36, 0.35, 0.34], note: "Ned fra 0.41" },
        ].map((kpi, i) => (
          <div
            key={i}
            style={{
              background: "var(--bg)",
              padding: "18px 20px",
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            <div className="eyebrow">{kpi.k}</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
              <div className="display num" style={{ fontSize: 38 }}>
                {kpi.v}
              </div>
              <Sparkline data={kpi.trend} width={80} height={28} color="var(--fg-muted)" />
            </div>
            <div style={{ fontSize: 12, color: "var(--fg-dim)" }}>{kpi.note}</div>
          </div>
        ))}
      </div>

      {/* Main split */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: layoutVariant === "feed" ? "1fr 360px" : "1.6fr 1fr",
          gap: 24,
        }}
      >
        {/* Left */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section className="card" style={{ overflow: "hidden" }}>
            <header
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid var(--border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
              }}
            >
              <div>
                <div className="eyebrow">Saker med mest aktivitet</div>
                <h3 style={{ fontSize: 18, marginTop: 6 }}>På dagsorden</h3>
              </div>
              <button
                onClick={() => onNav("bills")}
                style={{
                  background: "none",
                  border: 0,
                  cursor: "pointer",
                  color: "var(--fg-muted)",
                  fontSize: 13,
                }}
              >
                Alle saker →
              </button>
            </header>
            <div>
              {BILLS.slice(0, 5).map((b, i) => (
                <button
                  key={b.id}
                  onClick={() => onNav("bill", { id: b.id })}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "32px minmax(0, 1fr) 130px",
                    columnGap: 16,
                    rowGap: 10,
                    alignItems: "center",
                    padding: "16px 20px",
                    width: "100%",
                    textAlign: "left",
                    background: "none",
                    border: 0,
                    cursor: "pointer",
                    borderTop: i ? "1px solid var(--border)" : "none",
                    color: "inherit",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elev)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <div
                    className="mono"
                    style={{ fontSize: 12, color: "var(--fg-faint)", alignSelf: "start", paddingTop: 2 }}
                  >
                    0{i + 1}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "center",
                        marginBottom: 6,
                        flexWrap: "wrap",
                      }}
                    >
                      <span className="mono" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
                        {b.id}
                      </span>
                      <StatusChip status={b.status} />
                      <span className="chip">{b.category}</span>
                    </div>
                    <div
                      style={{
                        fontSize: 15,
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
                  </div>
                  <div
                    style={{
                      textAlign: "right",
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      color: "var(--fg-dim)",
                      alignSelf: "start",
                      paddingTop: 2,
                    }}
                  >
                    <div>{b.debates} debatter</div>
                    <div>{b.amendments} endr.</div>
                  </div>
                  <div style={{ gridColumn: "2 / -1" }}>
                    <StageBar stage={b.stage} status={b.status} />
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="card" style={{ padding: 24 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 16,
              }}
            >
              <div>
                <div className="eyebrow">Enighet med regjeringen (A + Sp)</div>
                <h3 style={{ fontSize: 18, marginTop: 6 }}>12 ukers rullerende gjennomsnitt</h3>
              </div>
              <button
                onClick={() => onNav("votes")}
                style={{
                  background: "none",
                  border: 0,
                  cursor: "pointer",
                  color: "var(--fg-muted)",
                  fontSize: 13,
                }}
              >
                Full analyse →
              </button>
            </div>
            <MultiLine
              series={(["SV", "R", "MDG", "V", "KrF", "H", "FrP"] as const).map((id) => {
                const p = partyById(id);
                return { id, label: p.short, color: p.color, data: AGREEMENT_SERIES[id] };
              })}
              height={240}
            />
          </section>

          <section className="card" style={{ overflow: "hidden" }}>
            <header style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
              <div className="eyebrow">Siste votering</div>
              <h3 style={{ fontSize: 18, marginTop: 6 }}>{RECENT_VOTES[0].title}</h3>
            </header>
            <div style={{ padding: 20 }}>
              <div style={{ display: "flex", gap: 12, marginBottom: 12, alignItems: "center" }}>
                <span className="mono" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
                  {RECENT_VOTES[0].date} · {RECENT_VOTES[0].time}
                </span>
                <StatusChip status={RECENT_VOTES[0].result === "vedtatt" ? "Vedtatt" : "Avvist"} />
              </div>
              <PartyVoteBar vote={RECENT_VOTES[0]} height={14} showLabels />
              <div
                style={{
                  marginTop: 20,
                  display: "grid",
                  gridTemplateColumns: "repeat(5, 1fr)",
                  gap: 8,
                }}
              >
                {PARTIES.map((p) => {
                  const v = RECENT_VOTES[0].by[p.id];
                  if (!v) return null;
                  return (
                    <div key={p.id} style={{ background: "var(--bg-elev)", borderRadius: 6, padding: "8px 10px" }}>
                      <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 2 }}>
                        <span className="party-dot" style={{ background: p.color }} />
                        <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--fg-muted)" }}>
                          {p.short}
                        </span>
                      </div>
                      <div className="mono num" style={{ fontSize: 13 }}>
                        <span style={{ color: "var(--pos)" }}>{v.for}</span>
                        <span style={{ color: "var(--fg-faint)", margin: "0 3px" }}>·</span>
                        <span style={{ color: "var(--neg)" }}>{v.against}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        </div>

        {/* Right */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section className="card" style={{ padding: 20 }}>
            <div className="eyebrow" style={{ marginBottom: 8 }}>
              Sammensetning · 169 mandater
            </div>
            <Hemicycle parties={PARTIES} size="md" />
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: 6,
                marginTop: 14,
              }}
            >
              {PARTIES.map((p) => (
                <button
                  key={p.id}
                  onClick={() => onNav("party", { id: p.id })}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "4px 6px",
                    background: "none",
                    border: 0,
                    cursor: "pointer",
                    borderRadius: 4,
                    textAlign: "left",
                    color: "inherit",
                    fontSize: 12,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elev)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <span className="party-dot" style={{ background: p.color, width: 10, height: 10 }} />
                  <span style={{ flex: 1 }}>{p.short}</span>
                  <span className="mono num" style={{ color: "var(--fg-dim)" }}>
                    {p.seats}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="card" style={{ padding: 20, background: "var(--bg-elev)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 4,
                  background: "var(--fg)",
                  color: "var(--bg)",
                  display: "grid",
                  placeItems: "center",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                }}
              >
                A
              </span>
              <div className="eyebrow">Ukentlig AI-briefing</div>
              <span className="chip" style={{ marginLeft: "auto", fontSize: 10 }}>
                generert 07:00
              </span>
            </div>
            <h3 style={{ fontSize: 16, marginBottom: 10, lineHeight: 1.3 }}>
              Formuesskatten dominerer — men koalisjonsflanker holder
            </h3>
            <p style={{ fontSize: 13.5, color: "var(--fg-muted)", lineHeight: 1.55, marginBottom: 12 }}>
              Tre tyngre saker kommer til votering denne uken. Prop. 142 L (formuesskatt) ventes å splitte
              opposisjonen. Ap–Sp holder sin flanke mot SV/R, mens Høyre og FrP forhandler om formulering.
              Fastlegegarantien har bred støtte men uklar finansieringsmodell.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                ["Prop. 142 L", "Formuesskatt — ventes vedtatt med A+Sp+V+KrF"],
                ["Prop. 131 L", "Fastlegegaranti — bredt flertall, H/FrP splittet"],
                ["Prop. 138 S", "Klimaplan — dypt splittet komité"],
              ].map(([k, v], i) => (
                <div key={i} style={{ display: "flex", gap: 10, fontSize: 12.5 }}>
                  <span className="mono" style={{ color: "var(--fg-dim)", minWidth: 80 }}>
                    {k}
                  </span>
                  <span style={{ color: "var(--fg-muted)" }}>{v}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="card" style={{ overflow: "hidden" }}>
            <header style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
              <div className="eyebrow">Møteplan</div>
              <h3 style={{ fontSize: 15, marginTop: 4 }}>Denne uken</h3>
            </header>
            <div>
              {SCHEDULE.map((s, i) => (
                <div
                  key={i}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "56px 1fr",
                    gap: 12,
                    padding: "10px 20px",
                    borderTop: i ? "1px solid var(--border)" : "none",
                    alignItems: "flex-start",
                  }}
                >
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-dim)" }}>
                    <div style={{ color: "var(--fg)" }}>
                      {new Date(s.date).toLocaleDateString("nb-NO", { day: "2-digit", month: "short" })}
                    </div>
                    <div>{s.time}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 13, marginBottom: 2 }}>{s.title}</div>
                    <span className="chip" style={{ fontSize: 10 }}>
                      {s.type}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </Page>
  );
}
