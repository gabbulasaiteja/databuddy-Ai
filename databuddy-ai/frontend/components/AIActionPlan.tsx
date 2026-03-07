"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info, Play } from "lucide-react";
import { useAppStore } from "@/lib/store";

export function AIActionPlan() {
  const { sql, isExecuting, executeSQL, messages, isTranslating } = useAppStore();
  
  // Get the latest AI explanation/plan from messages
  const latestSystemMessage = messages
    .filter((msg) => msg.role === "system")
    .slice(-1)[0];
  
  const latestPlan = latestSystemMessage?.content || 
    (isTranslating 
      ? "Analyzing your request..." 
      : "I will analyze your request and generate the appropriate SQL query...");

  const handleRunUpdate = () => {
    if (sql && !isExecuting) {
      executeSQL(sql, false); // Will trigger confirmation if destructive
    }
  };

  return (
    <TooltipProvider>
      <Card className="h-full bg-[#171717] border-[#262626] p-4 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-[#9CA3AF]">
              AI ACTION PLAN
            </span>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                <p>This shows what the AI plans to do with your request</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
        <div className="flex-1 overflow-auto mb-3">
          <div className="text-sm text-[#EDEDED] whitespace-pre-wrap">
            {latestPlan}
          </div>
        </div>
        {sql && (
          <Button
            onClick={handleRunUpdate}
            disabled={isExecuting}
            className="w-full bg-[#00E599] text-[#0A0A0A] hover:bg-[#00CC88] disabled:opacity-50"
          >
            <Play className="h-4 w-4 mr-2" />
            {isExecuting ? "RUNNING..." : "🟢 RUN UPDATE"}
          </Button>
        )}
      </Card>
    </TooltipProvider>
  );
}
