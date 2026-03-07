"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Settings, Info, Download, RotateCcw, History } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useState } from "react";
import { toast } from "sonner";
import { downloadBlob } from "@/lib/utils";
import { ImportDialog } from "@/components/ImportDialog";
import { HistoryPanel } from "@/components/HistoryPanel";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function NewHeader() {
  const { tables, selectedTable, loadingSchema, selectTable, previewRows, previewColumns } = useAppStore();
  const [databaseName] = useState("Sample_Inventory");
  const [historyOpen, setHistoryOpen] = useState(false);

  const handleTableChange = async (tableName: string) => {
    await selectTable(tableName, 1); // Reset to page 1 when table changes
  };

  const handleExport = async () => {
    if (previewRows.length === 0 || previewColumns.length === 0) {
      toast.error("No data to export");
      return;
    }

    try {
      // Export current preview data as CSV (client-side)
      const headers = previewColumns.join(",");
      const rows = previewRows.map(row =>
        previewColumns.map(col => {
          const value = row[col] ?? row[col.toLowerCase()] ?? row[col.toUpperCase()] ?? "";
          // Escape commas and quotes
          const str = String(value);
          if (str.includes(",") || str.includes('"') || str.includes("\n")) {
            return `"${str.replace(/"/g, '""')}"`;
          }
          return str;
        }).join(",")
      ).join("\n");
      
      const csvContent = `${headers}\n${rows}`;
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const filename = selectedTable 
        ? `${selectedTable}_export_${new Date().getTime()}.csv`
        : `table_export_${new Date().getTime()}.csv`;
      downloadBlob(blob, filename);
      toast.success("Exported as CSV");
    } catch (error) {
      toast.error("Failed to export");
      console.error("Export error:", error);
    }
  };

  const handleResetDB = async () => {
    if (!confirm("Are you sure you want to reset the database? This will delete all data.")) {
      return;
    }

    try {
      // This would need a backend endpoint
      toast.info("Reset DB functionality needs backend implementation");
    } catch (error) {
      toast.error("Failed to reset database");
    }
  };

  return (
    <TooltipProvider>
      <header className="flex h-14 items-center justify-between border-b border-[#262626] bg-[#0A0A0A] px-6">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-[#EDEDED]">
            [&gt;] DATABUDDY AI
          </span>
          <span className="text-sm text-[#9CA3AF]">/</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-[#9CA3AF]">(📦)</span>
            <span className="text-sm text-[#EDEDED]">{databaseName}</span>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                <p>This is your current database workspace</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <span className="text-sm text-[#9CA3AF]">/</span>
          <Select
            value={selectedTable || undefined}
            onValueChange={handleTableChange}
            disabled={loadingSchema || tables.length === 0}
          >
            <SelectTrigger className="h-8 w-[180px] bg-[#171717] border-[#262626] text-[#EDEDED]">
              <SelectValue placeholder={loadingSchema ? "Loading..." : "Select table"} />
            </SelectTrigger>
            <SelectContent className="bg-[#171717] border-[#262626]">
              {tables.map((table) => (
                <SelectItem
                  key={table}
                  value={table}
                  className="text-[#EDEDED] focus:bg-[#262626]"
                >
                  {table}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
            </TooltipTrigger>
            <TooltipContent>
              <p>Select a table to view and edit its data</p>
            </TooltipContent>
          </Tooltip>
        </div>
        <div className="flex items-center gap-3">
          <ImportDialog />
          <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="text-[#EDEDED] hover:bg-[#262626] h-8"
              >
                <History className="h-4 w-4 mr-2" />
                History
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[85vh] bg-[#171717] border-[#262626] text-[#EDEDED] p-0">
              <DialogHeader className="px-6 pt-6 pb-4">
                <DialogTitle className="text-[#EDEDED]">Query History</DialogTitle>
              </DialogHeader>
              <div className="px-6 pb-6 max-h-[calc(85vh-100px)] overflow-hidden">
                <HistoryPanel />
              </div>
            </DialogContent>
          </Dialog>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExport}
            disabled={previewRows.length === 0 || previewColumns.length === 0}
            className="text-[#EDEDED] hover:bg-[#262626] disabled:opacity-50 h-8"
          >
            <Download className="h-4 w-4 mr-2" />
             Export
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetDB}
            className="text-[#EDEDED] hover:bg-[#262626] h-8"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
             Reset DB
          </Button>
        
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
            </TooltipTrigger>
            <TooltipContent>
              <p>Real-time connection to your Neon PostgreSQL database</p>
            </TooltipContent>
          </Tooltip>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </header>
    </TooltipProvider>
  );
}
