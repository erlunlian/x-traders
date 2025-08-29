"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { apiClient } from "@/lib/api/client";
import type { CreateAgentRequest, LLMModel } from "@/types/api";
import { Bot, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

interface CreateAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAgentCreated?: () => void;
}

export function CreateAgentDialog({
  open,
  onOpenChange,
  onAgentCreated,
}: CreateAgentDialogProps) {
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [formData, setFormData] = useState<Partial<CreateAgentRequest>>({
    name: "",
    llm_model: "",
    temperature: 0.7,
    personality_prompt: "",
    is_active: true,
    initial_balance_in_cents: 10000000, // Default $100,000
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      fetchModels();
    }
  }, [open]);

  const fetchModels = async () => {
    try {
      const data = await apiClient.get<LLMModel[]>(
        "/api/agents/models/available"
      );
      setModels(data);
    } catch (err) {
      console.error("Error fetching models:", err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.name || !formData.llm_model || !formData.personality_prompt) {
      setError("Please fill in all required fields");
      return;
    }

    try {
      setLoading(true);
      await apiClient.post("/api/agents/", formData);

      // Reset form
      setFormData({
        name: "",
        llm_model: "",
        temperature: 0.7,
        personality_prompt: "",
        is_active: true,
        initial_balance_in_cents: 10000000,
      });

      onOpenChange(false);
      if (onAgentCreated) {
        onAgentCreated();
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to create agent";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const formatModelName = (model: LLMModel) => {
    return `${model.display_name} (${model.provider})`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Create AI Agent
            </DialogTitle>
            <DialogDescription>
              Configure a new AI trading agent to analyze tweets and make
              trading decisions.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {error && (
              <div className="bg-destructive/10 border border-destructive text-destructive px-3 py-2 rounded-md text-sm">
                {error}
              </div>
            )}

            <div className="grid gap-2">
              <Label htmlFor="name">Agent Name</Label>
              <Input
                id="name"
                placeholder="e.g., Market Analyzer Bot"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                disabled={loading}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="balance">Initial Balance</Label>
              <div className="flex items-center gap-2">
                <span className="text-lg">$</span>
                <Input
                  id="balance"
                  type="number"
                  placeholder="100000"
                  value={(formData.initial_balance_in_cents || 0) / 100}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      initial_balance_in_cents: Math.round(
                        parseFloat(e.target.value || "0") * 100
                      ),
                    })
                  }
                  disabled={loading}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Starting balance for the agent&apos;s trading account
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="model">LLM Model</Label>
              <Select
                value={formData.llm_model}
                onValueChange={(value) =>
                  setFormData({ ...formData, llm_model: value })
                }
                disabled={loading}
              >
                <SelectTrigger id="model">
                  <SelectValue placeholder="Select an LLM model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => (
                    <SelectItem key={model.id} value={model.value}>
                      {formatModelName(model)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="temperature">
                Temperature: {formData.temperature}
              </Label>
              <input
                type="range"
                id="temperature"
                min="0"
                max="1"
                step="0.1"
                value={formData.temperature}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    temperature: parseFloat(e.target.value),
                  })
                }
                className="w-full"
                disabled={loading}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0 (Deterministic)</span>
                <span>1 (Creative)</span>
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="prompt">Personality</Label>
              <Textarea
                id="prompt"
                placeholder="A cautious trader who values stability over risky gains, prefers established accounts with strong fundamentals..."
                value={formData.personality_prompt}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    personality_prompt: e.target.value,
                  })
                }
                rows={6}
                disabled={loading}
              />
              <p className="text-xs text-muted-foreground">
                Define the agent&apos;s unique personality and trading style.
                The system will provide standard trading instructions.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="active"
                checked={formData.is_active}
                onChange={(e) =>
                  setFormData({ ...formData, is_active: e.target.checked })
                }
                className="h-4 w-4"
                disabled={loading}
              />
              <Label htmlFor="active" className="cursor-pointer">
                Activate agent immediately
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Agent
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
