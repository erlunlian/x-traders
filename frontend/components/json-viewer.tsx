"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

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
  maxHeight = "max-h-60"
}: JsonViewerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  
  // Try to parse and format JSON
  let formattedData = data;
  let isValidJson = false;
  
  try {
    const parsed = JSON.parse(data);
    formattedData = JSON.stringify(parsed, null, 2);
    isValidJson = true;
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
    <div className={cn("block w-full overflow-hidden", className)}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <span>{expanded ? "Collapse" : "Expand"}</span>
        <span className="text-muted-foreground/60 ml-1">
          ({formattedData.length} chars)
        </span>
      </button>
      
      {expanded && (
        <div 
          className={cn(
            "mt-1 rounded border border-border/50 bg-background/50 overflow-hidden",
            maxHeight
          )}
        >
          <pre 
            className="text-xs p-2 overflow-auto whitespace-pre block"
            style={{ 
              wordBreak: "normal", 
              overflowWrap: "normal",
              width: "100%",
              minWidth: 0
            }}
          >
            <code>{formattedData}</code>
          </pre>
        </div>
      )}
      
      {!expanded && (
        <div className="text-xs text-muted-foreground font-mono truncate mt-1">
          {formattedData.substring(0, 80)}...
        </div>
      )}
    </div>
  );
}