"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Info, AlertTriangle, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";

interface EditableCellProps {
  value: any;
  column: string;
  rowIndex: number;
  tableName: string | null;
  row: Record<string, any>;
  previewColumns: string[];
  onUpdate: () => void;
}

function EditableCell({ value, column, rowIndex, tableName, row, previewColumns, onUpdate }: EditableCellProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(String(value ?? ""));
  const [isUpdating, setIsUpdating] = useState(false);
  const [flashColor, setFlashColor] = useState<string | null>(null);
  const { executeSQL, selectTable } = useAppStore();

  const handleDoubleClick = () => {
    setIsEditing(true);
    setEditValue(String(value ?? ""));
  };

  const handleBlur = async () => {
    if (editValue === String(value ?? "")) {
      setIsEditing(false);
      return;
    }

    if (!tableName) {
      toast.error("No table selected");
      setIsEditing(false);
      return;
    }

    setIsUpdating(true);
    try {
      // Build WHERE clause using all columns (simple approach)
      
      // Build WHERE clause using all columns (simple approach)
      const whereConditions = previewColumns
        .map((col) => {
          const val = row[col] ?? row[col.toLowerCase()] ?? row[col.toUpperCase()];
          if (val === null || val === undefined) return null;
          return `${col} = '${String(val).replace(/'/g, "''")}'`;
        })
        .filter(Boolean)
        .slice(0, 3); // Limit to first 3 columns for WHERE clause

      if (whereConditions.length === 0) {
        toast.error("Cannot update: no identifying columns");
        setIsEditing(false);
        setIsUpdating(false);
        return;
      }

      const sql = `UPDATE ${tableName} SET ${column} = '${editValue.replace(/'/g, "''")}' WHERE ${whereConditions.join(" AND ")};`;
      
      // Use executeSQL from store to get proper state updates
      await executeSQL(sql);
      
      // Flash animation
      setFlashColor("green");
      setTimeout(() => setFlashColor(null), 1000);
      
      toast.success("Cell updated successfully");
      
      // Refresh the table preview
      if (tableName) {
        await selectTable(tableName, 1); // Reset to page 1 after update
      }
    } catch (error) {
      setFlashColor("yellow");
      setTimeout(() => setFlashColor(null), 1000);
      toast.error("Failed to update cell", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsUpdating(false);
      setIsEditing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleBlur();
    } else if (e.key === "Escape") {
      setEditValue(String(value ?? ""));
      setIsEditing(false);
    }
  };

  const displayValue = value !== null && value !== undefined ? String(value) : "-";
  const isLowStock = column.toLowerCase().includes("stock") && 
    typeof value === "number" && value < 5;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <TableCell
            className={`code-font text-[#EDEDED] cursor-pointer relative ${
              flashColor === "green" ? "bg-[#00E599]/20" : 
              flashColor === "yellow" ? "bg-yellow-500/20" : ""
            } transition-colors duration-300`}
            onDoubleClick={handleDoubleClick}
          >
            {isEditing ? (
              <Input
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={handleBlur}
                onKeyDown={handleKeyDown}
                disabled={isUpdating}
                autoFocus
                className="h-6 text-xs bg-[#0A0A0A] border-[#00E599] text-[#EDEDED]"
              />
            ) : (
              <div className="flex items-center gap-1">
                {isLowStock && <AlertTriangle className="h-3 w-3 text-yellow-500" />}
                <span className={isLowStock ? "text-yellow-500" : ""}>
                  {displayValue}
                </span>
              </div>
            )}
          </TableCell>
        </TooltipTrigger>
        <TooltipContent>
          <p>Double-click to edit this cell</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function EditableTable() {
  const {
    previewColumns,
    previewRows,
    loadingPreview,
    selectedTable,
    selectTable,
    loadPreviewPage,
    tables,
    populateSampleData,
    schema,
    previewPage,
    previewPageSize,
    previewTotalRows,
  } = useAppStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [totalRowCount, setTotalRowCount] = useState<number | null>(null);

  // Get column types and primary keys from schema
  const columnInfo = useMemo(() => {
    if (!selectedTable || !schema.length) return {};
    const table = schema.find(t => t.name === selectedTable);
    if (!table) return {};
    
    const info: Record<string, { type: string; isPrimary: boolean }> = {};
    table.columns.forEach(col => {
      info[col.name] = {
        type: col.type,
        isPrimary: col.is_primary,
      };
    });
    return info;
  }, [selectedTable, schema]);

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

  // Reset search when table changes
  useEffect(() => {
    setSearchQuery("");
  }, [selectedTable]);

  // Use previewTotalRows from store instead of fetching separately
  // This avoids duplicate COUNT queries and rate limit issues
  useEffect(() => {
    setTotalRowCount(previewTotalRows);
  }, [previewTotalRows]);

  const handleRefresh = () => {
    if (selectedTable) {
      selectTable(selectedTable, 1); // Reset to page 1 on refresh
    }
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

  const hasNoData = tables.length === 0 && !loadingPreview;

  return (
    <TooltipProvider>
      <div className="h-full flex flex-col">
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-[#9CA3AF]">
              REAL-TIME DATABASE PREVIEW
            </span>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                <p>The Canvas - Your live database view</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {hasNoData && (
          <div className="mb-4 p-4 border border-[#262626] bg-[#171717] rounded">
            <div className="text-sm text-[#EDEDED] mb-2">
              No tables found. Get started with sample data:
            </div>
            <button
              onClick={populateSampleData}
              className="px-4 py-2 bg-[#00E599] text-[#0A0A0A] hover:bg-[#00CC88] rounded text-sm font-medium"
            >
              📦 Load Sample Inventory Data
            </button>
          </div>
        )}

        {/* Pagination Controls - Above Search Bar */}
        {previewColumns.length > 0 && previewRows.length > 0 && (
          <div className="mb-3 flex items-center justify-between px-1">
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

        {/* Search/Filter Bar */}
        {previewColumns.length > 0 && previewRows.length > 0 && (
          <div className="mb-3">
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

        <div className="flex-1 overflow-auto border border-[#262626] bg-[#171717] rounded">
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
                  {previewColumns.map((col) => {
                    const colInfo = columnInfo[col] || { type: "TEXT", isPrimary: false };
                    return (
                      <TableHead
                        key={col}
                        className="code-font text-[#737373] font-medium"
                      >
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-1">
                            {col}
                            {colInfo.isPrimary && (
                              <span className="text-xs" title="Primary Key">🔑</span>
                            )}
                          </div>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Info className="h-3 w-3 text-[#9CA3AF] cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>
                                {col.toLowerCase() === "id" 
                                  ? "This is a unique finger-print for this row."
                                  : `Column: ${col}`}
                                {colInfo.type && `\nType: ${colInfo.type}`}
                                {colInfo.isPrimary && "\n🔑 Primary Key"}
                              </p>
                            </TooltipContent>
                          </Tooltip>
                          <span className="text-xs text-[#737373] font-normal">
                            ({colInfo.type})
                          </span>
                        </div>
                      </TableHead>
                    );
                  })}
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
                        const value = row[col] ?? row[col.toLowerCase()] ?? row[col.toUpperCase()] ?? null;
                        return (
                          <EditableCell
                            key={col}
                            value={value}
                            column={col}
                            rowIndex={idx}
                            tableName={selectedTable}
                            row={row}
                            previewColumns={previewColumns}
                            onUpdate={handleRefresh}
                          />
                        );
                      })}
                    </TableRow>
                  ))
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
            <div className="flex items-center justify-center h-full text-[#9CA3AF] p-8">
              <div className="text-sm text-center">
                <p>No table selected or no data available.</p>
                <p className="text-xs mt-2">( Double-click any cell to edit directly )</p>
              </div>
            </div>
          )}
        </div>

        {/* Row Count Footer */}
        {previewColumns.length > 0 && previewRows.length > 0 && (
          <div className="mt-3 flex items-center justify-between text-xs text-[#9CA3AF] px-2">
            <div>
              {searchQuery ? (
                <span>
                  Showing {filteredRows.length} of {previewRows.length} rows
                  {previewTotalRows !== null && previewTotalRows > previewRows.length && (
                    <span> (of {previewTotalRows} total)</span>
                  )}
                </span>
              ) : (
                <span>
                  Showing {previewRows.length} row{previewRows.length !== 1 ? 's' : ''}
                  {previewTotalRows !== null && previewTotalRows > previewRows.length && (
                    <span> of {previewTotalRows} total</span>
                  )}
                </span>
              )}
            </div>
            {previewRows.length >= previewPageSize && previewTotalRows !== null && previewTotalRows > previewRows.length && (
              <div className="text-[#737373]">
                Use arrows above to navigate pages
              </div>
            )}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
