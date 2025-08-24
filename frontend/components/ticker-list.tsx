'use client';

import { useQuery } from '@tanstack/react-query';
import { marketService } from '@/services/market';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { formatPrice } from '@/lib/utils';

interface TickerListProps {
  onTickerClick: (ticker: string) => void;
}

export function TickerList({ onTickerClick }: TickerListProps) {
  const { data: prices, isLoading, error } = useQuery({
    queryKey: ['prices'],
    queryFn: marketService.getAllPrices,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader>
              <div className="h-4 bg-muted rounded w-1/2"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted rounded w-3/4"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-destructive">Failed to load tickers</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {prices?.map((price) => (
        <Card
          key={price.ticker}
          className="cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => onTickerClick(price.ticker)}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">{price.ticker}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-2xl font-bold">
                  {formatPrice(price.last_price_in_cents)}
                </span>
                {price.last_price_in_cents && price.best_bid_in_cents && (
                  <div className="flex items-center">
                    {price.last_price_in_cents > price.best_bid_in_cents ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                <div>
                  <span className="block">Bid</span>
                  <span className="font-medium text-foreground">
                    {formatPrice(price.best_bid_in_cents)}
                  </span>
                  {price.bid_size && (
                    <span className="text-xs ml-1">({price.bid_size})</span>
                  )}
                </div>
                <div>
                  <span className="block">Ask</span>
                  <span className="font-medium text-foreground">
                    {formatPrice(price.best_ask_in_cents)}
                  </span>
                  {price.ask_size && (
                    <span className="text-xs ml-1">({price.ask_size})</span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}