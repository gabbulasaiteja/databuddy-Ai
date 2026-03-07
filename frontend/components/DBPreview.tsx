"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { RefreshCw, Loader2, Copy, Download, FileDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { copyToClipboard, downloadBlob } from "@/lib/utils";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useState, useMemo } from "react";

export function DBPreview() {
  const {
    tables,
    selectedTable,
    previewColumns,
    previewRows,
    loadingPreview,
    loadingSchema,
    selectTable,
    loadPreviewPage,
    fetchSchema,
    sql,
    previewPage,
    previewPageSize,
    previewTotalRows,
  } = useAppStore();
  const [exporting, setExporting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Filter rows based on search query
  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) return previewRows;
    
    const query = searchQuery.toLowerCase();
    return previewRows.filter(row =>
      previewColumns.some(col => {
        const value = row[col] ?? row[col.toLowerCase()] ?? row[col.toUpperCase()] ?? "";
        return String(value).toLowerCase().includes(query);
      })
    );
  }, [previewRows, previewColumns, searchQuery]);

  const handleTableChange = async (tableName: string) => {
    setSearchQuery(""); // Reset search when table changes
    await selectTable(tableName, 1); // Reset to page 1 when table changes
  };

  const handlePreviousPage = async () => {
    if (previewPage > 1) {
      await loadPreviewPage(previewPage - 1);
    }
  };

  const handleNextPage = async () => {
    const maxPage = previewTotalRows ? Math.ceil(previewTotalRows / previewPageSize) : null;
    if (!maxPage || previewPage < maxPage) {
      await loadPreviewPage(previewPage + 1);
    }
  };

  const totalPages = previewTotalRows ? Math.ceil(previewTotalRows / previewPageSize) : null;
  const startRow = previewTotalRows ? (previewPage - 1) * previewPageSize + 1 : null;
  const endRow = previewTotalRows 
    ? Math.min(previewPage * previewPageSize, previewTotalRows) 
    : previewRows.length;

  const handleRefresh = async () => {
    await fetchSchema();
    if (selectedTable) {
      await selectTable(selectedTable, previewPage); // Maintain current page
    }
  };

  const handleCopyTable = async () => {
    if (previewRows.length === 0) return;
    
    // Create CSV format
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
    const success = await copyToClipboard(csvContent);
    if (success) {
      toast.success("Table data copied to clipboard");
    } else {
      toast.error("Failed to copy table data");
    }
  };

  const handleExportCSV = async () => {
    if (!sql || previewRows.length === 0) {
      toast.error("No data to export");
      return;
    }
    
    setExporting(true);
    try {
      const blob = await api.exportCSV(sql);
      const filename = `query_results_${new Date().getTime()}.csv`;
      downloadBlob(blob, filename);
      toast.success("Exported as CSV");
    } catch (error) {
      toast.error("Failed to export CSV");
      console.error("Export error:", error);
    } finally {
      setExporting(false);
    }
  };

  const handleExportJSON = async () => {
    if (!sql || previewRows.length === 0) {
      toast.error("No data to export");
      return;
    }
    
    setExporting(true);
    try {
      const blob = await api.exportJSON(sql);
      const filename = `query_results_${new Date().getTime()}.json`;
      downloadBlob(blob, filename);
      toast.success("Exported as JSON");
    } catch (error) {
      toast.error("Failed to export JSON");
      console.error("Export error:", error);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="h-full p-4">
        <div className="mb-2 text-xs font-medium text-[#9CA3AF]">
          REAL-TIME DB PREVIEW
        </div>
        <Card className="h-full flex flex-col bg-[#171717] border-[#262626]">
          {/* Table Selector and Actions */}
          <div className="flex items-center justify-between border-b border-[#262626] p-4 gap-2">
            <Select
              value={selectedTable || undefined}
              onValueChange={handleTableChange}
              disabled={loadingSchema || tables.length === 0}
            >
              <SelectTrigger className="w-[200px] bg-[#0A0A0A] border-[#262626] text-[#EDEDED]">
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
            <div className="flex items-center gap-2">
              {previewRows.length > 0 && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopyTable}
                    disabled={loadingPreview}
                    className="text-[#EDEDED] hover:bg-[#262626] disabled:opacity-50"
                    title="Copy table data"
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleExportCSV}
                    disabled={exporting || loadingPreview || !sql}
                    className="text-[#EDEDED] hover:bg-[#262626] disabled:opacity-50"
                    title="Export as CSV"
                  >
                    {exporting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <FileDown className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleExportJSON}
                    disabled={exporting || loadingPreview || !sql}
                    className="text-[#EDEDED] hover:bg-[#262626] disabled:opacity-50"
                    title="Export as JSON"
                  >
                    {exporting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )}
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={loadingSchema || loadingPreview}
                className="text-[#EDEDED] hover:bg-[#262626] disabled:opacity-50"
              >
                {loadingSchema || loadingPreview ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Refresh
              </Button>
            </div>
          </div>

          {/* Pagination Controls - Above Search Bar */}
          {previewColumns.length > 0 && previewRows.length > 0 && (
            <div className="border-b border-[#262626] px-4 py-3 flex items-center justify-between bg-[#171717]">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handlePreviousPage}
                  disabled={loadingPreview || previewPage === 1}
                  className="text-[#EDEDED] hover:bg-[#262626] hover:text-[#EDEDED] disabled:opacity-50 disabled:cursor-not-allowed h-8 px-3"
                  title="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-xs text-[#9CA3AF] px-2 font-medium">
                  Page {previewPage}
                  {totalPages ? ` of ${totalPages}` : ""}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleNextPage}
                  disabled={loadingPreview || (totalPages !== null && previewPage >= totalPages)}
                  className="text-[#EDEDED] hover:bg-[#262626] hover:text-[#EDEDED] disabled:opacity-50 disabled:cursor-not-allowed h-8 px-3"
                  title="Next page"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
              <div className="text-xs text-[#9CA3AF]">
                {startRow && previewTotalRows ? (
                  <>Showing {startRow}-{endRow} of {previewTotalRows} rows</>
                ) : (
                  <>Showing {previewRows.length} row{previewRows.length !== 1 ? "s" : ""}</>
                )}
              </div>
            </div>
          )}

          {/* Search Bar */}
          {previewColumns.length > 0 && previewRows.length > 0 && (
            <div className="border-b border-[#262626] px-4 py-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#9CA3AF]" />
                <Input
                  type="text"
                  placeholder="Search in table..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-[#0A0A0A] border-[#262626] text-[#EDEDED] placeholder:text-[#9CA3AF]"
                />
              </div>
            </div>
          )}

          {/* Data Table */}
          <div className="flex-1 overflow-auto">
            {loadingPreview ? (
              <div className="p-4 space-y-2">
                <Skeleton className="h-4 w-full bg-[#262626]" />
                <Skeleton className="h-4 w-full bg-[#262626]" />
                <Skeleton className="h-4 w-full bg-[#262626]" />
              </div>
            ) : previewColumns.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow className="border-[#262626] hover:bg-[#262626]">
                    {previewColumns.map((col) => (
                      <TableHead
                        key={col}
                        className="code-font text-[#737373] font-medium"
                      >
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRows.length > 0 ? (
                    filteredRows.map((row, idx) => (
                      <TableRow
                        key={idx}
                        className="border-[#262626] hover:bg-[#262626]"
                      >
                        {previewColumns.map((col) => {
                          // Try multiple key formats (case-insensitive)
                          const value = row[col] ?? row[col.toLowerCase()] ?? row[col.toUpperCase()] ?? null;
                          return (
                            <TableCell
                              key={col}
                              className="code-font text-[#EDEDED]"
                            >
                              {value !== null && value !== undefined ? String(value) : "-"}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))
                  ) : searchQuery.trim() ? (
                    <TableRow className="border-[#262626]">
                      <TableCell
                        colSpan={previewColumns.length}
                        className="code-font text-center text-[#9CA3AF] py-8"
                      >
                        No results found for "{searchQuery}"
                      </TableCell>
                    </TableRow>
                  ) : (
                    <TableRow className="border-[#262626]">
                      <TableCell
                        colSpan={previewColumns.length}
                        className="code-font text-center text-[#9CA3AF] py-8"
                      >
                        (No data)
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            ) : (
              <div className="flex items-center justify-center h-full text-[#9CA3AF]">
                {loadingSchema ? (
                  <div className="text-sm">Loading schema...</div>
                ) : tables.length === 0 ? (
                  <div className="text-sm">No tables found. Create one to get started!</div>
                ) : (
                  <div className="text-sm">Select a table to preview</div>
                )}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
