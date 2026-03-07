"use client";

import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Copy, Check } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { copyToClipboard } from "@/lib/utils";
import { toast } from "sonner";

export function SQLPanel() {
  const { sql, executionLogs, isExecuting } = useAppStore();
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [executionLogs]);

  const handleCopySQL = async () => {
    if (!sql) return;
    const success = await copyToClipboard(sql);
    if (success) {
      setCopied(true);
      toast.success("SQL copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } else {
      toast.error("Failed to copy SQL");
    }
  };

  const handleCopyLogs = async () => {
    const logsText = executionLogs.join("\n");
    if (!logsText) return;
    const success = await copyToClipboard(logsText);
    if (success) {
      toast.success("Logs copied to clipboard");
    } else {
      toast.error("Failed to copy logs");
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* SQL Code Block */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs font-medium text-[#9CA3AF]">SQL PANEL</div>
            {sql && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopySQL}
                className="h-6 px-2 text-[#9CA3AF] hover:text-[#EDEDED] hover:bg-[#262626]"
              >
                {copied ? (
                  <Check className="h-3 w-3 mr-1" />
                ) : (
                  <Copy className="h-3 w-3 mr-1" />
                )}
                Copy SQL
              </Button>
            )}
          </div>
          <Card className="h-full bg-[#171717] border-[#262626] p-4">
            <ScrollArea className="h-full">
              <pre className="code-font text-sm text-[#EDEDED] whitespace-pre-wrap">
                {sql || (
                  <span className="text-[#9CA3AF]">
                    SQL will appear here after you send a prompt...
                  </span>
                )}
              </pre>
            </ScrollArea>
          </Card>
        </div>
      </div>

      <Separator className="bg-[#262626]" />

      {/* Terminal / Execution Log */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs font-medium text-[#9CA3AF]">
              TERMINAL / EXECUTION LOG
            </div>
            {executionLogs.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyLogs}
                className="h-6 px-2 text-[#9CA3AF] hover:text-[#EDEDED] hover:bg-[#262626]"
              >
                <Copy className="h-3 w-3 mr-1" />
                Copy Logs
              </Button>
            )}
          </div>
          <Card className="h-full bg-[#171717] border-[#262626] p-4">
            <ScrollArea className="h-full">
              <div className="code-font space-y-1 text-sm">
                {executionLogs.length > 0 ? (
                  <>
                    {executionLogs.map((log, idx) => (
                      <div key={idx} className="text-[#EDEDED]">
                        {log.startsWith("[✅]") ? (
                          <span className="text-[#00E599]">{log}</span>
                        ) : log.startsWith("[❌]") ? (
                          <span className="text-red-500">{log}</span>
                        ) : log.startsWith("[⚠️]") ? (
                          <span className="text-yellow-500">{log}</span>
                        ) : (
                          <span>{log}</span>
                        )}
                      </div>
                    ))}
                    {isExecuting && (
                      <div className="text-[#9CA3AF]">
                        &gt; Executing...
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-[#9CA3AF]">
                    Execution logs will appear here...
                  </div>
                )}
                <div ref={logsEndRef} />
              </div>
            </ScrollArea>
          </Card>
        </div>
      </div>
    </div>
  );
}
