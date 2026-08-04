"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Upload, MessageSquare, BarChart3, Database, Wand2,
  Download, Settings, Menu, X, ChevronLeft, ChevronRight,
  FileText, Cpu, Hash, Tag, TrendingUp, AlertCircle,
  Sparkles, Home, RefreshCw, Trash2, LogOut, Loader2
} from "lucide-react";
import { auth } from "../../lib/firebase";
import { signOut } from "firebase/auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAppStore } from "../../lib/store";
import { api } from "../../lib/api";
import { formatBytes, formatNumber } from "../../lib/utils";
import FileUpload from "../../components/upload/FileUpload";
import ChatInterface from "../../components/chat/ChatInterface";
import DatasetProfileView from "../../components/profile/DatasetProfile";
import EDAView from "../../components/charts/EDAView";
import SQLView from "../../components/sql/SQLView";
import CleaningView from "../../components/cleaning/CleaningView";
import ExportView from "../../components/export/ExportView";
import SettingsModal from "../../components/settings/SettingsModal";
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

function SidebarContent({
  sidebarCollapsed,
  setSidebarCollapsed,
  onClose,
  isMobile,
}: {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  onClose?: () => void;
  isMobile?: boolean;
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

  // On mobile the sidebar is always "expanded" (full width drawer)
  const isCollapsed = isMobile ? false : sidebarCollapsed;

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center justify-between px-3 py-4 border-b"
        style={{ borderColor: "var(--border-subtle)", minHeight: "60px" }}>
        {isCollapsed ? (
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
              <img src="/icon.svg" alt="Logo" className="w-10 h-10 object-contain flex-shrink-0" />
              <div className="min-w-0">
                <p className="font-bold text-sm leading-tight" style={{ color: "var(--text-primary)" }}>
                  Data Analyst
                </p>
                <p className="text-xs" style={{ color: "var(--accent)" }}>Copilot</p>
              </div>
            </motion.div>
            {/* On mobile show X close, on desktop show collapse arrow */}
            {isMobile ? (
              <button onClick={onClose} className="btn-ghost p-1 ml-auto flex-shrink-0">
                <X className="w-4 h-4 flex-shrink-0" />
              </button>
            ) : (
              <button
                onClick={() => setSidebarCollapsed(true)}
                className="btn-ghost p-1 ml-auto flex-shrink-0">
                <ChevronLeft className="w-4 h-4 flex-shrink-0" />
              </button>
            )}
          </>
        )}
      </div>

      {/* Upload section */}
      <div className="p-3 border-b" style={{ borderColor: "var(--border-subtle)" }}>
        {!isCollapsed ? (
          <div>
            {!activeDataset ? (
              <>
                <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                  DATASET
                </p>
                <FileUpload onUploadSuccess={() => { refetch(); onClose?.(); }} />
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
      {activeDataset && !isCollapsed && (
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

      {/* Saved Datasets */}
      <div className="flex-1 overflow-y-auto px-3 py-2 custom-scrollbar">
        {!isCollapsed && datasets && datasets.length > 0 && (
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
                    onClose?.();
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
      {!isCollapsed && (
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
      <div className={`p-3 border-t flex gap-2 safe-bottom ${isCollapsed ? "flex-col items-center" : "flex-row"}`} style={{ borderColor: "var(--border)" }}>
        <button
          onClick={() => router.push("/")}
          className={`btn-ghost p-2 flex items-center justify-center ${isCollapsed ? "w-12 h-12 rounded-xl" : ""}`}
          style={isCollapsed ? { background: "var(--bg-card)", border: "1px solid var(--border)" } : {}}
          title="Home">
          <Home className="w-4 h-4 flex-shrink-0" />
        </button>
        <button
          onClick={() => { setSettingsOpen(true); onClose?.(); }}
          className={`btn-ghost p-2 flex items-center justify-center ${isCollapsed ? "w-12 h-12 rounded-xl" : "flex-1"}`}
          style={isCollapsed ? { background: "var(--bg-card)", border: "1px solid var(--border)" } : {}}
          title="Settings">
          <Settings className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span className="ml-2 text-xs">Settings</span>}
        </button>
        <button
          onClick={async () => {
            await signOut(auth);
            router.push("/login");
          }}
          className={`btn-ghost p-2 flex items-center justify-center ${isCollapsed ? "w-12 h-12 rounded-xl text-red-400" : "text-red-400 hover:bg-red-500/10"}`}
          style={isCollapsed ? { background: "var(--bg-card)", border: "1px solid var(--border)" } : {}}
          title="Log out">
          <LogOut className="w-4 h-4 flex-shrink-0" />
        </button>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { activeTab, setActiveTab, activeDataset, settingsOpen } = useAppStore();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const currentTab = (activeTab as TabId) || "chat";

  // Auto-collapse sidebar on tablet, expand on desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024 && window.innerWidth >= 768) {
        setSidebarCollapsed(true);
      } else if (window.innerWidth >= 1024) {
        setSidebarCollapsed(false);
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Close mobile menu on route/tab change
  const handleTabChange = (tabId: TabId) => {
    setActiveTab(tabId);
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg-primary)" }}>

      {/* ── Desktop Sidebar (md+) ── */}
      <motion.aside
        animate={{ width: sidebarCollapsed ? 72 : 240 }}
        transition={{ duration: 0.25, ease: "easeInOut" }}
        className="hidden md:flex flex-shrink-0 flex-col border-r overflow-visible shadow-lg z-40 relative"
        style={{
          background: "var(--bg-secondary)",
          borderColor: "var(--border)",
          height: "100vh",
        }}>
        <SidebarContent
          sidebarCollapsed={sidebarCollapsed}
          setSidebarCollapsed={setSidebarCollapsed}
          isMobile={false}
        />
      </motion.aside>

      {/* ── Mobile Sidebar Drawer (< md) ── */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="sidebar-overlay md:hidden"
              onClick={() => setMobileMenuOpen(false)}
            />
            {/* Drawer */}
            <motion.div
              key="drawer"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="fixed left-0 top-0 h-full w-[280px] z-50 md:hidden flex flex-col border-r shadow-2xl"
              style={{
                background: "var(--bg-secondary)",
                borderColor: "var(--border)",
              }}>
              <SidebarContent
                sidebarCollapsed={false}
                setSidebarCollapsed={setSidebarCollapsed}
                onClose={() => setMobileMenuOpen(false)}
                isMobile={true}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top bar */}
        <div className="flex items-center border-b px-2 sm:px-4 py-2 gap-2 sm:gap-3 flex-shrink-0"
          style={{ borderColor: "var(--border-subtle)", background: "var(--bg-secondary)", minHeight: "48px" }}>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="md:hidden btn-ghost p-2 flex items-center justify-center flex-shrink-0"
            aria-label="Open menu">
            <Menu className="w-4 h-4" />
          </button>

          {/* Tab bar — scrollable, icons-only on small mobile */}
          <div className="flex items-center gap-0.5 sm:gap-1 overflow-x-auto flex-1 scrollbar-none">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex-shrink-0"
                  style={{
                    background: isActive ? "var(--bg-hover)" : "transparent",
                    color: isActive ? "var(--accent)" : "var(--text-secondary)",
                    border: isActive ? "1px solid var(--border)" : "1px solid transparent",
                  }}>
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                  {/* Label: hidden on mobile (< sm), visible on sm+ */}
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Dataset pill */}
          {activeDataset && (
            <div className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg border flex-shrink-0 text-xs"
              style={{
                background: "var(--bg-panel)",
                borderColor: "var(--border)",
                color: "var(--accent2)"
              }}>
              <Sparkles className="w-3 h-3 flex-shrink-0" />
              <span className="max-w-[60px] sm:max-w-[120px] truncate">{activeDataset.filename}</span>
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
            <div className="flex flex-col items-center justify-center h-full gap-4 px-4">
              <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl flex items-center justify-center"
                style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
                <Upload className="w-7 h-7 md:w-8 md:h-8" style={{ color: "var(--accent)" }} />
              </div>
              <div className="text-center">
                <p className="font-semibold mb-2" style={{ color: "var(--text-primary)" }}>No dataset loaded</p>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {/* Different hint text for mobile vs desktop */}
                  <span className="md:hidden">Tap ☰ and upload a dataset to get started</span>
                  <span className="hidden md:inline">Upload a CSV or Excel file from the sidebar to get started</span>
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
