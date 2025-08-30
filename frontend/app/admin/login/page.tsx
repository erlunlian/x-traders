"use client";

import { useEffect, useState } from "react";

export default function AdminLoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [nextPath, setNextPath] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const next = params.get("next");
    const err = params.get("err");
    if (next) setNextPath(next);
    if (err === "not_configured") setError("Admin password not configured.");
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/auth/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.error || "Invalid password");
      }
      const data = await res.json();
      if (data?.token) {
        try {
          window.localStorage.setItem("admin_token", data.token);
        } catch {}
      }
      const target = nextPath || "/admin";
      window.location.href = target;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm border rounded-lg p-6 space-y-4"
      >
        <div>
          <h1 className="text-2xl font-semibold">Admin Login</h1>
          <p className="text-sm text-muted-foreground">
            Enter the admin password to continue
          </p>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Password</label>
          <input
            type="password"
            className="w-full border rounded px-3 py-2 text-black"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoFocus
          />
        </div>
        {error && <div className="text-sm text-destructive">{error}</div>}
        <button
          type="submit"
          className="w-full border rounded px-3 py-2"
          disabled={loading || password.length === 0}
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
