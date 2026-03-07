"use client";

import { Button } from "@/components/ui/button";
import { Database, Download, RotateCcw } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { downloadBlob } from "@/lib/utils";
import { ImportDialog } from "@/components/ImportDialog";

export function BottomActionBar() {
  const { previewRows, previewColumns, fetchSchema, selectedTable } = useAppStore();

  const handleVisualizeSchema = async () => {
    await fetchSchema();
    toast.success("Schema refreshed");
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
    <div className="flex items-center gap-3 px-6 py-3 border-t border-[#262626] bg-[#0A0A0A]">
      <Button
        variant="ghost"
        size="sm"
        onClick={handleVisualizeSchema}
        className="text-[#EDEDED] hover:bg-[#262626]"
      >
        <Database className="h-4 w-4 mr-2" />
        📊 Visualize Schema
      </Button>
      <ImportDialog />
      <Button
        variant="ghost"
        size="sm"
        onClick={handleExport}
        disabled={previewRows.length === 0 || previewColumns.length === 0}
        className="text-[#EDEDED] hover:bg-[#262626] disabled:opacity-50"
      >
        <Download className="h-4 w-4 mr-2" />
        📥 Export
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleResetDB}
        className="text-[#EDEDED] hover:bg-[#262626]"
      >
        <RotateCcw className="h-4 w-4 mr-2" />
        🔃 Reset DB
      </Button>
    </div>
  );
}
