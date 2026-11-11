import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/manrope";
import "@fontsource/dm-mono/400.css";
import "@fontsource/dm-mono/500.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "TokGuard — Less context. More coding.",
  description:
    "TokGuard helps coding agents spend less context on repository scans and command output. Set it up for Codex, Claude Code, and Antigravity with one PowerShell command.",
  openGraph: {
    title: "TokGuard — Less context. More coding.",
    description: "Focused repository context and quieter command output for coding agents.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
