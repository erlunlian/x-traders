"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient } from "@/lib/api/client";
import type {
  Agent,
  AgentStats,
  AgentThought,
  LLMModel,
  ThoughtListResponse,
} from "@/types/api";
import {
  Activity,
  Bot,
  Brain,
  Calendar,
  Check,
  Copy,
  DollarSign,
  Edit,
  History,
  Pause,
  Play,
  Save,
  Shield,
  ShoppingCart,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
}

interface Order {
  order_id: string;
  ticker: string;
  side: string;
  order_type: string;
  quantity: number;
  filled_quantity: number;
  limit_price: number | null;
  status: string;
  created_at: string;
}

interface Trade {
  trade_id: string;
  ticker: string;
  price: number;
  quantity: number;
  side: string;
  executed_at: string;
}

interface TraderDetail {
  trader_id: string;
  is_active: boolean;
  is_admin: boolean;
  balance_in_cents: number;
  created_at: string;
  positions: Position[];
  unfilled_orders: Order[];
  recent_trades: Trade[];
  agent?: Agent;
}

interface TraderDetailDrawerProps {
  traderId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TraderDetailDrawer({
  traderId,
  open,
  onOpenChange,
}: TraderDetailDrawerProps) {
  const [trader, setTrader] = useState<TraderDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentStats, setAgentStats] = useState<AgentStats | null>(null);
  const [agentThoughts, setAgentThoughts] = useState<AgentThought[]>([]);
  const [togglingAgent, setTogglingAgent] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedAgent, setEditedAgent] = useState<Partial<Agent> | null>(null);
  const [availableModels, setAvailableModels] = useState<LLMModel[]>([]);
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchAvailableModels = useCallback(async () => {
    try {
      const models = await apiClient.get<LLMModel[]>(
        "/api/agents/models/available"
      );
      setAvailableModels(models);
    } catch (err) {
      console.error("Error fetching models:", err);
    }
  }, []);

  const fetchTraderDetail = useCallback(async () => {
    if (!traderId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<TraderDetail>(
        `/api/traders/${traderId}`
      );
      setTrader(data);

      // If trader has an agent, fetch agent stats and recent thoughts
      if (data.agent) {
        try {
          const [stats, thoughts] = await Promise.all([
            apiClient.get<AgentStats>(
              `/api/agents/${data.agent.agent_id}/stats`
            ),
            apiClient.get<ThoughtListResponse>(
              `/api/agents/${data.agent.agent_id}/thoughts?limit=10`
            ),
          ]);
          setAgentStats(stats);
          setAgentThoughts(thoughts.thoughts);
        } catch (err) {
          console.error("Error fetching agent data:", err);
        }
      }
    } catch (err) {
      setError("Failed to load trader details");
      console.error("Error fetching trader:", err);
    } finally {
      setLoading(false);
    }
  }, [traderId]);

  useEffect(() => {
    if (traderId && open) {
      fetchTraderDetail();
      fetchAvailableModels();
    }
  }, [traderId, open, fetchTraderDetail, fetchAvailableModels]);

  useEffect(() => {
    // Reset edit mode when drawer closes
    if (!open) {
      setEditMode(false);
      setEditedAgent(null);
    }
  }, [open]);

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(cents / 100);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const toggleAgent = async () => {
    if (!trader?.agent) return;

    try {
      setTogglingAgent(true);
      const updatedAgent = await apiClient.post<Agent>(
        `/api/agents/${trader.agent.agent_id}/toggle`
      );

      // Update the trader's agent in state
      setTrader((prev) =>
        prev
          ? {
              ...prev,
              agent: updatedAgent,
            }
          : null
      );
    } catch (err) {
      console.error("Error toggling agent:", err);
    } finally {
      setTogglingAgent(false);
    }
  };

  const startEdit = () => {
    if (trader?.agent) {
      setEditedAgent({
        ...trader.agent,
      });
      setEditMode(true);
    }
  };

  const cancelEdit = () => {
    setEditMode(false);
    setEditedAgent(null);
  };

  const saveAgentChanges = async () => {
    if (!trader?.agent || !editedAgent) return;

    try {
      setSaving(true);
      const updatedAgent = await apiClient.put<Agent>(
        `/api/agents/${trader.agent.agent_id}`,
        {
          temperature: editedAgent.temperature,
          llm_model: editedAgent.llm_model,
        }
      );

      // Update the trader's agent in state
      setTrader((prev) =>
        prev
          ? {
              ...prev,
              agent: updatedAgent,
            }
          : null
      );

      setEditMode(false);
      setEditedAgent(null);
    } catch (err) {
      console.error("Error saving agent:", err);
    } finally {
      setSaving(false);
    }
  };

  const copyToClipboard = async (text: string, idType: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(idType);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            Trader Details
            {trader?.is_admin && (
              <Badge variant="destructive">
                <Shield className="mr-1 h-3 w-3" />
                Admin
              </Badge>
            )}
          </SheetTitle>
          <SheetDescription>
            View and manage trader information
          </SheetDescription>
        </SheetHeader>

        {/* Trader info moved outside SheetDescription */}
        {trader && (
          <div className="space-y-2 mt-4">
            <div className="flex items-center gap-2">
              <Badge variant={trader.is_active ? "default" : "secondary"}>
                <Activity className="mr-1 h-3 w-3" />
                {trader.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">ID:</span>
              <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                {trader.trader_id}
              </code>
            </div>
          </div>
        )}

        {loading && (
          <div className="mt-6 space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {error && (
          <Card className="mt-6 border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Error</CardTitle>
              <CardDescription>{error}</CardDescription>
            </CardHeader>
          </Card>
        )}

        {trader && !loading && (
          <div className="mt-6">
            {/* Agent Section for traders with agents */}
            {trader.agent && (
              <Card className="mb-6 border-primary/20">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Bot className="h-5 w-5 text-primary" />
                      AI Agent: {trader.agent.name}
                    </CardTitle>
                    <div className="flex gap-2">
                      {!editMode ? (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={startEdit}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant={
                              trader.agent.is_active ? "destructive" : "default"
                            }
                            onClick={toggleAgent}
                            disabled={togglingAgent}
                          >
                            {togglingAgent ? (
                              "..."
                            ) : trader.agent.is_active ? (
                              <>
                                <Pause className="mr-2 h-4 w-4" />
                                Pause
                              </>
                            ) : (
                              <>
                                <Play className="mr-2 h-4 w-4" />
                                Resume
                              </>
                            )}
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={cancelEdit}
                            disabled={saving}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="default"
                            onClick={saveAgentChanges}
                            disabled={saving}
                          >
                            {saving ? (
                              "..."
                            ) : (
                              <>
                                <Save className="mr-2 h-4 w-4" />
                                Save
                              </>
                            )}
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Agent ID with copy button */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Agent ID
                      </span>
                      <div className="flex items-center gap-2">
                        <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                          {trader.agent.agent_id.slice(0, 8)}...
                        </code>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0"
                          onClick={() =>
                            copyToClipboard(
                              trader.agent?.agent_id || "",
                              "agent"
                            )
                          }
                        >
                          {copiedId === "agent" ? (
                            <Check className="h-3 w-3 text-green-600" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                    </div>

                    {/* Trader ID with copy button */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Trader ID
                      </span>
                      <div className="flex items-center gap-2">
                        <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                          {trader.trader_id.slice(0, 8)}...
                        </code>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0"
                          onClick={() =>
                            copyToClipboard(trader.trader_id, "trader")
                          }
                        >
                          {copiedId === "trader" ? (
                            <Check className="h-3 w-3 text-green-600" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                    </div>

                    {/* Model field - editable in edit mode */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Model
                      </span>
                      {!editMode ? (
                        <Badge variant="outline">
                          {trader.agent.llm_model}
                        </Badge>
                      ) : (
                        <Select
                          value={editedAgent?.llm_model}
                          onValueChange={(value) =>
                            setEditedAgent((prev) =>
                              prev ? { ...prev, llm_model: value } : null
                            )
                          }
                        >
                          <SelectTrigger className="w-48 h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {availableModels.map((model) => (
                              <SelectItem key={model.id} value={model.value}>
                                {model.display_name} ({model.provider})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Status
                      </span>
                      <Badge
                        variant={
                          trader.agent.is_active ? "default" : "secondary"
                        }
                      >
                        {trader.agent.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>

                    {/* Temperature field - editable in edit mode */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Temperature
                      </span>
                      {!editMode ? (
                        <span className="font-mono text-sm">
                          {trader.agent.temperature}
                        </span>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Input
                            type="number"
                            min="0"
                            max="1"
                            step="0.1"
                            value={editedAgent?.temperature || 0}
                            onChange={(e) =>
                              setEditedAgent((prev) =>
                                prev
                                  ? {
                                      ...prev,
                                      temperature: parseFloat(e.target.value),
                                    }
                                  : null
                              )
                            }
                            className="w-20 h-8"
                          />
                        </div>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Total Decisions
                      </span>
                      <span className="font-semibold">
                        {trader.agent?.total_decisions}
                      </span>
                    </div>
                    {trader.agent?.last_decision_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          Last Decision
                        </span>
                        <span className="text-sm">
                          {formatDate(trader.agent?.last_decision_at || "")}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Agent Stats */}
                  {agentStats && (
                    <div className="mt-4 pt-4 border-t space-y-3">
                      <div className="text-sm font-semibold mb-2">
                        Performance Metrics
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="text-center p-2 bg-muted rounded">
                          <div className="text-lg font-bold">
                            {agentStats.total_thoughts}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Total Thoughts
                          </div>
                        </div>
                        <div className="text-center p-2 bg-muted rounded">
                          <div className="text-lg font-bold">
                            {agentStats.last_activity_at
                              ? new Date(
                                  agentStats.last_activity_at
                                ).toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                })
                              : "—"}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Last Activity
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Personality Preview */}
                  <div className="mt-4 pt-4 border-t">
                    <div className="text-sm font-semibold mb-2">
                      Personality
                    </div>
                    <div className="text-xs text-muted-foreground bg-muted p-2 rounded max-h-24 overflow-y-auto">
                      {trader.agent?.personality_prompt}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* No Agent Message for admin traders without agents */}
            {!trader.agent && trader.is_admin && (
              <Card className="mb-6 border-dashed">
                <CardContent className="py-6">
                  <div className="text-center text-muted-foreground">
                    <Bot className="h-10 w-10 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">
                      No AI agent configured for this trader
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            <Tabs defaultValue="overview" className="space-y-4">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="trading">Trading</TabsTrigger>
                {trader.agent && (
                  <TabsTrigger value="agent">Agent Activity</TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                {/* Balance Card */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <DollarSign className="h-5 w-5" />
                      Cash Balance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-green-600">
                      {formatCurrency(trader.balance_in_cents)}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      <Calendar className="inline mr-1 h-3 w-3" />
                      Created {formatDate(trader.created_at)}
                    </div>
                  </CardContent>
                </Card>

                {/* Positions */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      Positions ({trader.positions.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {trader.positions.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        No positions
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {trader.positions.map((position) => (
                          <div
                            key={position.ticker}
                            className="flex items-center justify-between p-2 rounded-lg border"
                          >
                            <div>
                              <div className="font-semibold text-sm">
                                {position.ticker}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {position.quantity} @{" "}
                                {formatCurrency(position.avg_cost)}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-semibold text-sm">
                                {formatCurrency(
                                  position.quantity * position.avg_cost
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="trading" className="space-y-4">
                {/* Unfilled Orders */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <ShoppingCart className="h-5 w-5" />
                      Unfilled Orders ({trader.unfilled_orders.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {trader.unfilled_orders.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        No unfilled orders
                      </p>
                    ) : (
                      <ScrollArea className="h-64">
                        <div className="space-y-2">
                          {trader.unfilled_orders.map((order) => (
                            <div
                              key={order.order_id}
                              className="p-2 rounded-lg border"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-semibold text-sm">
                                  {order.ticker}
                                </span>
                                <Badge
                                  variant={
                                    order.side === "BUY"
                                      ? "default"
                                      : "destructive"
                                  }
                                  className="text-xs"
                                >
                                  {order.side}
                                </Badge>
                              </div>
                              <div className="text-xs text-muted-foreground space-y-1">
                                <div className="flex justify-between">
                                  <span>{order.order_type}</span>
                                  <span>
                                    {order.filled_quantity}/{order.quantity}
                                  </span>
                                </div>
                                {order.limit_price && (
                                  <div>
                                    Limit: {formatCurrency(order.limit_price)}
                                  </div>
                                )}
                                <div className="flex justify-between">
                                  <Badge variant="outline" className="text-xs">
                                    {order.status}
                                  </Badge>
                                  <span>
                                    {new Date(
                                      order.created_at
                                    ).toLocaleTimeString()}
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    )}
                  </CardContent>
                </Card>

                {/* Recent Trades */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <History className="h-5 w-5" />
                      Recent Trades ({trader.recent_trades.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {trader.recent_trades.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        No trades yet
                      </p>
                    ) : (
                      <ScrollArea className="h-64">
                        <div className="space-y-2">
                          {trader.recent_trades.map((trade) => (
                            <div
                              key={trade.trade_id}
                              className="p-2 rounded-lg border"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-semibold text-sm">
                                  {trade.ticker}
                                </span>
                                <Badge
                                  variant={
                                    trade.side === "BUY"
                                      ? "default"
                                      : "destructive"
                                  }
                                  className="text-xs"
                                >
                                  {trade.side}
                                </Badge>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                <div className="flex justify-between">
                                  <span>
                                    {trade.quantity} @{" "}
                                    {formatCurrency(trade.price)}
                                  </span>
                                  <span className="font-semibold">
                                    {formatCurrency(
                                      trade.price * trade.quantity
                                    )}
                                  </span>
                                </div>
                                <div className="mt-1">
                                  {formatDate(trade.executed_at)}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {trader.agent && (
                <TabsContent value="agent" className="space-y-4">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Brain className="h-5 w-5" />
                        Recent Thoughts
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {agentThoughts.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No thoughts yet
                        </p>
                      ) : (
                        <ScrollArea className="h-96">
                          <div className="space-y-3">
                            {agentThoughts.map((thought) => (
                              <div
                                key={thought.thought_id}
                                className="p-3 rounded-lg border"
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <Badge variant="outline">
                                    {thought.thought_type}
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">
                                    {formatDate(thought.created_at)}
                                  </span>
                                </div>
                                {thought.content && (
                                  <p className="text-xs text-muted-foreground mb-2">
                                    {thought.content}
                                  </p>
                                )}
                                {thought.tool_name && (
                                  <div className="text-xs text-muted-foreground">
                                    <Zap className="inline mr-1 h-3 w-3" />
                                    {thought.tool_name}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </ScrollArea>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              )}
            </Tabs>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
