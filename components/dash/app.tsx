"use client";

import React from "react";
import { Nav, type RouteName, type Params } from "./components";
import { Dashboard } from "./page-dashboard";
import { Bills, BillDetail } from "./page-bills";
import { Reps, RepDetail } from "./page-reps";
import { Parties, PartyDetail } from "./page-parties";
import { Votes, Committees } from "./page-votes";

type Route = { name: RouteName; params: Params };
type Tweaks = {
  dashboardLayout: "classic" | "feed";
  billsView: "table" | "cards";
  showAiBadges: boolean;
};

const TWEAK_DEFAULTS: Tweaks = {
  dashboardLayout: "feed",
  billsView: "table",
  showAiBadges: true,
};

function readRoute(): Route {
  try {
    const r = localStorage.getItem("storting.route");
    if (r) return JSON.parse(r);
  } catch {}
  return { name: "home", params: {} };
}

function readTheme(): "light" | "dark" {
  const t = localStorage.getItem("storting.theme");
  return t === "dark" ? "dark" : "light";
}

function readDensity(): "comfortable" | "compact" {
  const d = localStorage.getItem("storting.density");
  return d === "compact" ? "compact" : "comfortable";
}

export function App() {
  // Components that use `"use client"` can still pre-render on the server;
  // these reads run only in the browser because App is loaded via
  // next/dynamic with ssr: false (see app/page.tsx).
  const [route, setRoute] = React.useState<Route>(readRoute);
  const [theme, setTheme] = React.useState<"light" | "dark">(readTheme);
  const [density, setDensity] = React.useState<"comfortable" | "compact">(readDensity);
  const [tweaks, setTweaks] = React.useState<Tweaks>(TWEAK_DEFAULTS);
  const [editMode, setEditMode] = React.useState(false);

  React.useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("storting.theme", theme);
  }, [theme]);

  React.useEffect(() => {
    document.documentElement.dataset.density = density;
    localStorage.setItem("storting.density", density);
  }, [density]);

  React.useEffect(() => {
    localStorage.setItem("storting.route", JSON.stringify(route));
    window.scrollTo(0, 0);
  }, [route]);

  React.useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if (!e.data || typeof e.data !== "object") return;
      if (e.data.type === "__activate_edit_mode") setEditMode(true);
      if (e.data.type === "__deactivate_edit_mode") setEditMode(false);
    };
    window.addEventListener("message", onMsg);
    window.parent?.postMessage({ type: "__edit_mode_available" }, "*");
    return () => window.removeEventListener("message", onMsg);
  }, []);

  const setTweak = <K extends keyof Tweaks>(k: K, v: Tweaks[K]) => {
    setTweaks((t) => {
      const next = { ...t, [k]: v };
      window.parent?.postMessage({ type: "__edit_mode_set_keys", edits: { [k]: v } }, "*");
      return next;
    });
  };

  const nav = (name: RouteName, params?: Params) => setRoute({ name, params: params ?? {} });

  let page: React.ReactNode;
  switch (route.name) {
    case "home":
      page = <Dashboard onNav={nav} layoutVariant={tweaks.dashboardLayout} />;
      break;
    case "bills":
      page = <Bills onNav={nav} layoutVariant={tweaks.billsView} />;
      break;
    case "bill":
      page = <BillDetail onNav={nav} params={route.params} />;
      break;
    case "reps":
      page = <Reps onNav={nav} />;
      break;
    case "rep":
      page = <RepDetail onNav={nav} params={route.params} />;
      break;
    case "parties":
      page = <Parties onNav={nav} />;
      break;
    case "party":
      page = <PartyDetail onNav={nav} params={route.params} />;
      break;
    case "votes":
      page = <Votes />;
      break;
    case "committees":
      page = <Committees />;
      break;
    default:
      page = <Dashboard onNav={nav} layoutVariant={tweaks.dashboardLayout} />;
  }

  const currentTab: string =
    route.name === "bill"
      ? "bills"
      : route.name === "rep"
      ? "reps"
      : route.name === "party"
      ? "parties"
      : route.name;

  return (
    <>
      <Nav
        current={currentTab}
        onNav={nav}
        theme={theme}
        setTheme={setTheme}
        density={density}
        setDensity={setDensity}
      />
      {page}
      <footer
        style={{
          borderTop: "1px solid var(--border)",
          padding: "32px 24px",
          marginTop: 48,
          color: "var(--fg-dim)",
          fontSize: 12,
          fontFamily: "var(--font-mono)",
          display: "flex",
          justifyContent: "space-between",
          maxWidth: 1440,
          margin: "0 auto",
        }}
      >
        <span>Parlytics — politisk analyse · data.stortinget.no</span>
        <span>v0.9 · 2026.04</span>
      </footer>
      {editMode && <TweakPanel tweaks={tweaks} setTweak={setTweak} onClose={() => setEditMode(false)} />}
    </>
  );
}

function TweakPanel({
  tweaks,
  setTweak,
  onClose,
}: {
  tweaks: Tweaks;
  setTweak: <K extends keyof Tweaks>(k: K, v: Tweaks[K]) => void;
  onClose: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        zIndex: 100,
        width: 300,
        background: "var(--bg)",
        border: "1px solid var(--border-strong)",
        borderRadius: 10,
        padding: 16,
        boxShadow: "0 10px 40px rgba(0,0,0,0.15)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <div className="eyebrow">Tweaks</div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: 0,
            cursor: "pointer",
            color: "var(--fg-dim)",
            fontSize: 18,
          }}
        >
          ×
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <label
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--fg-dim)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Dashboardlayout
          </label>
          <div
            style={{
              display: "flex",
              marginTop: 6,
              background: "var(--bg-elev)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: 2,
            }}
          >
            {(["classic", "feed"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setTweak("dashboardLayout", v)}
                style={{
                  flex: 1,
                  padding: "6px 10px",
                  border: 0,
                  cursor: "pointer",
                  borderRadius: 4,
                  background: tweaks.dashboardLayout === v ? "var(--bg)" : "transparent",
                  color: tweaks.dashboardLayout === v ? "var(--fg)" : "var(--fg-dim)",
                  fontSize: 12,
                }}
              >
                {v === "classic" ? "Klassisk" : "Feed"}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--fg-dim)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Saker — visning
          </label>
          <div
            style={{
              display: "flex",
              marginTop: 6,
              background: "var(--bg-elev)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: 2,
            }}
          >
            {(["table", "cards"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setTweak("billsView", v)}
                style={{
                  flex: 1,
                  padding: "6px 10px",
                  border: 0,
                  cursor: "pointer",
                  borderRadius: 4,
                  background: tweaks.billsView === v ? "var(--bg)" : "transparent",
                  color: tweaks.billsView === v ? "var(--fg)" : "var(--fg-dim)",
                  fontSize: 12,
                }}
              >
                {v === "table" ? "Tabell" : "Kort"}
              </button>
            ))}
          </div>
        </div>

        <div
          style={{
            fontSize: 11,
            color: "var(--fg-faint)",
            fontFamily: "var(--font-mono)",
            paddingTop: 8,
            borderTop: "1px solid var(--border)",
          }}
        >
          Tema og tetthet er i toppmenyen.
        </div>
      </div>
    </div>
  );
}
