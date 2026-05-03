# Arbiter: CI/CD Healing Agent

## 📖 What is Arbiter?

Arbiter is an intelligent, autonomous CI/CD (Continuous Integration / Continuous Deployment) healing agent. Modern software development pipelines often fail due to flaky tests, environment misconfigurations, or unexpected code regressions. When pipelines break, developers lose valuable time parsing through dense terminal logs to find the root cause.

**Arbiter solves this by:**
1. **Monitoring:** Actively watching CI/CD pipeline runs.
2. **Analyzing:** Parsing complex node logs and error outputs when a failure occurs.
3. **Healing:** Utilizing AI to identify the root cause of the failure and, where possible, automatically suggesting or implementing fixes to "heal" the broken pipeline.

## 🏗️ Architecture

The Arbiter project is built on a modern, decoupled architecture:

*   **Frontend:** A responsive, interactive dashboard built with **React** and **Vite**. It allows developers to view pipeline statuses, review agent healing runs, and manage system configurations.
*   **Backend:** A robust **Python** backend that handles the core AI agent logic, interfaces with LLMs, processes logs, and manages the healing workflows.
*   **Database:** Powered by **Supabase** (PostgreSQL), providing secure storage for user profiles, agent run histories, and detailed node logs, complete with Row-Level Security (RLS).

---

## 🚀 Installation & Setup Guide

Follow these steps to get Arbiter running on your local machine.

### Prerequisites
Before you begin, ensure you have the following installed:
*   **Node.js** (v18 or higher) & **npm**
*   **Python** (v3.10 or higher)
*   A **Supabase** account (or local Supabase CLI setup)

### 1. Clone the Repository
```bash
git clone https://github.com/aryan-dani/Arbiter.git
cd Arbiter
```

### 2. Database (Supabase) Setup
1. Create a new Supabase project.
2. Run the provided SQL initialization scripts (found in your database/schema folders) in your Supabase SQL Editor to create the necessary tables (`profiles`, `agent_runs`, `node_logs`).
3. Obtain your **Project URL** and **Anon Key** from the Supabase dashboard.

### 3. Backend Setup (Python)
The backend requires setting up a Python virtual environment and installing dependencies.

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Environment Variables
# Copy the example environment file and fill in your keys
cp .env.example .env.local
```
*Note: Make sure to update `.env.local` with your Supabase credentials, LLM API keys (e.g., OpenAI/OpenRouter), and any other required secrets.*

### 4. Frontend Setup (React/Vite)
The frontend requires installing Node dependencies and setting up environment variables.

```bash
# Open a new terminal and navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Environment Variables
# Ensure your .env.local file has the required Supabase keys:
# VITE_SUPABASE_URL=your_supabase_url
# VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# Start the development server
npm run dev
```

### 5. Running the Application
Once both servers are running:
1. Access the frontend dashboard at `http://localhost:5173` (or the port Vite provides).
2. The Python backend will be running on its specified local port (e.g., `http://localhost:8000`), ready to receive webhooks or API requests from the frontend.

---

## 🛠️ Development & Quality Assurance

*   **Frontend Linting:** Run `npm run lint` or `npm run format` in the `/frontend` directory to ensure code quality using ESLint and Prettier.
*   **Backend Linting:** Run `ruff check .` and `ruff format .` in the `/backend` directory to enforce Python standards.
