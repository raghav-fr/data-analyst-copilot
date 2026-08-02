"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Dataset } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { formatBytes } from "@/lib/utils";
import { toast } from "sonner";
import { auth } from "@/lib/firebase";
import { getStorage, ref, uploadBytesResumable } from "firebase/storage";

interface FileUploadProps {
  onUploadSuccess?: (data: any) => void;
}

type UploadStatus = "idle" | "uploading" | "processing" | "success" | "error";

interface FileWithStatus {
  file: File;
  status: UploadStatus;
  error?: string;
  progress: number;
  datasetId?: string;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [fileState, setFileState] = useState<FileWithStatus | null>(null);
  const { activeDataset, setActiveDataset, setActiveConversationId } = useAppStore();
  const queryClient = useQueryClient();

  // Helper to poll for dataset processing status
  const pollDatasetStatus = useCallback(async (datasetId: string, filename: string) => {
    let polling = true;
    while (polling) {
      try {
        const statusData = await api.getDatasetStatus(datasetId);
        if (statusData.status === "ready") {
          polling = false;
          setFileState((prev) => prev ? { ...prev, status: "success" } : null);
          setActiveConversationId(null);
          queryClient.invalidateQueries({ queryKey: ["datasets"] });
          
          const datasetDetails = {
            id: datasetId,
            dataset_id: datasetId,
            filename: filename,
            rows: statusData.rows || 0,
            columns: statusData.columns || 0,
            column_names: statusData.column_names || [],
          };
          
          setActiveDataset(datasetDetails);
          toast.success(`Dataset ready: ${statusData.rows?.toLocaleString()} rows × ${statusData.columns} columns`);
          onUploadSuccess?.(datasetDetails);
        } else if (statusData.status === "error") {
          polling = false;
          setFileState((prev) => prev ? { ...prev, status: "error", error: statusData.error_message } : null);
          toast.error(`Processing failed: ${statusData.error_message}`);
        } else {
          // Still processing, wait 2 seconds
          await new Promise((resolve) => setTimeout(resolve, 2000));
        }
      } catch (err: any) {
        polling = false;
        setFileState((prev) => prev ? { ...prev, status: "error", error: err.message } : null);
        toast.error(`Failed to get status: ${err.message}`);
      }
    }
  }, [setActiveConversationId, queryClient, setActiveDataset, onUploadSuccess]);


  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!auth.currentUser) {
      toast.error("You must be logged in to upload files.");
      return;
    }

    setFileState({ file, status: "uploading", progress: 0 });

    try {
      const datasetId = crypto.randomUUID();
      const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      const safeName = `${datasetId}${ext}`;
      const storagePath = `users/${auth.currentUser.uid}/datasets/${datasetId}/${safeName}`;
      
      const storage = getStorage();
      const storageRef = ref(storage, storagePath);
      
      const uploadTask = uploadBytesResumable(storageRef, file);
      
      uploadTask.on(
        "state_changed",
        (snapshot) => {
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
          setFileState((prev) => prev ? { ...prev, progress } : null);
        },
        (error) => {
          setFileState((prev) => prev ? { ...prev, status: "error", error: error.message } : null);
          toast.error(`Upload failed: ${error.message}`);
        },
        async () => {
          // Upload complete! Notify backend
          setFileState((prev) => prev ? { ...prev, status: "processing", datasetId } : null);
          try {
            await api.processDataset(datasetId, file.name, storagePath, file.size);
            // Start polling for processing completion
            pollDatasetStatus(datasetId, file.name);
          } catch (err: any) {
            setFileState((prev) => prev ? { ...prev, status: "error", error: err.message } : null);
            toast.error(`Failed to initiate processing: ${err.message}`);
          }
        }
      );
    } catch (err: any) {
      setFileState((prev) => prev ? { ...prev, status: "error", error: err.message } : null);
      toast.error(`Failed to start upload: ${err.message}`);
    }
  }, [pollDatasetStatus]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "application/json": [".json"],
      "application/octet-stream": [".parquet"],
    },
    maxSize: 1024 * 1024 * 1024, // 1GB
    multiple: false,
    disabled: fileState?.status === "uploading" || fileState?.status === "processing",
  });

  const reset = () => {
    setFileState(null);
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
                  Fast direct-to-cloud upload up to 1GB
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
                  {fileState.status !== "uploading" && fileState.status !== "processing" && (
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
                      Uploading to cloud... {Math.round(fileState.progress)}%
                    </p>
                  </div>
                )}
                
                {fileState.status === "processing" && (
                  <div>
                    <div className="progress-bar mb-1">
                      <motion.div
                        className="progress-fill"
                        initial={{ width: "100%" }}
                        animate={{ backgroundPosition: ["0% 0%", "100% 0%"] }}
                        transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                        style={{
                          backgroundSize: "200% 100%",
                          backgroundImage: "linear-gradient(90deg, var(--accent) 0%, rgba(255,255,255,0.4) 50%, var(--accent) 100%)"
                        }}
                      />
                    </div>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      Analyzing dataset with Pandas...
                    </p>
                  </div>
                )}

                {fileState.status === "success" && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" style={{ color: "var(--success)" }} />
                    <span className="text-xs" style={{ color: "var(--success)" }}>
                      Dataset successfully parsed and ready for analysis!
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

              {(fileState.status === "uploading" || fileState.status === "processing") && (
                <Loader2 className="w-5 h-5 animate-spin flex-shrink-0" style={{ color: "var(--accent)" }} />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
