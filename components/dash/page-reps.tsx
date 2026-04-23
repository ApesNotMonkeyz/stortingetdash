"use client";

import React from "react";
import {
  REPRESENTATIVES,
  PARTIES,
  RECENT_VOTES,
  partyById,
  committeeById,
  repById,
  type Representative,
} from "./data";
import { Page, PartyTag, type Nav, type Params } from "./components";
import { useApiResource } from "@/lib/stortinget/client";
import type {
  MergedParty,
  MergedPartiesEnvelope,
  MergedRepresentative,
  MergedRepsEnvelope,
} from "@/lib/stortinget/types";

export function Reps({ onNav }: { onNav: Nav }) {
  const [query, setQuery] = React.useState("");
  const [party, setParty] = React.useState("alle");
  const [fylke, setFylke] = React.useState("alle");
  const [sortBy, setSortBy] = React.useState<"name" | "party" | "voteShare">("name");

  const live = useApiResource<MergedRepresentative[], MergedRepsEnvelope["meta"]>(
    "/api/stortinget/representatives/full",
  );
  const reps: Representative[] = live.status === "ready" ? live.data : REPRESENTATIVES;
  const isLive = live.status === "ready";

  const filtered = reps.filter((r) => {
    if (query && !r.name.toLowerCase().includes(query.toLowerCase())) return false;
    if (party !== "alle" && r.party !== party) return false;
    if (fylke !== "alle" && r.fylke !== fylke) return false;
    return true;
  }).sort((a, b) => {
    if (sortBy === "name") return a.name.localeCompare(b.name, "nb");
    if (sortBy === "party") return a.party.localeCompare(b.party);
    if (sortBy === "voteShare") {
      // NaN-safe: treat missing attendance as lowest so live rows stay together.
      const av = Number.isFinite(a.voteShare) ? a.voteShare : -Infinity;
      const bv = Number.isFinite(b.voteShare) ? b.voteShare : -Infinity;
      return bv - av;
    }
    return 0;
  });

  const fylker = Array.from(new Set(reps.map((r) => r.fylke))).sort();

  const sourceLabel = isLive ? `live · ${live.meta.source}` : "mock";

  return (
    <Page
      eyebrow={`${reps.length} mandater · ${sourceLabel}`}
      title="Representanter"
      subtitle="Alle stortingsrepresentanter i inneværende periode, med komitéverv og aktivitet."
    >
      <div
        className="card"
        style={{
          padding: 16,
          display: "grid",
          gridTemplateColumns: "1fr auto auto auto",
          gap: 10,
          marginBottom: 20,
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
            placeholder="Søk representant…"
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
          value={party}
          onChange={(e) => setParty(e.target.value)}
          className="btn"
          style={{ height: 36 }}
        >
          <option value="alle">Alle partier</option>
          {PARTIES.map((p) => (
            <option key={p.id} value={p.id}>
              {p.short} — {p.name}
            </option>
          ))}
        </select>
        <select
          value={fylke}
          onChange={(e) => setFylke(e.target.value)}
          className="btn"
          style={{ height: 36 }}
        >
          <option value="alle">Alle fylker</option>
          {fylker.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          className="btn"
          style={{ height: 36 }}
        >
          <option value="name">Sorter: navn</option>
          <option value="party">Sorter: parti</option>
          <option value="voteShare">Sorter: oppmøte</option>
        </select>
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.6fr) 90px minmax(0, 1fr) 90px",
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
          <div>Representant</div>
          <div>Parti</div>
          <div>Fylke · Rolle</div>
          <div style={{ textAlign: "right" }}>Oppmøte</div>
        </div>
        {filtered.map((r, i) => {
          const p = partyById(r.party);
          return (
            <button
              key={r.id}
              onClick={() => onNav("rep", { id: r.id })}
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.6fr) 90px minmax(0, 1fr) 90px",
                padding: "12px 20px",
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
              <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 6,
                    flex: "none",
                    background: `color-mix(in oklab, ${p.color} 16%, transparent)`,
                    color: p.color,
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    fontWeight: 600,
                    display: "grid",
                    placeItems: "center",
                    border: `1px solid color-mix(in oklab, ${p.color} 30%, transparent)`,
                  }}
                >
                  {r.name
                    .split(" ")
                    .map((w) => w[0])
                    .slice(0, 2)
                    .join("")}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 500,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {r.name}
                  </div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--fg-faint)" }}>
                    f. {Number.isFinite(r.born) ? r.born : "—"}
                  </div>
                </div>
              </div>
              <div>
                <PartyTag id={r.party} />
              </div>
              <div style={{ fontSize: 13, color: "var(--fg-muted)", minWidth: 0 }}>
                <div
                  style={{
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {r.fylke}
                </div>
                <div
                  style={{
                    fontSize: 11.5,
                    color: "var(--fg-dim)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {r.role}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <span className="mono num" style={{ fontSize: 13 }}>
                  {Number.isFinite(r.voteShare) ? `${(r.voteShare * 100).toFixed(0)}%` : "—"}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </Page>
  );
}

export function RepDetail({ onNav, params }: { onNav: Nav; params: Params }) {
  const liveReps = useApiResource<MergedRepresentative[], MergedRepsEnvelope["meta"]>(
    "/api/stortinget/representatives/full",
  );
  const liveParties = useApiResource<MergedParty[], MergedPartiesEnvelope["meta"]>(
    "/api/stortinget/parties/full",
  );

  // Prefer live data when available — live reps have canonical ids that won't
  // resolve through the mock lookup. Fall back to the mock only to keep the
  // page renderable during the initial loading frame.
  const liveRep =
    liveReps.status === "ready" ? liveReps.data.find((r) => r.id === params.id) : undefined;
  const rep = liveRep ?? repById(params.id) ?? REPRESENTATIVES[0];

  const liveParty =
    liveParties.status === "ready"
      ? liveParties.data.find((p) => p.id === rep.party)
      : undefined;
  const party = liveParty ?? partyById(rep.party);

  // Live reps carry the committee name directly; mock reps reference it by id.
  const committeeName = liveRep ? liveRep.committee : committeeById(rep.committee).name;

  const voteRecord = React.useMemo(
    () =>
      RECENT_VOTES.map((v, i) => {
        const pv = v.by[rep.party];
        const voted = pv && pv.for > pv.against ? "for" : "mot";
        // deterministic (seed by index so it doesn't flip across renders)
        const withParty = (i * 37 + rep.id.length * 7) % 100 > 8;
        return { vote: v, voted: withParty ? voted : voted === "for" ? "mot" : "for", withParty };
      }),
    [rep.id, rep.party]
  );

  return (
    <Page
      crumb={[{ label: "Representanter", to: "reps" }, { label: rep.name }]}
      onNav={onNav}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 320px",
          gap: 48,
          marginBottom: 32,
          alignItems: "flex-start",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
            <PartyTag id={rep.party} size="md" showName />
            <span className="mono" style={{ color: "var(--fg-dim)", fontSize: 12 }}>
              ·
            </span>
            <span style={{ fontSize: 13, color: "var(--fg-muted)" }}>{rep.fylke}</span>
          </div>
          <h1 className="display" style={{ fontSize: 64, lineHeight: 1 }}>
            {rep.name}
          </h1>
          <p style={{ fontSize: 16, color: "var(--fg-muted)", marginTop: 16, maxWidth: 580 }}>
            {rep.role} · {committeeName || "—"}. Representant for {rep.fylke}
            {Number.isFinite(rep.born) ? `, født ${rep.born}` : ""}.
          </p>
        </div>
        <div
          style={{
            aspectRatio: "4/5",
            background: `color-mix(in oklab, ${party.color} 8%, var(--bg-elev))`,
            border: "1px solid var(--border)",
            borderRadius: 10,
            display: "grid",
            placeItems: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 140,
              color: party.color,
              opacity: 0.92,
            }}
          >
            {rep.name
              .split(" ")
              .map((w) => w[0])
              .slice(0, 2)
              .join("")}
          </div>
          <div
            style={{
              position: "absolute",
              bottom: 10,
              left: 12,
              right: 12,
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              color: "var(--fg-faint)",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <span>portrait · {rep.id}</span>
            <span>{Number.isFinite(rep.born) ? rep.born : "—"}</span>
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
          [
            "Oppmøte",
            Number.isFinite(rep.voteShare) ? `${(rep.voteShare * 100).toFixed(0)}%` : "—",
          ],
          ["Stemmer m/parti", "94%"],
          ["Innlegg i sal", "42"],
          ["Forslag fremmet", "8"],
        ].map(([k, v], i) => (
          <div key={i} style={{ background: "var(--bg)", padding: "16px 20px" }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>
              {k}
            </div>
            <div className="display num" style={{ fontSize: 34 }}>
              {v}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 24 }}>
        <section className="card" style={{ overflow: "hidden" }}>
          <header style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
            <div className="eyebrow">Siste voteringer</div>
            <h3 style={{ fontSize: 16, marginTop: 4 }}>
              Hvordan {rep.name.split(" ")[0]} har stemt
            </h3>
          </header>
          {voteRecord.map((r, i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 90px 100px",
                padding: "14px 20px",
                gap: 16,
                alignItems: "center",
                borderTop: i ? "1px solid var(--border)" : "none",
              }}
            >
              <div>
                <div className="mono" style={{ fontSize: 11, color: "var(--fg-dim)" }}>
                  {r.vote.date}
                </div>
                <div style={{ fontSize: 13.5 }}>{r.vote.title}</div>
              </div>
              <div>
                <span
                  className="chip"
                  style={{
                    background:
                      r.voted === "for"
                        ? "color-mix(in oklab, var(--pos) 12%, transparent)"
                        : "color-mix(in oklab, var(--neg) 12%, transparent)",
                    color: r.voted === "for" ? "var(--pos)" : "var(--neg)",
                    borderColor: "transparent",
                  }}
                >
                  {r.voted === "for" ? "For" : "Mot"}
                </span>
              </div>
              <div
                style={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  color: r.withParty ? "var(--fg-faint)" : "var(--warn)",
                  textAlign: "right",
                }}
              >
                {r.withParty ? "m/ parti" : "bryter m/ parti"}
              </div>
            </div>
          ))}
        </section>

        <section className="card" style={{ padding: 20 }}>
          <div className="eyebrow" style={{ marginBottom: 14 }}>
            Profil
          </div>
          {[
            ["Parti", party.name],
            ["Valgkrets", rep.fylke],
            ["Født", Number.isFinite(rep.born) ? rep.born : "—"],
            ["Rolle", rep.role],
            ["Komité", committeeName || "—"],
            ["Periode", "2025–2029"],
            ["Kontor", "A-4/12"],
            ["Rådgivere", "2"],
          ].map(([k, v]) => (
            <div
              key={String(k)}
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
      </div>
    </Page>
  );
}
