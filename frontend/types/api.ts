export interface CurrentPrice {
  ticker: string;
  last_price_in_cents: number | null;
  best_bid_in_cents: number | null;
  best_ask_in_cents: number | null;
  bid_size: number | null;
  ask_size: number | null;
  timestamp: string;
}

export interface Trade {
  trade_id: string;
  ticker: string;
  price_in_cents: number;
  quantity: number;
  buyer_id: string;
  seller_id: string;
  executed_at: string;
}

export interface OrderBookLevel {
  price_in_cents: number;
  quantity: number;
}

export interface OrderBookSnapshot {
  ticker: string;
  bids: Record<string, number>; // price_in_cents -> quantity
  asks: Record<string, number>; // price_in_cents -> quantity
  last_price_in_cents: number | null;
  timestamp: string;
}

export interface PriceHistory {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Agent {
  agent_id: string;
  name: string;
  trader_id: string;
  llm_model: string;
  temperature: number;
  personality_prompt: string;
  is_active: boolean;
  total_decisions: number;
  last_decision_at: string | null;
  created_at: string;
  last_processed_tweet_at?: string | null;
}

export interface AgentThought {
  thought_id: string;
  agent_id: string;
  step_number: number;
  thought_type: string;
  content: string;
  tool_name?: string | null;
  tool_args?: string | null;
  tool_result?: string | null;
  created_at: string;
}


export interface AgentStats {
  agent_id: string;
  name: string;
  llm_model: string;
  is_active: boolean;
  total_thoughts: number;
  thought_breakdown: Record<string, number>;
  last_activity_at: string | null;
}

export interface MemoryInfo {
  memory_id: string;
  memory_type: string;
  content: string;
  token_count: number;
  created_at: string;
}

export interface AgentMemoryState {
  working_memory: MemoryInfo | null;
  insights: MemoryInfo[];
  total_insights: number;
}

export interface ThoughtListResponse {
  thoughts: AgentThought[];
  total: number;
  offset: number;
  limit: number;
}

export interface AgentLeaderboardEntry {
  agent_id: string;
  name: string;
  trader_id: string;
  llm_model: string;
  is_active: boolean;
  balance_in_cents: number;
  total_assets_value_in_cents: number;
  total_trades_executed: number;
  total_decisions: number;
  profit_loss_in_cents: number;
  created_at: string;
  last_decision_at: string | null;
}

export interface AgentLeaderboardResponse {
  agents: AgentLeaderboardEntry[];
  total: number;
}

export interface CreateAgentRequest {
  name: string;
  llm_model: string;
  personality_prompt: string;
  temperature?: number;
  is_active?: boolean;
  initial_balance_in_cents?: number;
}

export interface UpdateAgentRequest {
  temperature?: number;
  personality_prompt?: string;
  is_active?: boolean;
}

export interface LLMModel {
  id: string;
  value: string;
  provider: string;
  display_name: string;
}

export interface Trader {
  trader_id: string;
  is_active: boolean;
  is_admin: boolean;
  balance_in_cents: number;
  created_at: string;
  agent?: Agent;
}

export interface Position {
  ticker: string;
  quantity: number;
  average_cost_in_cents: number;
  market_value_in_cents: number;
  pnl_in_cents: number;
}

export interface Portfolio {
  agent_id: string;
  positions: Position[];
  cash_balance_in_cents: number;
  total_value_in_cents: number;
}

export type AdminOrderRequest = {
  trader_id: string;
  ticker: string;
  side: "BUY" | "SELL";
  order_type: "MARKET" | "LIMIT" | "IOC";
  quantity: number;
  limit_price_in_cents?: number | null;
  tif_seconds?: number;
};

export type AdminOrderResponse = {
  order_id: string;
};

export type CreateTraderResponse = {
  trader_id: string;
};
