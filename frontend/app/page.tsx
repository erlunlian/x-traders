"use client";

import { TickerDetails } from "@/components/ticker-details";
import { TickerList } from "@/components/ticker-list";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useState } from "react";

export default function Home() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-8 py-8">
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Market Overview</CardTitle>
            <CardDescription>
              This app is a simulated market where ai trader agents trade shares
              of X profiles.
            </CardDescription>
            <CardDescription>
              Click on any ticker to view detailed price history, order book,
              and recent trades
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
