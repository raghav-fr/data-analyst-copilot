"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Code2, BarChart2, Bot, User, Clock, Copy, Check } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, ChatMessage as ChatMsg } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import DataTable from "@/components/data/DataTable";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  code?: string;
  chart_url?: string;
  table_data?: Record<string, unknown>;
  intent?: string;
  execution_time_ms?: number;
  timestamp: Date;
}

interface SuggestedQuestion {
  question: string;
  category: string;
  icon: string;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [showCode, setShowCode] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { activeDataset, activeConversationId, setActiveConversationId, selectedModel } = useAppStore();

  // Load suggestions
  const { data: suggestionsData } = useQuery({
    queryKey: ["suggestions", activeDataset?.id],
    queryFn: () => api.getSuggestions(activeDataset!.id, selectedModel),
    enabled: !!activeDataset?.id && messages.length === 0,
  });

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      api.chat(activeDataset!.id, message, activeConversationId || undefined, selectedModel),
    onSuccess: (data: ChatMsg) => {
      setActiveConversationId(data.conversation_id);
      const assistantMsg: Message = {
        id: data.message_id,
        role: "assistant",
        content: data.content,
        code: data.code || undefined,
        chart_url: data.chart_url || undefined,
        table_data: data.table_data || undefined,
        intent: data.intent || undefined,
        execution_time_ms: data.execution_time_ms,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    },
    onError: (err: Error) => {
      toast.error(err.message);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: `Error: ${err.message}`,
          timestamp: new Date(),
        },
      ]);
    },
  });

  const sendMessage = (text?: string) => {
    const msg = text || input.trim();
    if (!msg || !activeDataset) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: msg,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    chatMutation.mutate(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const copyCode = async (code: string, id: string) => {
    await navigator.clipboard.writeText(code);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatMutation.isPending]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 140) + "px";
    }
  }, [input]);

  if (!activeDataset) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Bot className="w-14 h-14 mx-auto mb-4 opacity-30" style={{ color: "var(--accent)" }} />
          <p className="font-medium mb-2" style={{ color: "var(--text-secondary)" }}>No dataset selected</p>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Upload a CSV or Excel file to start chatting</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
            <Sparkles className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
          </div>
          <div>
            <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>AI Chat</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{activeDataset.filename}</p>
          </div>
        </div>
        <span className="badge badge-blue text-xs">{selectedModel}</span>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
        {messages.length === 0 && (
          <div className="animate-fade-in">
            {/* Welcome */}
            <div className="text-center mb-6 pt-4">
              <div className="w-12 h-12 rounded-xl mx-auto mb-3 flex items-center justify-center"
                style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
                <Bot className="w-6 h-6" style={{ color: "var(--accent)" }} />
              </div>
              <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>
                Ask me anything about <span style={{ color: "var(--accent)" }}>{activeDataset.filename}</span>
              </p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {activeDataset.rows.toLocaleString()} rows × {activeDataset.columns} columns
              </p>
            </div>

            {/* Suggested questions */}
            {suggestionsData?.questions && suggestionsData.questions.length > 0 && (
              <div>
                <p className="text-xs font-medium mb-3" style={{ color: "var(--text-muted)" }}>
                  💡 Suggested questions
                </p>
                <div className="grid grid-cols-1 gap-2">
                  {suggestionsData.questions.slice(0, 6).map((q, i) => (
                    <motion.button
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      onClick={() => sendMessage(q.question)}
                      className="text-left px-3 py-2.5 rounded-lg border transition-all text-sm hover:border-blue-500/30"
                      style={{
                        background: "var(--bg-hover)",
                        borderColor: "var(--border)",
                        color: "var(--text-secondary)"
                      }}>
                      <span className="mr-2">{q.icon}</span>
                      {q.question}
                    </motion.button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
              {/* Avatar */}
              <div className={`w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center`}
                style={{
                  background: msg.role === "user" ? "var(--bg-hover)" : "var(--bg-card)",
                  border: "1px solid var(--border)",
                  marginTop: "2px"
                }}>
                {msg.role === "user"
                  ? <User className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
                  : <Bot className="w-3.5 h-3.5" style={{ color: "var(--purple)" }} />}
              </div>

              <div className={`flex flex-col gap-2 max-w-[85%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                {/* Message bubble */}
                <div className={msg.role === "user" ? "chat-user" : "chat-assistant"}>
                  {msg.role === "user" ? (
                    <p className="text-sm" style={{ color: "var(--text-primary)" }}>{msg.content}</p>
                  ) : (
                    <div className="prose-dark">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>

                {/* Chart */}
                {msg.chart_url && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="glass-card p-3 rounded-xl border w-full"
                    style={{ borderColor: "var(--border)" }}>
                    <img
                      src={msg.chart_url}
                      alt="Generated chart"
                      className="w-full rounded-lg"
                      style={{ maxHeight: "350px", objectFit: "contain" }}
                    />
                  </motion.div>
                )}

                {/* Table result */}
                {msg.table_data && msg.table_data.type === "dataframe" && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="w-full glass-card rounded-xl overflow-hidden border"
                    style={{ borderColor: "var(--border-subtle)" }}>
                    <DataTable
                      columns={(msg.table_data.columns as string[]) || []}
                      data={(msg.table_data.data as Record<string, unknown>[]) || []}
                      maxRows={10}
                    />
                  </motion.div>
                )}

                {/* Scalar result */}
                {msg.table_data && msg.table_data.type === "scalar" && (
                  <div className="px-4 py-3 rounded-xl border"
                    style={{ background: "var(--bg-hover)", borderColor: "var(--border)" }}>
                    <p className="text-2xl font-bold" style={{ color: "var(--accent2)" }}>
                      {typeof msg.table_data.value === "number"
                        ? msg.table_data.value.toLocaleString(undefined, { maximumFractionDigits: 4 })
                        : String(msg.table_data.value)}
                    </p>
                  </div>
                )}

                {/* Code block */}
                {msg.code && (
                  <div className="w-full">
                    <button
                      onClick={() => setShowCode((prev) => ({ ...prev, [msg.id]: !prev[msg.id] }))}
                      className="flex items-center gap-1.5 text-xs mb-1.5 transition-colors"
                      style={{ color: showCode[msg.id] ? "var(--accent)" : "var(--text-muted)" }}>
                      <Code2 className="w-3.5 h-3.5" />
                      {showCode[msg.id] ? "Hide code" : "Show code"}
                    </button>
                    <AnimatePresence>
                      {showCode[msg.id] && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="relative">
                          <pre className="code-block text-xs overflow-x-auto"
                            style={{ color: "var(--accent2)" }}>
                            <code>{msg.code}</code>
                          </pre>
                          <button
                            onClick={() => copyCode(msg.code!, msg.id)}
                            className="absolute top-2 right-2 p-1.5 rounded-md transition-colors"
                            style={{ background: "var(--bg-panel)" }}>
                            {copied === msg.id
                              ? <Check className="w-3.5 h-3.5 text-green-400" />
                              : <Copy className="w-3.5 h-3.5" style={{ color: "var(--text-muted)" }} />}
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {/* Metadata */}
                <div className="flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  {msg.intent && <span className="badge badge-purple">{msg.intent}</span>}
                  {msg.execution_time_ms && (
                    <span>{msg.execution_time_ms}ms</span>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading indicator */}
        {chatMutation.isPending && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <Bot className="w-3.5 h-3.5" style={{ color: "var(--purple)" }} />
            </div>
            <div className="chat-assistant">
              <div className="loading-dots">
                <span /><span /><span />
              </div>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 px-4 pb-4 pt-2 border-t" style={{ borderColor: "var(--border-subtle)" }}>
        <div className="flex items-end gap-2 rounded-xl border p-2 transition-all focus-within:border-blue-500/40"
          style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={activeDataset ? `Ask about ${activeDataset.filename}...` : "Upload a dataset first"}
            disabled={!activeDataset || chatMutation.isPending}
            className="flex-1 bg-transparent resize-none outline-none text-sm py-1.5 px-2 min-h-[38px] max-h-[140px]"
            style={{ color: "var(--text-primary)", caretColor: "var(--accent)" }}
            rows={1}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => sendMessage()}
            disabled={!input.trim() || !activeDataset || chatMutation.isPending}
            className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-all disabled:opacity-40"
            style={{
              background: input.trim()
                ? "var(--accent)"
                : "var(--bg-hover)",
              border: "1px solid var(--border)",
            }}>
            <Send className="w-4 h-4 text-white" />
          </motion.button>
        </div>
        <p className="text-xs mt-1.5 text-center" style={{ color: "var(--text-muted)" }}>
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
