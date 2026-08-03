"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Upload, MessageSquare, BarChart3, Database, Wand2,
  Download, Settings, Menu, X, ChevronLeft, ChevronRight,
  FileText, Cpu, Hash, Tag, TrendingUp, AlertCircle,
  Sparkles, Home, RefreshCw, Trash2, LogOut, Loader2
} from "lucide-react";
import { auth } from "@/lib/firebase";
import { signOut } from "firebase/auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { formatBytes, formatNumber } from "@/lib/utils";
import FileUpload from "@/components/upload/FileUpload";
import ChatInterface from "@/components/chat/ChatInterface";
import DatasetProfileView from "@/components/profile/DatasetProfile";
import EDAView from "@/components/charts/EDAView";
import SQLView from "@/components/sql/SQLView";
import CleaningView from "@/components/cleaning/CleaningView";
import ExportView from "@/components/export/ExportView";
import SettingsModal from "@/components/settings/SettingsModal";
import { toast } from "sonner";

type TabId = "chat" | "profile" | "eda" | "sql" | "cleaning" | "export";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "chat", label: "AI Chat", icon: MessageSquare },
  { id: "profile", label: "Profile", icon: FileText },
  { id: "eda", label: "EDA Charts", icon: BarChart3 },
  { id: "sql", label: "SQL Agent", icon: Database },
  { id: "cleaning", label: "Cleaning", icon: Wand2 },
  { id: "export", label: "Export", icon: Download },
];

