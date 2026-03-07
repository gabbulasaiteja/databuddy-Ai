"use client";

import { create } from "zustand";
import { fetchApi, getBaseUrl } from "./api";

export interface SchemaColumn {
  name: string;
  type: string;
  is_primary: boolean;
}

export interface SchemaTable {
  name: string;
  description?: string;
  columns: SchemaColumn[];
}

export interface HistoryItem {
  id: number;
  prompt: string;
  sql: string;
  timestamp: string;
}

export interface Message {
  role: string;
  content: string;
}

interface ExecuteResponse {
  columns: string[];
  rows: Record<string, unknown>[];
  count: number;
  execution_time_ms: number;
  query_id: string;
  rows_affected: number;
  execution_logs: string[];
  query_type: string;
  schema_refresh_required?: boolean;
}

function getDestructiveType(sql: string): string | null {
  const upper = sql.toUpperCase().replace(/\s+/g, " ").trim();
  if (upper.startsWith("DROP ")) return "DROP";
  if (upper.startsWith("TRUNCATE ")) return "TRUNCATE";
  if (upper.startsWith("DELETE FROM ") && !upper.includes(" WHERE ")) return "DELETE";
  if (/^DELETE\s+FROM\s+/i.test(upper)) return "DELETE";
  return null;
}

