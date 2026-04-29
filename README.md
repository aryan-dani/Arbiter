# Arbiter — Autonomous CI/CD healing agent

Multi-agent workflow (discovery → test → debug → fix → git → score) orchestrated with **LangGraph**, powered by **Google Gemini**.

![Architecture Diagram](docs/Architecture_diagram_the_arbiter.png)
![Agent workflow](docs/Agent_workflow_the_arbiter.png)

## Architecture overview

| Component        | Responsibility |
|-----------------|----------------|
| Discovery       | Clone/fork repo, detect stack and tests |
| Tester          | Run tests inside Docker sandboxes |
| Debugger        | Analyze failures with Gemini |
| Fixer           | Generate patches; optionally uses PostgreSQL-backed run history (“agent memory”) |
| Git             | Branch, commit, open PR |
| Scoring         | Final score and timeline |

## Tech stack

- **Frontend**: React (Vite), TailwindCSS
- **Backend**: FastAPI, Python 3.11+, LangGraph
- **AI**: Google Gemini
- **Data**: PostgreSQL via `DATABASE_URL` (runs, node logs); optional — logging is disabled without it
- **Sandbox**: Docker Desktop (for tester node)

## Local setup

**Prerequisites:** Docker Desktop running, Python 3.11+, Node 18+, a Gemini API key.

### Backend

From the **repository root**:

```bash
python -m venv backend/venv
# Windows: backend\venv\Scripts\activate   |  Linux/macOS: source backend/venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env — set GOOGLE_API_KEY and optionally DATABASE_URL, GITHUB_TOKEN
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Set VITE_API_URL to your API base, e.g. http://localhost:8000
npm run dev
```

### PostgreSQL (`DATABASE_URL`)

Use any managed Postgres (e.g. **Amazon RDS**) or local Postgres. On first startup the API creates tables `agent_runs` and `node_logs`.

Example URI:

`postgresql://USER:PASSWORD@HOST:5432/DATABASE`

### CORS (production)

Set `CORS_ORIGINS` to a comma-separated list of allowed browser origins (e.g. `https://your-domain.com`).

## Deploy on AWS EC2 (overview)

See **[docs/DEPLOY_EC2.md](docs/DEPLOY_EC2.md)** for systemd, RDS, nginx, TLS, and environment variables.

## Limitations

- Optimized primarily for Python (`pytest`) repositories; Node support is experimental.
- Docker needs sufficient RAM (4GB+ recommended).
- Gemini API quota applies per your GCP account.
