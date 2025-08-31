"use client";

import { AgentDetailDialog } from "@/components/agent-detail-dialog";
import { CreateAgentDialog } from "@/components/create-agent-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiClient } from "@/lib/api/client";
import type {
  AgentLeaderboardEntry,
  AgentLeaderboardResponse,
} from "@/types/api";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Bot,
  Plus,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";

type SortField =
  | "name"
  | "total_assets"
  | "balance"
  | "initial_balance"
  | "trades"
  | "decisions"
  | "profit_loss"
  | "created_at";
type SortDirection = "asc" | "desc";

export function AgentLeaderboard({ readOnly = true }: { readOnly?: boolean }) {
  const [agents, setAgents] = useState<AgentLeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTraderId, setSelectedTraderId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [createAgentOpen, setCreateAgentOpen] = useState(false);
  const [sortField, setSortField] = useState<SortField>("total_assets");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<AgentLeaderboardResponse>(
        "/api/agents/leaderboard"
      );
      setAgents(data.agents);
      setSelected((prev) => {
        const updated: Record<string, boolean> = {};
        for (const a of data.agents)
          updated[a.agent_id] = prev[a.agent_id] || false;
        return updated;
      });
    } catch (err) {
      setError("Failed to load agent leaderboard");
      console.error("Error fetching agent leaderboard:", err);
    } finally {
      setLoading(false);
    }
  };

  const selectedIds = Object.entries(selected)
    .filter(([, v]) => v)
    .map(([k]) => k);

  const canBulkDelete = agents
    .filter((a) => selected[a.agent_id])
    .every((a) => a.total_trades_executed === 0);

  const bulkToggle = async (activate: boolean) => {
    if (selectedIds.length === 0) return;
    try {
      setBusy(true);
      await apiClient.post<AgentLeaderboardEntry[]>("/api/agents/bulk/toggle", {
        agent_ids: selectedIds,
        is_active: activate,
      });
      await fetchAgents();
    } catch (e) {
      console.error("Bulk toggle failed", e);
    } finally {
      setBusy(false);
    }
  };

  const bulkDelete = async () => {
    if (selectedIds.length === 0 || !canBulkDelete) return;
    try {
      setBusy(true);
      await apiClient.post<{ deleted: string[]; skipped: string[] }>(
        "/api/agents/bulk/delete",
        { agent_ids: selectedIds }
      );
      await fetchAgents();
    } catch (e) {
      console.error("Bulk delete failed", e);
    } finally {
      setBusy(false);
    }
  };

  const formatCurrency = (cents: number) => {
    const isNegative = cents < 0;
    const absValue = Math.abs(cents);
    return `${isNegative ? "-" : ""}$${(absValue / 100).toLocaleString(
      "en-US",
      {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }
    )}`;
  };

  const formatModel = (model: string) => {
    return model.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortedAgents = [...agents].sort((a, b) => {
    let aValue: string | number;
    let bValue: string | number;

    switch (sortField) {
      case "name":
        aValue = a.name.toLowerCase();
        bValue = b.name.toLowerCase();
        break;
      case "total_assets":
        aValue = a.total_assets_value_in_cents;
        bValue = b.total_assets_value_in_cents;
        break;
      case "balance":
        aValue = a.balance_in_cents;
        bValue = b.balance_in_cents;
        break;
      case "initial_balance":
        aValue = a.initial_balance_in_cents;
        bValue = b.initial_balance_in_cents;
        break;
      case "trades":
        aValue = a.total_trades_executed;
        bValue = b.total_trades_executed;
        break;
      case "decisions":
        aValue = a.total_decisions;
        bValue = b.total_decisions;
        break;
      case "profit_loss":
        aValue = a.profit_loss_in_cents;
        bValue = b.profit_loss_in_cents;
        break;
      case "created_at":
        aValue = new Date(a.created_at).getTime();
        bValue = new Date(b.created_at).getTime();
        break;
      default:
        return 0;
    }

    if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
    if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
    return 0;
  });

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1 h-3 w-3 text-muted-foreground" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="ml-1 h-3 w-3" />
    ) : (
      <ArrowDown className="ml-1 h-3 w-3" />
    );
  };

  const handleAgentClick = (traderId: string) => {
    setSelectedTraderId(traderId);
    setDialogOpen(true);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 sm:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">AI Agent Leaderboard</h1>
          <p className="text-muted-foreground mt-2">
            Track performance of all AI trading agents
          </p>
        </div>
        <Card>
          <CardContent className="p-0">
            <div className="w-full overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rank</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead>Total Assets</TableHead>
                    <TableHead>Cash Balance</TableHead>
                    <TableHead>Trades</TableHead>
                    <TableHead>P&L</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[...Array(5)].map((_, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Skeleton className="h-4 w-8" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-32" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-16" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-16" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 sm:px-8 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-8 py-8">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">AI Agent Leaderboard</h1>
            <p className="text-muted-foreground mt-2">
              Track performance of all AI trading agents
            </p>
          </div>
          {!readOnly && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  disabled={busy || selectedIds.length === 0}
                  onClick={() => bulkToggle(true)}
                >
                  Start Selected
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy || selectedIds.length === 0}
                  onClick={() => bulkToggle(false)}
                >
                  Pause Selected
                </Button>
                <Button
                  variant="destructive"
                  disabled={busy || selectedIds.length === 0 || !canBulkDelete}
                  onClick={bulkDelete}
                  title={
                    !canBulkDelete && selectedIds.length > 0
                      ? "Cannot delete agents with trades"
                      : undefined
                  }
                >
                  Delete Selected
                </Button>
              </div>
              <Button onClick={() => setCreateAgentOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Agent
              </Button>
            </div>
          )}
        </div>
      </div>

      {agents.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No Agents Yet</CardTitle>
            <CardDescription>
              {readOnly
                ? "No AI agents have been created."
                : 'No AI agents have been created. Click "Create Agent" to add your first AI trader.'}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="w-full overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {!readOnly && (
                      <TableHead className="w-[40px] hidden sm:table-cell">
                        <input
                          type="checkbox"
                          aria-label="Select all"
                          checked={
                            agents.length > 0 &&
                            agents.every((a) => selected[a.agent_id])
                          }
                          onChange={(e) => {
                            const checked = e.target.checked;
                            const next: Record<string, boolean> = {};
                            for (const a of agents) next[a.agent_id] = checked;
                            setSelected(next);
                          }}
                        />
                      </TableHead>
                    )}
                    <TableHead className="w-[60px]">Rank</TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 hover:bg-transparent"
                        onClick={() => handleSort("name")}
                      >
                        Agent
                        {getSortIcon("name")}
                      </Button>
                    </TableHead>
                    <TableHead className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 hover:bg-transparent"
                        onClick={() => handleSort("total_assets")}
                      >
                        Total Assets
                        {getSortIcon("total_assets")}
                      </Button>
                    </TableHead>
                    <TableHead className="text-right hidden lg:table-cell">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 hover:bg-transparent"
                        onClick={() => handleSort("initial_balance")}
                      >
                        Initial Balance
                        {getSortIcon("initial_balance")}
                      </Button>
                    </TableHead>
                    <TableHead className="text-right hidden sm:table-cell">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 hover:bg-transparent"
                        onClick={() => handleSort("balance")}
                      >
                        Cash Balance
                        {getSortIcon("balance")}
                      </Button>
                    </TableHead>
                    <TableHead className="text-center w-[72px] px-2 hidden md:table-cell">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 hover:bg-transparent"
                        onClick={() => handleSort("trades")}
                      >
                        Trades
                        {getSortIcon("trades")}
                      </Button>
                    </TableHead>
                    <TableHead className="text-center w-[88px] px-2 hidden lg:table-cell">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 hover:bg-transparent"
                        onClick={() => handleSort("decisions")}
                      >
                        Decisions
                        {getSortIcon("decisions")}
                      </Button>
                    </TableHead>
                    <TableHead className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 hover:bg-transparent"
                        onClick={() => handleSort("profit_loss")}
                      >
                        P&L
                        {getSortIcon("profit_loss")}
                      </Button>
                    </TableHead>
                    <TableHead className="min-w-[140px] hidden xl:table-cell">
                      Model
                    </TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedAgents.map((agent, index) => (
                    <TableRow
                      key={agent.agent_id}
                      className="hover:bg-muted/50"
                    >
                      {!readOnly && (
                        <TableCell className="hidden sm:table-cell">
                          <input
                            type="checkbox"
                            aria-label={`Select ${agent.name}`}
                            checked={!!selected[agent.agent_id]}
                            onChange={(e) =>
                              setSelected((prev) => ({
                                ...prev,
                                [agent.agent_id]: e.target.checked,
                              }))
                            }
                          />
                        </TableCell>
                      )}
                      <TableCell>
                        <div className="flex items-center">
                          <span className="font-mono text-sm">
                            #{index + 1}
                          </span>
                          {index === 0 && <span className="ml-1">🏆</span>}
                          {index === 1 && <span className="ml-1">🥈</span>}
                          {index === 2 && <span className="ml-1">🥉</span>}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Bot className="h-4 w-4 text-primary" />
                          <button
                            className="font-medium text-left hover:underline"
                            onClick={() => handleAgentClick(agent.trader_id)}
                          >
                            {agent.name}
                          </button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(agent.total_assets_value_in_cents)}
                      </TableCell>
                      <TableCell className="text-right font-mono hidden lg:table-cell">
                        {formatCurrency(agent.initial_balance_in_cents)}
                      </TableCell>
                      <TableCell className="text-right font-mono hidden sm:table-cell">
                        {formatCurrency(agent.balance_in_cents)}
                      </TableCell>
                      <TableCell className="text-center w-[72px] px-2 py-4 hidden md:table-cell">
                        <Badge variant="secondary" className="font-mono">
                          {agent.total_trades_executed}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center w-[88px] px-2 py-4 hidden lg:table-cell">
                        <Badge variant="outline" className="font-mono">
                          {agent.total_decisions}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div
                          className={`flex items-center justify-end gap-1 font-mono ${
                            agent.profit_loss_in_cents > 0
                              ? "text-green-600 dark:text-green-400"
                              : agent.profit_loss_in_cents < 0
                              ? "text-red-600 dark:text-red-400"
                              : "text-muted-foreground"
                          }`}
                        >
                          {agent.profit_loss_in_cents > 0 && (
                            <TrendingUp className="h-3 w-3" />
                          )}
                          {agent.profit_loss_in_cents < 0 && (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          {formatCurrency(agent.profit_loss_in_cents)}
                        </div>
                      </TableCell>
                      <TableCell className="min-w-[140px] hidden xl:table-cell">
                        <Badge
                          variant="outline"
                          className="text-xs whitespace-nowrap"
                        >
                          {formatModel(agent.llm_model)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={agent.is_active ? "default" : "secondary"}
                          className="gap-1"
                        >
                          {agent.is_active ? (
                            <>
                              <Activity className="h-3 w-3" />
                              Active
                            </>
                          ) : (
                            "Inactive"
                          )}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <AgentDetailDialog
        traderId={selectedTraderId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        readOnly={readOnly}
      />

      {!readOnly && (
        <CreateAgentDialog
          open={createAgentOpen}
          onOpenChange={setCreateAgentOpen}
          onAgentCreated={fetchAgents}
        />
      )}
    </div>
  );
}
