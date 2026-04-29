# Deploying Arbiter on AWS EC2

This guide assumes Ubuntu 22.04 LTS on a small EC2 instance and a **PostgreSQL** database reachable from that instance (**Amazon RDS** or Postgres on another host).

## 1. RDS (or Postgres)

1. Create an RDS PostgreSQL instance (same region as EC2 simplifies networking).
2. Security group for RDS: **inbound PostgreSQL (5432)** from the EC2 instance security group only.
3. Note the endpoint, database name, user, password. Build **`DATABASE_URL`**:

   `postgresql://USER:PASSWORD@your-rds.region.rds.amazonaws.com:5432/DATABASE`

4. Arbiter creates `agent_runs` and `node_logs` tables automatically on API startup—no manual migration file is required.

## 2. EC2 instance

1. Launch an instance (e.g. **t3.micro**/free tier eligible); attach a security group with:
   - **SSH (22)** from your IP  
   - **HTTP (80)** / **HTTPS (443)** from the internet (if you serve the UI or reverse-proxy the API).
2. Allocate an **Elastic IP** if you want a stable public address.

## 3. System packages

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx git
```

Install **Docker** if you run the tester node on this host ([Docker CE install for Ubuntu](https://docs.docker.com/engine/install/ubuntu/)).

## 4. Application layout

Suggested paths:

```
/opt/arbiter/          # git clone repository here
/opt/arbiter/backend/.env
```

Clone the repo, create a venv, install dependencies:

```bash
sudo mkdir -p /opt/arbiter
sudo chown $USER:$USER /opt/arbiter
cd /opt/arbiter
git clone <YOUR_REPO_URL> .
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Configure **`backend/.env`** (minimal):

```env
GOOGLE_API_KEY=...
DATABASE_URL=postgresql://USER:PASSWORD@RDS_HOST:5432/DBNAME
GITHUB_TOKEN=...                    # optional, for forks / private APIs
CORS_ORIGINS=https://your-frontend-domain.com
PORT=8000
HOST=0.0.0.0
```

## 5. systemd service (backend)

`/etc/systemd/system/arbiter-api.service`:

```ini
[Unit]
Description=Arbiter FastAPI
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/arbiter
Environment="PATH=/opt/arbiter/backend/venv/bin"
ExecStart=/opt/arbiter/backend/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now arbiter-api
sudo systemctl status arbiter-api
```

## 6. Frontend (options)

**A. Static build + nginx**

On a build machine (or CI):

```bash
cd frontend
echo 'VITE_API_URL=https://api.your-domain.com' > .env
npm install && npm run build
```

Copy `frontend/dist` to `/var/www/arbiter` on the server. Example nginx site (single host serving SPA and proxying `/api/` to uvicorn—you may prefer two subdomains instead):

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/arbiter;
    try_files $uri $uri/ /index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

If your FastAPI routes stay at **`/`** (`/health`, `/start-healing`), either mount them under **`/api`** in FastAPI or run the UI on another origin and set **`VITE_API_URL`** to the full backend URL (recommended: `https://api.your-domain.com`). Add every UI origin to **`CORS_ORIGINS`**.

**B. Separate hosting (e.g. Vercel)**

Build with `VITE_API_URL` pointing to your EC2 public URL or API subdomain. Add that origin to **`CORS_ORIGINS`** on the backend.

## 7. TLS

Use **Let’s Encrypt** (certbot) with nginx, or terminate TLS on an **Application Load Balancer** in front of EC2.

## 8. Health check

`GET /health` should return `{"status":"ok"}`.

## 9. SSH key security

Keep private `.pem` keys **off** the repository; prefer IAM roles or AWS Secrets Manager for production secrets.
