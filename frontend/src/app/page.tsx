"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  BarChart3, Brain, Database, FileUp, GitBranch,
  LineChart, MessageSquare, Sparkles, Zap, ChevronRight,
  ArrowRight, Shield, Cpu, Globe
} from "lucide-react";

const features = [
  {
    icon: FileUp,
    title: "Upload Any Dataset",
    desc: "CSV, Excel, JSON — drop your file and instantly see a full profile",
    color: "from-blue-500/20 to-blue-600/10",
    border: "border-blue-500/20",
    iconColor: "text-blue-400",
  },
  {
    icon: Brain,
    title: "AI-Powered Chat",
    desc: "Ask questions in plain English and get instant answers with code",
    color: "from-purple-500/20 to-purple-600/10",
    border: "border-purple-500/20",
    iconColor: "text-purple-400",
  },
  {
    icon: BarChart3,
    title: "Auto-EDA Charts",
    desc: "Histograms, heatmaps, boxplots, scatter plots generated automatically",
    color: "from-cyan-500/20 to-cyan-600/10",
    border: "border-cyan-500/20",
    iconColor: "text-cyan-400",
  },
  {
    icon: Database,
    title: "SQL Agent",
    desc: "Run DuckDB SQL queries or convert natural language to SQL instantly",
    color: "from-emerald-500/20 to-emerald-600/10",
    border: "border-emerald-500/20",
    iconColor: "text-emerald-400",
  },
  {
    icon: LineChart,
    title: "Statistical Analysis",
    desc: "Correlation, ANOVA, regression, outlier detection, and distributions",
    color: "from-amber-500/20 to-amber-600/10",
    border: "border-amber-500/20",
    iconColor: "text-amber-400",
  },
  {
    icon: GitBranch,
    title: "ML Assistant",
    desc: "AutoML with scikit-learn — detect target, train, and evaluate models",
    color: "from-rose-500/20 to-rose-600/10",
    border: "border-rose-500/20",
    iconColor: "text-rose-400",
  },
];

const stats = [
  { value: "20+", label: "Analysis Phases" },
  { value: "10+", label: "Chart Types" },
  { value: "4", label: "Export Formats" },
  { value: "∞", label: "Datasets" },
];

