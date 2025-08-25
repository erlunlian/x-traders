'use client';

import { useState, useEffect } from 'react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Users, DollarSign, Calendar, Shield, Activity, TrendingUp, ShoppingCart, History } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

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
}

interface TraderDetailDrawerProps {
  traderId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TraderDetailDrawer({ traderId, open, onOpenChange }: TraderDetailDrawerProps) {
  const [trader, setTrader] = useState<TraderDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (traderId && open) {
      fetchTraderDetail();
    }
  }, [traderId, open]);

  const fetchTraderDetail = async () => {
    if (!traderId) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<TraderDetail>(`/api/traders/${traderId}`);
      setTrader(data);
    } catch (err) {
      setError('Failed to load trader details');
      console.error('Error fetching trader:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(cents / 100);
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
            {trader && (
              <div className="space-y-2 mt-2">
                <div className="flex items-center gap-2">
                  <Badge variant={trader.is_active ? "default" : "secondary"}>
                    <Activity className="mr-1 h-3 w-3" />
                    {trader.is_active ? 'Active' : 'Inactive'}
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
          </SheetDescription>
        </SheetHeader>

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
          <div className="mt-6 space-y-6">
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
                  <p className="text-sm text-muted-foreground">No positions</p>
                ) : (
                  <div className="space-y-2">
                    {trader.positions.map((position) => (
                      <div 
                        key={position.ticker}
                        className="flex items-center justify-between p-2 rounded-lg border"
                      >
                        <div>
                          <div className="font-semibold text-sm">{position.ticker}</div>
                          <div className="text-xs text-muted-foreground">
                            {position.quantity} @ {formatCurrency(position.avg_cost)}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold text-sm">
                            {formatCurrency(position.quantity * position.avg_cost)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

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
                  <ScrollArea className="h-64">
                    <div className="space-y-2">
                      {trader.unfilled_orders.map((order) => (
                        <div 
                          key={order.order_id}
                          className="p-2 rounded-lg border"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-sm">{order.ticker}</span>
                            <Badge variant={order.side === 'BUY' ? 'default' : 'destructive'} className="text-xs">
                              {order.side}
                            </Badge>
                          </div>
                          <div className="text-xs text-muted-foreground space-y-1">
                            <div className="flex justify-between">
                              <span>{order.order_type}</span>
                              <span>{order.filled_quantity}/{order.quantity}</span>
                            </div>
                            {order.limit_price && (
                              <div>Limit: {formatCurrency(order.limit_price)}</div>
                            )}
                            <div className="flex justify-between">
                              <Badge variant="outline" className="text-xs">
                                {order.status}
                              </Badge>
                              <span>{new Date(order.created_at).toLocaleTimeString()}</span>
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
                  <p className="text-sm text-muted-foreground">No trades yet</p>
                ) : (
                  <ScrollArea className="h-64">
                    <div className="space-y-2">
                      {trader.recent_trades.map((trade) => (
                        <div 
                          key={trade.trade_id}
                          className="p-2 rounded-lg border"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-sm">{trade.ticker}</span>
                            <Badge 
                              variant={trade.side === 'BUY' ? 'default' : 'destructive'}
                              className="text-xs"
                            >
                              {trade.side}
                            </Badge>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            <div className="flex justify-between">
                              <span>{trade.quantity} @ {formatCurrency(trade.price)}</span>
                              <span className="font-semibold">
                                {formatCurrency(trade.price * trade.quantity)}
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
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}