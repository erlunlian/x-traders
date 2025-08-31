"use client";

import { Sidebar } from "./sidebar";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-auto">{children}</div>
        <footer className="border-t px-4 py-2 text-xs text-muted-foreground">
          Built by{" "}
          <a
            href="https://x.com/erlunlian"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            @erlunlian
          </a>
        </footer>
      </div>
    </div>
  );
}
