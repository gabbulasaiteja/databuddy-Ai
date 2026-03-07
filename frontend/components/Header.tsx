"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Settings, History } from "lucide-react";
import { HistoryPanel } from "@/components/HistoryPanel";

export function Header() {
  const [historyOpen, setHistoryOpen] = useState(false);

  return (
    <header className="flex h-12 items-center justify-between border-b border-[#262626] bg-[#0A0A0A] px-4">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-[#EDEDED]">
          [&gt;] DataBuddy AI Studio
        </span>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="outline" className="border-[#00E599] text-[#00E599]">
          🟢 Neon DB Connected
        </Badge>
        <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8" title="Query History">
              <History className="h-4 w-4" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-[500px] bg-[#0A0A0A] border-[#262626] p-0">
            <SheetHeader className="border-b border-[#262626] p-4">
              <SheetTitle className="text-[#EDEDED]">Query History</SheetTitle>
            </SheetHeader>
            <div className="h-[calc(100vh-73px)]">
              <HistoryPanel />
            </div>
          </SheetContent>
        </Sheet>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
