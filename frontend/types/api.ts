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
  prompt: string;
  balance_in_cents: number;
  created_at: string;
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