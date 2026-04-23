"use client";

import React from "react";
import { PARTIES, partyById, type Party, type Vote } from "./data";

export type RouteName =
  | "home"
  | "bills"
  | "bill"
  | "reps"
  | "rep"
  | "parties"
  | "party"
  | "votes"
  | "committees";

export type Params = Record<string, string>;
export type Nav = (name: RouteName, params?: Params) => void;

export function cls(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

/* ---------- Party tag ---------- */
export function PartyTag({
  id,
  size = "sm",
  showName = false,
}: {
  id: string;
  size?: "sm" | "md";
  showName?: boolean;
}) {
  const p = partyById(id);
  const dot = <span className="party-dot" style={{ background: p.color }} />;
  if (showName) {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          fontSize: size === "md" ? 13 : 12,
        }}
      >
        {dot}
        <span style={{ color: "var(--fg)" }}>{p.short}</span>
        <span style={{ color: "var(--fg-dim)" }}>{p.name}</span>
      </span>
    );
  }
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "2px 7px 2px 6px",
        borderRadius: 4,
        background: `color-mix(in oklab, ${p.color} 12%, transparent)`,
        color: p.color,
        fontFamily: "var(--font-mono)",
        fontSize: size === "md" ? 12 : 11,
        fontWeight: 500,
        letterSpacing: "0.02em",
        border: `1px solid color-mix(in oklab, ${p.color} 25%, transparent)`,
      }}
    >
      {dot}
      {p.short}
    </span>
  );
}

/* ---------- Status chip ---------- */
export function StatusChip({ status }: { status: string }) {
  const map: Record<string, { bg: string; label: string }> = {
    "Til behandling": { bg: "var(--warn)", label: "Til behandling" },
    Vedtatt: { bg: "var(--pos)", label: "Vedtatt" },
    Avvist: { bg: "var(--neg)", label: "Avvist" },
    Trukket: { bg: "var(--fg-dim)", label: "Trukket" },
  };
  const s = map[status] ?? map["Til behandling"];
  return (
    <span
      className="chip"
      style={{
        background: `color-mix(in oklab, ${s.bg} 10%, transparent)`,
        color: s.bg,
        borderColor: `color-mix(in oklab, ${s.bg} 30%, transparent)`,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: s.bg }} />
      {s.label}
    </span>
  );
}

