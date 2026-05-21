from fastapi import APIRouter

from app.services.health import get_health_status


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return get_health_status()
