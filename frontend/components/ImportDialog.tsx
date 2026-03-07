"use client";

import { useState, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, Loader2, FileText } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { toast } from "sonner";

export function ImportDialog() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [tableName, setTableName] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { fetchSchema, selectTable } = useAppStore();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const extension = selectedFile.name.split('.').pop()?.toLowerCase();
      if (extension !== 'csv' && extension !== 'json') {
        toast.error("Please select a CSV or JSON file");
        return;
      }
      setFile(selectedFile);
      // Auto-fill table name from filename if empty
      if (!tableName) {
        const nameWithoutExt = selectedFile.name.replace(/\.[^/.]+$/, "");
        setTableName(nameWithoutExt.replace(/[^a-zA-Z0-9_]/g, "_"));
      }
    }
  };

  const handleImport = async () => {
    if (!file) {
      toast.error("Please select a file");
      return;
    }

    if (!tableName.trim()) {
      toast.error("Please enter a table name");
      return;
    }

    // Validate table name
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tableName.trim())) {
      toast.error("Invalid table name. Use only letters, numbers, and underscores");
      return;
    }

    setIsImporting(true);
    try {
      const result = await api.importData(file, tableName.trim());
      toast.success(`Successfully imported ${result.rows_imported} rows into '${result.table_name}'`);
      
      // Refresh schema and select the new table
      await fetchSchema();
      await selectTable(result.table_name, 1); // Reset to page 1 for new table
      
      // Reset form
      setFile(null);
      setTableName("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setOpen(false);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to import data";
      toast.error(errorMessage);
      console.error("Import error:", error);
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="text-[#EDEDED] hover:bg-[#262626] h-8"
        >
          <Upload className="h-4 w-4 mr-2" />
          Import
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#171717] border-[#262626] text-[#EDEDED]">
        <DialogHeader>
          <DialogTitle className="text-[#EDEDED]">Import Data</DialogTitle>
          <DialogDescription className="text-[#9CA3AF]">
            Upload a CSV or JSON file to import data into a table
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="file" className="text-[#EDEDED]">
              File (CSV or JSON)
            </Label>
            <div className="flex items-center gap-2">
              <Input
                ref={fileInputRef}
                id="file"
                type="file"
                accept=".csv,.json"
                onChange={handleFileSelect}
                disabled={isImporting}
                className="bg-[#0A0A0A] border-[#262626] text-[#EDEDED] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-[#00E599] file:text-[#0A0A0A] hover:file:bg-[#00CC88]"
              />
            </div>
            {file && (
              <div className="flex items-center gap-2 text-sm text-[#9CA3AF]">
                <FileText className="h-4 w-4" />
                <span>{file.name}</span>
                <span className="text-xs">({(file.size / 1024).toFixed(2)} KB)</span>
              </div>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="tableName" className="text-[#EDEDED]">
              Table Name
            </Label>
            <Input
              id="tableName"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
              placeholder="e.g., products, employees"
              disabled={isImporting}
              className="bg-[#0A0A0A] border-[#262626] text-[#EDEDED] placeholder:text-[#9CA3AF]"
            />
            <p className="text-xs text-[#9CA3AF]">
              Table will be created automatically if it doesn't exist
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={() => setOpen(false)}
            disabled={isImporting}
            className="text-[#EDEDED] hover:bg-[#262626]"
          >
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={!file || !tableName.trim() || isImporting}
            className="bg-[#00E599] text-[#0A0A0A] hover:bg-[#00CC88] disabled:opacity-50"
          >
            {isImporting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Import Data
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
