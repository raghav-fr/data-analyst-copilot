"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, CheckCircle2, AlertCircle, Loader2, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, UploadResponse, Dataset } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { formatBytes } from "@/lib/utils";
import { toast } from "sonner";

interface FileUploadProps {
  onUploadSuccess?: (data: UploadResponse) => void;
}

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface FileWithStatus {
  file: File;
  status: UploadStatus;
  error?: string;
  progress: number;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [fileState, setFileState] = useState<FileWithStatus | null>(null);
  const { activeDataset, setActiveDataset, setActiveConversationId } = useAppStore();
  const queryClient = useQueryClient();

  const { data: datasets } = useQuery({
    queryKey: ["datasets"],
    queryFn: () => api.listDatasets(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDataset(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      if (activeDataset?.id === deletedId) {
        setActiveDataset(null);
        setActiveConversationId(null);
      }
      toast.success("Dataset deleted successfully");
    },
    onError: (err: Error) => {
      toast.error(`Failed to delete: ${err.message}`);
    }
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadFile(file),
    onSuccess: (data) => {
      setFileState((prev) => prev ? { ...prev, status: "success", progress: 100 } : null);
      setActiveConversationId(null);
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      setActiveDataset({
        id: data.dataset_id,
        filename: data.filename,
        rows: data.rows,
        columns: data.columns,
        column_names: data.column_names,
      });
      toast.success(`Dataset loaded: ${data.rows.toLocaleString()} rows × ${data.columns} columns`);
      onUploadSuccess?.(data);
    },
    onError: (err: Error) => {
      setFileState((prev) => prev ? { ...prev, status: "error", error: err.message } : null);
      toast.error(`Upload failed: ${err.message}`);
    },
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setFileState({ file, status: "uploading", progress: 0 });

    // Simulate progress while uploading
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress > 90) { clearInterval(interval); progress = 90; }
      setFileState((prev) => prev ? { ...prev, progress } : null);
    }, 200);

    uploadMutation.mutate(file, {
      onSettled: () => clearInterval(interval),
    });
  }, [uploadMutation]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "application/json": [".json"],
      "application/octet-stream": [".parquet"],
    },
    maxSize: 100 * 1024 * 1024,
    multiple: false,
    disabled: uploadMutation.isPending,
  });

  const reset = () => {
    setFileState(null);
    uploadMutation.reset();
  };

  return (
    <div className="w-full">
      <AnimatePresence mode="wait">
        {!fileState ? (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.2 }}>
            <div
              {...getRootProps()}
              className={`drop-zone aspect-square flex flex-col items-center justify-center p-4 text-center transition-all ${isDragActive ? "active" : ""} ${isDragReject ? "border-red-500/50" : ""}`}>
              <input {...getInputProps()} />
              <motion.div
                animate={isDragActive ? { scale: 1.1 } : { scale: 1 }}
                transition={{ type: "spring", stiffness: 300 }}>
                <div className="flex justify-center mb-5">
                  <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                    style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
                    <Upload className="w-8 h-8" style={{ color: "var(--accent)" }} />
                  </div>
                </div>

                <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                  {isDragActive ? "Drop your file here" : "Upload your dataset"}
                </h3>
                <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
                  Drag & drop or{" "}
                  <span style={{ color: "var(--accent)", cursor: "pointer" }}>browse files</span>
                </p>
                <div className="flex justify-center gap-2 flex-wrap">
                  {["CSV", "Excel", "JSON", "Parquet"].map((fmt) => (
                    <span key={fmt} className="badge badge-blue">{fmt}</span>
                  ))}
                </div>
                <p className="text-xs mt-4" style={{ color: "var(--text-muted)" }}>
                  Max file size: 100MB
                </p>
              </motion.div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="file-status"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="glass-card p-5">
            <div className="flex items-start gap-4">
              {/* File icon */}
              <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
                <FileText className="w-6 h-6" style={{ color: "var(--accent)" }} />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <p className="font-medium truncate text-sm" style={{ color: "var(--text-primary)" }}>
                    {fileState.file.name}
                  </p>
                  {fileState.status !== "uploading" && (
                    <button onClick={reset} className="btn-ghost p-1 ml-2 flex-shrink-0">
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
                <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
                  {formatBytes(fileState.file.size)}
                </p>

                {/* Progress bar */}
                {fileState.status === "uploading" && (
                  <div>
                    <div className="progress-bar mb-1">
                      <motion.div
                        className="progress-fill"
                        initial={{ width: 0 }}
                        animate={{ width: `${fileState.progress}%` }}
                        transition={{ ease: "easeOut" }}
                      />
                    </div>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      Uploading... {Math.round(fileState.progress)}%
                    </p>
                  </div>
                )}

                {fileState.status === "success" && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" style={{ color: "var(--success)" }} />
                    <span className="text-xs" style={{ color: "var(--success)" }}>
                      Upload successful — dataset ready for analysis
                    </span>
                  </div>
                )}

                {fileState.status === "error" && (
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" style={{ color: "var(--danger)" }} />
                    <span className="text-xs" style={{ color: "var(--danger)" }}>
                      {fileState.error}
                    </span>
                  </div>
                )}
              </div>

              {fileState.status === "uploading" && (
                <Loader2 className="w-5 h-5 animate-spin flex-shrink-0" style={{ color: "var(--accent)" }} />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
