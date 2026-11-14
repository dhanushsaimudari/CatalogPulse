# CatalogPulse AI

> **Tagline:** *From raw industrial data to verified, commerce-ready catalogs.*  
> **Subtitle:** *Industrial Product Intelligence Platform*  
> **Product Category:** AI-Powered Industrial Product Catalog Intelligence & Enrichment Platform  
> **Competition Track:** Startup Buildathon 2026  
> **Status:** Production-Ready (Thread-Safe Stateless Session Architecture)  
> **Deployment Targets:** Backend on **Render** | Frontend on **Vercel**

---

## 1. Executive Summary

Industrial manufacturers, suppliers, and distributors manage millions of SKUs across legacy enterprise systems, fragmented spreadsheets, technical PDF cut-sheets, and unstructured distributor feeds. Transforming raw product listings into standardized, high-conversion, marketplace-ready catalogs currently demands hundreds of manual engineering hours.

**CatalogPulse AI** automates industrial catalog intelligence while preserving auditability, physical evidence, and human oversight. 

### Core Product Promise
> **Upload messy industrial product data. Extract technical attributes. Validate specifications. Review evidence. Export structured catalogs.**

### Target Customers
- **Small & Medium Industrial Manufacturers:** Digitize technical spec sheets into structured digital catalogs.
- **Industrial Product Distributors:** Normalize disparate vendor feeds with inconsistent UOMs, taxonomy, and MPNs.
- **Electrical & Mechanical Equipment Suppliers:** Extract multi-tier electrical (voltage, amperage) and mechanical specs with physical verification.
- **Automotive & Aerospace Parts Suppliers:** Standardize critical dimensions, materials, and tolerance ratings.
- **B2B Marketplace Onboarding Agencies:** Accelerate time-to-market for vendor catalog ingestion.

---

## 2. Core Architecture & Workflow

```text
        Messy Industrial Feeds (CSV / XLSX / PDF / Images)
                              │
                              ▼
                   [ 1. Ingestion Engine ]
              File parsing, stream hashing, session isolation
                              │
                              ▼
                [ 2. AI Intelligence Engine ]
         Google Gemini (Primary) ──► IBM watsonx.ai (Secondary)
                              │
                              └──► Local Deterministic Heuristic
                              │
                              ▼
              [ 3. Open-World Dynamic Discovery ]
       Manufacturer, brand, 4-tier taxonomy, dynamic attributes
                              │
                              ▼
              [ 4. Deterministic Rule Validator ]
       UOM spacing, character limits, duplicate MPNs, auto-fixes
                              │
                              ▼
             [ 5. Side-by-Side Evidence Center ]
       Physical bounding-box viewer (PDF & image source audit)
                              │
                              ▼
            [ 6. Human-in-the-Loop Review Queue ]
         Single & bulk approval, override edits, audit trails
                              │
                              ▼
                 [ 7. Dual Export Center ]
    ┌─────────────────────────┴─────────────────────────┐
    ▼                                                   ▼
[ Primary Clean Dynamic CSV ]             [ Legacy 252-Column Unilog CSV ]
Universal schema union of all              Strict backward-compatible 
discovered technical specs                 enterprise distribution schema
```

### Operational Philosophy
> **AI proposes. Rules validate. Evidence supports. Humans decide.**

* **No Hallucinated Attributes:** Extraction preserves source references with page numbers and coordinate bounding boxes.
* **Open-World Reality:** No restrictive manufacturer allowlists or rigid taxonomies. The engine dynamically learns and isolates real-world industrial categories.
* **Deterministic Guardrails:** Physical unit-of-measurement (UOM) standards, copy channel constraints, and duplicate MPN detection run through mathematical rules, not probabilistic guesses.

---

## 3. Google AI Integration & Prompt Engineering

CatalogPulse AI leverages Google Cloud and Gemini AI technologies as its primary intelligence engine:

### A. Primary AI Provider: Google Gemini
- **Model Support:** Native integration with `gemini-2.5-flash` (default) and `gemini-1.5-flash` via the official `google-genai` / `google-generativeai` SDK.
- **Configuration:** Set via `GEMINI_API_KEY` and `GEMINI_MODEL` in `.env`.
- **Multimodal Understanding:** Capable of ingesting complex PDF engineering drawings, specification cut-sheets, and industrial product photos to extract precise physical dimensions, electrical ratings, and operational tolerances.
- **Structured Pydantic Extraction:** Prompts enforce strict JSON schemas matching backend Pydantic models (`ProductEnrichmentResponse`), preventing unstructured text drift.
- **Prompt Design:** Engineered with few-shot domain examples tailored for industrial abbreviations (e.g., `SS 316`, `120V/60Hz`, `NEMA 4X`, `Class 150#`, `IP67`).
- **Resilient Fallback Hierarchy:**
  1. **Google Gemini** *(Primary cloud provider when `GEMINI_API_KEY` is present)*
  2. **IBM watsonx.ai** *(Secondary fallback if configured)*
  3. **Deterministic Local Heuristic Engine** *(Offline rule-based classifier ensuring 100% operational continuity even without network or API keys)*

