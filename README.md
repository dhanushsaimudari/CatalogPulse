# SORTOLOG IQ

> **Tagline:** *From messy data to commerce-ready intelligence.*  
> **Product Category:** Open-World Industrial Product Intelligence & Enrichment Engine  
> **Status:** Production-Ready (Stateless Session Architecture)  
> **Deployment Targets:** Backend on **Render** | Frontend on **Vercel**

---

## 1. Executive Summary

**SORTOLOG IQ** is an open-world industrial product intelligence engine designed for messy, heterogeneous manufacturer and distributor datasets. Raw distributor feeds are cryptic, abbreviated, inconsistently branded, and lack standard technical attributes.

SORTOLOG IQ transforms uncurated industrial data (CSV, XLSX, PDF, Images) into structured, validated, evidence-backed product intelligence. It operates **open-world**—meaning it never enforces a closed manufacturer allowlist or rigid category boundaries, discovers attributes dynamically from physical evidence, and delivers both:
1. **The Official 252-Column Unilog Delivery CSV** (delivery projection schema)
2. **The Clean Dynamic Intelligence CSV** (complete, normalized product record with all discovered attributes)

---

## 2. Core Operational Flow

```text
Raw Customer Feeds (CSV / XLSX / PDF / Images)
                    ↓
          Evidence Preservation
                    ↓
     Manufacturer & Brand Resolution (Open-World)
                    ↓
          Product Understanding
                    ↓
           Dynamic Taxonomy (4-Tier)
                    ↓
      Dynamic Attribute Discovery & Units
                    ↓
       Deterministic Validation & Auto-Fix
                    ↓
     Human-in-the-Loop Bulk Review Queue
                    ↓
           Benchmark Evaluation
                    ↓
        Dual Delivery Projections:
  ├── Official 252-Column Unilog Delivery CSV
  └── Clean Dynamic Intelligence CSV
```

### Core Philosophy:
> **AI proposes. Rules validate. Evidence supports. Humans decide.**

* **Semantic Intelligence:** IBM watsonx.ai (`meta-llama/llama-3-3-70b-instruct`) as primary LLM, Google Gemini (`gemini-1.5-flash`) as secondary fallback.
* **Deterministic Rules:** Open-world reference normalization, UOM space enforcement, character channel limits, and trademark compliance rules.
* **Local Fallback:** Full offline deterministic heuristic engine runs automatically if cloud AI services are unavailable.

---

## 3. Production Cloud Deployment Guide

### A. Backend Deployment on Render

The backend is a FastAPI application that runs via `uvicorn` and binds to `0.0.0.0:$PORT`.

