"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Settings, X, Wifi, WifiOff, User, Mail, Shield, Palette, AlertOctagon, Trash2, LogOut
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { auth } from "@/lib/firebase";
import { signOut } from "firebase/auth";
import { useRouter } from "next/navigation";

export default function SettingsModal() {
  const { settingsOpen, setSettingsOpen, user, setActiveDataset, setActiveConversationId } = useAppStore();
  const queryClient = useQueryClient();
  const router = useRouter();

  const clearDataMutation = useMutation({
    mutationFn: () => api.deleteUserDatasets(),
    onSuccess: () => {
      toast.success("All datasets have been cleared.");
      setActiveDataset(null);
      setActiveConversationId(null);
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
    onError: (err: Error) => {
      toast.error(`Failed to clear data: ${err.message}`);
    }
  });

  const deleteAccountMutation = useMutation({
    mutationFn: () => api.deleteUserAccount(),
    onSuccess: async () => {
      toast.success("Account deleted successfully.");
      setSettingsOpen(false);
      setActiveDataset(null);
      setActiveConversationId(null);
      await signOut(auth);
      router.push("/login");
    },
    onError: (err: Error) => {
      toast.error(`Failed to delete account: ${err.message}`);
    }
  });

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.healthCheck(),
    retry: false,
    refetchInterval: 30000,
  });

  if (!settingsOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: "rgba(0, 0, 0, 0.2)", backdropFilter: "blur(4px)" }}
        onClick={() => setSettingsOpen(false)}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="glass-card rounded-2xl w-full max-w-lg overflow-hidden"
          style={{ border: "1px solid var(--border)" }}
          onClick={(e) => e.stopPropagation()}>
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b"
            style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5" style={{ color: "var(--accent)" }} />
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>Settings & Profile</span>
            </div>
            <button onClick={() => setSettingsOpen(false)} className="btn-ghost p-1">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            
            {/* Profile Section */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide mb-3 block flex items-center gap-2"
                style={{ color: "var(--text-muted)" }}>
                <User className="w-4 h-4" /> User Profile
              </label>
              <div className="glass-card p-4 rounded-xl space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: "var(--accent)", color: "#fff" }}>
                    {user?.email?.charAt(0).toUpperCase() || <User className="w-5 h-5" />}
                  </div>
                  <div>
                    <p className="font-medium text-sm" style={{ color: "var(--text-primary)" }}>
                      {user?.displayName || "Data Analyst User"}
                    </p>
                    <p className="text-xs flex items-center gap-1 mt-0.5" style={{ color: "var(--text-secondary)" }}>
                      <Mail className="w-3 h-3" /> {user?.email || "Not signed in"}
                    </p>
                  </div>
                </div>
                {user?.uid && (
                  <div className="pt-3 border-t mt-3 flex items-center gap-2 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                    <Shield className="w-3 h-3" /> Account ID: <code className="bg-black/10 px-1 py-0.5 rounded">{user.uid}</code>
                  </div>
                )}
              </div>
            </div>



            {/* Danger Zone */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide mb-3 block flex items-center gap-2"
                style={{ color: "var(--danger)" }}>
                <AlertOctagon className="w-4 h-4" /> Danger Zone
              </label>
              <div className="glass-card rounded-xl overflow-hidden divide-y" style={{ borderColor: "var(--danger)", border: "1px solid var(--danger)" }}>
                
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 gap-4">
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Clear All Data</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>Deletes all your uploaded datasets and chat history.</p>
                  </div>
                  <button 
                    onClick={() => {
                      if (window.confirm("Are you sure you want to clear all your datasets? This action cannot be undone.")) {
                        clearDataMutation.mutate();
                      }
                    }}
                    disabled={clearDataMutation.isPending || deleteAccountMutation.isPending}
                    className="btn-ghost flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border flex-shrink-0"
                    style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}>
                    <Trash2 className="w-3.5 h-3.5" />
                    {clearDataMutation.isPending ? "Clearing..." : "Clear Data"}
                  </button>
                </div>

                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 gap-4">
                  <div>
                    <p className="text-sm font-medium text-red-500">Delete Account</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>Permanently destroys your account and all associated data.</p>
                  </div>
                  <button 
                    onClick={() => {
                      if (window.confirm("WARNING: This will permanently delete your account and all data. This action is irreversible. Continue?")) {
                        deleteAccountMutation.mutate();
                      }
                    }}
                    disabled={clearDataMutation.isPending || deleteAccountMutation.isPending}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border flex-shrink-0 bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors"
                    style={{ borderColor: "rgba(239, 68, 68, 0.2)" }}>
                    <LogOut className="w-3.5 h-3.5" />
                    {deleteAccountMutation.isPending ? "Deleting..." : "Delete Account"}
                  </button>
                </div>

              </div>
            </div>

            {/* Backend status */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide mb-3 block"
                style={{ color: "var(--text-muted)" }}>
                System Status
              </label>
              <div className="glass-card p-3 rounded-xl flex items-center gap-3">
                {health ? (
                  <><Wifi className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                      Backend connected <span className="text-emerald-400">●</span>
                    </span></>
                ) : (
                  <><WifiOff className="w-4 h-4 text-red-400" />
                    <span className="text-sm" style={{ color: "var(--danger)" }}>
                      Backend not reachable — is it running on port 8000?
                    </span></>
                )}
              </div>
            </div>

          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
