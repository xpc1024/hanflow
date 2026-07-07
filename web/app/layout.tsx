import type { Metadata } from "next";
import "./globals.css";
import "../styles/tokens.css";

export const metadata: Metadata = {
  title: "Hanflow Studio",
  description: "Visual workflow editor for the Hanflow agent framework",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark">
      <body style={{ margin: 0, fontFamily: "var(--font-sans)", background: "var(--canvas-bg)", color: "var(--text-primary)" }}>
        {children}
      </body>
    </html>
  );
}
