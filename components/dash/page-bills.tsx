"use client";

import React from "react";
import { BILLS, PARTIES, RECENT_VOTES, billById, committeeById } from "./data";
import { Page, StatusChip, StageBar, PartyTag, type Nav, type Params } from "./components";

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

  const filtered = BILLS.filter((b) => {
    if (
      query &&
      !(b.title.toLowerCase().includes(query.toLowerCase()) ||
        b.id.toLowerCase().includes(query.toLowerCase()))
    )
      return false;
    if (cat !== "alle" && b.category !== cat) return false;
    if (status !== "alle" && b.status !== status) return false;
    return true;
  });

  const cats = ["alle", ...Array.from(new Set(BILLS.map((b) => b.category)))];
  const statuses = ["alle", "Til behandling", "Vedtatt", "Avvist"];

  return (
    <Page
      eyebrow={`${BILLS.length} saker i sesjonen`}
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
              key={b.id}
              onClick={() => onNav("bill", { id: b.id })}
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
                {b.id}
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
                  {b.category} · {committeeById(b.committee).short}
                </div>
              </div>
              <div>
                <StatusChip status={b.status} />
              </div>
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
              key={b.id}
              onClick={() => onNav("bill", { id: b.id })}
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
                  {b.id}
                </span>
                <StatusChip status={b.status} />
              </div>
              <h3 style={{ fontSize: 16, lineHeight: 1.3 }}>{b.title}</h3>
              <div style={{ color: "var(--fg-dim)", fontSize: 12.5 }}>
                {b.category} · {committeeById(b.committee).short}
              </div>
              <StageBar stage={b.stage} status={b.status} />
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
  const bill = billById(params.id) ?? BILLS[0];
  const committee = committeeById(bill.committee);
  const vote = RECENT_VOTES.find((v) => v.bill === bill.id);

  const expected = bill.expectedSupport;
  const supportParty = (id: string) => {
    if (expected.for.includes(id)) return "for";
    if (expected.against.includes(id)) return "mot";
    if (expected.split.includes(id)) return "split";
    return "ukjent";
  };

  const timeline = [
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
  ].filter((t) => t.date);

  return (
    <Page
      crumb={[{ label: "Saker", to: "bills" }, { label: bill.id }]}
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
            {bill.id}
          </span>
          <StatusChip status={bill.status} />
          <span className="chip">{bill.category}</span>
          <span className="chip">{committee.name}</span>
        </div>
        <h1 className="display" style={{ fontSize: 44, lineHeight: 1.05, maxWidth: 1000 }}>
          {bill.title}
        </h1>
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <div className="eyebrow" style={{ marginBottom: 16 }}>
          Saksgang
        </div>
        <StageBar stage={bill.stage} status={bill.status} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
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

          <section className="card" style={{ padding: 24 }}>
            <div className="eyebrow" style={{ marginBottom: 4 }}>
              {vote ? "Avstemningsresultat" : "Forventet stemmegivning"}
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
          </section>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section className="card" style={{ padding: 20 }}>
            <div className="eyebrow" style={{ marginBottom: 10 }}>
              Metadata
            </div>
            {[
              ["Saks-ID", bill.id],
              ["Fremmet av", bill.proposer],
              ["Dato fremmet", bill.date],
              ["Komité", committee.name],
              ["Kategori", bill.category],
              ["Debatter", `${bill.debates} holdt`],
              ["Endringer", `${bill.amendments} forslag`],
            ].map(([k, v]) => (
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
            <div className="eyebrow" style={{ marginBottom: 14 }}>
              Tidslinje
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
                    {t.date}
                  </div>
                  <div style={{ fontSize: 13.5, fontWeight: 500 }}>{t.label}</div>
                  <div style={{ fontSize: 12.5, color: "var(--fg-dim)" }}>{t.desc}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </Page>
  );
}
