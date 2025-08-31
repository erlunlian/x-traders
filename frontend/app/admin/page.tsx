"use client";

import { AgentLeaderboard } from "@/components/agent-leaderboard";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import { marketService } from "@/services/market";
import { useEffect, useState } from "react";
import AdminLoginPage from "./login/page";

export default function AdminPage() {
  const [hasToken, setHasToken] = useState<boolean | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [monitorErrors, setMonitorErrors] = useState<
    Array<{
      timestamp: string;
      error_type: string;
      message: string;
      traceback?: string;
    }>
  >([]);
  const [showTrace, setShowTrace] = useState<Record<number, boolean>>({});

  useEffect(() => {
    try {
      const token = window.localStorage.getItem("admin_token");
      setHasToken(!!token);
    } catch {
      setHasToken(false);
    }
    const onUnauthorized = () => setHasToken(false);
    window.addEventListener(
      "adminUnauthorized",
      onUnauthorized as EventListener
    );
    return () => {
      window.removeEventListener(
        "adminUnauthorized",
        onUnauthorized as EventListener
      );
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const fetchErrors = async () => {
      try {
        const errs = await marketService.getMonitorErrors(100);
        if (!cancelled) setMonitorErrors(errs);
      } catch {}
    };
    fetchErrors();
    const id = setInterval(fetchErrors, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (hasToken === null) return null;
  if (!hasToken) return <AdminLoginPage />;

  const logout = () => {
    try {
      window.localStorage.removeItem("admin_token");
    } catch {}
    setHasToken(false);
  };

  const runSeedTreasury = async () => {
    setMessage(null);
    setBusy("treasury");
    try {
      const res = await apiClient.post<{ ok: boolean; message: string }>(
        "/api/admin/seed/treasury"
      );
      setMessage(res.message || "Treasury seeded");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Failed to seed treasury"
      );
    } finally {
      setBusy(null);
    }
  };

  const runSeedAgents = async (count: 10 | 50) => {
    setMessage(null);
    setBusy("agents");
    try {
      const res = await apiClient.post<{ ok: boolean; message: string }>(
        "/api/admin/seed/agents",
        { count }
      );
      setMessage(res.message || `Seeded ${count} agents`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to seed agents");
    } finally {
      setBusy(null);
    }
  };

  const runBackfillTweets = async () => {
    setMessage(null);
    setBusy("backfill");
    try {
      const res = await apiClient.post<{ ok: boolean }>(
        "/api/admin/tweets/backfill"
      );
      setMessage(res ? "Backfill completed" : "Backfill triggered");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Failed to backfill tweets"
      );
    } finally {
      setBusy(null);
    }
  };

  const runExportTweets = async () => {
    setMessage(null);
    setBusy("export");
    try {
      const res = await apiClient.post<{ ok: boolean; backup_file?: string }>(
        "/api/admin/tweets/export"
      );
      setMessage(
        res.backup_file ? `Exported to ${res.backup_file}` : "Export completed"
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to export");
    } finally {
      setBusy(null);
    }
  };

  const runImportTweets = async () => {
    setMessage(null);
    setBusy("import");
    try {
      await apiClient.post("/api/admin/tweets/import");
      setMessage("Import completed");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to import");
    } finally {
      setBusy(null);
    }
  };

  const runSyncTweets = async () => {
    setMessage(null);
    setBusy("sync");
    try {
      await apiClient.post("/api/admin/tweets/sync");
      setMessage("Sync completed");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to sync");
    } finally {
      setBusy(null);
    }
  };

  const runDbUpgrade = async () => {
    setMessage(null);
    setBusy("upgrade");
    try {
      const res = await apiClient.post<{ ok: boolean; message?: string }>(
        "/api/admin/db/upgrade"
      );
      setMessage(res.message || "DB upgrade completed");
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Failed to run DB upgrade"
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="container mx-auto px-8 py-6">
      <div className="flex items-center justify-end mb-4">
        <Button variant="outline" size="sm" onClick={logout}>
          Logout
        </Button>
      </div>
      <div className="mb-6 grid gap-3 sm:grid-cols-2">
        <div className="flex gap-2 items-center">
          <Button
            variant="default"
            disabled={busy !== null}
            onClick={runSeedTreasury}
          >
            {busy === "treasury" ? "Seeding Treasury..." : "Seed Treasury"}
          </Button>
        </div>
        <div className="flex gap-2 items-center">
          <Button
            variant="default"
            disabled={busy !== null}
            onClick={() => runSeedAgents(10)}
          >
            {busy === "agents" ? "Seeding Agents..." : "Seed 10 Agents"}
          </Button>
          <Button
            variant="default"
            disabled={busy !== null}
            onClick={() => runSeedAgents(50)}
          >
            {busy === "agents" ? "Seeding Agents..." : "Seed 50 Agents"}
          </Button>
        </div>
        <div className="flex gap-2 items-center">
          <Button
            variant="outline"
            disabled={busy !== null}
            onClick={runBackfillTweets}
          >
            {busy === "backfill" ? "Backfilling..." : "Backfill Tweets"}
          </Button>
        </div>
        <div className="flex gap-2 items-center">
          <Button
            variant="secondary"
            disabled={busy !== null}
            onClick={runExportTweets}
          >
            {busy === "export" ? "Exporting..." : "Export Tweets"}
          </Button>
          <Button
            variant="secondary"
            disabled={busy !== null}
            onClick={runImportTweets}
          >
            {busy === "import" ? "Importing..." : "Import Tweets"}
          </Button>
          <Button
            variant="secondary"
            disabled={busy !== null}
            onClick={runSyncTweets}
          >
            {busy === "sync" ? "Syncing..." : "Sync Tweets"}
          </Button>
        </div>
        <div className="flex gap-2 items-center">
          <Button
            variant="default"
            disabled={busy !== null}
            onClick={runDbUpgrade}
          >
            {busy === "upgrade" ? "Running DB Upgrade..." : "Run DB Upgrade"}
          </Button>
        </div>
      </div>
      {message && (
        <div className="mb-4 text-sm text-muted-foreground">{message}</div>
      )}
      <div className="mb-6">
        <h2 className="text-base font-semibold mb-2">Agent Monitor Errors</h2>
        {monitorErrors.length === 0 ? (
          <div className="text-sm text-muted-foreground">No recent errors</div>
        ) : (
          <div className="space-y-2">
            {monitorErrors.map((e, idx) => (
              <div key={`${e.timestamp}-${idx}`} className="rounded border p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-sm">
                    <div className="font-medium">{e.error_type}</div>
                    <div className="text-muted-foreground break-words">
                      {e.message}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {new Date(e.timestamp).toLocaleString()}
                    </div>
                  </div>
                  {e.traceback && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setShowTrace((s) => ({ ...s, [idx]: !s[idx] }))
                      }
                    >
                      {showTrace[idx] ? "Hide Trace" : "Show Trace"}
                    </Button>
                  )}
                </div>
                {e.traceback && showTrace[idx] && (
                  <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs bg-muted p-2 rounded">
                    {e.traceback}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      <AgentLeaderboard readOnly={false} />
    </div>
  );
}