/* ---------- Stage progress ---------- */
export function StageBar({ stage, status }: { stage: number; status: string }) {
  const labels = ["Foreslått", "Komité", "Votering", status === "Avvist" ? "Avvist" : "Vedtatt"];
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {labels.map((l, i) => {
        const active = i + 1 <= stage;
        const current = i + 1 === stage;
        const isEnd = i === 3 && stage === 4;
        const color =
          isEnd && status === "Avvist"
            ? "var(--neg)"
            : isEnd
            ? "var(--pos)"
            : current
            ? "var(--fg)"
            : active
            ? "var(--fg-dim)"
            : "var(--border)";
        return (
          <div key={i} style={{ flex: 1, minWidth: 0 }}>
            <div style={{ height: 3, borderRadius: 2, background: color }} />
            <div
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginTop: 6,
                color: active ? "var(--fg-muted)" : "var(--fg-faint)",
                fontWeight: current ? 600 : 400,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {l}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- Party vote bar ---------- */
export function PartyVoteBar({
  vote,
  height = 10,
  showLabels = false,
}: {
  vote: Vote;
  height?: number;
  showLabels?: boolean;
}) {
  const parties = PARTIES;
  const totalSeats = parties.reduce((s, p) => s + p.seats, 0);
  return (
    <div>
      <div
        style={{
          display: "flex",
          height,
          borderRadius: height / 2,
          overflow: "hidden",
          background: "var(--bg-sunk)",
          border: "1px solid var(--border)",
        }}
      >
        {parties.map((p) => {
          const v = vote.by[p.id];
          if (!v) return null;
          const width = (v.total / totalSeats) * 100;
          const forPct = v.for / v.total;
          return (
            <div
              key={p.id}
              style={{ width: width + "%", display: "flex", borderRight: "1px solid var(--bg)" }}
              title={`${p.short}: ${v.for} for, ${v.against} mot, ${v.absent} ikke avgitt`}
            >
              <div style={{ width: forPct * 100 + "%", background: p.color, opacity: 1 }} />
              <div style={{ flex: 1, background: p.color, opacity: 0.18 }} />
            </div>
          );
        })}
      </div>
      {showLabels && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 8,
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "var(--fg-dim)",
          }}
        >
          <span>
            <span style={{ color: "var(--pos)" }}>■</span> For {vote.tally.for}
          </span>
          <span>
            <span style={{ color: "var(--neg)" }}>■</span> Mot {vote.tally.against}
          </span>
          <span style={{ color: "var(--fg-faint)" }}>Ikke avgitt {vote.tally.absent}</span>
        </div>
      )}
    </div>
  );
}

/* ---------- Hemicycle ---------- */
// Political order left → right. Parties not in this list are appended at the right end.
const HEMICYCLE_ORDER = ["R", "SV", "A", "MDG", "Sp", "V", "KrF", "H", "FrP"];

export function Hemicycle({
  parties,
  highlightId,
  size = "md",
}: {
  parties: Party[];
  highlightId?: string;
  size?: "sm" | "md" | "lg";
}) {
  const total = parties.reduce((s, p) => s + p.seats, 0);
  if (total === 0) return null;

  // Arrange parties left → right by political order, then remaining parties
  const ordered: Party[] = [
    ...HEMICYCLE_ORDER.flatMap((id) => {
      const p = parties.find((q) => q.id === id);
      return p && p.seats > 0 ? [p] : [];
    }),
    ...parties.filter((p) => !HEMICYCLE_ORDER.includes(p.id) && p.seats > 0),
  ];

  // Build cumulative position slices in [0, 1]: each party occupies a fraction
  // proportional to its seat count, left (0) → right (1).
  const slices: { id: string; color: string; end: number }[] = [];
  let cum = 0;
  for (const p of ordered) {
    cum += p.seats / total;
    slices.push({ id: p.id, color: p.color, end: cum });
  }
  // Map political position t ∈ [0,1] to party
  const partyAt = (t: number) => {
    for (const s of slices) if (t <= s.end) return s;
    return slices[slices.length - 1];
  };

  // SVG geometry — semi-circle, cx/cy at the flat bottom edge
  const W = size === "lg" ? 640 : size === "sm" ? 320 : 480;
  const H = Math.round(W * 0.52);
  const cx = W / 2;
  // cy sits slightly below H so endpoint dots (at angle π and 0) aren't clipped
  const cy = H + 4;

  // 8 rows; outer/inner radius ratio ≈ 33/8 so the innermost row holds ~8 seats
  // and the outermost ~33 for Stortinget's 169 mandates.
  const ROWS = 8;
  const rMax = H * 0.92;
  const rMin = rMax * (8 / 33);

  const radii = Array.from({ length: ROWS }, (_, i) =>
    rMin + (rMax - rMin) * (i / (ROWS - 1)),
  );
  const radiiSum = radii.reduce((s, r) => s + r, 0);

  // Seat count per row proportional to arc length (radius)
  let rowCounts = radii.map((r) => Math.floor((total * r) / radiiSum));
  // Distribute any remainder to rows with the highest fractional residuals
  const residuals = radii
    .map((r, i) => ({ i, f: (total * r) / radiiSum - rowCounts[i] }))
    .sort((a, b) => b.f - a.f);
  let rem = total - rowCounts.reduce((s, n) => s + n, 0);
  for (let j = 0; rem > 0; j++, rem--) rowCounts[residuals[j].i]++;

  // Place seats for each row
  const placed: { x: number; y: number; id: string; color: string }[] = [];
  for (let r = 0; r < ROWS; r++) {
    const n = rowCounts[r];
    if (n === 0) continue;
    const radius = radii[r];
    for (let i = 0; i < n; i++) {
      const t = n > 1 ? i / (n - 1) : 0.5;
      const party = partyAt(t);
      // angle goes from π (left) to 0 (right) as t goes 0 → 1
      const angle = Math.PI * (1 - t);
      placed.push({
        x: cx + radius * Math.cos(angle),
        y: cy - radius * Math.sin(angle),
        id: party.id,
        color: party.color,
      });
    }
  }

  const dotR = size === "sm" ? 3 : 4;

  return (
    <svg
      viewBox={`0 0 ${W} ${cy + dotR}`}
      width="100%"
      style={{ display: "block" }}
    >
      {placed.map((s, i) => (
        <circle
          key={i}
          cx={s.x}
          cy={s.y}
          r={dotR}
          fill={s.color}
          opacity={highlightId && s.id !== highlightId ? 0.12 : 1}
        />
      ))}
    </svg>
  );
}

/* ---------- Sparkline ---------- */
export function Sparkline({
  data,
  color = "var(--fg)",
  width = 120,
  height = 32,
  fill = true,
}: {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
  fill?: boolean;
}) {
  if (!data || !data.length) return null;
  const min = Math.min(...data),
    max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const points = data.map((v, i) => [i * stepX, height - ((v - min) / range) * (height - 2) - 1] as const);
  const d = points.map(([x, y], i) => (i ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1)).join(" ");
  const area = d + ` L ${width},${height} L 0,${height} Z`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} style={{ display: "block" }}>
      {fill && <path d={area} fill={color} opacity="0.08" />}
      <path d={d} stroke={color} strokeWidth="1.25" fill="none" />
    </svg>
  );
}

