"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Database, Play, Loader2, AlertCircle, Clock, Rows } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useAppStore } from "../../lib/store";
import { toast } from "sonner";
import DataTable from "../../components/data/DataTable";

const EXAMPLE_QUERIES = [
  "SELECT * FROM data LIMIT 10",
  "SELECT COUNT(*) as total FROM data",
  "SELECT * FROM data WHERE 1=1 LIMIT 5",
];

export default function SQLView() {
  const { activeDataset, selectedModel } = useAppStore();
  const [query, setQuery] = useState("SELECT * FROM data LIMIT 10");
  const [nlQuestion, setNlQuestion] = useState("");
  const [activeMode, setActiveMode] = useState<"sql" | "nl">("sql");

  const sqlMutation = useMutation({
    mutationFn: (q: string) => api.runSQL(activeDataset!.id, q),
    onError: (err: Error) => toast.error(`SQL Error: ${err.message}`),
  });

  const nlMutation = useMutation({
    mutationFn: async (q: string) => {
      const result = await api.nlToSQL(activeDataset!.id, q, selectedModel);
      return result as { sql: string; explanation: string; result: { rows: number; columns: string[]; data: Record<string, unknown>[]; execution_time_ms: number } };
    },
    onSuccess: (data) => {
      if (data?.sql) setQuery(data.sql);
    },
    onError: (err: Error) => toast.error(`Error: ${err.message}`),
  });

  
  useEffect(() => {
    sqlMutation.reset();
    nlMutation.reset();
    setQuery("SELECT * FROM data LIMIT 10");
    setNlQuestion("");
  }, [activeDataset?.id]);

  if (!activeDataset) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--text-muted)" }}>Upload a dataset to run SQL queries</p>
      </div>
    );
  }

  const result = sqlMutation.data;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0 justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <span className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>SQL Agent</span>
          <span className="badge badge-green text-xs">DuckDB</span>
        </div>
        <div className="tab-bar text-xs self-start sm:self-auto">
          <button
            onClick={() => setActiveMode("sql")}
            className={`tab-item py-1 px-3 ${activeMode === "sql" ? "active" : ""}`}>
            SQL Editor
          </button>
          <button
            onClick={() => setActiveMode("nl")}
            className={`tab-item py-1 px-3 ${activeMode === "nl" ? "active" : ""}`}>
            Natural Language
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* NL to SQL mode */}
        {activeMode === "nl" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Describe what you want in plain English and AI will convert it to SQL.
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                value={nlQuestion}
                onChange={(e) => setNlQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && nlQuestion && nlMutation.mutate(nlQuestion)}
                placeholder="e.g. Show top 10 customers by revenue"
                className="input-base flex-1"
              />
              <button
                onClick={() => nlQuestion && nlMutation.mutate(nlQuestion)}
                disabled={!nlQuestion || nlMutation.isPending}
                className="btn-primary flex items-center gap-2 justify-center flex-shrink-0">
                {nlMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Convert
              </button>
            </div>
            {nlMutation.data?.explanation && (
              <div className="glass-card p-3 rounded-xl border text-sm"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}>
                💡 {nlMutation.data.explanation}
              </div>
            )}
          </motion.div>
        )}

        {/* SQL Editor */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
              SQL Query <span style={{ color: "var(--text-muted)" }}>(table name: <code>data</code>)</span>
            </label>
            <div className="flex gap-1">
              {EXAMPLE_QUERIES.slice(0, 2).map((q, i) => (
                <button key={i} onClick={() => setQuery(q)}
                  className="badge badge-blue text-xs cursor-pointer">
                  Example {i + 1}
                </button>
              ))}
            </div>
          </div>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="input-base font-mono text-xs"
            style={{ minHeight: "120px", resize: "vertical", fontFamily: "JetBrains Mono, monospace" }}
            placeholder="SELECT * FROM data LIMIT 10"
          />
          <div className="flex items-center justify-between">
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Only SELECT queries allowed. Table name is always <code className="text-xs">data</code>.
            </p>
            <button
              onClick={() => query && sqlMutation.mutate(query)}
              disabled={!query.trim() || sqlMutation.isPending}
              className="btn-primary flex items-center gap-2">
              {sqlMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run Query
            </button>
          </div>
        </div>

        {/* Error */}
        {sqlMutation.isError && (
          <div className="flex items-start gap-3 p-4 rounded-xl border"
            style={{ background: "var(--bg-secondary)", borderColor: "var(--danger)" }}>
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--danger)" }} />
            <div>
              <p className="font-medium text-sm mb-1" style={{ color: "var(--danger)" }}>Query Error</p>
              <p className="text-xs font-mono" style={{ color: "var(--text-secondary)" }}>
                {sqlMutation.error?.message}
              </p>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            {/* Result header */}
            <div className="flex flex-wrap items-center gap-3 sm:gap-4 mb-3 text-sm">
              <div className="flex items-center gap-1.5">
                <Rows className="w-4 h-4" style={{ color: "var(--accent)" }} />
                <span style={{ color: "var(--text-primary)" }}>{result.rows.toLocaleString()} rows</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Database className="w-4 h-4" style={{ color: "var(--accent2)" }} />
                <span style={{ color: "var(--text-primary)" }}>{result.columns.length} columns</span>
              </div>
              <div className="flex items-center gap-1.5 sm:ml-auto">
                <Clock className="w-3.5 h-3.5" style={{ color: "var(--text-muted)" }} />
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>{result.execution_time_ms}ms</span>
              </div>
            </div>

            {/* Table */}
            <div className="glass-card rounded-xl overflow-hidden border"
              style={{ borderColor: "var(--border)" }}>
              <DataTable columns={result.columns} data={result.data} maxRows={200} />
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
