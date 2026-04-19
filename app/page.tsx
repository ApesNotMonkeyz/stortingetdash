"use client";

import dynamic from "next/dynamic";

const App = dynamic(() => import("@/components/dash/app").then((m) => m.App), {
  ssr: false,
});

export default function Home() {
  return <App />;
}
