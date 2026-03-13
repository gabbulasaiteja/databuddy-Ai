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
  const [copiedError, setCopiedError] = useState(false);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [executionLogs]);

  // Check if there are any errors in the logs
  const hasError = executionLogs.some(log => log.startsWith("[❌]") || log.includes("error") || log.includes("Error") || log.includes("failed"));

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

  const handleCopyErrorDetails = async () => {
    // Copy SQL + error logs for diagnosis
    const errorLogs = executionLogs.filter(log => 
      log.startsWith("[❌]") || log.includes("error") || log.includes("Error") || log.includes("failed")
    );
    const errorText = `SQL Query:\n${sql}\n\nError Details:\n${errorLogs.join("\n")}`;
    const success = await copyToClipboard(errorText);
    if (success) {
      setCopiedError(true);
      toast.success("Error details copied to clipboard");
      setTimeout(() => setCopiedError(false), 2000);
    } else {
      toast.error("Failed to copy error details");
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
          <Card className={`h-full bg-[#171717] border-[#262626] p-4 ${hasError ? 'border-red-500/50' : ''}`}>
            <ScrollArea className="h-full">
              <div className="code-font space-y-1 text-sm">
                {executionLogs.length > 0 ? (
                  <>
                    {hasError && sql && (
                      <div className="mb-3 p-3 bg-red-500/10 border border-red-500/30 rounded">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-medium text-red-400">
                            ⚠️ Execution Error Detected
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleCopyErrorDetails}
                            className="h-6 px-2 text-red-400 hover:text-red-300 hover:bg-red-500/20"
                          >
                            {copiedError ? (
                              <Check className="h-3 w-3 mr-1" />
                            ) : (
                              <Copy className="h-3 w-3 mr-1" />
                            )}
                            Copy Error Details
                          </Button>
                        </div>
                        <div className="text-xs text-[#9CA3AF]">
                          Click to copy SQL query and error details for diagnosis
                        </div>
                      </div>
                    )}
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
