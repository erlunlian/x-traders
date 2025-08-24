'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PriceChart } from './price-chart';
import { OrderBook } from './order-book';
import { RecentTrades } from './recent-trades';

interface TickerDetailsProps {
  ticker: string | null;
  onClose: () => void;
}

export function TickerDetails({ ticker, onClose }: TickerDetailsProps) {
  if (!ticker) return null;

  return (
    <Dialog open={!!ticker} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl w-[90vw] h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="text-2xl">{ticker}</DialogTitle>
        </DialogHeader>
        
        <Tabs defaultValue="chart" className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid w-full grid-cols-3 flex-shrink-0">
            <TabsTrigger value="chart">Price Chart</TabsTrigger>
            <TabsTrigger value="orderbook">Order Book</TabsTrigger>
            <TabsTrigger value="trades">Recent Trades</TabsTrigger>
          </TabsList>
          
          <div className="flex-1 overflow-y-auto mt-4">
            <TabsContent value="chart" className="h-full m-0">
              <PriceChart ticker={ticker} />
            </TabsContent>
            
            <TabsContent value="orderbook" className="h-full m-0">
              <OrderBook ticker={ticker} />
            </TabsContent>
            
            <TabsContent value="trades" className="h-full m-0">
              <RecentTrades ticker={ticker} />
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}