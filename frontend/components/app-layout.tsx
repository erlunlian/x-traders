"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Menu, TrendingUp } from "lucide-react";
import { Sidebar } from "./sidebar";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <div className="hidden md:block">
        <Sidebar />
      </div>
      <div className="flex-1 flex flex-col">
        <div className="md:hidden flex h-16 items-center justify-between border-b px-4">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="w-9 h-9">
                <Menu className="h-5 w-5" />
                <span className="sr-only">Open navigation</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="p-0 w-64">
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <Sidebar />
            </SheetContent>
          </Sheet>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-primary" />
            <span className="text-base font-semibold">X-Traders</span>
          </div>
          <ThemeToggle />
        </div>
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
