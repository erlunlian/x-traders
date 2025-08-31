"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OrderBook } from "./order-book";
import { PriceChart } from "./price-chart";
import { RecentTrades } from "./recent-trades";
import { TickerFeed } from "./ticker-feed";

interface TickerDetailsProps {
  ticker: string | null;
  onClose: () => void;
}

export function TickerDetails({ ticker, onClose }: TickerDetailsProps) {
  if (!ticker) return null;

  return (
    <Dialog open={!!ticker} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl w-[100vw] sm:w-[90vw] h-[82vh] sm:h-[85vh] flex flex-col p-3 sm:p-6">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="text-lg sm:text-2xl">{ticker}</DialogTitle>
        </DialogHeader>

        <Tabs
          defaultValue="chart"
          className="flex-1 flex flex-col overflow-hidden"
        >
          <TabsList className="flex w-full gap-2 overflow-x-auto sm:grid sm:grid-cols-4 flex-shrink-0 h-12 pr-1">
            <TabsTrigger className="min-w-[6.5rem]" value="chart">
              Price Chart
            </TabsTrigger>
            <TabsTrigger className="min-w-[6.5rem]" value="orderbook">
              Order Book
            </TabsTrigger>
            <TabsTrigger className="min-w-[7.5rem]" value="trades">
              Recent Trades
            </TabsTrigger>
            <TabsTrigger className="min-w-[4.5rem]" value="feed">
              Feed
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto mt-2 sm:mt-4">
            <TabsContent value="chart" className="h-full m-0">
              <PriceChart ticker={ticker} />
            </TabsContent>

            <TabsContent value="orderbook" className="h-full m-0">
              <OrderBook ticker={ticker} />
            </TabsContent>

            <TabsContent value="trades" className="h-full m-0">
              <RecentTrades ticker={ticker} />
            </TabsContent>

            <TabsContent value="feed" className="h-full m-0">
              <TickerFeed ticker={ticker} />
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
