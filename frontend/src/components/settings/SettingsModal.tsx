"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings, X, Brain, Key, Check, Loader2, Wifi, WifiOff, ChevronRight
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useQuery } from "@tanstack/react-query";

export default function SettingsModal() {
  const { settingsOpen, setSettingsOpen, openRouterApiKey, setOpenRouterApiKey } = useAppStore();
  const [keyInput, setKeyInput] = useState(openRouterApiKey);
  const [saving, setSaving] = useState(false);

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.healthCheck(),
    retry: false,
    refetchInterval: 30000,
  });

  const handleSave = async () => {
    setSaving(true);
    setOpenRouterApiKey(keyInput);
    await new Promise(r => setTimeout(r, 500));
    setSaving(false);
    toast.success("API key saved — AI features are now active!");
  };

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
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>Settings</span>
            </div>
            <button onClick={() => setSettingsOpen(false)} className="btn-ghost p-1">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-6 space-y-6">
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

            {/* API Key */}
            <div>
              <label className="text-xs font-medium uppercase tracking-wide mb-3 block"
                style={{ color: "var(--text-muted)" }}>
                OpenRouter API Key
              </label>
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={keyInput}
                    onChange={(e) => setKeyInput(e.target.value)}
                    placeholder="sk-or-v1-..."
                    className="input-base flex-1 text-sm"
                  />
                  <button
                    onClick={handleSave}
                    disabled={saving || keyInput === openRouterApiKey}
                    className="btn-primary flex items-center gap-1.5 flex-shrink-0">
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    Save
                  </button>
                </div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Get your key at{" "}
                  <a href="https://openrouter.ai/keys" target="_blank" className="underline"
                    style={{ color: "var(--accent)" }}>
                    openrouter.ai/keys
                  </a>
                </p>
              </div>
              {openRouterApiKey && (
                <div className="flex items-center gap-2 mt-2 text-xs" style={{ color: "var(--success)" }}>
                  <Check className="w-3 h-3" /> API key configured
                </div>
              )}
            </div>

            {/* Note about backend config */}
            <div className="p-4 rounded-xl border text-xs"
              style={{ background: "var(--bg-secondary)", borderColor: "var(--warning)", color: "var(--text-secondary)" }}>
              <strong style={{ color: "var(--warning)" }}>⚠️ Important:</strong>{" "}
              Your API key must also be set in <code className="text-xs">backend/.env</code> as{" "}
              <code className="text-xs" style={{ color: "var(--accent2)" }}>OPENROUTER_API_KEY=...</code>{" "}
              for the backend to use it.
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
