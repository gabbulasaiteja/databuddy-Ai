"use client";

import { useState, useRef, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Send, Loader2, Info, Sparkles } from "lucide-react";
import { useAppStore } from "@/lib/store";

const EXAMPLE_PROMPTS = [
  "Find products with low stock and give them a 10% discount",
  "Create a new employee table with name, email, and salary",
  "Show me all orders from the last 30 days",
];

export function BottomInputBar() {
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { isTranslating, translatePrompt, tables, populateSampleData } = useAppStore();

  useEffect(() => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const newHeight = Math.min(textareaRef.current.scrollHeight, 120);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [inputValue]);

  const handleSend = async () => {
    if (inputValue.trim() && !isTranslating) {
      await translatePrompt(inputValue.trim());
      setInputValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleExampleClick = (example: string) => {
    setInputValue(example);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <TooltipProvider>
      <div className="border-t border-[#262626] bg-[#0A0A0A] px-6 py-4">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-[#00E599]" />
              <span className="text-sm text-[#9CA3AF]">
                Ask AI to execute a command...
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Type in natural language and AI will translate it to SQL</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="flex gap-2">
              <Textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Find products with low stock and give them a 10% discount..."
                disabled={isTranslating}
                rows={1}
                className="bg-[#171717] border-[#262626] text-[#EDEDED] placeholder:text-[#9CA3AF] focus-visible:ring-[#00E599] resize-none min-h-[40px] max-h-[120px] overflow-y-auto"
              />
              <Button
                onClick={handleSend}
                disabled={isTranslating || !inputValue.trim()}
                className="bg-[#00E599] text-[#0A0A0A] hover:bg-[#00CC88] disabled:opacity-50 h-[40px] px-6"
              >
                {isTranslating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className="text-xs text-[#9CA3AF]">Try an example:</span>
              {tables.length === 0 && (
                <Badge
                  variant="outline"
                  className="cursor-pointer hover:bg-[#262626] border-[#00E599] text-[#00E599] text-xs"
                  onClick={populateSampleData}
                >
                  📦 Load Sample Data
                </Badge>
              )}
              {EXAMPLE_PROMPTS.map((example, idx) => (
                <Badge
                  key={idx}
                  variant="outline"
                  className="cursor-pointer hover:bg-[#262626] border-[#262626] text-[#EDEDED] text-xs"
                  onClick={() => handleExampleClick(example)}
                >
                  {example}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
