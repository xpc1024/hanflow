"use client";
import dynamic from "next/dynamic";

const StudioShell = dynamic(() => import("@/components/canvas/StudioShell").then(m => ({ default: m.StudioShell })), {
  ssr: false,
  loading: () => (
    <main style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--canvas-bg)", color: "var(--text-primary)" }}>
      <div style={{ fontSize: 32 }}>✨</div>
      <div style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 8 }}>Loading Studio...</div>
    </main>
  ),
});

export default function Home() {
  return <StudioShell />;
}
