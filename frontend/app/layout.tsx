import type { Metadata } from "next";

import "./globals.css";
import { Sidebar } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "Lakarra AI Operating System",
  description: "Multi-agent AI operating system for the Lakarra business.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