/* ---------- Multi-line chart ---------- */
export function MultiLine({
  series,
  width = 760,
  height = 220,
  highlight,
}: {
  series: Array<{ id: string; label: string; color: string; data: number[] }>;
  width?: number;
  height?: number;
  highlight?: string | null;
}) {
  const min = 0,
    max = 1;
  const pad = { t: 18, r: 60, b: 28, l: 28 };
  const W = width - pad.l - pad.r;
  const H = height - pad.t - pad.b;
  const n = series[0]?.data.length || 1;
  const stepX = W / (n - 1);
  const yFor = (v: number) => pad.t + H - ((v - min) / (max - min)) * H;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ display: "block" }}>
      {[0, 0.25, 0.5, 0.75, 1].map((v, i) => (
        <g key={i}>
          <line
            x1={pad.l}
            x2={pad.l + W}
            y1={yFor(v)}
            y2={yFor(v)}
            stroke="var(--border)"
            strokeDasharray="2,3"
          />
          <text
            x={pad.l - 6}
            y={yFor(v) + 3}
            fontSize="10"
            textAnchor="end"
            fill="var(--fg-faint)"
            fontFamily="var(--font-mono)"
          >
            {(v * 100).toFixed(0)}%
          </text>
        </g>
      ))}
      {[0, Math.floor(n / 2), n - 1].map((i) => (
        <text
          key={i}
          x={pad.l + i * stepX}
          y={height - 8}
          fontSize="10"
          textAnchor="middle"
          fill="var(--fg-faint)"
          fontFamily="var(--font-mono)"
        >{`U${3 + i}`}</text>
      ))}
      {series.map((s) => {
        const d = s.data
          .map((v, i) => (i ? "L" : "M") + (pad.l + i * stepX).toFixed(1) + "," + yFor(v).toFixed(1))
          .join(" ");
        const dim = highlight && highlight !== s.id;
        return (
          <g key={s.id}>
            <path d={d} stroke={s.color} strokeWidth={dim ? 1 : 2} fill="none" opacity={dim ? 0.25 : 1} />
            <text
              x={pad.l + (n - 1) * stepX + 6}
              y={yFor(s.data[s.data.length - 1]) + 3}
              fontSize="10"
              fill={s.color}
              fontFamily="var(--font-mono)"
              fontWeight="500"
              opacity={dim ? 0.4 : 1}
            >
              {s.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ---------- Nav ---------- */
export function Nav({
  current,
  onNav,
  theme,
  setTheme,
  density,
  setDensity,
}: {
  current: string;
  onNav: Nav;
  theme: "light" | "dark";
  setTheme: (t: "light" | "dark") => void;
  density: "comfortable" | "compact";
  setDensity: (d: "comfortable" | "compact") => void;
}) {
  const items: Array<{ id: RouteName; label: string }> = [
    { id: "home", label: "Oversikt" },
    { id: "bills", label: "Saker" },
    { id: "reps", label: "Representanter" },
    { id: "parties", label: "Partier" },
    { id: "votes", label: "Stemmegivning" },
    { id: "committees", label: "Komitéer" },
  ];
  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "color-mix(in oklab, var(--bg) 88%, transparent)",
        backdropFilter: "blur(10px)",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div
        style={{
          maxWidth: 1440,
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          gap: 28,
          padding: "0 24px",
          height: 54,
        }}
      >
        <button
          onClick={() => onNav("home")}
          style={{
            background: "none",
            border: 0,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: 0,
          }}
        >
          <svg width="22" height="22" viewBox="0 0 22 22">
            <rect x="0" y="0" width="22" height="22" rx="4" fill="var(--fg)" />
            <rect x="4" y="12" width="2" height="6" fill="var(--bg)" />
            <rect x="7.5" y="9" width="2" height="9" fill="var(--bg)" />
            <rect x="11" y="5" width="2" height="13" fill="var(--bg)" />
            <rect x="14.5" y="8" width="2" height="10" fill="var(--bg)" />
            <rect x="18" y="11" width="2" height="7" fill="var(--bg)" />
          </svg>
          <span className="display" style={{ fontSize: 22, letterSpacing: "-0.02em" }}>
            Parlytics
          </span>
        </button>

        <div style={{ display: "flex", gap: 2, marginLeft: 12 }}>
          {items.map((it) => (
            <button
              key={it.id}
              onClick={() => onNav(it.id)}
              style={{
                padding: "6px 12px",
                borderRadius: 6,
                background: current === it.id ? "var(--bg-elev)" : "transparent",
                color: current === it.id ? "var(--fg)" : "var(--fg-muted)",
                border: 0,
                cursor: "pointer",
                fontSize: 13.5,
                fontWeight: current === it.id ? 500 : 400,
              }}
            >
              {it.label}
            </button>
          ))}
        </div>

        <div style={{ flex: 1 }} />

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "4px 10px",
            height: 32,
            border: "1px solid var(--border)",
            borderRadius: 6,
            background: "var(--bg-elev)",
            color: "var(--fg-dim)",
            fontSize: 13,
            minWidth: 260,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" />
            <path d="M9.5 9.5L12 12" stroke="currentColor" strokeLinecap="round" />
          </svg>
          <span>Søk saker, representanter, partier…</span>
          <span
            style={{
              marginLeft: "auto",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--fg-faint)",
            }}
          >
            ⌘K
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <DensityToggle density={density} setDensity={setDensity} />
          <ThemeToggle theme={theme} setTheme={setTheme} />
        </div>
      </div>
    </nav>
  );
}

export function ThemeToggle({
  theme,
  setTheme,
}: {
  theme: "light" | "dark";
  setTheme: (t: "light" | "dark") => void;
}) {
  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      style={{
        width: 32,
        height: 32,
        borderRadius: 6,
        background: "var(--bg-elev)",
        border: "1px solid var(--border)",
        display: "grid",
        placeItems: "center",
        cursor: "pointer",
        color: "var(--fg-muted)",
      }}
      title={theme === "dark" ? "Bytt til lys" : "Bytt til mørk"}
    >
      {theme === "dark" ? (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="7" cy="7" r="3" fill="currentColor" />
          <g stroke="currentColor" strokeLinecap="round">
            <line x1="7" y1="1" x2="7" y2="2.5" />
            <line x1="7" y1="11.5" x2="7" y2="13" />
            <line x1="1" y1="7" x2="2.5" y2="7" />
            <line x1="11.5" y1="7" x2="13" y2="7" />
            <line x1="2.8" y1="2.8" x2="3.8" y2="3.8" />
            <line x1="10.2" y1="10.2" x2="11.2" y2="11.2" />
            <line x1="11.2" y1="2.8" x2="10.2" y2="3.8" />
            <line x1="3.8" y1="10.2" x2="2.8" y2="11.2" />
          </g>
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <path d="M10.5 8.5A5 5 0 0 1 5.5 3.5c0-.6.1-1.2.3-1.7A5.5 5.5 0 1 0 12.2 9.3c-.5.2-1.1.2-1.7.2z" />
        </svg>
      )}
    </button>
  );
}

export function DensityToggle({
  density,
  setDensity,
}: {
  density: "comfortable" | "compact";
  setDensity: (d: "comfortable" | "compact") => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        background: "var(--bg-elev)",
        border: "1px solid var(--border)",
        borderRadius: 6,
        padding: 2,
        height: 32,
      }}
    >
      {(["comfortable", "compact"] as const).map((d) => (
        <button
          key={d}
          onClick={() => setDensity(d)}
          style={{
            padding: "0 10px",
            border: 0,
            cursor: "pointer",
            background: density === d ? "var(--bg)" : "transparent",
            color: density === d ? "var(--fg)" : "var(--fg-dim)",
            borderRadius: 4,
            fontSize: 11.5,
            fontFamily: "var(--font-mono)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            boxShadow: density === d ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
          }}
          title={d === "compact" ? "Kompakt" : "Komfortabel"}
        >
          {d === "compact" ? "K" : "C"}
        </button>
      ))}
    </div>
  );
}