### B. Antigravity Agentic Acceleration
This platform transformation was designed, architected, and refactored using **Antigravity**, Google's agentic AI development environment:
- Rapid code transformation and continuous test verification across 87 unit and regression test suites.
- Strict isolation of business logic, avoiding hallucinated data, synthetic benchmark counts, or broken contracts.
- Automated creation of end-to-end industrial test fixtures and regression guardrails.

---

## 4. Key Differentiators

| Feature | Generic Catalog Tools | CatalogPulse AI |
|---|---|---|
| **Evidence Audit** | Black-box AI outputs | **Physical bounding-box audit** linking every attribute to source PDF/image |
| **Taxonomy Model** | Rigid closed allowlists | **Open-world discovery** adapting to novel manufacturers & categories |
| **Validation** | Pure LLM self-evaluation | **Deterministic rule engine** checking UOM syntax, limits & duplicates |
| **Human Review** | Clunky manual spreadsheets | **Side-by-side Review Center** with keyboard shortcuts & bulk fixes |
| **Export Options** | Fixed proprietary format | **Dual export:** Primary Clean Dynamic CSV + Legacy 252-Column Unilog CSV |
| **Offline Resilience** | Fails on API timeout | **Full offline deterministic engine** runs with zero API keys |

---

## 5. Production Cloud Deployment Guide

### A. Backend Deployment on Render

The backend is a high-performance FastAPI application configured to run via `uvicorn` binding to `0.0.0.0:$PORT`.

