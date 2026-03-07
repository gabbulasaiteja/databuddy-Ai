"use client";

import { useEffect, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Copy, RefreshCw, Loader2, Check } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { copyToClipboard } from "@/lib/utils";
import { toast } from "sonner";

export function HistoryPanel() {
  const { history, loadingHistory, fetchHistory, executeSQL } = useAppStore();
  const [copiedId, setCopiedId] = useState<number | null>(null);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleCopySQL = async (sql: string, id: number) => {
    const success = await copyToClipboard(sql);
    if (success) {
      setCopiedId(id);
      toast.success("SQL copied to clipboard");
      setTimeout(() => setCopiedId(null), 2000);
    } else {
      toast.error("Failed to copy SQL");
    }
  };

  const handleRunQuery = async (sql: string) => {
    await executeSQL(sql);
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col h-full">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-xs font-medium text-[#9CA3AF]">QUERY HISTORY</div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchHistory}
            disabled={loadingHistory}
            className="h-6 px-2 text-[#9CA3AF] hover:text-[#EDEDED] hover:bg-[#262626]"
          >
            {loadingHistory ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="h-3 w-3" />
            )}
          </Button>
        </div>
        <Card className="flex-1 bg-[#171717] border-[#262626] p-4 overflow-hidden flex flex-col min-h-0">
          <ScrollArea className="flex-1 min-h-0">
            {loadingHistory ? (
              <div className="flex items-center justify-center h-full text-[#9CA3AF]">
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Loading history...
              </div>
            ) : history.length === 0 ? (
              <div className="flex items-center justify-center h-full text-[#9CA3AF]">
                <div className="text-sm">No query history yet</div>
              </div>
            ) : (
              <div className="space-y-3">
                {history.map((item) => (
                  <div
                    key={item.id}
                    className="bg-[#0A0A0A] border border-[#262626] rounded p-3 hover:border-[#404040] transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="text-xs text-[#9CA3AF] mb-1">
                          {formatTimestamp(item.timestamp)}
                        </div>
                        {item.prompt && item.prompt !== item.sql && (
                          <div className="text-sm text-[#EDEDED] mb-2">
                            <span className="text-[#9CA3AF]">Prompt:</span> {item.prompt}
                          </div>
                        )}
                        <div className="code-font text-xs text-[#00E599] bg-[#171717] p-2 rounded border border-[#262626]">
                          {item.sql}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopySQL(item.sql, item.id)}
                        className="h-7 px-2 text-[#9CA3AF] hover:text-[#EDEDED] hover:bg-[#262626]"
                      >
                        {copiedId === item.id ? (
                          <Check className="h-3 w-3 mr-1" />
                        ) : (
                          <Copy className="h-3 w-3 mr-1" />
                        )}
                        Copy
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRunQuery(item.sql)}
                        className="h-7 px-2 text-[#9CA3AF] hover:text-[#00E599] hover:bg-[#262626]"
                      >
                        Run
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </Card>
      </div>
    </div>
  );
}
