"use client";

import { Card } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Info } from "lucide-react";
import { useAppStore } from "@/lib/store";

export function SQLTranslation() {
  const { sql } = useAppStore();

  return (
    <TooltipProvider>
      <div className="h-full flex flex-col p-4">
        <div className="mb-2 text-xs font-medium text-[#9CA3AF]">SQL PANEL</div>
        <Card className="flex-1 bg-[#171717] border-[#262626] p-4 flex flex-col overflow-hidden min-h-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>This is the technical 'brain' view. You can safely ignore this!</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
          <ScrollArea className="flex-1 min-h-0">
            <pre className="code-font text-xs text-[#EDEDED] whitespace-pre-wrap">
              {sql || (
                <span className="text-[#9CA3AF]">
                  SQL will appear here after you send a prompt...
                </span>
              )}
            </pre>
          </ScrollArea>
        </Card>
      </div>
    </TooltipProvider>
  );
}
