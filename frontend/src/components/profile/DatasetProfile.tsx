"use client";

import { motion } from "framer-motion";
import { AlertCircle, Brain, Database, Hash, Tag, Calendar, TrendingUp, BarChart2 } from "lucide-react";
import { DatasetProfile, ColumnProfile } from "../../lib/api";
import { formatNumber, getTypeColor, getTypeIcon } from "../../lib/utils";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useAppStore } from "../../lib/store";

function StatCard({ label, value, sublabel, color }: {
  label: string; value: string | number; sublabel?: string; color?: string;
}) {
  return (
    <div className="stat-card">
      <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p className={`text-xl font-bold ${color || ""}`}
        style={!color ? { color: "var(--text-primary)" } : undefined}>
        {typeof value === "number" ? formatNumber(value) : value}
      </p>
      {sublabel && <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{sublabel}</p>}
    </div>
  );
}

function ColumnCard({ col }: { col: ColumnProfile }) {
  const icon = getTypeIcon(col.dtype);
  const color = getTypeColor(col.dtype);
  const missingPct = col.missing_pct;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card glass-card-hover p-4 rounded-xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-xs font-mono font-bold w-5 h-5 flex items-center justify-center rounded ${color}`}
            style={{ background: "var(--bg-hover)" }}>
            {icon}
          </span>
          <span className="font-medium text-sm truncate" style={{ color: "var(--text-primary)" }}>
            {col.name}
          </span>
        </div>
        <span className="badge badge-blue text-xs flex-shrink-0">{col.dtype}</span>
      </div>

      {/* Missing bar */}
      {missingPct > 0 && (
        <div className="mb-3">
          <div className="flex justify-between text-xs mb-1" style={{ color: "var(--text-muted)" }}>
            <span className="flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> Missing
            </span>
            <span style={{ color: missingPct > 20 ? "var(--danger)" : missingPct > 5 ? "var(--warning)" : "var(--success)" }}>
              {missingPct.toFixed(1)}%
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{
              width: `${missingPct}%`,
              background: missingPct > 20 ? "var(--danger)" : missingPct > 5 ? "var(--warning)" : "var(--success)"
            }} />
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
        <div>
          <p style={{ color: "var(--text-muted)" }}>Unique</p>
          <p className="font-medium" style={{ color: "var(--text-primary)" }}>
            {formatNumber(col.unique)} ({col.unique_pct.toFixed(1)}%)
          </p>
        </div>
        <div>
          <p style={{ color: "var(--text-muted)" }}>Missing</p>
          <p className="font-medium" style={{ color: "var(--text-primary)" }}>
            {formatNumber(col.missing)}
          </p>
        </div>
      </div>

      {/* Numeric stats */}
      {col.stats && "mean" in col.stats && (
        <div className="grid grid-cols-3 gap-1 text-xs border-t pt-3" style={{ borderColor: "var(--border)" }}>
          {(
            [
              ["Mean", col.stats.mean],
              ["Median", col.stats.median],
              ["Std", col.stats.std],
            ] as [string, number | null | undefined][]
          ).map(([label, val]) => (
            <div key={label}>
              <p style={{ color: "var(--text-muted)" }}>{label}</p>
              <p className="font-medium" style={{ color: "var(--accent2)" }}>
                {val !== null && val !== undefined ? Number(val).toFixed(2) : "—"}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Categorical top values */}
      {col.stats && "top_values" in col.stats && (
        <div className="border-t pt-3" style={{ borderColor: "var(--border)" }}>
          <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>Top values</p>
          <div className="flex flex-wrap gap-1">
            {Object.entries(col.stats.top_values as Record<string, number>).slice(0, 4).map(([val, count]) => (
              <span key={val} className="badge badge-cyan text-xs">
                {String(val).slice(0, 15)}{" "}
                <span style={{ opacity: 0.7 }}>({count})</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sample values */}
      {(!col.stats || Object.keys(col.stats).length === 0) && col.sample_values.length > 0 && (
        <div className="border-t pt-3" style={{ borderColor: "var(--border)" }}>
          <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>Sample values</p>
          <p className="text-xs truncate" style={{ color: "var(--text-secondary)" }}>
            {col.sample_values.slice(0, 3).join(", ")}
          </p>
        </div>
      )}
    </motion.div>
  );
}

export default function DatasetProfileView() {
  const { activeDataset, activeTab } = useAppStore();

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ["profile", activeDataset?.id],
    queryFn: () => api.getProfile(activeDataset!.id),
    enabled: !!activeDataset?.id,
  });

  if (!activeDataset) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--text-muted)" }}>Upload a dataset to see its profile</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[1,2,3,4].map(i => <div key={i} className="skeleton h-20" />)}
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[1,2,3,4,5,6].map(i => <div key={i} className="skeleton h-40" />)}
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--danger)" }}>Failed to load profile</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6 overflow-auto h-full">
      {/* Overview stats */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="flex items-center gap-2 mb-4">
          <Brain className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <h3 className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>Dataset Overview</h3>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <StatCard label="Total Rows" value={profile.rows} />
          <StatCard label="Total Columns" value={profile.columns} />
          <StatCard
            label="Missing Values"
            value={`${profile.total_missing_pct.toFixed(1)}%`}
            sublabel={`${profile.total_missing.toLocaleString()} cells`}
            color={profile.total_missing_pct > 10 ? "text-amber-400" : "text-emerald-400"}
          />
          <StatCard
            label="Duplicates"
            value={profile.duplicates}
            color={profile.duplicates > 0 ? "text-amber-400" : "text-emerald-400"}
          />
        </div>

        {/* Column type breakdown */}
        <div className="glass-card p-4 rounded-xl">
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <Hash className="w-4 h-4 text-blue-400" />
              <span style={{ color: "var(--text-secondary)" }}>
                <span className="font-semibold text-blue-400">{profile.numeric_columns.length}</span> Numeric
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Tag className="w-4 h-4 text-emerald-400" />
              <span style={{ color: "var(--text-secondary)" }}>
                <span className="font-semibold text-emerald-400">{profile.categorical_columns.length}</span> Categorical
              </span>
            </div>
            {profile.datetime_columns.length > 0 && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-amber-400" />
                <span style={{ color: "var(--text-secondary)" }}>
                  <span className="font-semibold text-amber-400">{profile.datetime_columns.length}</span> DateTime
                </span>
              </div>
            )}
            <div className="flex items-center gap-2 ml-auto">
              <Database className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {profile.memory_usage_mb.toFixed(2)} MB
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Column profiles */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BarChart2 className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <h3 className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
            Column Details
          </h3>
          <span className="badge badge-blue ml-auto">{profile.column_profiles.length} columns</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
          {profile.column_profiles.map((col, i) => (
            <motion.div
              key={col.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}>
              <ColumnCard col={col} />
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
