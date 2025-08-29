'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { 
  Users, 
  DollarSign, 
  Calendar, 
  Shield, 
  Activity, 
  TrendingUp, 
  ShoppingCart, 
  History, 
  Bot, 
  Brain, 
  Zap, 
  BarChart3, 
  Pause, 
  Play, 
  Edit, 
  Save, 
  X, 
  Copy, 
  Check,
  ChartBar,
  Clock,
  MessageSquare,
  Package,
  TrendingDown
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import type { Agent, AgentStats, AgentDecision, AgentThought, AgentMemoryState } from '@/types/api';

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
}

type SectionType = 'overview' | 'trades' | 'activity' | 'memory';

const navigationItems = [
  { id: 'overview' as SectionType, name: 'Overview', icon: ChartBar },
  { id: 'trades' as SectionType, name: 'Trade History', icon: History },
  { id: 'activity' as SectionType, name: 'Agent Activity', icon: Brain },
  { id: 'memory' as SectionType, name: 'Memory', icon: MessageSquare },
];

export function AgentDetailDialog({ traderId, open, onOpenChange }: AgentDetailDialogProps) {
  const [activeSection, setActiveSection] = useState<SectionType>('overview');
  const [trader, setTrader] = useState<TraderDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentStats, setAgentStats] = useState<AgentStats | null>(null);
  const [agentDecisions, setAgentDecisions] = useState<AgentDecision[]>([]);
  const [togglingAgent, setTogglingAgent] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedAgent, setEditedAgent] = useState<Partial<Agent> | null>(null);
  const [availableModels, setAvailableModels] = useState<LLMModel[]>([]);
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [loadingDecisions, setLoadingDecisions] = useState(false);
  const [expandedDecision, setExpandedDecision] = useState<string | null>(null);
  const [agentMemory, setAgentMemory] = useState<AgentMemoryState | null>(null);
  const [loadingMemory, setLoadingMemory] = useState(false);

  useEffect(() => {
    if (traderId && open) {
      fetchTraderDetail();
      fetchAvailableModels();
    }
  }, [traderId, open]);

  useEffect(() => {
    // Reset state when dialog closes
    if (!open) {
      setEditMode(false);
      setEditedAgent(null);
      setActiveSection('overview');
      setExpandedDecision(null);
    }
  }, [open]);

  const fetchTraderDetail = async () => {
    if (!traderId) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<TraderDetail>(`/api/traders/${traderId}`);
      setTrader(data);
      
      // If trader has an agent, fetch agent stats, decisions, and memory
      if (data.agent) {
        try {
          const [stats, decisions, memory] = await Promise.all([
            apiClient.get<AgentStats>(`/api/agents/${data.agent.agent_id}/stats`),
            apiClient.get<{ decisions: AgentDecision[] }>(`/api/agents/${data.agent.agent_id}/decisions?limit=20`),
            apiClient.get<AgentMemoryState>(`/api/agents/${data.agent.agent_id}/memory`)
          ]);
          setAgentStats(stats);
          setAgentDecisions(decisions.decisions);
          setAgentMemory(memory);
        } catch (err) {
          console.error('Error fetching agent data:', err);
        }
      }
    } catch (err) {
      setError('Failed to load trader details');
      console.error('Error fetching trader:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchMoreDecisions = async () => {
    if (!trader?.agent || loadingDecisions) return;
    
    try {
      setLoadingDecisions(true);
      const decisions = await apiClient.get<{ decisions: AgentDecision[] }>(
        `/api/agents/${trader.agent.agent_id}/decisions?limit=50&offset=${agentDecisions.length}`
      );
      setAgentDecisions(prev => [...prev, ...decisions.decisions]);
    } catch (err) {
      console.error('Error fetching more decisions:', err);
    } finally {
      setLoadingDecisions(false);
    }
  };

  const formatCurrency = (cents: number) => {
    const isNegative = cents < 0;
    const absValue = Math.abs(cents);
    return `${isNegative ? '-' : ''}$${(absValue / 100).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const fetchAvailableModels = async () => {
    try {
      const models = await apiClient.get<LLMModel[]>('/api/agents/models/available');
      setAvailableModels(models);
    } catch (err) {
      console.error('Error fetching models:', err);
    }
  };

  const toggleAgent = async () => {
    if (!trader?.agent) return;
    
    try {
      setTogglingAgent(true);
      const updatedAgent = await apiClient.post<Agent>(`/api/agents/${trader.agent.agent_id}/toggle`);
      
      // Update the trader's agent in state
      setTrader(prev => prev ? {
        ...prev,
        agent: updatedAgent
      } : null);
    } catch (err) {
      console.error('Error toggling agent:', err);
    } finally {
      setTogglingAgent(false);
    }
  };

  const startEdit = () => {
    if (trader?.agent) {
      setEditedAgent({
        ...trader.agent
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
      setTrader(prev => prev ? {
        ...prev,
        agent: updatedAgent
      } : null);
      
      setEditMode(false);
      setEditedAgent(null);
    } catch (err) {
      console.error('Error saving agent:', err);
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
      console.error('Failed to copy:', err);
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
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={startEdit}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant={trader.agent.is_active ? "destructive" : "default"}
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
            <CardContent className="space-y-3">
              {/* Model field */}
              <div className="flex items-center justify-between">
                <Label className="text-sm">Model</Label>
                {!editMode ? (
                  <Badge variant="outline">{trader.agent.llm_model}</Badge>
                ) : (
                  <Select
                    value={editedAgent?.llm_model}
                    onValueChange={(value) => setEditedAgent(prev => prev ? {...prev, llm_model: value} : null)}
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

              {/* Temperature field */}
              <div className="flex items-center justify-between">
                <Label className="text-sm">Temperature</Label>
                {!editMode ? (
                  <span className="font-mono text-sm">{trader.agent.temperature}</span>
                ) : (
                  <Input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={editedAgent?.temperature || 0}
                    onChange={(e) => setEditedAgent(prev => prev ? {...prev, temperature: parseFloat(e.target.value)} : null)}
                    className="w-20 h-8"
                  />
                )}
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-sm">Status</Label>
                <Badge variant={trader.agent.is_active ? "default" : "secondary"}>
                  <Activity className="mr-1 h-3 w-3" />
                  {trader.agent.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>

              {/* IDs with copy buttons */}
              <div className="pt-3 border-t space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Agent ID</span>
                  <div className="flex items-center gap-2">
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                      {trader.agent.agent_id.slice(0, 8)}...
                    </code>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      onClick={() => copyToClipboard(trader.agent?.agent_id || '', 'agent')}
                    >
                      {copiedId === 'agent' ? (
                        <Check className="h-3 w-3 text-green-600" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Trader ID</span>
                  <div className="flex items-center gap-2">
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                      {trader.trader_id.slice(0, 8)}...
                    </code>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      onClick={() => copyToClipboard(trader.trader_id, 'trader')}
                    >
                      {copiedId === 'trader' ? (
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
        <div className="grid gap-4 md:grid-cols-2">
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

          {agentStats && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  <div className="text-center">
                    <div className="text-lg font-bold">{agentStats.trade_decisions}</div>
                    <div className="text-xs text-muted-foreground">Decisions</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold">{agentStats.executed_trades}</div>
                    <div className="text-xs text-muted-foreground">Executed</div>
                  </div>
                  <div className="col-span-2 text-center pt-2 border-t">
                    <div className="text-lg font-bold">{agentStats.execution_rate.toFixed(1)}%</div>
                    <div className="text-xs text-muted-foreground">Success Rate</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

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
                        {position.quantity} shares @ {formatCurrency(position.avg_cost)}
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
              <p className="text-sm text-muted-foreground">No unfilled orders</p>
            ) : (
              <div className="space-y-2">
                {trader.unfilled_orders.map((order) => (
                  <div 
                    key={order.order_id}
                    className="p-3 rounded-lg border"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{order.ticker}</span>
                      <Badge variant={order.side === 'BUY' ? 'default' : 'destructive'}>
                        {order.side}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                      <div>Type: {order.order_type}</div>
                      <div>Status: {order.status}</div>
                      <div>Quantity: {order.filled_quantity}/{order.quantity}</div>
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
              <p className="text-sm text-muted-foreground">No trades executed yet</p>
            ) : (
              <div className="space-y-2">
                {trader.recent_trades.map((trade) => (
                  <div 
                    key={trade.trade_id}
                    className="p-3 rounded-lg border"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{trade.ticker}</span>
                      <Badge 
                        variant={trade.side === 'BUY' ? 'default' : 'destructive'}
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
                        <span>Tokens: {agentMemory.working_memory.token_count}</span>
                        <span>Updated: {formatDate(agentMemory.working_memory.created_at)}</span>
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
                        <div key={insight.memory_id || index} className="bg-muted/30 p-3 rounded-lg">
                          <p className="text-sm whitespace-pre-wrap">
                            {insight.content}
                          </p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            <span>Tokens: {insight.token_count}</span>
                            <span>Created: {formatDate(insight.created_at)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(!agentMemory.working_memory && (!agentMemory.insights || agentMemory.insights.length === 0)) && (
                  <p className="text-sm text-muted-foreground italic">No memory data available yet</p>
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
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Agent Activity Log
            </CardTitle>
            <CardDescription>
              Agent's thought process and decision-making history
            </CardDescription>
          </CardHeader>
          <CardContent>
            {agentDecisions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No decisions made yet</p>
            ) : (
              <div className="space-y-3">
                {agentDecisions.map((decision) => (
                  <div
                    key={decision.decision_id}
                    className="border rounded-lg overflow-hidden"
                  >
                    <button
                      className="w-full p-4 text-left hover:bg-muted/50 transition-colors"
                      onClick={() => setExpandedDecision(
                        expandedDecision === decision.decision_id ? null : decision.decision_id
                      )}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={
                              decision.action === 'BUY' ? 'default' : 
                              decision.action === 'SELL' ? 'destructive' : 
                              'secondary'
                            }
                          >
                            {decision.action}
                          </Badge>
                          {decision.ticker && (
                            <span className="font-semibold">{decision.ticker}</span>
                          )}
                          {decision.quantity && (
                            <span className="text-sm text-muted-foreground">
                              x{decision.quantity}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="outline" className="text-xs">
                            <Zap className="mr-1 h-3 w-3" />
                            {decision.trigger_type}
                          </Badge>
                          <Clock className="h-3 w-3" />
                          <span>{formatDate(decision.created_at)}</span>
                        </div>
                      </div>
                      {decision.reasoning && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {decision.reasoning}
                        </p>
                      )}
                      {decision.executed && (
                        <Badge variant="outline" className="mt-2 text-xs">
                          <Check className="mr-1 h-3 w-3" />
                          Executed
                        </Badge>
                      )}
                    </button>
                    
                    {expandedDecision === decision.decision_id && (
                      <div className="border-t bg-muted/20 p-4">
                        {decision.thoughts && decision.thoughts.length > 0 ? (
                          <>
                            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                              <MessageSquare className="h-4 w-4" />
                              Thought Process
                            </h4>
                            <div className="space-y-2">
                              {decision.thoughts.map((thought, index) => (
                                <div key={thought.thought_id || index} className="flex gap-3">
                                  <div className="flex-shrink-0">
                                    <Badge variant="outline" className="text-xs">
                                      Step {thought.step_number || index + 1}
                                    </Badge>
                                  </div>
                                  <div className="flex-1">
                                    <div className="text-xs text-muted-foreground mb-1 font-medium">
                                      {thought.thought_type}
                                    </div>
                                    <p className="text-sm whitespace-pre-wrap">
                                      {thought.content}
                                    </p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </>
                        ) : (
                          <p className="text-sm text-muted-foreground italic">No thought process recorded for this decision</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                
                {agentDecisions.length >= 20 && (
                  <div className="text-center pt-4">
                    <Button 
                      variant="outline" 
                      onClick={fetchMoreDecisions}
                      disabled={loadingDecisions}
                    >
                      {loadingDecisions ? 'Loading...' : 'Load More'}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl h-[90vh] p-0">
        <div className="flex h-full">
          {/* Side Navigation */}
          <div className="w-64 border-r bg-muted/10 flex flex-col">
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
                  <Badge variant={trader.is_active ? "default" : "secondary"} className="text-xs">
                    <Activity className="mr-1 h-3 w-3" />
                    {trader.is_active ? 'Active' : 'Inactive'}
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
                  // Hide activity and memory sections if no agent
                  if ((item.id === 'activity' || item.id === 'memory') && !trader?.agent) return null;
                  
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveSection(item.id)}
                      className={cn(
                        'w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        activeSection === item.id
                          ? 'bg-primary/10 text-primary'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
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
          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="p-6">
                {loading && (
                  <div className="space-y-4">
                    <Skeleton className="h-32 w-full" />
                    <Skeleton className="h-32 w-full" />
                    <Skeleton className="h-32 w-full" />
                  </div>
                )}

                {error && (
                  <Card className="border-destructive">
                    <CardHeader>
                      <CardTitle className="text-destructive">Error</CardTitle>
                      <CardDescription>{error}</CardDescription>
                    </CardHeader>
                  </Card>
                )}

                {trader && !loading && (
                  <>
                    {activeSection === 'overview' && renderOverview()}
                    {activeSection === 'trades' && renderTradeHistory()}
                    {activeSection === 'activity' && renderAgentActivity()}
                    {activeSection === 'memory' && renderMemory()}
                  </>
                )}
              </div>
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}