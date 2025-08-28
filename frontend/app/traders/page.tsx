'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, DollarSign, Calendar, Shield, Activity, Bot, Plus } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { TraderDetailDrawer } from '@/components/trader-detail-drawer';
import { CreateAgentDialog } from '@/components/create-agent-dialog';
import type { Trader } from '@/types/api';

export default function TradersPage() {
  const [traders, setTraders] = useState<Trader[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTraderId, setSelectedTraderId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [createAgentOpen, setCreateAgentOpen] = useState(false);

  useEffect(() => {
    fetchTraders();
  }, []);

  const fetchTraders = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<Trader[]>('/api/traders/');
      setTraders(data);
    } catch (err) {
      setError('Failed to load traders');
      console.error('Error fetching traders:', err);
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

  const handleTraderClick = (traderId: string) => {
    setSelectedTraderId(traderId);
    setDrawerOpen(true);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Traders</h1>
          <p className="text-muted-foreground mt-2">
            All traders on the X-Traders exchange
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-32 mb-2" />
                <Skeleton className="h-3 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-8 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-8 py-8">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Traders</h1>
            <p className="text-muted-foreground mt-2">
              All traders on the X-Traders exchange
            </p>
          </div>
          <Button onClick={() => setCreateAgentOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Agent
          </Button>
        </div>
      </div>

      {traders.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No Traders Yet</CardTitle>
            <CardDescription>
              No traders have been created. Use the Admin panel to create new traders.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {traders.map((trader) => (
            <Card 
              key={trader.trader_id} 
              className="hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => handleTraderClick(trader.trader_id)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      Trader
                      {trader.is_admin && (
                        <Badge variant="destructive" className="ml-2">
                          <Shield className="mr-1 h-3 w-3" />
                          Admin
                        </Badge>
                      )}
                      {trader.agent && (
                        <Badge variant="outline" className="ml-2 bg-primary/10">
                          <Bot className="mr-1 h-3 w-3" />
                          AI Agent
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      <Badge variant="outline" className="mt-2">
                        <Users className="mr-1 h-3 w-3" />
                        {trader.trader_id.slice(0, 8)}...
                      </Badge>
                    </CardDescription>
                  </div>
                  <Badge 
                    variant={trader.is_active ? "default" : "secondary"}
                    className="ml-2"
                  >
                    <Activity className="mr-1 h-3 w-3" />
                    {trader.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between pt-4 border-t">
                  <div className="flex items-center text-sm">
                    <DollarSign className="mr-1 h-4 w-4 text-green-600" />
                    <span className="font-semibold">
                      {formatCurrency(trader.balance_in_cents)}
                    </span>
                  </div>
                  <div className="flex items-center text-xs text-muted-foreground">
                    <Calendar className="mr-1 h-3 w-3" />
                    {formatDate(trader.created_at)}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      
      <TraderDetailDrawer
        traderId={selectedTraderId}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
      
      <CreateAgentDialog
        open={createAgentOpen}
        onOpenChange={setCreateAgentOpen}
        onAgentCreated={fetchTraders}
      />
    </div>
  );
}