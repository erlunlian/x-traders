"use client";

import { cn } from "@/lib/utils";
import { ChevronRight, ChevronUp } from "lucide-react";
import { useState } from "react";

interface JsonViewerProps {
  data: string;
  className?: string;
  defaultExpanded?: boolean;
  maxHeight?: string;
}

export function JsonViewer({
  data,
  className,
  defaultExpanded = false,
  maxHeight = "max-h-96",
}: JsonViewerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  let formattedData = data;

  try {
    const parsed = JSON.parse(data);
    formattedData = JSON.stringify(parsed, null, 2);
  } catch {
    // If not valid JSON, show as-is
    formattedData = data;
  }

  // For simple/short data, just show it inline
  if (formattedData.length < 100) {
    return (
      <div className={cn("font-mono text-xs break-all", className)}>
        {formattedData}
      </div>
    );
  }

  return (
    <div className={cn("block w-full", className)}>
      {expanded ? (
        <>
          <div
            className={cn(
              "rounded border border-border/50 bg-background/50 overflow-auto overscroll-contain",
              maxHeight
            )}
          >
            <pre
              className="text-xs p-2 whitespace-pre block max-w-full"
              style={{
                wordBreak: "normal",
                overflowWrap: "normal",
                width: "100%",
                minWidth: 0,
              }}
            >
              <code>{formattedData}</code>
            </pre>
          </div>

          <button
            onClick={() => setExpanded(false)}
            className="mt-1 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronUp className="h-3 w-3" />
            <span>Collapse</span>
            <span className="text-muted-foreground/60 ml-1">
              ({formattedData.length} chars)
            </span>
          </button>
        </>
      ) : (
        <>
          <div className="text-xs text-muted-foreground font-mono truncate">
            {formattedData.substring(0, 80)}...
          </div>

          <button
            onClick={() => setExpanded(true)}
            className="mt-1 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronRight className="h-3 w-3" />
            <span>Expand</span>
            <span className="text-muted-foreground/60 ml-1">
              ({formattedData.length} chars)
            </span>
          </button>
        </>
      )}
    </div>
  );
}
