"use client";

import { AgentLeaderboard } from "@/components/agent-leaderboard";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import AdminLoginPage from "./login/page";

export default function AdminPage() {
  const [hasToken, setHasToken] = useState<boolean | null>(null);

  useEffect(() => {
    try {
      const token = window.localStorage.getItem("admin_token");
      setHasToken(!!token);
    } catch {
      setHasToken(false);
    }
  }, []);

  if (hasToken === null) return null;
  if (!hasToken) return <AdminLoginPage />;

  const logout = () => {
    try {
      window.localStorage.removeItem("admin_token");
    } catch {}
    setHasToken(false);
  };

  return (
    <div className="container mx-auto px-8 py-6">
      <div className="flex items-center justify-end mb-4">
        <Button variant="outline" size="sm" onClick={logout}>
          Logout
        </Button>
      </div>
      <AgentLeaderboard readOnly={false} />
    </div>
  );
}
