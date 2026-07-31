# 🤖 Data Analyst Copilot

> An AI-powered assistant that can analyze any CSV/Excel dataset, answer questions in natural language, generate visualizations, perform statistical analysis, create reports, and explain insights.

![Data Analyst Copilot](https://img.shields.io/badge/AI-OpenRouter-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green?style=flat-square)
![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📁 **Dataset Upload** | CSV, Excel, JSON, Parquet support |
| 🔍 **Auto Profiling** | Missing values, dtypes, stats, distributions |
| 📊 **Auto-EDA** | Histograms, heatmaps, boxplots, scatter plots |
| 💬 **AI Chat** | Natural language questions → instant answers |
| 🐼 **NL → Pandas** | Convert questions to Pandas code, execute safely |
| 🦆 **SQL Agent** | DuckDB SQL + NL-to-SQL conversion |
| 📈 **Statistics** | Correlation, ANOVA, regression, outlier detection |
| 🧹 **Data Cleaning** | Remove duplicates, fill missing, normalize, encode |
| 🤖 **ML Assistant** | AutoML with scikit-learn |
| 📄 **Export** | CSV, Excel, JSON, PDF reports |
| 🔒 **Safe Executor** | Sandboxed Python execution with allowlist |

---

## 🏗️ Architecture

```
User
  │
Next.js Frontend (Port 3000)
  │
  ├── Upload Dataset
  ├── Chat Interface (AI Chat)
  ├── Profile View (Dataset Stats)
  ├── EDA Charts (Auto-Generated)
  ├── SQL Agent (DuckDB)
  ├── Data Cleaning
  └── Export (CSV/Excel/PDF/JSON)
  │
FastAPI Backend (Port 8000)
  │
  ├── Data Service (Pandas session store)
  ├── AI Service (OpenRouter)
  ├── Safe Executor (sandboxed exec)
  ├── Chart Service (Matplotlib/Seaborn)
  ├── Memory Service (SQLite)
  └── LangGraph Agent (Intent → Code → Execute → Explain)
```

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Start the API server
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/api/docs

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

App available at: http://localhost:3000

---

## 🔑 Environment Variables

### Backend (`backend/.env`)
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
DATABASE_URL=sqlite:///./data_copilot.db
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
MAX_FILE_SIZE_MB=100
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Get your OpenRouter API key at: https://openrouter.ai/keys

---

## 📖 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload/` | POST | Upload CSV/Excel/JSON |
| `/api/upload/datasets` | GET | List all datasets |
| `/api/profile/{id}` | GET | Full dataset profile |
| `/api/profile/{id}/preview` | GET | Paginated data preview |
| `/api/eda/{id}` | GET | Auto-EDA charts |
| `/api/chat/` | POST | AI chat message |
| `/api/statistics/analyze` | POST | Statistical analysis |
| `/api/sql/query` | POST | Run DuckDB SQL |
| `/api/sql/nl-to-sql` | POST | NL → SQL conversion |
| `/api/cleaning/` | POST | Data cleaning operation |
| `/api/suggestions/{id}` | GET | AI-generated questions |
| `/api/export/` | POST | Export dataset |

---

## 🧠 AI Workflow (LangGraph)

```
User Question
      │
      ▼
Intent Detection (OpenRouter)
      │
      ├── dataset_info → Direct Response
      ├── statistics ──────────────────┐
      ├── visualization ───────────────┤
      ├── filtering ───────────────────┤
      └── aggregation ─────────────────┤
                                       ▼
                              Code Generation (NL → Pandas)
                                       │
                                       ▼
                              Safe Execution (Sandbox)
                                       │
                                       ▼
                              AI Explanation (OpenRouter)
                                       │
                                       ▼
                              Response + Chart/Table
```

---

## 🗂️ Project Structure

```
data-analyst-copilot/
├── backend/
│   ├── main.py                    # FastAPI entrypoint
│   ├── requirements.txt
│   ├── .env
│   ├── agent/
│   │   └── graph.py               # LangGraph workflow
│   ├── routes/
│   │   ├── upload.py
│   │   ├── profile.py
│   │   ├── eda.py
│   │   ├── chat.py
│   │   ├── statistics.py
│   │   ├── cleaning.py
│   │   ├── sql_agent.py
│   │   ├── suggestions.py
│   │   └── export.py
│   ├── services/
│   │   ├── ai_service.py          # OpenRouter client
│   │   ├── data_service.py        # Pandas session manager
│   │   ├── executor.py            # Safe code sandbox
│   │   ├── chart_service.py       # Chart generation
│   │   └── memory_service.py      # Conversation memory
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── db_models.py           # SQLAlchemy models
│   ├── database/
│   │   └── db.py                  # SQLite setup
│   └── prompts/
│       └── system_prompts.py      # All LLM prompts
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx           # Landing page
│       │   ├── layout.tsx
│       │   ├── globals.css        # Design system
│       │   └── dashboard/
│       │       └── page.tsx       # Main dashboard
│       ├── components/
│       │   ├── chat/              # AI chat interface
│       │   ├── upload/            # File upload
│       │   ├── profile/           # Dataset profile
│       │   ├── charts/            # EDA charts view
│       │   ├── sql/               # SQL agent view
│       │   ├── cleaning/          # Data cleaning
│       │   ├── export/            # Export options
│       │   └── settings/          # Settings modal
│       └── lib/
│           ├── api.ts             # API client
│           ├── store.ts           # Zustand state
│           └── utils.ts           # Utilities
└── README.md
```

---

## 🛡️ Security

The Python executor uses a strict allowlist:

**Allowed:** `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `sklearn`

**Blocked:** `os`, `sys`, `subprocess`, `socket`, `open`, `__import__`, `eval`, `exec`

---

## 🗺️ Roadmap

- [x] Phase 1: Upload + Profile
- [x] Phase 2: Auto-EDA
- [x] Phase 3: AI Chat + Code Execution
- [x] Phase 4: Statistics + SQL Agent
- [x] Phase 5: Data Cleaning + Export
- [ ] Phase 6: ML Assistant (AutoML)
- [ ] Phase 7: PDF Report Generator
- [ ] Phase 8: Voice Assistant
- [ ] Phase 9: Authentication + Teams
- [ ] Phase 10: Docker + Cloud Deployment

---

## 📝 License

MIT — free for personal and commercial use.
