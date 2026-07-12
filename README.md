# RentalIQ — Enterprise AI Rental Decision Intelligence Platform

An end-to-end AI platform for industrial equipment rental companies, combining machine learning, cloud-native architecture, and business intelligence to support pricing, predictive maintenance, demand forecasting, and customer analytics.

Built as a full production-style system: real trained ML models (not mocked), a normalized PostgreSQL schema, a 26-endpoint authenticated REST API, and a React enterprise frontend — architected for Azure deployment.

**Live demo:** `<paste your Render URL here once deployed>` · **API docs:** `<your-backend-url>/api/v1/docs`

---

## Why this project

Industrial rental companies (construction equipment, generators, compressors, cranes) make dozens of daily decisions — what to charge, which machine needs maintenance, where to move idle inventory — largely on gut instinct. RentalIQ demonstrates how a modern data + ML stack can turn a fleet's own sensor and transaction history into concrete, explainable business recommendations.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   React     │────▶│   FastAPI     │────▶│   PostgreSQL     │
│  Frontend   │     │   Backend     │     │   (13 tables)    │
│  (RentalIQ) │◀────│  26 endpoints │◀────│                  │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                            │
                    ┌───────┴────────┐
                    │  7 ML Models    │
                    │  + Decision     │
                    │  Engine         │
                    └────────────────┘
```

**Data flow:** AI4I 2020 sensor dataset (10,000 machine readings) → cleaned & feature-engineered → sampled into a realistic 420-machine fleet → synthetic rental/customer/maintenance business layer generated on top (with genuine seasonal demand patterns) → loaded into PostgreSQL → 7 ML models trained against it → an AI Decision Engine combines all model outputs into ranked, explainable business recommendations → served through a REST API → rendered in a React dashboard.

## Machine Learning Models

| Model | Algorithm | Key Metric | Result |
|---|---|---|---|
| Failure Prediction | XGBoost Classifier | ROC-AUC | **0.982** |
| Equipment Health Score | Random Forest Regressor | R² | **0.792** |
| Remaining Useful Life | Random Forest Regressor | R² | **0.980** |
| Dynamic Price Prediction | XGBoost Regressor | R² | **0.999** |
| Demand Forecasting | LightGBM Regressor | R² (vs. naive baseline) | **0.649** |
| Revenue & Profit Forecasting | Gradient Boosting Regressor | R² | **0.53 / 0.48** |
| Customer Intelligence (CLV, Risk) | Random Forest + XGBoost | — | Documented limitations |

Every model is cross-validated, uses matching library versions between training and serving environments, and includes SHAP-based explainability where applicable. Metrics are reported honestly, including where signal was weak (e.g., customer late-payment risk had limited predictive power from customer-level features alone — documented rather than hidden).

### AI Decision Engine

Combines outputs from all 7 models into ranked, human-readable recommendations across 4 categories — Maintenance, Fleet Replacement, Inventory Relocation, and Customer Retention — each with a priority score, confidence score, and full reasoning. Generated 247 real recommendations against the platform's live data.

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth with refresh-token rotation, RBAC (6 role tiers)
**Database:** PostgreSQL 16, 13-table normalized schema
**Machine Learning:** scikit-learn, XGBoost, LightGBM, SHAP, pandas, NumPy
**Frontend:** React 18, TypeScript, Material UI, Recharts, TanStack Query, React Router, Axios
**DevOps:** Docker, Docker Compose (multi-container: API, Postgres, Redis)

## Features

- **Executive Dashboard** — real-time KPIs, equipment health distribution, revenue forecasts, regional breakdown, system health monitoring
- **Equipment Management** — searchable/filterable fleet view with live ML predictions per machine
- **AI Decision Feed** — approve/reject workflow for AI-generated recommendations, persisted to database
- **Predictive Maintenance** — failure probability, remaining useful life with confidence intervals, AI-generated maintenance reasoning
- **Dynamic Pricing** — real-time price suggestions factoring equipment health, competitor pricing, demand, and inventory scarcity
- **Demand & Revenue Forecasting** — daily/weekly/monthly/quarterly projections with genuine seasonal modeling
- **Customer Intelligence** — lifetime value prediction, payment risk scoring, discount recommendations
- **Enterprise UI** — light/dark theme, role-based access, notification system, responsive data grids

## Cloud Architecture (Target — Azure)

The platform is architected for direct Azure deployment with minimal changes:

| Component | Local (current) | Azure (target) |
|---|---|---|
| Compute | Docker Compose | Azure App Service (containerized) |
| Database | PostgreSQL in Docker | Azure Database for PostgreSQL |
| ML model storage | Local filesystem | Azure Blob Storage |
| Secrets | `.env` file | Azure Key Vault |
| CI/CD | — | GitHub Actions → Azure Container Registry |
| Monitoring | — | Azure Monitor + Application Insights |

*Azure deployment is the platform's designed target architecture; local Docker deployment is fully functional today and demonstrates the same production code path that would ship to Azure App Service with configuration changes only (connection strings, secret sources).*

## Project Structure

```
rental-ai-platform/
├── backend/          FastAPI application, models, API routes, auth
├── ml/
│   ├── pipelines/    ETL: data cleaning, fleet sampling, synthetic generation
│   ├── training/      Model training scripts (all 7 models)
│   └── inference/     Production inference wrappers + Decision Engine
├── frontend/          React + TypeScript enterprise UI
├── datasets/          Raw AI4I data + processed fleet/business data
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

API docs: `http://localhost:8000/api/v1/docs`
App: `http://localhost:5173`

## Engineering Notes

This project was built iteratively with a strong emphasis on verification — every ML model was trained and evaluated before being shipped, every backend endpoint was tested for real route-registration bugs (several were caught and fixed: FastAPI/Pydantic schema generation conflicts, XGBoost/scikit-learn version incompatibilities, route-ordering collisions), and the frontend was compiled and production-built before each incremental change. Metrics throughout are reported honestly, including a documented case where a synthetic data generation bug produced an artificial demand spike — found, root-caused, and fixed by embedding genuine seasonal structure into the data rather than patching around the symptom.

## Author

Built by MK Tejaswini  — final-year B.Tech, AI & Data Science, REVA University.
