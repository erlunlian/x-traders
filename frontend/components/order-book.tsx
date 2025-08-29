"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatPrice } from "@/lib/utils";
import { marketService } from "@/services/market";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";

interface OrderBookProps {
  ticker: string;
}

export function OrderBook({ ticker }: OrderBookProps) {
  const { data: orderBook, isLoading } = useQuery({
    queryKey: ["orderbook", ticker],
    queryFn: () => marketService.getOrderBook(ticker),
    refetchInterval: 2000, // Refresh every 2 seconds
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Order Book</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (!orderBook) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Order Book</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No order book data available</p>
        </CardContent>
      </Card>
    );
  }

  // Convert and sort bids (highest first) and asks (lowest first)
  const bids = Object.entries(orderBook.bids)
    .map(([price, quantity]) => ({
      price: parseInt(price),
      quantity,
    }))
    .sort((a, b) => b.price - a.price)
    .slice(0, 10);

  const asks = Object.entries(orderBook.asks)
    .map(([price, quantity]) => ({
      price: parseInt(price),
      quantity,
    }))
    .sort((a, b) => a.price - b.price)
    .slice(0, 10);

  const maxQuantity = Math.max(
    ...bids.map((b) => b.quantity),
    ...asks.map((a) => a.quantity)
  );

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle>Order Book - {ticker}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        <div className="space-y-4">
          {/* Asks (Sell Orders) */}
          <div>
            <h4 className="text-sm font-medium text-muted-foreground mb-2">
              Asks
            </h4>
            <div className="space-y-1">
              {asks.length > 0 ? (
                asks.map((ask, i) => (
                  <div
                    key={`ask-${i}`}
                    className="grid grid-cols-3 gap-2 text-sm relative"
                  >
                    <div
                      className="absolute inset-0 bg-red-500 opacity-10"
                      style={{
                        width: `${(ask.quantity / maxQuantity) * 100}%`,
                      }}
                    />
                    <span className="text-red-500 font-medium z-10">
                      {formatPrice(ask.price)}
                    </span>
                    <span className="text-center z-10">
                      {formatNumber(ask.quantity)}
                    </span>
                    <span className="text-right text-muted-foreground z-10">
                      {formatPrice(ask.price * ask.quantity)}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No sell orders</p>
              )}
            </div>
          </div>

          {/* Spread */}
          <div className="border-t border-b py-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Spread</span>
              <span className="font-medium">
                {asks.length > 0 && bids.length > 0
                  ? formatPrice(asks[0].price - bids[0].price)
                  : "-"}
              </span>
            </div>
            {orderBook.current_price_in_cents && (
              <div className="flex justify-between text-sm mt-1">
                <span className="text-muted-foreground">Current Price</span>
                <span className="font-medium">
                  {formatPrice(orderBook.current_price_in_cents)}
                </span>
              </div>
            )}
          </div>

          {/* Bids (Buy Orders) */}
          <div>
            <h4 className="text-sm font-medium text-muted-foreground mb-2">
              Bids
            </h4>
            <div className="space-y-1">
              {bids.length > 0 ? (
                bids.map((bid, i) => (
                  <div
                    key={`bid-${i}`}
                    className="grid grid-cols-3 gap-2 text-sm relative"
                  >
                    <div
                      className="absolute inset-0 bg-green-500 opacity-10"
                      style={{
                        width: `${(bid.quantity / maxQuantity) * 100}%`,
                      }}
                    />
                    <span className="text-green-500 font-medium z-10">
                      {formatPrice(bid.price)}
                    </span>
                    <span className="text-center z-10">
                      {formatNumber(bid.quantity)}
                    </span>
                    <span className="text-right text-muted-foreground z-10">
                      {formatPrice(bid.price * bid.quantity)}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No buy orders</p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
