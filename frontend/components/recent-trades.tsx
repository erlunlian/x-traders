'use client';

import { useQuery } from '@tanstack/react-query';
import { marketService } from '@/services/market';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatPrice, formatNumber } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface RecentTradesProps {
  ticker: string;
}

export function RecentTrades({ ticker }: RecentTradesProps) {
  const { data: trades, isLoading } = useQuery({
    queryKey: ['trades', ticker],
    queryFn: () => marketService.getRecentTrades(ticker, 20),
    refetchInterval: 3000, // Refresh every 3 seconds
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Trades</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (!trades || trades.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Trades</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No recent trades</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle>Recent Trades - {ticker}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead className="text-right">Quantity</TableHead>
              <TableHead className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {trades.map((trade) => {
              const tradeTime = new Date(trade.executed_at);
              const isRecent = Date.now() - tradeTime.getTime() < 10000; // Less than 10 seconds

              return (
                <TableRow
                  key={trade.trade_id}
                  className={isRecent ? 'bg-accent/50' : ''}
                >
                  <TableCell className="font-mono text-sm">
                    {tradeTime.toLocaleTimeString()}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatPrice(trade.price_in_cents)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(trade.quantity)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {formatPrice(trade.price_in_cents * trade.quantity)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}