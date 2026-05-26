# 🛠️ Local Setup Guide — Windows (No Docker)

## Prerequisites

| Software | Version | Download |
|----------|---------|----------|
| Python | 3.11+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| PostgreSQL | 16 | https://www.postgresql.org/download/windows/ |
| Neo4j Community | 5.x | https://neo4j.com/deployment-center/ |
| OpenSSL | (for JWT keys) | Included with Git for Windows |

---

## Step 1: Clone / Copy Files

```
e:\Hospital dashboard Project\
├── frontend\
├── backend\
├── scripts\
└── docs\
```

---

## Step 2: Configure Backend Environment

```bat
cd "e:\Hospital dashboard Project\backend"
copy .env.template .env
```

Edit `.env` and set:

```env
# Required
ENCRYPTION_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
ANTHROPIC_API_KEY=sk-ant-...   # Get from console.anthropic.com

# Database (choose one)
USE_SQLITE=true                 # Easy start — no PostgreSQL needed
# OR for full PostgreSQL:
USE_SQLITE=false
DATABASE_URL=postgresql://hospital_user:hospital_pass@localhost:5432/hospital_db
```

---

## Step 3: Install Python Dependencies

```bat
cd "e:\Hospital dashboard Project\backend"
pip install -r requirements.txt
```

> **Note:** Prophet may require `pystan` compiler. If it fails:
> ```bat
> pip install prophet --no-deps
> pip install holidays convertdate lunarcalendar
> ```

---

## Step 4: Generate JWT RSA Keys

```bat
cd "e:\Hospital dashboard Project\backend"
mkdir keys
openssl genrsa -out keys\private.pem 2048
openssl rsa -in keys\private.pem -pubout -out keys\public.pem
```

> If `openssl` not found, install Git for Windows (includes OpenSSL).  
> Or set `USE_SQLITE=true` to use HS256 fallback in development.

---

## Step 5: PostgreSQL Setup (Skip if USE_SQLITE=true)

```sql
-- Run in psql or pgAdmin:
CREATE USER hospital_user WITH PASSWORD 'hospital_pass';
CREATE DATABASE hospital_db OWNER hospital_user;
GRANT ALL PRIVILEGES ON DATABASE hospital_db TO hospital_user;
```

---

## Step 6: Neo4j Setup (Optional — graph features)

```bat
REM Download Neo4j Community 5.x ZIP, extract to C:\neo4j\
C:\neo4j\bin\neo4j console
REM Browser: http://localhost:7474  (change default password on first login)
REM Update NEO4J_PASSWORD in backend\.env
```

---

## Step 7: Initialize Database & Seed Data

```bat
scripts\init_db.bat
```

This will:
1. Install all Python deps
2. Generate RSA keys (if not present)
3. Create all database tables
4. Seed 2000 patient records (encrypted)
5. Build ChromaDB RAG index
6. Create CEO user (username: `ceo`, password: `Aarogya@2024`)

---

## Step 8: Install Frontend Dependencies

```bat
cd "e:\Hospital dashboard Project\frontend"
npm install
copy .env.template .env.local
```

Edit `.env.local`:
```env
VITE_API_URL=http://localhost:8000
VITE_USE_BACKEND=true          # Set to true when backend is running
```

---

## Step 9: Start Everything

**Option A — One-click:**
```bat
scripts\start_all.bat
```

**Option B — Manual (separate windows):**
```bat
REM Window 1: Backend
cd backend
python -m uvicorn main:app --reload --port 8000

REM Window 2: Frontend
cd frontend
npm run dev
```

---

## Access Points

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Dashboard (Vite dev server) |
| http://localhost:8000 | FastAPI backend |
| http://localhost:8000/docs | Swagger UI (dev only) |
| http://localhost:8000/api/health | Health check |
| http://localhost:7474 | Neo4j browser (if running) |

---

## Default Credentials

| User | Username | Password | Role |
|------|----------|----------|------|
| CEO | `ceo` | `Aarogya@2024` | Full access |

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'cryptography'"
```bat
pip install cryptography==42.0.7
```

### "Cannot connect to PostgreSQL"
→ Set `USE_SQLITE=true` in `.env` for quick start.

### "Neo4j unavailable" warning
→ Normal if Neo4j is not installed. All non-graph features work without it.

### "ENCRYPTION_KEY must be exactly 64 hex characters"
→ Generate: `python -c "import secrets; print(secrets.token_hex(32))"`

### "RSA key not found" warning
→ Either generate keys (Step 4) or system falls back to HS256 for development.

### Vite port 5173 in use
→ Vite will automatically use the next available port (5174, etc.)

### Frontend shows "Offline" badge
→ Set `VITE_USE_BACKEND=true` and ensure backend is running at port 8000.

---

## Production Checklist

- [ ] Set `APP_ENV=production` in `.env`
- [ ] Use full PostgreSQL (not SQLite)
- [ ] Generate strong `ENCRYPTION_KEY` and store securely
- [ ] Generate RSA keys for JWT
- [ ] Set `ALLOWED_ORIGINS` to production domain only
- [ ] Enable HTTPS (nginx reverse proxy or Caddy)
- [ ] Set up PostgreSQL SSL
- [ ] Configure automatic backups (pg_dump cron)
- [ ] Set up log rotation for uvicorn logs
- [ ] Change default CEO password