#### Option 1: Blueprint Deployment (Recommended)
This repository contains a ready-to-deploy [`render.yaml`](render.yaml) blueprint:
1. Log in to [Render](https://render.com) and click **New** → **Blueprint**.
2. Connect your `CatalogPulse-AI` repository.
3. Render automatically provisions the web service using `render.yaml`.

#### Option 2: Manual Web Service Setup
1. On Render, click **New** → **Web Service**.
2. Connect your repository.
3. Configure the service:
   - **Name:** `catalogpulse-ai-backend`
   - **Runtime:** `Python 3` (Python `3.11.9` is pinned in `.python-version`)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python run_backend.py`
   - **Health Check Path:** `/health`
4. Set Environment Variables:
   | Key | Value / Description | Required? |
   |---|---|---|
   | `APP_ENV` | `production` | Yes |
   | `HOST` | `0.0.0.0` | Yes |
   | `FRONTEND_URL` | `https://<your-vercel-app>.vercel.app` | Yes (for CORS) |
   | `PRIMARY_AI_PROVIDER` | `gemini` | Yes |
   | `GEMINI_API_KEY` | Your Google Gemini API Key | Recommended (Primary AI) |
   | `GEMINI_MODEL` | `gemini-2.5-flash` (or `gemini-1.5-flash`) | Optional |
   | `WATSONX_API_KEY` | Your IBM Cloud API key | Optional (Secondary Fallback) |
   | `WATSONX_PROJECT_ID` | Your watsonx project ID | Optional |
5. Click **Deploy Web Service**.
6. Verify deployment at `https://<your-service>.onrender.com/health`:
   ```json
   {
     "status": "OK",
     "service": "catalogpulse-ai-backend",
     "version": "1.0.0",
     "providers": {
       "primary": "Gemini",
       "secondary": "IBM watsonx.ai",
       "fallback": "DeterministicLocal"
     }
   }
   ```

---

### B. Frontend Deployment on Vercel

The frontend is a modern Next.js 14 App Router application located in `frontend/`.

#### Step-by-Step Vercel Deployment:
1. Log in to [Vercel](https://vercel.com) and select **Add New** → **Project**.
2. Import the `CatalogPulse-AI` repository.
3. Set the project configuration:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** `frontend`
4. Configure Environment Variables:
   | Key | Value | Purpose |
   |---|---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<your-render-service>.onrender.com/api/v1` | Direct browser API calls |
   | `BACKEND_URL` | `https://<your-render-service>.onrender.com` | Next.js serverless proxy rewrite |
5. Click **Deploy**. Vercel will build and distribute the production bundle globally.

---

## 6. Local Development Setup

### Prerequisites
- **Python:** 3.10, 3.11, or 3.12
- **Node.js:** 18+ and `npm`

### 1. Backend Setup
From the repository root:
```bash
# 1. Create and activate a Python virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure local environment variables
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY if desired

# 4. Start the backend server
python run_backend.py
```
- API Server: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/health`

### 2. Frontend Setup
From the repository root:
```bash
# Option A: From root script
npm run dev

# Option B: From frontend directory
cd frontend
npm install
npm run dev
```
- Web Application: `http://localhost:3000`

---

## 7. Automated Testing & Verification

The project includes an automated test suite enforcing regression safety, thread concurrency, export schemas, and UI integrity.

### Run Backend Test Suite
```bash
python -m pytest backend/tests -v
```
**Results:** `87 passed, 0 failed`

#### Key Architectural & Regression Tests:
- `test_ai_providers.py`: Validates Google Gemini as primary provider with fallback to watsonx and local heuristics.
- `test_duplicate_mpn_concurrency.py`: Verifies thread-safe collision-free ID allocation for duplicate MPNs across 10 concurrent worker threads (1,000 input rows yield exactly 1,000 processed products).
- `test_review_attribute_safety.py`: Guarantees that updating non-existent attributes returns safe `None` without corrupting product data.
- `test_export_252_columns.py`: Confirms exact 252-column ordering, names, and triplet structure against `output_columns.json`.
- `test_review_bulk_fix.py`: Enforces UI invariants, export header bindings, and bulk auto-fix operations.
- `test_sanity_dataset.py`: Executes end-to-end ingestion, validation, and dual exports against real industrial catalogs.

### Run Frontend Structure & Interface Verification
```bash
python frontend/scripts/test_frontend.py
```
**Results:** `49 / 49 frontend components and pages verified`

---

## 8. Guided Demonstration Walkthrough

A sample industrial dataset is provided at [`sample_data/catalogpulse_industrial_demo.csv`](sample_data/catalogpulse_industrial_demo.csv). It contains 10 realistic industrial SKUs across valves, cutting discs, LED lighting, grade 8 fasteners, industrial circuit breakers, flexible couplings, smart thermostats, and grinding wheels.

### Step-by-Step Demo Script:

1. **Upload Catalog:**
   - Navigate to `/upload` (New Catalog).
   - Drag and drop `sample_data/catalogpulse_industrial_demo.csv`.
   - The system ingests all 10 products, computing session hashes and initializing isolation.

2. **Inspect Product Intelligence:**
   - Navigate to `/products` (Product Intelligence).
   - View normalized manufacturers, brands, MPNs, dynamically discovered categories, and extracted specifications.
   - Filter by status (`Requires Review`, `Valid`, `Warning`).

3. **Audit Physical Evidence:**
   - Click on the industrial dishwasher SKU (`DW-COMM-200`) or click `/evidence`.
   - The side-by-side Evidence Center displays the source cut-sheet on the left with exact coordinate bounding boxes (`[ymin, xmin, ymax, xmax]`), and extracted attributes on the right.

4. **Human-in-the-Loop Review Center:**
   - Navigate to `/review` (Review Center).
   - Filter by products flagged for review.
   - Review auto-fix recommendations (e.g., standardizing `PSI` to `psi`, normalizing voltage formats).
   - Click **Apply Fix** or approve records using keyboard shortcuts (`A` to approve, `E` to edit, `R` to reject).

5. **Export Intelligence:**
   - Navigate to `/export` (Export Center).
   - Choose between:
     - **Primary Clean Dynamic Intelligence CSV:** Complete dynamic attribute schema for modern data lakes and PIM systems.
     - **Legacy 252-Column Unilog CSV:** Exact legacy standard for enterprise marketplace compliance.

---

## 9. Product Honesty & Operational Boundaries

To ensure absolute industrial reliability, CatalogPulse AI operates with transparent engineering boundaries:

- **Evidence Transparency:** When evidence is extracted from PDFs or spec sheets, exact page numbers and bounding boxes are presented. If an attribute was inferred from textual descriptions where bounding boxes do not exist, it is explicitly labeled as *Document Evidence Unavailable*—never fabricated.
- **HSN/GST Classification:** HSN and GST codes provided by the platform represent **assisted AI classification suggestions** based on commodity categories. Because CatalogPulse AI is not connected to a live government tax-authority portal, classifications must be audited by human compliance officers before filing.
- **Dynamic Attribute Limits:** The Clean Dynamic CSV accommodates unlimited discovered attributes. The Legacy 252-Column Unilog export enforces an engineering cutoff at 50 attribute triplets (`ATTRIBUTE_LABEL_1..50`) to comply strictly with legacy database schemas.

---

## 10. Roadmap

- [ ] **Direct ERP/PIM Connectors:** Native bi-directional sync with SAP S/4HANA, Akeneo, and Pimcore.
- [ ] **CAD Drawing Attribute Extraction:** Native vector ingestion for AutoCAD and SolidWorks technical drawings.
- [ ] **Automated Syndication Webhooks:** Instant event publishing to Amazon Business, Zoro, and Grainger procurement endpoints.

---

## 11. License & Hackathon Context

Developed for the **Startup Buildathon 2026**.  
*Transforming messy industrial data into verified, commerce-ready catalogs.*
