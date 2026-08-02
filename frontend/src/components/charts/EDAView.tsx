"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BarChart3, Loader2, ChevronDown, ChevronUp, Lightbulb, AlertCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";

interface ChartCardProps {
  chart: {
    chart_type: string;
    title: string;
    column?: string;
    image_url: string;
    insight?: string;
  };
  index: number;
}

function ChartCard({ chart, index }: ChartCardProps) {
  const [showInsight, setShowInsight] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  const typeColors: Record<string, string> = {
    histogram: "badge-blue",
    boxplot: "badge-cyan",
    correlation_heatmap: "badge-purple",
    countplot: "badge-green",
    pairplot: "badge-amber",
    missing_heatmap: "badge-red",
    line_chart: "badge-cyan",
    bar_chart: "badge-blue",
    scatter: "badge-purple",
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.06, duration: 0.4 }}
        className="glass-card rounded-xl overflow-hidden border"
        style={{ borderColor: "var(--border)" }}>
        {/* Card header */}
        <div className="flex items-center justify-between px-4 py-3 border-b"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
          <div className="flex items-center gap-2 min-w-0">
            <span className={`badge ${typeColors[chart.chart_type] || "badge-blue"} text-xs flex-shrink-0`}>
              {chart.chart_type.replace("_", " ")}
            </span>
            <span className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
              {chart.title}
            </span>
          </div>
          <button
            onClick={() => setFullscreen(true)}
            className="btn-ghost p-1 text-xs flex-shrink-0"
            style={{ color: "var(--text-muted)" }}>
            ⤢
          </button>
        </div>

        {/* Chart image */}
        <div className="p-3 cursor-pointer" onClick={() => setFullscreen(true)}>
          <img
            src={chart.image_url}
            alt={chart.title}
            className="w-full rounded-lg"
            style={{ maxHeight: "280px", objectFit: "contain" }}
            loading="lazy"
          />
        </div>

        {/* Insight toggle */}
        {chart.insight && (
          <div className="border-t" style={{ borderColor: "var(--border)" }}>
            <button
              onClick={() => setShowInsight(!showInsight)}
              className="flex items-center gap-2 w-full px-4 py-2.5 text-sm transition-colors"
              style={{ color: showInsight ? "var(--accent)" : "var(--text-secondary)" }}>
              <Lightbulb className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="flex-1 text-left">AI Insight</span>
              {showInsight ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            <AnimatePresence>
              {showInsight && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden">
                  <div className="px-4 pb-4">
                    <div className="prose-dark text-xs rounded-lg p-3"
                      style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{chart.insight}</ReactMarkdown>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </motion.div>

      {/* Fullscreen modal */}
      <AnimatePresence>
        {fullscreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: "var(--bg-secondary)" }}
            onClick={() => setFullscreen(false)}>
            <motion.div
              initial={{ scale: 0.92 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.92 }}
              className="glass-card rounded-2xl max-w-5xl w-full max-h-[90vh] overflow-auto"
              onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between px-5 py-3 border-b"
                style={{ borderColor: "var(--border)" }}>
                <h3 className="font-semibold" style={{ color: "var(--text-primary)" }}>{chart.title}</h3>
                <button onClick={() => setFullscreen(false)} className="btn-ghost p-1">✕</button>
              </div>
              <div className="p-5">
                <img src={chart.image_url} alt={chart.title} className="w-full rounded-xl" />
                {chart.insight && (
                  <div className="mt-5 prose-dark"
                    style={{ background: "var(--bg-hover)", border: "1px solid var(--border)", borderRadius: "10px", padding: "14px" }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{chart.insight}</ReactMarkdown>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default function EDAView() {
  const { activeDataset, activeTab } = useAppStore();
  const [filter, setFilter] = useState<string>("all");

  const { data: edaData, isLoading, error, refetch } = useQuery({
    queryKey: ["eda", activeDataset?.id],
    queryFn: () => api.runEDA(activeDataset!.id, true),
    enabled: !!activeDataset?.id,
    staleTime: 5 * 60 * 1000,
  });

  if (!activeDataset) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--text-muted)" }}>Upload a dataset to run EDA</p>
      </div>
    );
  }

  const filters = ["all", "histogram", "boxplot", "correlation_heatmap", "countplot", "pairplot", "missing_heatmap"];
  const filteredCharts = edaData?.charts.filter(c => filter === "all" || c.chart_type === filter) || [];

  return (
    <div className="h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b sticky top-0 z-10"
        style={{ borderColor: "var(--border)", background: "var(--bg-primary)" }}>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <h3 className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
            Exploratory Data Analysis
          </h3>
          {edaData && (
            <span className="badge badge-blue">{edaData.charts.length} charts</span>
          )}
        </div>
        {!isLoading && (
          <button onClick={() => refetch()} className="btn-ghost text-xs px-3 py-1.5">
            Refresh
          </button>
        )}
      </div>

      {isLoading && (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <div className="relative w-12 h-12">
            <div className="absolute inset-0 rounded-full border-2 border-blue-500/20" />
            <div className="absolute inset-0 rounded-full border-2 border-t-blue-500 animate-spin" />
          </div>
          <div className="text-center">
            <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>Generating EDA charts...</p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              AI is analyzing your data and generating insights
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--danger)" }} />
            <p style={{ color: "var(--danger)" }}>Failed to generate EDA charts</p>
            <button onClick={() => refetch()} className="btn-secondary mt-3 text-sm">Retry</button>
          </div>
        </div>
      )}

      {edaData && (
        <div className="p-4 space-y-5">
          {/* EDA summary insight */}
          {edaData.summary_insight && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-5 rounded-xl border"
              style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-4 h-4" style={{ color: "var(--accent)" }} />
                <h4 className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
                  AI EDA Summary
                </h4>
              </div>
              <div className="prose-dark text-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{edaData.summary_insight}</ReactMarkdown>
              </div>
            </motion.div>
          )}

          {/* Chart type filter */}
          <div className="flex gap-2 flex-wrap">
            {filters.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`badge text-xs cursor-pointer transition-all ${filter === f ? "badge-blue" : ""}`}
                style={filter !== f ? {
                  background: "var(--bg-card)",
                  color: "var(--text-secondary)",
                  borderColor: "var(--border)"
                } : {}}>
                {f === "all" ? `All (${edaData.charts.length})` : f.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* Charts grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredCharts.map((chart, i) => (
              <ChartCard key={`${chart.chart_type}-${chart.column || i}`} chart={chart} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
