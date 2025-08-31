import { apiClient } from "@/lib/api/client";
import type {
  CurrentPrice,
  OrderBookSnapshot,
  PriceHistory,
  Trade,
} from "@/types/api";

export const marketService = {
  // Get all tickers
  async getTickers(): Promise<string[]> {
    return apiClient.get<string[]>("/api/tickers");
  },

  // Get current price for a ticker
  async getPrice(ticker: string): Promise<CurrentPrice> {
    return apiClient.get<CurrentPrice>(`/api/exchange/price/${ticker}`);
  },

  // Get all prices
  async getAllPrices(): Promise<CurrentPrice[]> {
    return apiClient.get<CurrentPrice[]>("/api/exchange/prices");
  },

  // Get recent trades
  async getRecentTrades(ticker: string, limit: number = 50): Promise<Trade[]> {
    return apiClient.get<Trade[]>(
      `/api/exchange/trades/${ticker}?limit=${limit}`
    );
  },

  // Get order book
  async getOrderBook(ticker: string): Promise<OrderBookSnapshot> {
    return apiClient.get<OrderBookSnapshot>(
      `/api/exchange/orderbook/${ticker}`
    );
  },

  // Get price history (to be implemented in backend)
  async getPriceHistory(
    ticker: string,
    timeRange: "1d" | "1w" | "1m" | "6m" | "1y"
  ): Promise<PriceHistory[]> {
    return apiClient.get<PriceHistory[]>(
      `/api/exchange/price-history/${ticker}?range=${timeRange}`
    );
  },
  // Get recent agent monitor errors
  async getMonitorErrors(limit: number = 100): Promise<
    Array<{
      timestamp: string;
      error_type: string;
      message: string;
      traceback?: string;
    }>
  > {
    return apiClient.get(
      `/api/agents/monitor/errors?limit=${encodeURIComponent(String(limit))}`
    );
  },
};
