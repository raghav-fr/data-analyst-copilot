"use client";

import { motion } from "framer-motion";
import { Download, FileText, Table2, FileJson, FileSpreadsheet, Loader2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const EXPORT_OPTIONS = [
  {
    format: "csv" as const,
    label: "CSV",
    description: "Comma-separated values for Excel/Python",
    icon: Table2,
    color: "from-emerald-500/20 to-emerald-600/10",
    border: "border-emerald-500/20",
    iconColor: "text-emerald-400",
  },
  {
    format: "excel" as const,
    label: "Excel (.xlsx)",
    description: "Excel workbook with profile sheet",
    icon: FileSpreadsheet,
    color: "from-green-500/20 to-green-600/10",
    border: "border-green-500/20",
    iconColor: "text-green-400",
  },
  {
    format: "json" as const,
    label: "JSON",
    description: "JSON records format",
    icon: FileJson,
    color: "from-amber-500/20 to-amber-600/10",
    border: "border-amber-500/20",
    iconColor: "text-amber-400",
  },
  {
    format: "pdf" as const,
    label: "PDF Report",
    description: "Executive analysis report with insights",
    icon: FileText,
    color: "from-rose-500/20 to-rose-600/10",
    border: "border-rose-500/20",
    iconColor: "text-rose-400",
  },
];

export default function ExportView() {
  const { activeDataset } = useAppStore();

  const exportMutation = useMutation({
    mutationFn: (format: "csv" | "excel" | "pdf" | "json") =>
      api.exportDataset(activeDataset!.id, format, true),
    onSuccess: () => toast.success("Export downloaded successfully!"),
    onError: (err: Error) => toast.error(`Export failed: ${err.message}`),
  });

  if (!activeDataset) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--text-muted)" }}>Upload a dataset to export it</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Download className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <span className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>Export Dataset</span>
      </div>

      {/* Dataset info */}
      <div className="glass-card p-4 rounded-xl text-sm" style={{ borderColor: "rgba(79,142,247,0.15)" }}>
        <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>{activeDataset.filename}</p>
        <p style={{ color: "var(--text-muted)" }}>
          {activeDataset.rows.toLocaleString()} rows × {activeDataset.columns} columns
        </p>
      </div>

      {/* Export options */}
      <div className="grid grid-cols-2 gap-3">
        {EXPORT_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const isLoading = exportMutation.isPending && exportMutation.variables === opt.format;

          return (
            <motion.button
              key={opt.format}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => exportMutation.mutate(opt.format)}
              disabled={exportMutation.isPending}
              className={`glass-card p-5 rounded-xl border text-left transition-all disabled:opacity-60 ${opt.border}`}
              style={{ background: `linear-gradient(135deg, ${opt.color})` }}>
              <div className="flex items-center justify-between mb-3">
                <Icon className={`w-6 h-6 ${opt.iconColor}`} />
                {isLoading && <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--text-muted)" }} />}
                {!isLoading && <Download className="w-4 h-4 opacity-40" style={{ color: "var(--text-muted)" }} />}
              </div>
              <p className="font-semibold text-sm mb-1" style={{ color: "var(--text-primary)" }}>{opt.label}</p>
              <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{opt.description}</p>
            </motion.button>
          );
        })}
      </div>

      <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
        All exports include the cleaned/processed version of your dataset
      </p>
    </div>
  );
}
