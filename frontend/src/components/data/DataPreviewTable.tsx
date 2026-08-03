"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Table2, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import { useAppStore } from "../../lib/store";
import { getTypeColor, getTypeIcon } from "../../lib/utils";

export default function DataPreviewTable() {
  const { activeDataset } = useAppStore();
  const [page, setPage] = useState(1);
  const rowsPerPage = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["preview", activeDataset?.id, page],
    queryFn: () => api.getPreview(activeDataset!.id, rowsPerPage, page),
    enabled: !!activeDataset?.id,
  });

  const { data: schema } = useQuery({
    queryKey: ["schema", activeDataset?.id],
    queryFn: () => api.getSchema(activeDataset!.id),
    enabled: !!activeDataset?.id,
  });

  if (!activeDataset) return null;
  if (isLoading) return (
    <div className="flex items-center justify-center p-12">
      <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--accent)" }} />
    </div>
  );
  if (!data) return null;

  const previewData = data as {
    total_rows: number;
    total_pages: number;
    current_page: number;
    columns: string[];
    dtypes: Record<string, string>;
    data: Record<string, unknown>[];
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}>
        <div className="flex items-center gap-2">
          <Table2 className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <span className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>Data Preview</span>
          <span className="badge badge-blue">{previewData.total_rows.toLocaleString()} rows</span>
        </div>
        {/* Pagination */}
        <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          <span>Page {previewData.current_page} of {previewData.total_pages}</span>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-ghost p-1 disabled:opacity-30">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setPage(p => Math.min(previewData.total_pages, p + 1))}
            disabled={page >= previewData.total_pages}
            className="btn-ghost p-1 disabled:opacity-30">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: "50px" }}>#</th>
              {previewData.columns.map((col) => {
                const dtype = previewData.dtypes[col] || "";
                const color = getTypeColor(dtype);
                const icon = getTypeIcon(dtype);
                return (
                  <th key={col}>
                    <div className="flex items-center gap-1.5">
                      <span className={`font-mono text-xs ${color}`}>{icon}</span>
                      <span>{col}</span>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {previewData.data.map((row, i) => (
              <tr key={i}>
                <td style={{ color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {(page - 1) * rowsPerPage + i + 1}
                </td>
                {previewData.columns.map((col) => {
                  const val = row[col];
                  const isEmpty = val === null || val === undefined || val === "";
                  return (
                    <td key={col} title={isEmpty ? "" : String(val)}>
                      {isEmpty
                        ? <span style={{ color: "var(--text-muted)", fontStyle: "italic", fontSize: "11px" }}>null</span>
                        : String(val)
                      }
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
