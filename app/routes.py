from fastapi import APIRouter

from app.handlers import health

router = APIRouter()

router.add_api_route(path="/health", endpoint=health.health_check, methods=["GET"])
router.add_api_route(path="/ping", endpoint=health.ping, methods=["GET"])