function Sidebar({ sidebarCollapsed, setSidebarCollapsed }: {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
}) {
  const { user, authLoading, activeDataset, setActiveDataset, setActiveConversationId, setSettingsOpen } = useAppStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: datasets, refetch } = useQuery({
    queryKey: ["datasets"],
    queryFn: api.listDatasets.bind(api),
    staleTime: 60000,
    enabled: !!user && !authLoading,
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

  return (
    <motion.aside
      animate={{ width: sidebarCollapsed ? 72 : 240 }}
      transition={{ duration: 0.25, ease: "easeInOut" }}
      className="flex-shrink-0 flex flex-col border-r overflow-visible shadow-lg z-40 relative"
      style={{
        background: "var(--bg-secondary)",
        borderColor: "var(--border)",
        height: "100vh",
      }}>
      {/* Logo */}
      <div className="flex items-center justify-between px-3 py-4 border-b"
        style={{ borderColor: "var(--border-subtle)", minHeight: "60px" }}>
        {sidebarCollapsed ? (
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="btn-ghost p-1 mx-auto flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full"
            style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
            <ChevronRight className="w-4 h-4 flex-shrink-0" />
          </button>
        ) : (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/20"
                style={{ background: "linear-gradient(135deg, #4f8ef7, #22d3ee)" }}>
                <Brain className="w-4 h-4 text-white flex-shrink-0" />
              </div>
              <div className="min-w-0">
                <p className="font-bold text-sm leading-tight" style={{ color: "var(--text-primary)" }}>
                  Data Analyst
                </p>
                <p className="text-xs" style={{ color: "var(--accent)" }}>Copilot</p>
              </div>
            </motion.div>
            <button
              onClick={() => setSidebarCollapsed(true)}
              className="btn-ghost p-1 ml-auto flex-shrink-0">
              <ChevronLeft className="w-4 h-4 flex-shrink-0" />
            </button>
          </>
        )}
      </div>

      {/* Upload section */}
      <div className="p-3 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        {!sidebarCollapsed ? (
          <div>
            {!activeDataset ? (
              <>
                <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                  DATASET
                </p>
                <FileUpload onUploadSuccess={() => { refetch(); }} />
              </>
            ) : (
              <button 
                onClick={() => { setActiveDataset(null); setActiveConversationId(null); }}
                className="w-full py-2 px-3 rounded-lg border border-dashed flex items-center justify-center gap-2 text-xs font-medium transition-colors hover:bg-[var(--bg-hover)]"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
              >
                <Upload className="w-4 h-4" />
                Upload New Dataset
              </button>
            )}
          </div>
        ) : (
          <button className="flex items-center justify-center w-12 h-12 mx-auto rounded-xl border transition-all"
            style={{ borderColor: "var(--border)", background: "var(--bg-card)", color: "var(--text-secondary)" }}
            onClick={() => { setActiveDataset(null); setActiveConversationId(null); setSidebarCollapsed(false); }}
            title="Upload dataset">
            <Upload className="w-5 h-5 flex-shrink-0" />
          </button>
        )}
      </div>

      {/* Active dataset info */}
      {activeDataset && !sidebarCollapsed && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-3 my-3 p-3 rounded-xl border"
          style={{
            background: "var(--bg-hover)",
            borderColor: "var(--border)"
          }}>
          <div className="flex items-start justify-between gap-1">
            <div className="min-w-0">
              <p className="text-xs font-medium truncate" style={{ color: "var(--accent)" }}>
                {activeDataset.filename}
              </p>
              <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                <span>{formatNumber(activeDataset.rows)} rows</span>
                <span>×</span>
                <span>{activeDataset.columns} cols</span>
              </div>
            </div>
            <button
              onClick={() => { setActiveDataset(null); setActiveConversationId(null); }}
              className="btn-ghost p-0.5 flex-shrink-0">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </motion.div>
      )}

      {/* Spacer / Saved Datasets */}
      <div className="flex-1 overflow-y-auto px-3 py-2 custom-scrollbar">
        {!sidebarCollapsed && datasets && datasets.length > 0 && (
          <div className="flex flex-col gap-2 pb-4">
            <h4 className="text-xs font-semibold mb-1 mt-2" style={{ color: "var(--text-muted)" }}>SAVED DATASETS</h4>
            {datasets.map((ds) => (
              <div 
                key={ds.id} 
                className={`flex items-center justify-between p-2.5 rounded-lg border transition-colors ${activeDataset?.id === ds.id ? "bg-[var(--bg-hover)] border-[var(--accent)]" : "border-[var(--border)] hover:border-[var(--border-hover)]"}`}
              >
                <div 
                  className="flex items-center gap-2.5 min-w-0 flex-1 cursor-pointer"
                  onClick={() => {
                    if (activeDataset?.id !== ds.id) {
                      setActiveConversationId(null);
                      setActiveDataset({
                        id: ds.id,
                        filename: ds.filename,
                        rows: ds.rows,
                        columns: ds.columns,
                        column_names: [],
                      });
                    }
                  }}
                >
                  <FileText className="w-4 h-4 flex-shrink-0" style={{ color: "var(--accent)" }} />
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
                      {ds.filename}
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => deleteMutation.mutate(ds.id)}
                  disabled={deleteMutation.isPending}
                  className="btn-ghost p-1.5 flex-shrink-0 hover:bg-red-500/10 hover:text-red-500"
                  title="Delete dataset"
                >
                  {deleteMutation.isPending && deleteMutation.variables === ds.id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Model indicator */}
      {!sidebarCollapsed && (
        <div className="px-3 pb-2">
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg"
            style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
            <Cpu className="w-3 h-3" style={{ color: "var(--purple)" }} />
            <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
              OpenRouter (Nemotron)
            </span>
            <div className="w-1.5 h-1.5 rounded-full ml-auto" style={{ background: "var(--success)" }} />
          </div>
        </div>
      )}

      {/* Settings & Home & Logout */}
      <div className={`p-3 border-t flex gap-2 ${sidebarCollapsed ? "flex-col items-center" : "flex-row"}`} style={{ borderColor: "var(--border)" }}>
        <button
          onClick={() => router.push("/")}
          className={`btn-ghost p-2 flex items-center justify-center ${sidebarCollapsed ? "w-12 h-12 rounded-xl" : ""}`}
          style={sidebarCollapsed ? { background: "var(--bg-card)", border: "1px solid var(--border)" } : {}}
          title="Home">
          <Home className="w-4 h-4 flex-shrink-0" />
        </button>
        <button
          onClick={() => setSettingsOpen(true)}
          className={`btn-ghost p-2 flex items-center justify-center ${sidebarCollapsed ? "w-12 h-12 rounded-xl" : "flex-1"}`}
          style={sidebarCollapsed ? { background: "var(--bg-card)", border: "1px solid var(--border)" } : {}}
          title="Settings">
          <Settings className="w-4 h-4 flex-shrink-0" />
          {!sidebarCollapsed && <span className="ml-2 text-xs">Settings</span>}
        </button>
        <button
          onClick={async () => {
            await signOut(auth);
            router.push("/login");
          }}
          className={`btn-ghost p-2 flex items-center justify-center ${sidebarCollapsed ? "w-12 h-12 rounded-xl text-red-400" : "text-red-400 hover:bg-red-500/10"}`}
          style={sidebarCollapsed ? { background: "var(--bg-card)", border: "1px solid var(--border)" } : {}}
          title="Log out">
          <LogOut className="w-4 h-4 flex-shrink-0" />
        </button>
      </div>
    </motion.aside>
  );
}

export default function DashboardPage() {
  const { activeTab, setActiveTab, activeDataset, settingsOpen } = useAppStore();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const currentTab = (activeTab as TabId) || "chat";

  const renderContent = () => {
    switch (currentTab) {
      case "chat": return <ChatInterface />;
      case "profile": return <DatasetProfileView />;
      case "eda": return <EDAView />;
      case "sql": return <SQLView />;
      case "cleaning": return <CleaningView />;
      case "export": return <ExportView />;
      default: return <ChatInterface />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      {/* Sidebar */}
      <Sidebar sidebarCollapsed={sidebarCollapsed} setSidebarCollapsed={setSidebarCollapsed} />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top bar */}
        <div className="flex items-center border-b px-4 py-2 gap-3 flex-shrink-0"
          style={{ borderColor: "var(--border-subtle)", background: "var(--bg-secondary)", minHeight: "48px" }}>
          {/* Tab bar */}
          <div className="flex items-center gap-1 overflow-x-auto flex-1">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex-shrink-0"
                  style={{
                    background: isActive ? "var(--bg-hover)" : "transparent",
                    color: isActive ? "var(--accent)" : "var(--text-secondary)",
                    border: isActive ? "1px solid var(--border)" : "1px solid transparent",
                  }}>
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Dataset pill */}
          {activeDataset && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border flex-shrink-0 text-xs"
              style={{
                background: "var(--bg-panel)",
                borderColor: "var(--border)",
                color: "var(--accent2)"
              }}>
              <Sparkles className="w-3 h-3" />
              <span className="max-w-[120px] truncate">{activeDataset.filename}</span>
            </div>
          )}
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-hidden relative">
          <div className="h-full" style={{ display: !activeDataset && currentTab !== "chat" ? "none" : "block" }}>
            <div className={currentTab === "chat" ? "h-full" : "hidden"}><ChatInterface /></div>
            {activeDataset && (
              <>
                <div className={currentTab === "profile" ? "h-full" : "hidden"}><DatasetProfileView /></div>
                <div className={currentTab === "eda" ? "h-full" : "hidden"}><EDAView /></div>
                <div className={currentTab === "sql" ? "h-full" : "hidden"}><SQLView /></div>
                <div className={currentTab === "cleaning" ? "h-full" : "hidden"}><CleaningView /></div>
                <div className={currentTab === "export" ? "h-full" : "hidden"}><ExportView /></div>
              </>
            )}
          </div>
          
          {!activeDataset && currentTab !== "chat" && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
                <Upload className="w-8 h-8" style={{ color: "var(--accent)" }} />
              </div>
              <div className="text-center">
                <p className="font-semibold mb-2" style={{ color: "var(--text-primary)" }}>No dataset loaded</p>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Upload a CSV or Excel file from the sidebar to get started
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal />
    </div>
  );
}
