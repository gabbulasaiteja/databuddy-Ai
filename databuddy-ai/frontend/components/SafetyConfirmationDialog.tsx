"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AlertTriangle } from "lucide-react";
import { useAppStore } from "@/lib/store";

export function SafetyConfirmationDialog() {
  const { pendingDestructiveSQL, pendingQueryType, confirmDestructiveOperation, cancelDestructiveOperation } = useAppStore();

  const getOperationDetails = () => {
    if (!pendingQueryType) return { title: "Destructive Operation", description: "This operation cannot be undone." };
    
    switch (pendingQueryType) {
      case "DROP":
        return {
          title: "⚠️ Drop Table Confirmation",
          description: "This will permanently delete the table and all its data. This action cannot be undone.",
        };
      case "TRUNCATE":
        return {
          title: "⚠️ Clear All Data Confirmation",
          description: "This will permanently delete all rows from the table. This action cannot be undone.",
        };
      case "DELETE":
        return {
          title: "⚠️ Delete Data Confirmation",
          description: "This will permanently delete data from the table. This action cannot be undone.",
        };
      default:
        return {
          title: "⚠️ Destructive Operation Confirmation",
          description: "This operation will permanently modify or delete data. This action cannot be undone.",
        };
    }
  };

  const details = getOperationDetails();
  const sqlPreview = pendingDestructiveSQL 
    ? pendingDestructiveSQL.substring(0, 100) + (pendingDestructiveSQL.length > 100 ? "..." : "")
    : "";

  return (
    <AlertDialog open={!!pendingDestructiveSQL} onOpenChange={(open) => {
      if (!open) cancelDestructiveOperation();
    }}>
      <AlertDialogContent className="bg-[#171717] border-[#262626] text-[#EDEDED]">
        <AlertDialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/20">
              <AlertTriangle className="h-6 w-6 text-red-500" />
            </div>
            <div>
              <AlertDialogTitle className="text-[#EDEDED]">
                {details.title}
              </AlertDialogTitle>
            </div>
          </div>
          <AlertDialogDescription className="text-[#9CA3AF] pt-2">
            {details.description}
          </AlertDialogDescription>
          {sqlPreview && (
            <div className="mt-4 p-3 bg-[#0A0A0A] rounded border border-[#262626]">
              <div className="text-xs text-[#9CA3AF] mb-1">SQL Query:</div>
              <code className="text-xs text-[#EDEDED] font-mono">{sqlPreview}</code>
            </div>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel 
            onClick={cancelDestructiveOperation}
            className="bg-[#262626] text-[#EDEDED] hover:bg-[#333333] border-[#262626]"
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={confirmDestructiveOperation}
            className="bg-red-600 text-white hover:bg-red-700"
          >
            Yes, Continue
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
