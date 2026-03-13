"use client";

import { useState, useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Send, Loader2 } from "lucide-react";
import { useAppStore } from "@/lib/store";

export function Chatbot() {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { messages, isTranslating, translatePrompt } = useAppStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (inputValue.trim() && !isTranslating) {
      await translatePrompt(inputValue.trim());
      setInputValue("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const newHeight = Math.min(textareaRef.current.scrollHeight, 120);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    // SHIFT + ENTER allows new line (default behavior)
  };

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-2 text-xs font-medium text-[#9CA3AF]">CHATBOT</div>
      <Card className="flex-1 flex flex-col bg-[#171717] border-[#262626] overflow-hidden min-h-0">
        {/* Message History */}
        <ScrollArea className="flex-1 p-4 min-h-0">
            <div className="space-y-4">
              {messages.filter(msg => msg.role === "user").length === 0 ? (
                <div className="text-center text-[#9CA3AF] py-8">
                  <div className="text-sm">Start a conversation with AI...</div>
                </div>
              ) : (
                messages
                  .filter(msg => msg.role === "user")
                  .map((msg, idx) => (
                    <div
                      key={idx}
                      className="flex justify-start"
                    >
                      <div className="max-w-[90%] border-l-2 border-[#00E599] pl-3 py-1 text-[#EDEDED]">
                        <div className="text-xs font-medium mb-1 text-[#9CA3AF]">
                          [User]
                        </div>
                        <div className="text-sm">{msg.content}</div>
                      </div>
                    </div>
                  ))
              )}
              {isTranslating && (
                <div className="flex justify-start">
                  <div className="bg-[#0A0A0A] rounded px-3 py-2 text-[#EDEDED]">
                    <div className="text-xs font-medium mb-1 text-[#9CA3AF]">
                      [System AI]
                    </div>
                    <div className="text-sm flex items-center gap-2">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Generating SQL...
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input Console */}
          <div className="border-t border-[#262626] p-4">
            <div className="flex gap-2 items-end">
              <Textarea
                ref={textareaRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask AI to execute a command... (Shift+Enter for new line)"
                disabled={isTranslating}
                rows={1}
                className="bg-[#0A0A0A] border-[#262626] text-[#EDEDED] placeholder:text-[#9CA3AF] focus-visible:ring-[#262626] resize-none min-h-[40px] max-h-[120px] overflow-y-auto"
              />
              <Button
                onClick={handleSend}
                disabled={isTranslating || !inputValue.trim()}
                className="bg-[#FFFFFF] text-[#0A0A0A] hover:bg-[#EDEDED] rounded-none disabled:opacity-50 h-[40px]"
              >
                {isTranslating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </Card>
    </div>
  );
}
