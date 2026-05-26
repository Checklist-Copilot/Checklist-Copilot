from fastapi import APIRouter

from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.checklists import router as checklists_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.users import router as users_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(users_router, tags=["users"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(checklists_router, tags=["checklists"])
api_router.include_router(files_router, tags=["files"])
api_router.include_router(ai_router, tags=["ai"])