/* ---------- Breadcrumb ---------- */
export function Crumb({
  trail,
  onNav,
}: {
  trail: Array<{ label: string; to?: RouteName; params?: Params }>;
  onNav: Nav;
}) {
  return (
    <div
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: "var(--fg-dim)",
        display: "flex",
        gap: 6,
        alignItems: "center",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
      }}
    >
      {trail.map((t, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span style={{ color: "var(--fg-faint)" }}>/</span>}
          {t.to ? (
            <button
              onClick={() => onNav(t.to as RouteName, t.params)}
              style={{
                background: "none",
                border: 0,
                padding: 0,
                cursor: "pointer",
                color: "inherit",
                font: "inherit",
                letterSpacing: "inherit",
                textTransform: "inherit",
              }}
            >
              {t.label}
            </button>
          ) : (
            <span style={{ color: "var(--fg)" }}>{t.label}</span>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

/* ---------- Page shell ---------- */
export function Page({
  children,
  eyebrow,
  title,
  subtitle,
  actions,
  crumb,
  onNav,
}: {
  children: React.ReactNode;
  eyebrow?: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  crumb?: Array<{ label: string; to?: RouteName; params?: Params }>;
  onNav?: Nav;
}) {
  return (
    <div style={{ maxWidth: 1440, margin: "0 auto", padding: "28px 24px 80px" }}>
      {crumb && onNav && (
        <div style={{ marginBottom: 20 }}>
          <Crumb trail={crumb} onNav={onNav} />
        </div>
      )}
      {(title || eyebrow) && (
        <header
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 32,
            marginBottom: 32,
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: 280 }}>
            {eyebrow && (
              <div className="eyebrow" style={{ marginBottom: 10 }}>
                {eyebrow}
              </div>
            )}
            {title && (
              <h1 className="display" style={{ fontSize: 52, lineHeight: 1.02 }}>
                {title}
              </h1>
            )}
            {subtitle && (
              <p style={{ color: "var(--fg-muted)", fontSize: 15, maxWidth: 620, marginTop: 12, marginBottom: 0 }}>
                {subtitle}
              </p>
            )}
          </div>
          {actions && <div style={{ display: "flex", gap: 8 }}>{actions}</div>}
        </header>
      )}
      {children}
    </div>
  );
}