#### Option 1: Blueprint Deployment (Recommended)
This repository includes a [`render.yaml`](render.yaml) blueprint.
1. Log in to [Render](https://render.com) and click **New** → **Blueprint**.
2. Connect the `Sortlog-IQ` GitHub repository.
3. Render will automatically configure the web service using `render.yaml`.

#### Option 2: Manual Web Service Setup
1. On Render, click **New** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   - **Name:** `sortlog-iq-backend`
   - **Region:** Any (e.g. *Oregon (US West)* or *Frankfurt*)
   - **Branch:** `main`
   - **Root Directory:** *(leave blank — runs from repository root)*
   - **Runtime:** `Python 3` (Python `3.11.9` is automatically pinned via `.python-version`)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python run_backend.py`
   - **Health Check Path:** `/health`
4. Under **Environment Variables**, add:
   | Key | Value / Description | Required? |
   |---|---|---|
   | `APP_ENV` | `production` | Yes |
   | `HOST` | `0.0.0.0` | Yes |
   | `FRONTEND_URL` | `https://<your-vercel-app>.vercel.app` | Yes (for CORS) |
   | `WATSONX_API_KEY` | Your IBM Cloud API key | Optional (AI Primary) |
   | `WATSONX_PROJECT_ID` | Your watsonx project ID | Optional |
   | `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | Optional |
   | `WATSONX_MODEL_ID` | `meta-llama/llama-3-3-70b-instruct` | Optional |
   | `GEMINI_API_KEY` | Your Google Gemini API key | Optional (AI Secondary) |
   | `GEMINI_MODEL` | `gemini-1.5-flash` | Optional |
5. Click **Deploy Web Service**.
6. Verify deployment: visit `https://<your-render-service>.onrender.com/health`. You should receive:
   ```json
   {"status": "OK", "service": "SORTOLOG IQ API", "version": "1.0.0"}
   ```

> [!TIP]
> **Render Free Tier Warmup:** Render free-tier instances spin down on idle. Before a live demo, send a quick `GET` request to `https://<your-render-service>.onrender.com/health` to pre-warm the service.

---

### B. Frontend Deployment on Vercel

The frontend is a Next.js 14 App Router application located in the `frontend/` directory.

#### Step-by-Step Vercel Deployment:
1. Log in to [Vercel](https://vercel.com) and click **Add New** → **Project**.
2. Import your GitHub repository (`Sortlog-IQ`).
3. In the project setup screen:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click **Edit** and select `frontend`.
4. In the **Environment Variables** section, configure:
   | Key | Value | Purpose |
   |---|---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<your-render-service>.onrender.com/api/v1` | Direct client-side calls to backend |
   | `BACKEND_URL` | `https://<your-render-service>.onrender.com` | Serverless Next.js rewrite proxy target |
5. Click **Deploy**.
6. Vercel will build and deploy the Next.js frontend with automated global edge caching.

---

## 4. Local Development Setup

### Prerequisites
* Python 3.10+ (Python 3.11 recommended)
* Node.js 18+ & npm

### 1. Backend Setup
From the repository root:

```bash
# 1. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure local environment variables
cp .env.example .env
# Edit .env to add AI keys if desired

# 4. Start the backend server
python run_backend.py
```
* Backend API runs on: `http://localhost:8000`
* Interactive OpenAPI Docs: `http://localhost:8000/docs`
* Health Endpoint: `http://localhost:8000/health`

### 2. Frontend Setup
In a new terminal, you can start the frontend either from the root or inside `frontend/`:

```bash
# Option A: Directly from repository root
npm run dev

# Option B: From frontend directory
cd frontend
npm install
npm run dev
```
* Frontend Web App runs on: `http://localhost:3000`

---

## 5. Repository Structure

```text
Sortlog-IQ/
├── package.json                  # Root monorepo script runner
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git tracking rules (protects .env, node_modules, build cache)
├── .python-version               # Pinned Python version (3.11.9) for Render
├── Procfile                      # Procfile for web process deployment
├── render.yaml                   # Render Blueprint Infrastructure-as-Code
├── requirements.txt              # Pinned backend dependencies
├── run_backend.py                # Universal backend server runner (local & cloud)
├── vercel.json                   # Root Vercel monorepo configuration
├── input_columns.json            # Official 6-column raw input specification
├── output_columns.json           # Official 252-column Unilog delivery specification
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint, CORS configuration & lifespan
│   │   ├── api/
│   │   │   ├── router.py         # Unified API router
│   │   │   └── routes/           # REST endpoints (health, sessions, products, reviews, export, etc.)
│   │   ├── ai/                   # WatsonX & Gemini providers, prompts, parsers, router
│   │   ├── core/                 # App settings, logging, exceptions
│   │   ├── evaluation/           # Benchmark evaluator (6 domains, 6 error categories)
│   │   ├── evidence/             # Bounding box coordinates & document resolver
│   │   ├── schemas/              # Pydantic schemas (Product, Validation, Review, Evaluation)
│   │   ├── services/             # Ingestion, Processing, Quality, Review, Export services
│   │   ├── session/              # Thread-safe in-memory session manager & models
│   │   ├── storage/              # Object storage & local disk adapters
│   │   └── validation/           # Validation engine, rules, UOM/LOV checkers, auto-fix
│   └── tests/                    # 86 Unit, Regression & Scalability tests
└── frontend/
    ├── app/                      # Next.js App Router pages (Dashboard, Upload, Products, Review, Evaluation)
    ├── components/               # React UI, Enrichment, Review, and Evaluation components
    ├── lib/                      # API client connectors, session helpers, utils
    ├── types/                    # TypeScript interfaces matching backend Pydantic schemas
    ├── next.config.mjs           # Next.js config with API proxy rewrites
    └── vercel.json               # Frontend Vercel configuration
```

---

## 6. Testing & Quality Assurance

The codebase includes an extensive automated test suite covering open-world resolution, concurrent ingestion, attribute extraction, review auto-fix safety, and 252-column export compliance.

### Run Backend Tests
```bash
python -m pytest backend/tests -v
```
*(86 / 86 tests passing)*

### Key Regression Tests:
* `test_duplicate_mpn_concurrency.py` — Verifies thread-safe collision-free ID allocation for duplicate MPNs across 10 worker threads, ensuring 1,000 input rows yield exactly 1,000 processed products.
* `test_review_attribute_safety.py` — Protects against attribute corruption; ensures missing attributes return safe `None` without modifying `attributes[0]`.
* `test_export_252_columns.py` — Validates exact 252-column header names, order, and triplet alignment against `output_columns.json`.
* `test_open_world_intelligence.py` — Validates preservation of unknown manufacturers and brands without forced allowlists.

### Run Frontend Structure & Type Verification
```bash
python frontend/scripts/test_frontend.py
```
*(49 / 49 frontend components verified)*

---

## 7. Dual Export Formats

SORTOLOG IQ produces two distinct export artifacts:

1. **Official Unilog Delivery CSV (`POST /api/v1/sessions/{id}/export`)**
   - Strictly complies with the 252-column Unilog specification.
   - Outputs `ATTRIBUTE_LABEL_1..50`, `ATTRIBUTE_VALUE_1..50`, `ATTRIBUTE_UOM_1..50`.
   - Includes 6 copywriting channels, 10 feature bullets, and standardized taxonomy paths.
2. **Clean Dynamic Intelligence CSV (`POST /api/v1/sessions/{id}/export-clean`)**
   - Dynamic schema that unions all discovered technical attributes across products.
   - Clean column headers (e.g. `PRESSURE RATING`, `MATERIAL`, `DIAMETER`) without artificial 50-attribute limits.
   - Includes full normalization metadata, quality scores, and validation pass rates.

---

## 8. License

Developed for the **UniHack 2026 Hackathon**. Proprietary & Confidential.
