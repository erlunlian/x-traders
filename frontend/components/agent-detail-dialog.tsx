"use client";

import { JsonViewer } from "@/components/json-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type {
  Agent,
  AgentMemoryState,
  AgentThought,
  ThoughtListResponse,
} from "@/types/api";
import {
  Activity,
  Bot,
  Brain,
  Calendar,
  ChartBar,
  Check,
  Copy,
  DollarSign,
  Edit,
  History,
  MessageSquare,
  Package,
  Pause,
  Play,
  RefreshCw,
  Save,
  Shield,
  ShoppingCart,
  TrendingUp,
  Users,
  X,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

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

interface LLMModel {
  id: string;
  value: string;
  provider: string;
  display_name: string;
}

interface AgentDetailDialogProps {
  traderId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  readOnly?: boolean;
}

type SectionType = "overview" | "trades" | "activity" | "memory";

const navigationItems = [
  { id: "overview" as SectionType, name: "Overview", icon: ChartBar },
  { id: "trades" as SectionType, name: "Trade History", icon: History },
  { id: "activity" as SectionType, name: "Agent Activity", icon: Brain },
  { id: "memory" as SectionType, name: "Memory", icon: MessageSquare },
];

export function AgentDetailDialog({
  traderId,
  open,
  onOpenChange,
  readOnly = true,
}: AgentDetailDialogProps) {
  const [activeSection, setActiveSection] = useState<SectionType>("overview");
  const [trader, setTrader] = useState<TraderDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentThoughts, setAgentThoughts] = useState<AgentThought[]>([]);
  const [togglingAgent, setTogglingAgent] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedAgent, setEditedAgent] = useState<Partial<Agent> | null>(null);
  const [availableModels, setAvailableModels] = useState<LLMModel[]>([]);
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [loadingActivities, setLoadingActivities] = useState(false);
  const [agentMemory, setAgentMemory] = useState<AgentMemoryState | null>(null);
  const [refreshingActivities, setRefreshingActivities] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const activityEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

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

      // If trader has an agent, fetch agent stats, activity, and memory
      if (data.agent) {
        try {
          const thoughts = await apiClient.get<ThoughtListResponse>(
            `/api/agents/${data.agent.agent_id}/thoughts?limit=50`
          );
          // Reverse thoughts to show oldest first (newest at bottom)
          setAgentThoughts(thoughts.thoughts.reverse());

          if (isAdmin) {
            try {
              const memory = await apiClient.get<AgentMemoryState>(
                `/api/agents/${data.agent.agent_id}/memory`
              );
              setAgentMemory(memory);
            } catch (err) {
              // If memory fetch fails (e.g., unauthorized), clear memory state
              setAgentMemory(null);
            }
          } else {
            setAgentMemory(null);
          }
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
  }, [traderId, isAdmin]);

  useEffect(() => {
    if (traderId && open) {
      fetchTraderDetail();
      fetchAvailableModels();
    }
  }, [traderId, open, fetchTraderDetail, fetchAvailableModels]);

  useEffect(() => {
    // Reset state when dialog closes
    if (!open) {
      setEditMode(false);
      setEditedAgent(null);
      setActiveSection("overview");
    }
  }, [open]);

  // Determine admin authentication from localStorage token
  useEffect(() => {
    if (!open) return;
    try {
      const token =
        typeof window !== "undefined"
          ? window.localStorage.getItem("admin_token")
          : null;
      if (!token) {
        setIsAdmin(false);
        return;
      }
      const parts = token.split(".");
      if (parts.length !== 3) {
        setIsAdmin(false);
        return;
      }
      const exp = parseInt(parts[1] || "0", 10);
      const nowSec = Math.floor(Date.now() / 1000);
      setIsAdmin(Number.isFinite(exp) && nowSec < exp);
    } catch {
      setIsAdmin(false);
    }
  }, [open]);

  // Ensure we never show memory section if not admin
  useEffect(() => {
    if (!isAdmin && activeSection === "memory") {
      setActiveSection("overview");
    }
  }, [isAdmin, activeSection]);

  // Auto-scroll to bottom only on initial load or refresh
  useEffect(() => {
    if (
      activityEndRef.current &&
      activeSection === "activity" &&
      agentThoughts.length > 0 &&
      agentThoughts.length <= 50
    ) {
      // Only auto-scroll for initial load (when we have 50 or fewer messages)
      activityEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [agentThoughts.length, activeSection]);

  const fetchMoreActivities = async () => {
    if (!trader?.agent || loadingActivities) return;

    try {
      setLoadingActivities(true);

      // Save scroll height before loading
      const scrollContainer = scrollContainerRef.current;
      const previousScrollHeight = scrollContainer?.scrollHeight || 0;

      const response = await apiClient.get<ThoughtListResponse>(
        `/api/agents/${trader.agent.agent_id}/thoughts?limit=50&offset=${agentThoughts.length}`
      );

      // Prepend older messages (they come in newest-first from API)
      setAgentThoughts((prev) => {
        const newThoughts = [...response.thoughts.reverse(), ...prev];

        // Restore scroll position after DOM updates
        setTimeout(() => {
          if (scrollContainer) {
            const newScrollHeight = scrollContainer.scrollHeight;
            const scrollDiff = newScrollHeight - previousScrollHeight;
            scrollContainer.scrollTop = scrollContainer.scrollTop + scrollDiff;
          }
        }, 0);

        return newThoughts;
      });
    } catch (err) {
      console.error("Error fetching more activities:", err);
    } finally {
      setLoadingActivities(false);
    }
  };

  const refreshActivities = async () => {
    if (!trader?.agent || refreshingActivities) return;

    try {
      setRefreshingActivities(true);
      const response = await apiClient.get<ThoughtListResponse>(
        `/api/agents/${trader.agent.agent_id}/thoughts?limit=50`
      );
      // Reverse to show oldest first (newest at bottom)
      setAgentThoughts(response.thoughts.reverse());
    } catch (err) {
      console.error("Error refreshing activities:", err);
    } finally {
      setRefreshingActivities(false);
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const parseJsonSafe = (value?: string | null) => {
    if (!value)
      return undefined as unknown as Record<string, unknown> | undefined;
    try {
      return JSON.parse(value) as Record<string, unknown>;
    } catch {
      return undefined as unknown as Record<string, unknown> | undefined;
    }
  };

  const centsToDollarsString = (cents?: unknown) => {
    if (typeof cents !== "number") return "";
    return `$${(cents / 100).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const getToolDisplayName = (tool?: string | null) => {
    if (!tool) return "Action";
    const map: Record<string, string> = {
      rest: "Rest",
      check_price: "Check Price",
      check_order_book: "Check Order Book",
      get_x_user_info: "X User Info",
      get_x_user_tweets: "X User Tweets",
      buy_limit: "Buy Limit",
      sell_limit: "Sell Limit",
      cancel_order: "Cancel Order",
      check_order_status: "Check Order Status",
      check_portfolio: "Check Portfolio",
      check_all_prices: "Check All Prices",
      check_recent_trades: "Check Recent Trades",
      list_tickers: "List Tickers",
      create_post: "Create Post",
      like_post: "Like Post",
      add_comment: "Add Comment",
      get_ticker_posts: "Get Ticker Posts",
      get_post_comments: "Get Post Comments",
      get_x_recent_tweets: "X Recent Tweets",
      get_x_tweets_by_ids: "X Tweets By IDs",
      get_all_x_users: "All X Users",
    };
    return (
      map[tool] ||
      tool.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    );
  };

  const formatToolCallMessage = (
    tool?: string | null,
    argsStr?: string | null
  ) => {
    const args = parseJsonSafe(argsStr) || {};
    switch (tool) {
      case "rest": {
        const mins = (args as { duration_minutes?: number }).duration_minutes;
        return `Agent has decided to rest for ${
          typeof mins === "number" ? mins : "?"
        } minutes.`;
      }
      case "check_price": {
        const ticker = (args as { ticker?: string }).ticker;
        return `Checking prices for ${ticker ?? "ticker"}`;
      }
      case "check_order_book": {
        const ticker = (args as { ticker?: string }).ticker;
        return `Checking order book for ${ticker ?? "ticker"}`;
      }
      case "get_x_user_info": {
        const username = (args as { username?: string }).username;
        return `Checking X user info for @${username ?? "username"}`;
      }
      case "get_x_user_tweets": {
        const username = (args as { username?: string }).username;
        return `Checking X tweets for @${username ?? "username"}`;
      }
      case "sell_limit": {
        const qty = (args as { quantity?: number }).quantity;
        const ticker = (args as { ticker?: string }).ticker;
        const price = centsToDollarsString(
          (args as { limit_price_in_cents?: number }).limit_price_in_cents
        );
        return `Executing sell order of ${qty ?? "?"} shares for ${
          ticker ?? "ticker"
        } at price ${price || "$?.??"}`;
      }
      case "buy_limit": {
        const qty = (args as { quantity?: number }).quantity;
        const ticker = (args as { ticker?: string }).ticker;
        const price = centsToDollarsString(
          (args as { limit_price_in_cents?: number }).limit_price_in_cents
        );
        return `Executing buy order of ${qty ?? "?"} shares for ${
          ticker ?? "ticker"
        } at price ${price || "$?.??"}`;
      }
      case "cancel_order": {
        const orderId = (args as { order_id?: string }).order_id;
        return `Cancelling order ${orderId ?? ""}`.trim();
      }
      case "check_order_status": {
        const orderId = (args as { order_id?: string }).order_id;
        return `Checking status for order ${orderId ?? ""}`.trim();
      }
      case "check_portfolio": {
        return "Checking portfolio";
      }
      case "check_all_prices": {
        return "Checking all prices";
      }
      case "check_recent_trades": {
        const ticker = (args as { ticker?: string }).ticker;
        return `Checking recent trades for ${ticker ?? "ticker"}`;
      }
      case "list_tickers": {
        return "Listing all tickers";
      }
      case "create_post": {
        const ticker = (args as { ticker?: string }).ticker;
        const content = (args as { content?: string }).content;
        return `Posting under ${ticker ?? "ticker"}: "${content ?? ""}"`;
      }
      case "like_post": {
        return "Liking post";
      }
      case "add_comment": {
        const content = (args as { content?: string }).content;
        return `Commenting on post: "${content ?? ""}"`;
      }
      case "get_ticker_posts": {
        const ticker = (args as { ticker?: string }).ticker;
        return `Fetching recent posts for ${ticker ?? "ticker"}`;
      }
      case "get_post_comments": {
        return "Fetching recent comments for post";
      }
      case "get_x_recent_tweets": {
        return "Fetching recent X tweets";
      }
      case "get_x_tweets_by_ids": {
        const ids = (args as { tweet_ids?: string[] }).tweet_ids;
        const count = Array.isArray(ids) ? ids.length : undefined;
        return `Fetching tweets by IDs${
          typeof count === "number" ? ` (${count})` : ""
        }`;
      }
      case "get_all_x_users": {
        return "Fetching all X users";
      }
      default: {
        return tool
          ? `Executing ${getToolDisplayName(tool)}`
          : "Executing action";
      }
    }
  };

  const toggleAgent = async () => {
    if (!trader?.agent) return;
    if (readOnly) return;

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
    if (readOnly) return;
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
    if (readOnly) return;

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

  const renderOverview = () => {
    if (!trader) return null;

    return (
      <div className="space-y-4">
        {/* Agent Info Card */}
        {trader.agent && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Bot className="h-5 w-5 text-primary" />
                  Agent Configuration
                </CardTitle>
                <div className="flex gap-2">
                  {!editMode ? (
                    <>
                      {!readOnly && (
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
                      )}
                    </>
                  ) : (
                    <>
                      {!readOnly && (
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
                    </>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Model field */}
              <div className="flex items-center justify-between">
                <Label className="text-sm">Model</Label>
                {!editMode ? (
                  <Badge variant="outline">{trader.agent.llm_model}</Badge>
                ) : (
                  !readOnly && (
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
                  )
                )}
              </div>

              {/* Temperature field */}
              <div className="flex items-center justify-between">
                <Label className="text-sm">Temperature</Label>
                {!editMode ? (
                  <span className="font-mono text-sm">
                    {trader.agent.temperature}
                  </span>
                ) : (
                  !readOnly && (
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
                  )
                )}
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-sm">Status</Label>
                <Badge
                  variant={trader.agent.is_active ? "default" : "secondary"}
                >
                  <Activity className="mr-1 h-3 w-3" />
                  {trader.agent.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>

              {/* IDs with copy buttons */}
              <div className="pt-3 border-t space-y-2">
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
                        copyToClipboard(trader.agent?.agent_id || "", "agent")
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
              </div>
            </CardContent>
          </Card>
        )}

        {/* Balance and Stats */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(trader.balance_in_cents)}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              <Calendar className="inline mr-1 h-3 w-3" />
              Since {formatDate(trader.created_at)}
            </div>
          </CardContent>
        </Card>

        {/* Positions */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Package className="h-5 w-5" />
              Positions ({trader.positions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {trader.positions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No positions held</p>
            ) : (
              <div className="space-y-2">
                {trader.positions.map((position) => (
                  <div
                    key={position.ticker}
                    className="flex items-center justify-between p-3 rounded-lg border"
                  >
                    <div>
                      <div className="font-semibold">{position.ticker}</div>
                      <div className="text-sm text-muted-foreground">
                        {position.quantity} shares @{" "}
                        {formatCurrency(position.avg_cost)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">
                        {formatCurrency(position.quantity * position.avg_cost)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Personality Preview */}
        {trader.agent && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Personality
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground bg-muted p-3 rounded-lg">
                {trader.agent.personality_prompt}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  const renderTradeHistory = () => {
    if (!trader) return null;

    return (
      <div className="space-y-4">
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
              <div className="space-y-2">
                {trader.unfilled_orders.map((order) => (
                  <div key={order.order_id} className="p-3 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{order.ticker}</span>
                      <Badge
                        variant={
                          order.side === "BUY" ? "default" : "destructive"
                        }
                      >
                        {order.side}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                      <div>Type: {order.order_type}</div>
                      <div>Status: {order.status}</div>
                      <div>
                        Quantity: {order.filled_quantity}/{order.quantity}
                      </div>
                      {order.limit_price && (
                        <div>Limit: {formatCurrency(order.limit_price)}</div>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">
                      {formatDate(order.created_at)}
                    </div>
                  </div>
                ))}
              </div>
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
                No trades executed yet
              </p>
            ) : (
              <div className="space-y-2">
                {trader.recent_trades.map((trade) => (
                  <div key={trade.trade_id} className="p-3 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{trade.ticker}</span>
                      <Badge
                        variant={
                          trade.side === "BUY" ? "default" : "destructive"
                        }
                      >
                        {trade.side}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <div className="text-sm text-muted-foreground">
                        {trade.quantity} shares @ {formatCurrency(trade.price)}
                      </div>
                      <div className="font-semibold">
                        {formatCurrency(trade.price * trade.quantity)}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">
                      {formatDate(trade.executed_at)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderMemory = () => {
    if (!trader?.agent) {
      return (
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">
              <Bot className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No AI agent configured for this trader</p>
            </div>
          </CardContent>
        </Card>
      );
    }

    return (
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Agent Memory
            </CardTitle>
            <CardDescription>
              Current working memory and insights stored by the agent
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!agentMemory ? (
              <p className="text-sm text-muted-foreground">Loading memory...</p>
            ) : (
              <div className="space-y-4">
                {/* Working Memory */}
                {agentMemory.working_memory && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold flex items-center gap-2">
                      <Brain className="h-4 w-4" />
                      Working Memory
                    </h4>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <p className="text-sm whitespace-pre-wrap font-mono">
                        {agentMemory.working_memory.content}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span>
                          Tokens: {agentMemory.working_memory.token_count}
                        </span>
                        <span>
                          Updated:{" "}
                          {formatDate(agentMemory.working_memory.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Insights */}
                {agentMemory.insights && agentMemory.insights.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Insights ({agentMemory.insights.length})
                    </h4>
                    <div className="space-y-2">
                      {agentMemory.insights.map((insight, index) => (
                        <div
                          key={insight.memory_id || index}
                          className="bg-muted/30 p-3 rounded-lg"
                        >
                          <p className="text-sm whitespace-pre-wrap">
                            {insight.content}
                          </p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            <span>Tokens: {insight.token_count}</span>
                            <span>
                              Created: {formatDate(insight.created_at)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {!agentMemory.working_memory &&
                  (!agentMemory.insights ||
                    agentMemory.insights.length === 0) && (
                    <p className="text-sm text-muted-foreground italic">
                      No memory data available yet
                    </p>
                  )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderAgentActivity = () => {
    if (!trader?.agent) {
      return (
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">
              <Bot className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No AI agent configured for this trader</p>
            </div>
          </CardContent>
        </Card>
      );
    }

    return (
      <div className="h-full flex flex-col">
        <div className="p-4 pb-3 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Agent Activity Log
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                Agent&apos;s thought process and decision-making history
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={refreshActivities}
              disabled={refreshingActivities}
            >
              {refreshingActivities ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
        <div className="flex-1 min-h-0">
          {agentThoughts.length === 0 ? (
            <div className="p-4">
              <p className="text-sm text-muted-foreground">
                No activity recorded yet
              </p>
            </div>
          ) : (
            <div
              ref={scrollContainerRef}
              className="h-full overflow-y-auto p-4"
            >
              {/* Load more button at the top */}
              {agentThoughts.length >= 50 && (
                <div className="text-center pb-4">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={fetchMoreActivities}
                    disabled={loadingActivities}
                    className="text-xs"
                  >
                    {loadingActivities ? "Loading..." : "Load Earlier Messages"}
                  </Button>
                </div>
              )}

              <div className="space-y-2 flex-1">
                {agentThoughts.map((thought) => {
                  const itemId = thought.thought_id;

                  return (
                    <div
                      key={itemId}
                      className="animate-in fade-in-0 slide-in-from-bottom-2"
                    >
                      {/* Thought item - styled like a chat message */}
                      <div className="flex gap-3 w-full overflow-hidden">
                        <div className="flex-shrink-0 mt-1">
                          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                            {thought.thought_type === "TOOL_CALL" ? (
                              <Zap className="h-4 w-4 text-primary" />
                            ) : thought.thought_type === "ERROR" ? (
                              <X className="h-4 w-4 text-destructive" />
                            ) : (
                              <Brain className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                        </div>
                        <div className="flex-1 min-w-0 overflow-hidden">
                          <div className="flex items-center gap-2 flex-wrap">
                            {thought.thought_type === "ERROR" && (
                              <Badge variant="destructive" className="text-xs">
                                {thought.thought_type}
                              </Badge>
                            )}
                            <span className="text-xs text-muted-foreground">
                              {new Date(
                                thought.created_at
                              ).toLocaleTimeString()}
                            </span>
                          </div>
                          <div
                            className={cn(
                              "rounded-lg p-3 mt-1 overflow-hidden bg-muted/50"
                            )}
                            style={{ maxWidth: "min(100%, 600px)" }}
                          >
                            {(thought.thought_type === "TOOL_CALL" ||
                              thought.content) && (
                              <p className="text-sm whitespace-pre-wrap break-words">
                                {thought.thought_type === "TOOL_CALL"
                                  ? formatToolCallMessage(
                                      thought.tool_name,
                                      thought.tool_args
                                    )
                                  : thought.content}
                              </p>
                            )}
                            {thought.tool_result && (
                              <div className="mt-2 pt-2 border-t border-border/50">
                                <p className="text-xs font-medium text-muted-foreground mb-2">
                                  Result
                                </p>
                                <JsonViewer
                                  data={thought.tool_result}
                                  maxHeight="max-h-60"
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Scroll anchor - always scroll to here */}
                <div ref={activityEndRef} />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl w-[100vw] sm:w-[90vw] h-[82vh] sm:h-[90vh] p-0 flex flex-col overflow-hidden">
        <div className="flex flex-1 min-h-0">
          {/* Side Navigation (hidden on mobile) */}
          <div className="w-64 border-r bg-muted/10 flex-col hidden sm:flex">
            <DialogHeader className="p-6 border-b">
              <DialogTitle className="flex items-center gap-2">
                {trader?.agent ? (
                  <>
                    <Bot className="h-5 w-5 text-primary" />
                    {trader.agent.name}
                  </>
                ) : (
                  <>
                    <Users className="h-5 w-5" />
                    Trader Details
                  </>
                )}
              </DialogTitle>
              {trader && (
                <div className="flex items-center gap-2 mt-2">
                  <Badge
                    variant={trader.is_active ? "default" : "secondary"}
                    className="text-xs"
                  >
                    <Activity className="mr-1 h-3 w-3" />
                    {trader.is_active ? "Active" : "Inactive"}
                  </Badge>
                  {trader.is_admin && (
                    <Badge variant="destructive" className="text-xs">
                      <Shield className="mr-1 h-3 w-3" />
                      Admin
                    </Badge>
                  )}
                </div>
              )}
            </DialogHeader>

            <nav className="flex-1 p-3">
              <div className="space-y-1">
                {navigationItems.map((item) => {
                  if (
                    (item.id === "activity" || item.id === "memory") &&
                    !trader?.agent
                  )
                    return null;
                  if (item.id === "memory" && !isAdmin) return null;

                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveSection(item.id)}
                      className={cn(
                        "w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                        activeSection === item.id
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      <item.icon className="h-5 w-5" />
                      {item.name}
                    </button>
                  );
                })}
              </div>
            </nav>
          </div>

          {/* Content Area */}
          <div className="flex-1 min-w-0 min-h-0 flex flex-col pt-10 sm:pt-0">
            {/* Mobile Section Selector */}
            <div className="sm:hidden p-3 border-b">
              <Select
                value={activeSection}
                onValueChange={(v) => setActiveSection(v as SectionType)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select section" />
                </SelectTrigger>
                <SelectContent>
                  {navigationItems
                    .filter((item) => {
                      if (
                        (item.id === "activity" || item.id === "memory") &&
                        !trader?.agent
                      )
                        return false;
                      if (item.id === "memory" && !isAdmin) return false;
                      return true;
                    })
                    .map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            {loading && (
              <div className="p-6 space-y-4">
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            )}

            {error && (
              <div className="p-6">
                <Card className="border-destructive">
                  <CardHeader>
                    <CardTitle className="text-destructive">Error</CardTitle>
                    <CardDescription>{error}</CardDescription>
                  </CardHeader>
                </Card>
              </div>
            )}

            {trader && !loading && (
              <>
                {activeSection === "overview" && (
                  <ScrollArea className="h-full">
                    <div className="p-6">{renderOverview()}</div>
                  </ScrollArea>
                )}
                {activeSection === "trades" && (
                  <ScrollArea className="h-full">
                    <div className="p-6">{renderTradeHistory()}</div>
                  </ScrollArea>
                )}
                {activeSection === "activity" && renderAgentActivity()}
                {activeSection === "memory" && (
                  <ScrollArea className="h-full">
                    <div className="p-6">{renderMemory()}</div>
                  </ScrollArea>
                )}
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
