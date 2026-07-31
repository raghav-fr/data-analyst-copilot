"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Wand2, CheckCircle2, Loader2 } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

interface Suggestion {
  operation: string;
  description: string;
  params: Record<string, string>;
}

interface SuggestionsData {
  suggestions: Suggestion[];
}

const OPERATIONS = [
  { id: "drop_duplicates", label: "Remove Duplicates", icon: "🔄", description: "Remove duplicate rows", params: [] },
  { id: "fill_missing", label: "Fill Missing Values", icon: "🩹", description: "Fill null values using a strategy", params: [
    { key: "strategy", label: "Strategy", type: "select", options: ["mean", "median", "mode", "ffill", "bfill", "drop"] },
  ]},
  { id: "drop_columns", label: "Drop Columns", icon: "✂️", description: "Remove selected columns", params: [
    { key: "columns", label: "Columns to drop (Ctrl/Cmd+Click to select multiple)", type: "multiselect" },
  ]},
  { id: "normalize", label: "Normalize Data", icon: "📐", description: "Scale numeric columns", params: [
    { key: "method", label: "Method", type: "select", options: ["minmax", "zscore"] },
  ]},
  { id: "encode_categories", label: "Encode Categories", icon: "🔢", description: "Convert categoricals to numbers", params: [
    { key: "method", label: "Method", type: "select", options: ["label", "onehot"] },
  ]},
  { id: "drop_rows_with_missing", label: "Drop Rows with Nulls", icon: "🗑️", description: "Remove rows with missing values", params: [] },
];

export default function CleaningView() {
  const { activeDataset } = useAppStore();
  const [selectedOp, setSelectedOp] = useState(OPERATIONS[0]);
  const [params, setParams] = useState<Record<string, string>>({ strategy: "mean", method: "minmax" });
  const [history, setHistory] = useState<string[]>([]);

  const { data: suggestionsRaw } = useQuery({
    queryKey: ["cleaning-suggestions", activeDataset?.id],
    queryFn: () => api.getCleaningSuggestions(activeDataset!.id),
    enabled: !!activeDataset?.id,
  });

  const suggestions = suggestionsRaw as SuggestionsData | undefined;

  const cleanMutation = useMutation({
    mutationFn: () =>
      api.cleanData(activeDataset!.id, selectedOp.id, params as Record<string, unknown>),
    onSuccess: (data: unknown) => {
      const result = data as { message: string };
      const msg = result.message ?? "Operation complete";
      setHistory((prev) => [msg, ...prev.slice(0, 9)]);
      toast.success(msg);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (!activeDataset) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--text-muted)" }}>Upload a dataset to run cleaning operations</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}>
        <Wand2 className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <span className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>Data Cleaning</span>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-5">
        {/* AI Suggestions */}
        {suggestions && suggestions.suggestions && suggestions.suggestions.length > 0 && (
          <div className="glass-card p-4 rounded-xl border" style={{ borderColor: "rgba(79,142,247,0.2)" }}>
            <div className="flex items-center gap-2 mb-3">
              <span>🤖</span>
              <span className="font-medium text-sm" style={{ color: "var(--text-primary)" }}>AI Recommendations</span>
            </div>
            <div className="space-y-2">
              {suggestions.suggestions.slice(0, 3).map((s, i) => (
                <button
                  key={i}
                  onClick={() => {
                    const op = OPERATIONS.find(o => o.id === s.operation);
                    if (op) { setSelectedOp(op); setParams(s.params); }
                  }}
                  className="w-full text-left p-3 rounded-lg border text-sm transition-all"
                  style={{ background: "rgba(79,142,247,0.04)", borderColor: "rgba(79,142,247,0.15)", color: "var(--text-secondary)" }}>
                  <span className="font-medium" style={{ color: "var(--accent)" }}>{s.operation}: </span>
                  {s.description}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Operation selector */}
        <div className="space-y-3">
          <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Select Operation</label>
          <div className="grid grid-cols-2 gap-2">
            {OPERATIONS.map((op) => (
              <button
                key={op.id}
                onClick={() => setSelectedOp(op)}
                className="text-left p-3 rounded-xl border transition-all text-sm"
                style={{
                  background: selectedOp.id === op.id ? "rgba(79,142,247,0.1)" : "rgba(255,255,255,0.02)",
                  borderColor: selectedOp.id === op.id ? "rgba(79,142,247,0.3)" : "var(--border-subtle)",
                  color: selectedOp.id === op.id ? "var(--accent)" : "var(--text-secondary)"
                }}>
                <div className="text-lg mb-1">{op.icon}</div>
                <div className="font-medium text-xs">{op.label}</div>
                <div className="text-xs mt-0.5 opacity-70">{op.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Params */}
        {selectedOp.params.length > 0 && (
          <div className="space-y-3">
            <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Parameters</label>
            {selectedOp.params.map((param) => (
              <div key={param.key}>
                <label className="text-xs mb-1 block" style={{ color: "var(--text-muted)" }}>{param.label}</label>
                {param.type === "multiselect" ? (
                  <select
                    multiple
                    value={(params[param.key] as any as string[]) || []}
                    onChange={(e) => {
                      const vals = Array.from(e.target.selectedOptions).map(o => o.value);
                      setParams((p) => ({ ...p, [param.key]: vals as any }));
                    }}
                    className="input-base text-sm min-h-[120px] w-full"
                    style={{ padding: "8px" }}>
                    {activeDataset.column_names.map((col) => <option key={col} value={col} className="p-1">{col}</option>)}
                  </select>
                ) : (
                  <select
                    value={params[param.key] || ""}
                    onChange={(e) => setParams((p) => ({ ...p, [param.key]: e.target.value }))}
                    className="input-base text-sm w-full">
                    {param.options?.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Apply */}
        <button
          onClick={() => cleanMutation.mutate()}
          disabled={cleanMutation.isPending}
          className="btn-primary w-full flex items-center justify-center gap-2">
          {cleanMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>{selectedOp.icon}</span>}
          Apply: {selectedOp.label}
        </button>

        {/* Success */}
        {cleanMutation.isSuccess && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl border"
            style={{ background: "rgba(16,185,129,0.05)", borderColor: "rgba(16,185,129,0.2)" }}>
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="w-4 h-4" style={{ color: "var(--success)" }} />
              <span className="font-medium text-sm" style={{ color: "var(--success)" }}>Operation Complete</span>
            </div>
          </motion.div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>Recent Operations</p>
            {history.map((entry, i) => (
              <div key={i} className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
                style={{ background: "rgba(255,255,255,0.02)", color: "var(--text-secondary)" }}>
                <CheckCircle2 className="w-3 h-3" style={{ color: "var(--success)" }} />
                {entry}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