export const useAppStore = create<{
  // Schema & tables
  schema: SchemaTable[];
  tables: string[];
  selectedTable: string | null;
  loadingSchema: boolean;
  fetchSchema: () => Promise<void>;
  selectTable: (tableName: string, page?: number) => Promise<void>;

  // Preview
  previewRows: Record<string, unknown>[];
  previewColumns: string[];
  loadingPreview: boolean;
  previewPage: number;
  previewPageSize: number;
  previewTotalRows: number | null;
  loadPreviewPage: (page: number) => Promise<void>;

  // SQL & execution
  sql: string;
  executionLogs: string[];
  isExecuting: boolean;
  executeSQL: (sql: string, useTransaction?: boolean) => Promise<void>;

  // Internal: run execute without destructive check
  doExecuteSQL: (sql: string, useTransaction: boolean) => Promise<void>;

  // Destructive confirmation
  pendingDestructiveSQL: string | null;
  pendingQueryType: string | null;
  confirmDestructiveOperation: () => void;
  cancelDestructiveOperation: () => void;

  // Translate / chat
  messages: Message[];
  isTranslating: boolean;
  translatePrompt: (prompt: string) => Promise<void>;

  // History
  history: HistoryItem[];
  loadingHistory: boolean;
  fetchHistory: () => Promise<void>;

  // Sample data
  populateSampleData: () => Promise<void>;
}>((set, get) => ({
  schema: [],
  tables: [],
  selectedTable: null,
  loadingSchema: false,
  previewRows: [],
  previewColumns: [],
  loadingPreview: false,
  previewPage: 1,
  previewPageSize: 50,
  previewTotalRows: null,
  sql: "",
  executionLogs: [],
  isExecuting: false,
  pendingDestructiveSQL: null,
  pendingQueryType: null,
  messages: [],
  isTranslating: false,
  history: [],
  loadingHistory: false,

  fetchSchema: async () => {
    set({ loadingSchema: true });
    try {
      const res = await fetchApi<{ tables: SchemaTable[] }>("/api/schema");
      const schema = res.tables ?? [];
      const tables = schema.map((t) => t.name);
      set({ schema, tables, loadingSchema: false });
    } catch (e) {
      console.error("fetchSchema error:", e);
      set({ schema: [], tables: [], loadingSchema: false });
    }
  },

  selectTable: async (tableName: string, page = 1) => {
    const { schema } = get();
    const table = schema.find((t) => t.name === tableName);
    const previewColumns = table?.columns.map((c) => c.name) ?? [];
    set({
      selectedTable: tableName,
      previewColumns,
      previewPage: page,
      loadingPreview: true,
    });
    try {
      const limit = get().previewPageSize;
      const offset = (page - 1) * limit;
      const res = await fetchApi<ExecuteResponse>("/api/execute", {
        method: "POST",
        body: JSON.stringify({
          sql: `SELECT * FROM "${tableName}" LIMIT ${limit} OFFSET ${offset}`,
          use_transaction: false,
        }),
      });
      const rows = res.rows ?? [];
      const totalRes = await fetchApi<{ rows?: Record<string, unknown>[] }>("/api/execute", {
        method: "POST",
        body: JSON.stringify({
          sql: `SELECT COUNT(*) AS count FROM "${tableName}"`,
          use_transaction: false,
        }),
      });
      const firstRow = totalRes.rows?.[0];
      const previewTotalRows =
        firstRow && typeof firstRow.count === "number"
          ? firstRow.count
          : typeof firstRow?.count === "string"
            ? parseInt(String(firstRow.count), 10)
            : null;
      set({
        previewRows: rows,
        loadingPreview: false,
        previewTotalRows: previewTotalRows ?? null,
      });
    } catch (e) {
      console.error("selectTable error:", e);
      set({
        previewRows: [],
        loadingPreview: false,
        previewTotalRows: null,
      });
    }
  },

  loadPreviewPage: async (page: number) => {
    const { selectedTable } = get();
    if (!selectedTable) return;
    await get().selectTable(selectedTable, page);
  },

  executeSQL: async (sql: string, useTransaction = false) => {
    const destructiveType = getDestructiveType(sql);
    if (destructiveType) {
      set({
        pendingDestructiveSQL: sql,
        pendingQueryType: destructiveType,
      });
      return;
    }
    await get().doExecuteSQL(sql, useTransaction);
  },

  confirmDestructiveOperation: () => {
    const { pendingDestructiveSQL, pendingQueryType } = get();
    if (!pendingDestructiveSQL) return;
    set({ pendingDestructiveSQL: null, pendingQueryType: null });
    get().doExecuteSQL(pendingDestructiveSQL, false);
  },

  cancelDestructiveOperation: () => {
    set({ pendingDestructiveSQL: null, pendingQueryType: null });
  },

  doExecuteSQL: async (sql: string, useTransaction: boolean) => {
    set({ isExecuting: true, executionLogs: [] });
    try {
      const res = await fetchApi<ExecuteResponse>("/api/execute", {
        method: "POST",
        body: JSON.stringify({ sql, use_transaction: useTransaction }),
      });
      const logs = res.execution_logs ?? [];
      set((s) => ({
        sql,
        executionLogs: [...s.executionLogs, ...logs],
        isExecuting: false,
        previewColumns: res.columns ?? [],
        previewRows: res.rows ?? [],
        previewTotalRows: res.count ?? null,
      }));
      if (res.schema_refresh_required) {
        get().fetchSchema();
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Execution failed";
      set((s) => ({
        executionLogs: [...s.executionLogs, `[❌] ${msg}`],
        isExecuting: false,
      }));
      throw e;
    }
  },

  translatePrompt: async (prompt: string) => {
    set({ isTranslating: true });
    const { schema, tables } = get();
    const schema_context =
      schema.length > 0
        ? { tables: schema.map((t) => ({ name: t.name, columns: t.columns })) }
        : undefined;
    try {
      const res = await fetchApi<{
        sql: string;
        explanation?: string;
        status?: string;
        message?: string;
        is_conversational?: boolean;
      }>("/api/translate", {
        method: "POST",
        body: JSON.stringify({ prompt, schema_context }),
      });
      set((s) => ({
        messages: [
          ...s.messages,
          { role: "user", content: prompt },
          {
            role: "system",
            content:
              res.explanation ||
              res.message ||
              (res.is_conversational ? "That doesn't appear to be a database query." : "SQL generated."),
          },
        ],
        sql: res.sql ?? "",
        isTranslating: false,
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Translation failed";
      set((s) => ({
        messages: [
          ...s.messages,
          { role: "user", content: prompt },
          { role: "system", content: msg },
        ],
        isTranslating: false,
      }));
    }
  },

  fetchHistory: async () => {
    set({ loadingHistory: true });
    try {
      const list = await fetchApi<HistoryItem[]>("/history?limit=50");
      set({ history: Array.isArray(list) ? list : [], loadingHistory: false });
    } catch (e) {
      console.error("fetchHistory error:", e);
      set({ history: [], loadingHistory: false });
    }
  },

  populateSampleData: async () => {
    const base = getBaseUrl();
    const sampleSql = `
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category TEXT,
  price REAL,
  stock INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO products (name, category, price, stock) VALUES
  ('Widget A', 'Electronics', 29.99, 100),
  ('Widget B', 'Electronics', 49.99, 25),
  ('Gadget X', 'Tools', 19.99, 200);
`.trim();
    set({ isExecuting: true });
    try {
      await fetchApi("/api/execute", {
        method: "POST",
        body: JSON.stringify({ sql: sampleSql, use_transaction: true }),
      });
      await get().fetchSchema();
      const tables = get().tables;
      if (tables.includes("products")) {
        await get().selectTable("products", 1);
      }
    } finally {
      set({ isExecuting: false });
    }
  },
}));
