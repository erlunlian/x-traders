'use client';

import { useState } from 'react';
import { TickerList } from '@/components/ticker-list';
import { TickerDetails } from '@/components/ticker-details';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function Home() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-8 py-8">
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