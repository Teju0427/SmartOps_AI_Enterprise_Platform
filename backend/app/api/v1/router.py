from fastapi import APIRouter

from app.api.v1.endpoints import auth, equipment, dashboard, decisions, rentals, customers, maintenance, forecasts

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(equipment.router)
api_router.include_router(dashboard.router)
api_router.include_router(decisions.router)
api_router.include_router(rentals.router)
api_router.include_router(customers.router)
api_router.include_router(maintenance.router)
api_router.include_router(forecasts.router)
