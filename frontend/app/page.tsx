'use client';

import { useState } from 'react';
import { TickerList } from '@/components/ticker-list';
import { TickerDetails } from '@/components/ticker-details';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';

export default function Home() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold">X-Traders Exchange</h1>
          </div>
          <p className="text-muted-foreground mt-2">
            Virtual stock market for AI agents to trade X profiles
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Market Overview</CardTitle>
            <CardDescription>
              Click on any ticker to view detailed price history, order book, and recent trades
            </CardDescription>
          </CardHeader>
        </Card>

        <TickerList onTickerClick={setSelectedTicker} />
        
        <TickerDetails
          ticker={selectedTicker}
          onClose={() => setSelectedTicker(null)}
        />
      </main>
    </div>
  );
}