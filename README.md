# SmartOps AI — Enterprise AI Operations Intelligence Platform

An end-to-end AI platform for industrial and enterprise operations — combining machine learning, cloud-native architecture, and business intelligence to support pricing, predictive maintenance, demand forecasting, and customer analytics. Built as a full production-style system: real trained ML models on real sensor data, a normalized PostgreSQL schema, a 27-endpoint authenticated REST API, and a polished enterprise React frontend.

**Live demo:** `<Link>` · **API docs:** `<your-backend-url>/api/v1/docs`

---

## Data Sources — What's Real vs. Synthetic

**Real data:** The core predictive models are trained entirely on the **AI4I 2020 Predictive Maintenance Dataset** (Kaggle / UCI Machine Learning Repository) — 10,000 real industrial sensor readings (air/process temperature, rotational speed, torque, tool wear) with real documented failure labels (Machine failure, TWF, HDF, PWF, OSF, RNF).

**Synthetic (generated on top):** No public dataset exists for industrial-rental *business* transactions, so a business layer — a 420-machine fleet, 160 customers, 2,540 rental transactions, 1,030 maintenance records — was generated to demonstrate the full pricing, forecasting, and customer-intelligence pipeline. The synthetic fleet was sampled to match AI4I's real failure-rate distribution (3.33% vs. 3.39% in the source data) rather than drawn arbitrarily, and rental demand carries genuine embedded seasonality rather than uniform randomness.

| Model | Trained on |
|---|---|
| Failure Prediction, Health Score, Remaining Useful Life | **Real AI4I sensor data** |
| Dynamic Pricing, Demand Forecasting, Revenue Forecasting, Customer Intelligence | Synthetic business layer (sampled/seeded from real fleet failure distribution) |

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   React     │────▶│   FastAPI     │────▶│   PostgreSQL     │
│  Frontend   │     │   Backend     │     │   (13 tables)    │
│ (SmartOps)  │◀────│  27 endpoints │◀────│                  │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                            │
                    ┌───────┴────────┐
                    │  7 ML Models    │
                    │  + Decision     │
                    │  Engine         │
                    └────────────────┘
```

## Machine Learning Models

| Model | Algorithm | Key Metric | Result |
|---|---|---|---|
| Failure Prediction | XGBoost Classifier | ROC-AUC | **0.982** |
| Equipment Health Score | Random Forest Regressor | R² | **0.792** |
| Remaining Useful Life | Random Forest Regressor | R² | **0.980** |
| Dynamic Price Prediction | XGBoost Regressor | R² | **0.999** |
| Demand Forecasting | LightGBM Regressor | R² vs. naive baseline | **0.649** |
| Revenue & Profit Forecasting | Gradient Boosting Regressor | R² | **0.53 / 0.48** |
| Customer Intelligence (CLV, Risk) | Random Forest + XGBoost | — | Documented limitations |

Every model is cross-validated, uses matching library versions between training and serving environments, and includes SHAP-based explainability. Metrics are reported honestly, including where signal was weak — documented rather than hidden.

### AI Decision Engine

Combines outputs from all 7 models into ranked, explainable recommendations across the categories it actually generates — **Maintenance, Fleet Replacement, Inventory Relocation, Customer Retention** — each with a priority score, confidence score, and full plain-English reasoning. Generated 247 real recommendations against the platform's live data, with a working Approve/Reject workflow persisted to the database.

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth with refresh-token rotation, RBAC (6 role tiers)
**Database:** PostgreSQL 16, 13-table normalized schema
**Machine Learning:** scikit-learn, XGBoost, LightGBM, SHAP, pandas, NumPy
**Frontend:** React 18, TypeScript, Material UI, Recharts, TanStack Query, React Router, Axios, jsPDF
**DevOps:** Docker, Docker Compose (API + Postgres + Redis), deployed on Render

## Features

- **Executive Dashboard** — real-time KPIs, equipment health distribution, revenue forecasts, regional breakdown, system health monitoring
- **Equipment Management** — searchable/filterable fleet view with live ML predictions per machine, CSV/PDF export
- **Pricing** — live AI-suggested rental price for any machine, factoring health, competitor pricing, demand, and season
- **AI Decision Feed** — approve/reject workflow for AI-generated recommendations, persisted to database
- **Predictive Maintenance** — failure probability, remaining useful life with confidence intervals, CSV/PDF export
- **Demand & Revenue Forecasting** — daily/weekly/monthly/quarterly projections with genuine seasonal modeling
- **Customer Intelligence** — lifetime value prediction, payment risk scoring, discount recommendations, CSV/PDF export
- **Reports Center** — real-data CSV/PDF export across Equipment, Customers, Maintenance, and AI Decisions
- **Enterprise UI** — light/dark theme, role-based access, notification system, responsive data grids

## Cloud Architecture (Target — Azure)

| Component | Current | Azure Target |
|---|---|---|
| Compute | Docker Compose / Render | Azure App Service (containerized) |
| Database | PostgreSQL (Docker/Render) | Azure Database for PostgreSQL |
| ML model storage | Local filesystem | Azure Blob Storage |
| Secrets | .env / Render env vars | Azure Key Vault |
| CI/CD | — | GitHub Actions → Azure Container Registry |
| Monitoring | — | Azure Monitor + Application Insights |

*Deployed live on Render today; architected for Azure migration with configuration-only changes.*

## Project Structure

```
smartops-ai/
├── backend/          FastAPI application, models, API routes, auth
├── ml/
│   ├── pipelines/    ETL: AI4I cleaning, fleet sampling, synthetic generation
│   ├── training/     Model training scripts (all 7 models)
│   └── inference/    Production inference wrappers + Decision Engine
├── frontend/         React + TypeScript enterprise UI
├── datasets/         Real AI4I data (raw) + processed fleet/business data
└── docker-compose.yml
```

## Running Locally

```bash
# Backend + database
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python ml/pipelines/load_to_db.py --reset
docker compose exec backend python ml/inference/decision_engine.py

# Frontend
cd frontend && npm install && npm run dev
```

API docs: `http://localhost:8000/api/v1/docs` · App: `http://localhost:5173`

## Engineering Notes

Built with a strong emphasis on verification: every ML model trained and evaluated before shipping, every backend endpoint tested for real bugs (a FastAPI/Pydantic schema conflict, an XGBoost/scikit-learn version incompatibility, and a route-ordering collision were all caught and fixed), and the frontend compiled and production-built before each change. A systemic pagination bug — several pages requesting more records per call than the backend's enforced maximum — was traced across 7 locations and fixed with proper multi-page fetching, after being caught via real user testing rather than assumed away.

## Author

Built by MK Tejaswini — final-year B.Tech, AI & Data Science, REVA University.