const techStack = [
  { name: "OpenRouter", icon: "🧠" },
  { name: "FastAPI", icon: "⚡" },
  { name: "LangGraph", icon: "🔗" },
  { name: "Pandas", icon: "🐼" },
  { name: "DuckDB", icon: "🦆" },
  { name: "Next.js 14", icon: "▲" },
  { name: "Scikit-learn", icon: "🤖" },
  { name: "Plotly", icon: "📊" },
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen relative overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      {/* Background glow orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[400px] h-[400px] md:w-[600px] md:h-[600px] rounded-full opacity-[0.06]"
          style={{ background: "radial-gradient(circle, #4f8ef7, transparent)" }} />
        <div className="absolute top-[30%] right-[-15%] w-[300px] h-[300px] md:w-[500px] md:h-[500px] rounded-full opacity-[0.05]"
          style={{ background: "radial-gradient(circle, #22d3ee, transparent)" }} />
        <div className="absolute bottom-[-10%] left-[30%] w-[250px] h-[250px] md:w-[400px] md:h-[400px] rounded-full opacity-[0.04]"
          style={{ background: "radial-gradient(circle, #a78bfa, transparent)" }} />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-4 sm:px-6 md:px-8 py-4 md:py-5 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 md:gap-3">
          <img src="/icon.svg" alt="Logo" className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 object-contain" />
          <span className="font-bold text-sm sm:text-base md:text-lg" style={{ color: "var(--text-primary)" }}>
            <span className="hidden sm:inline">Data Analyst Copilot</span>
            <span className="sm:hidden">DA Copilot</span>
          </span>
        </div>
        <div className="flex items-center gap-2 md:gap-3">
          <a href="https://github.com" target="_blank"
            className="btn-ghost text-sm hidden sm:flex items-center gap-2">
            <Globe className="w-4 h-4" /> GitHub
          </a>
          <button
            onClick={() => router.push("/login")}
            className="btn-primary flex items-center gap-1.5 md:gap-2 text-sm px-4 md:px-5">
            Launch App <ArrowRight className="w-3.5 h-3.5 md:w-4 md:h-4" />
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 text-center pt-12 md:pt-20 pb-12 md:pb-16 px-4 sm:px-6 max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}>
          <div className="inline-flex items-center gap-2 px-3 md:px-4 py-1.5 md:py-2 rounded-full border mb-5 md:mb-6"
            style={{
              background: "var(--bg-hover)",
              borderColor: "var(--border)",
              color: "var(--accent)"
            }}>
            <Sparkles className="w-3 h-3 md:w-3.5 md:h-3.5" />
            <span className="text-xs font-medium">Powered by OpenRouter</span>
          </div>

          <h1 className="hero-title font-extrabold leading-tight mb-4 md:mb-6">
            <span className="gradient-text">AI Data Analyst</span>
            <br />
            <span style={{ color: "var(--text-primary)" }}>at Your Fingertips</span>
          </h1>

          <p className="text-base md:text-xl mb-8 md:mb-10 max-w-2xl mx-auto px-2" style={{ color: "var(--text-secondary)" }}>
            Upload any dataset. Ask questions in natural language. Get instant charts,
            statistics, SQL queries, ML models, and executive reports — all powered by AI.
          </p>

          <div className="flex items-center justify-center gap-3 md:gap-4 flex-wrap">
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push("/signup")}
              className="btn-primary flex items-center gap-2 text-sm md:text-base px-6 md:px-8 py-2.5 md:py-3"
              style={{ borderRadius: "12px" }}>
              <Zap className="w-4 h-4 md:w-5 md:h-5" />
              Start Analyzing Free
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.98 }}
              className="btn-secondary flex items-center gap-2 text-sm md:text-base px-6 md:px-8 py-2.5 md:py-3"
              style={{ borderRadius: "12px" }}>
              <MessageSquare className="w-4 h-4 md:w-5 md:h-5" />
              See Demo
            </motion.button>
          </div>
        </motion.div>

        {/* Stats row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="grid grid-cols-2 sm:grid-cols-4 gap-4 md:gap-6 mt-12 md:mt-16 max-w-2xl mx-auto">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-2xl md:text-3xl font-extrabold gradient-text">{stat.value}</div>
              <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* Dashboard Preview — hidden on very small screens, simplified on tablet */}
      <motion.section
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.7 }}
        className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 mb-16 md:mb-24">
        <div className="glass-card p-1 rounded-2xl"
          style={{ boxShadow: "0 4px 60px rgba(15, 23, 42, 0.08)" }}>
          {/* Mock browser chrome */}
          <div className="flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-2.5 md:py-3 rounded-t-xl border-b"
            style={{ background: "var(--bg-secondary)", borderColor: "var(--border)" }}>
            <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded-full" style={{ background: "#f43f5e" }} />
            <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded-full" style={{ background: "#f59e0b" }} />
            <div className="w-2.5 h-2.5 md:w-3 md:h-3 rounded-full" style={{ background: "#10b981" }} />
            <div className="flex-1 mx-2 md:mx-4 px-3 md:px-4 py-1 rounded-md text-xs text-center hidden sm:block"
              style={{ background: "var(--bg-panel)", color: "var(--text-muted)", border: "1px solid var(--border)" }}>
              localhost:3000/dashboard
            </div>
          </div>
          {/* Mock dashboard content */}
          <div className="rounded-b-xl overflow-hidden"
            style={{ background: "var(--bg-primary)" }}>

            {/* Mobile simplified preview */}
            <div className="block md:hidden p-6 text-center" style={{ minHeight: "160px" }}>
              <div className="flex items-center justify-center gap-3 mb-4">
                {["Chat", "EDA", "SQL", "Export"].map((item, i) => (
                  <div key={item} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs"
                    style={{
                      background: i === 0 ? "var(--bg-hover)" : "transparent",
                      color: i === 0 ? "var(--accent)" : "var(--text-muted)",
                      border: "1px solid var(--border)"
                    }}>
                    {item}
                  </div>
                ))}
              </div>
              <div className="space-y-2 text-left max-w-xs mx-auto">
                <div className="chat-user self-end text-xs" style={{ color: "var(--text-primary)" }}>
                  Which state has the highest revenue?
                </div>
                <div className="chat-assistant text-xs" style={{ color: "var(--text-primary)" }}>
                  California leads with $2.3M in total revenue, followed by Texas at $1.8M...
                </div>
              </div>
            </div>

            {/* Desktop full preview */}
            <div className="hidden md:grid grid-cols-12 h-[380px]">
              {/* Sidebar mock */}
              <div className="col-span-2 border-r p-3 flex flex-col gap-2"
                style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
                {["Chat", "EDA", "Statistics", "SQL", "Cleaning", "Export"].map((item, i) => (
                  <div key={item} className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
                    style={{
                      background: i === 0 ? "var(--bg-hover)" : "transparent",
                      color: i === 0 ? "var(--accent)" : "var(--text-secondary)"
                    }}>
                    <div className="w-3 h-3 rounded" style={{ background: i === 0 ? "var(--accent)" : "var(--border)" }} />
                    {item}
                  </div>
                ))}
              </div>
              {/* Main mock */}
              <div className="col-span-6 p-4 flex flex-col gap-3">
                {["Which state has the highest revenue?", "", "California leads with $2.3M in total revenue, followed by Texas at $1.8M..."].map((msg, i) => (
                  msg === "" ? null :
                    <div key={i} className={i === 0 ? "chat-user self-end" : "chat-assistant"}>
                      <p className="text-xs" style={{ color: i === 0 ? "#a0c4ff" : "var(--text-primary)" }}>{msg}</p>
                    </div>
                ))}
                <div className="glass-card p-3 rounded-lg border"
                  style={{ borderColor: "var(--border)", background: "var(--bg-panel)" }}>
                  <p className="text-xs font-mono" style={{ color: "var(--accent2)" }}>
                    df.groupby('State')['Revenue'].sum().sort_values(ascending=False).head()
                  </p>
                </div>
              </div>
              {/* Chart mock */}
              <div className="col-span-4 border-l p-4" style={{ borderColor: "var(--border)" }}>
                <p className="text-xs font-medium mb-3" style={{ color: "var(--text-secondary)" }}>Revenue by State</p>
                {["California", "Texas", "New York", "Florida", "Illinois"].map((state, i) => (
                  <div key={state} className="flex items-center gap-2 mb-2">
                    <span className="text-xs w-16 truncate" style={{ color: "var(--text-muted)" }}>{state}</span>
                    <div className="flex-1 h-4 rounded overflow-hidden" style={{ background: "var(--bg-panel)" }}>
                      <div className="h-full rounded transition-all"
                        style={{
                          width: `${100 - i * 16}%`,
                          background: `linear-gradient(90deg, ${["#4f8ef7","#22d3ee","#a78bfa","#10b981","#f59e0b"][i]}, transparent)`
                        }} />
                    </div>
                    <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{(2.3 - i * 0.4).toFixed(1)}M</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* Features Grid */}
      <section className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 mb-16 md:mb-24">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center mb-8 md:mb-12">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-3 md:mb-4" style={{ color: "var(--text-primary)" }}>
            Everything You Need to{" "}
            <span className="gradient-text">Analyze Data</span>
          </h2>
          <p className="text-sm md:text-base px-4" style={{ color: "var(--text-secondary)" }}>
            A complete analytics platform in one tool — no BI license required
          </p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i }}
                className="glass-card glass-card-hover p-5 md:p-6">
                <div className={`inline-flex p-2.5 md:p-3 rounded-xl bg-gradient-to-br ${f.color} border ${f.border} mb-3 md:mb-4`}>
                  <Icon className={`w-5 h-5 md:w-6 md:h-6 ${f.iconColor}`} />
                </div>
                <h3 className="font-semibold text-sm md:text-base mb-1.5 md:mb-2" style={{ color: "var(--text-primary)" }}>{f.title}</h3>
                <p className="text-xs md:text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{f.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 mb-16 md:mb-24">
        <div className="glass-card p-5 md:p-8">
          <div className="text-center mb-6 md:mb-8">
            <div className="flex items-center justify-center gap-2 mb-3">
              <Cpu className="w-4 h-4 md:w-5 md:h-5" style={{ color: "var(--accent)" }} />
              <span className="font-semibold text-sm md:text-base" style={{ color: "var(--text-primary)" }}>Built With World-Class Tech</span>
            </div>
          </div>
          <div className="flex flex-wrap justify-center gap-2 md:gap-3">
            {techStack.map((tech) => (
              <div key={tech.name}
                className="flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-1.5 md:py-2 rounded-full border text-xs md:text-sm"
                style={{
                  background: "var(--bg-hover)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)"
                }}>
                <span>{tech.icon}</span>
                <span className="font-medium">{tech.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 pb-16 md:pb-24 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6 }}>
          <div className="glass-card p-8 md:p-12"
            style={{ boxShadow: "0 4px 40px rgba(15, 23, 42, 0.06)" }}>
            <Shield className="w-8 h-8 md:w-10 md:h-10 mx-auto mb-3 md:mb-4" style={{ color: "var(--accent)" }} />
            <h2 className="text-2xl md:text-3xl font-bold mb-3 md:mb-4" style={{ color: "var(--text-primary)" }}>
              Ready to Analyze Smarter?
            </h2>
            <p className="mb-6 md:mb-8 text-sm md:text-base" style={{ color: "var(--text-secondary)" }}>
              Upload your first dataset and let AI do the heavy lifting.
              No setup required — just drop a file and start asking questions.
            </p>
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => router.push("/login")}
              className="btn-primary flex items-center gap-2 mx-auto text-sm md:text-base px-8 md:px-10 py-2.5 md:py-3"
              style={{ borderRadius: "12px" }}>
              Open Dashboard <ChevronRight className="w-4 h-4 md:w-5 md:h-5" />
            </motion.button>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
