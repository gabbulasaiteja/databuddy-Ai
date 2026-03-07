"use client";

import { useEffect } from "react";
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable";
import { NewHeader } from "@/components/NewHeader";
import { EditableTable } from "@/components/EditableTable";
import { Chatbot } from "@/components/Chatbot";
import { SQLTranslation } from "@/components/SQLTranslation";
import { SafetyConfirmationDialog } from "@/components/SafetyConfirmationDialog";
import { useAppStore } from "@/lib/store";

export default function Home() {
  const fetchSchema = useAppStore((state) => state.fetchSchema);

  useEffect(() => {
    // Fetch schema on mount
    fetchSchema();
  }, [fetchSchema]);

  return (
    <div className="flex h-screen flex-col bg-[#0A0A0A]">
      {/* Safety Confirmation Dialog */}
      <SafetyConfirmationDialog />
      
      {/* Top Header */}
      <NewHeader />
      
      {/* Main Canvas Area */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal" className="h-full">
          {/* Left Panel - Wide Canvas (70% width) */}
          <ResizablePanel defaultSize={70} minSize={50}>
            <div className="h-full p-6">
              <EditableTable />
            </div>
          </ResizablePanel>

          <ResizableHandle className="w-1 bg-transparent hover:bg-[#262626] transition-colors" />

          {/* Right Panel Group - SQL Panel + Chatbot (30% width) */}
          <ResizablePanel defaultSize={30} minSize={20} className="flex flex-col h-full overflow-hidden">
            {/* Top Right - SQL Panel (50% height) */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <SQLTranslation />
            </div>

            {/* Divider */}
            <div className="h-1 bg-transparent hover:bg-[#262626] transition-colors" />

            {/* Bottom Right - Chatbot/AI Panel (50% height) */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <Chatbot />
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}
