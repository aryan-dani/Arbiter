# RIFT 2026: Autonomous CI/CD Healing Agent

**Track:** AI/ML - Agentic Systems

---

## 🏗️ Architecture

Our agent follows a **Multi-Agent Architecture** powered by **Gemini 2.5 Flash** and executed within **Docker** sandboxes.

![Architecture Diagram](docs/Architecture_diagram_the_arbiter.png)
![Agent Workflow Diagram](docs/Agent_workflow_the_arbiter.png)


### Core Components
1. **Discovery Node**: Clones repo, detects stack (Python/Node), maps file structure.
2. **Tester Node**: Spins up ephemeral Docker containers to run `pytest` safely.
3. **Debugger Node**: Analyzes logs using **Anchor Resolution** (Traceback vs Function Maps) to find the Source of Truth.
4. **Fixer Node**: Uses **Agent Memory** (Supabase) and strict Context Locking to generate one-shot fixes.
5. **Git Node**: Commits fixes with `[AI-AGENT]` prefix and strictly formatted branch names.

---

## 🛠️ Tech Stack

- **Frontend**: React 18, Vite, TailwindCSS (Dark Mode Premium UI)
- **Backend**: FastAPI, Python 3.11, LangGraph
- **AI Model**: Google Gemini 2.5 Flash
- **Database**: Supabase (Real-time logs & History)
- **Infrastructure**: Docker (Sandboxing), Render/Vercel (Deployment)

---

## 🐛 Supported Bug Types

The agent autonomously detects and fixes:
- ✅ **LOGIC**: Incorrect boolean logic, math errors, off-by-one errors.
- ✅ **SYNTAX**: Missing colons, indentations, invalid syntax.
- ✅ **TYPE_ERROR**: String vs Integer mismatches, NoneType handling.
- ✅ **IMPORT**: Missing modules or incorrect function imports.
- ✅ **LINTING**: Flake8 compliance (unused imports, whitespace).

---

## ⚙️ Installation & Setup

### Prerequisites
- Docker Desktop (Running)
- Python 3.11+
- Node.js 18+
- Gemini API Key

### 1. Clone & Configure
```bash
git clone https://github.com/aryan-dani/RIFT_2026_Let-s_See.git
cd RIFT_2026_Let-s_See

# Backend Setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # Add GOOGLE_API_KEY
```

### 2. Frontend Setup
```bash
cd ../frontend
npm install
cp .env.example .env  # Add VITE_API_URL
npm run dev
```

### 3. Run Agent
1. Start Backend: `uvicorn main:app --reload`
2. Open Dashboard: `http://localhost:5173`
3. Enter Target Repo URL and Click **Run Agent**.

---

## ⚠️ Known Limitations
- Currently optimized for Python (`pytest`) repositories.
- Docker requires 4GB+ RAM for stable execution.
- Rate limits apply based on Gemini API tier.

---

## 👥 Team Members

- **[Leader Name]**: Aryan Dani [Full Stack & AI Logic]
- **[Member Name]**: Himali Dandavate [Frontend & Design]
