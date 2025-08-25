"use client";

import { apiClient } from "@/lib/api/client";
import type {
  AdminOrderRequest,
  AdminOrderResponse,
  CreateTraderResponse,
} from "@/types/api";
import { useState } from "react";

type Side = "BUY" | "SELL";
type OrderType = "MARKET" | "LIMIT" | "IOC";

export default function AdminPage() {
  const [traderId, setTraderId] = useState<string>("");
  const [ticker, setTicker] = useState<string>("@elonmusk");
  const [side, setSide] = useState<Side>("BUY");
  const [orderType, setOrderType] = useState<OrderType>("MARKET");
  const [quantity, setQuantity] = useState<number>(1);
  const [limitPrice, setLimitPrice] = useState<number | "">("");
  const [tifSeconds, setTifSeconds] = useState<number>(60);
  const [message, setMessage] = useState<string>("");

  const createTrader = async () => {
    setMessage("");
    try {
      const res = await apiClient.post<CreateTraderResponse>(
        "/api/admin/trader",
        {
          initial_cash_in_cents: 1_000_000_000_000,
        }
      );
      setTraderId(res.trader_id);
      setMessage(`Created trader: ${res.trader_id}`);
    } catch (e: any) {
      setMessage(e?.message || "Failed to create trader");
    }
  };

  const submitOrder = async () => {
    setMessage("");
    try {
      const payload: AdminOrderRequest = {
        trader_id: traderId,
        ticker,
        side,
        order_type: orderType,
        quantity,
        limit_price_in_cents: orderType === "LIMIT" ? Number(limitPrice) : null,
        tif_seconds: tifSeconds,
      };
      const res = await apiClient.post<AdminOrderResponse>(
        "/api/admin/order",
        payload
      );
      setMessage(`Order submitted: ${res.order_id}`);
    } catch (e: any) {
      setMessage(e?.message || "Failed to submit order");
    }
  };

  return (
    <div className="container mx-auto px-8 py-8">
      <div className="max-w-2xl space-y-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Admin Console</h1>
          <p className="text-muted-foreground mt-2">
            Create traders and execute trades with admin privileges
          </p>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium">Admin Trader</label>
          <div className="flex gap-2">
            <input
              className="flex-1 border rounded px-3 py-2"
              placeholder="Trader ID"
              value={traderId}
              onChange={(e) => setTraderId(e.target.value)}
            />
            <button className="border rounded px-3 py-2" onClick={createTrader}>
              Create Admin Trader
            </button>
          </div>
          <p className="text-xs text-gray-500">
            Admin buys ignore cash limits. Sells still require owned shares.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium">Ticker</label>
            <input
              className="w-full border rounded px-3 py-2"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium">Side</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={side}
              onChange={(e) => setSide(e.target.value as Side)}
            >
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium">Order Type</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={orderType}
              onChange={(e) => setOrderType(e.target.value as OrderType)}
            >
              <option value="MARKET">MARKET</option>
              <option value="LIMIT">LIMIT</option>
              <option value="IOC">IOC (Immediate or Cancel)</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium">Quantity</label>
            <input
              className="w-full border rounded px-3 py-2"
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />
          </div>
          {orderType === "LIMIT" && (
            <>
              <div className="space-y-2">
                <label className="block text-sm font-medium">
                  Limit Price (cents)
                </label>
                <input
                  className="w-full border rounded px-3 py-2"
                  type="number"
                  value={limitPrice}
                  onChange={(e) =>
                    setLimitPrice(e.target.value ? Number(e.target.value) : "")
                  }
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium">
                  TIF (seconds)
                </label>
                <input
                  className="w-full border rounded px-3 py-2"
                  type="number"
                  value={tifSeconds}
                  onChange={(e) => setTifSeconds(Number(e.target.value))}
                />
              </div>
            </>
          )}
        </div>

        <div className="flex gap-2">
          <button
            className="border rounded px-4 py-2"
            onClick={submitOrder}
            disabled={!traderId}
          >
            Submit Order
          </button>
        </div>

        {message && <div className="text-sm text-gray-700">{message}</div>}
      </div>
    </div>
  );
}