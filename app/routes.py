from fastapi import APIRouter

from app.handlers import dora, health

router = APIRouter()

router.add_api_route(path="/health", endpoint=health.health_check, methods=["GET"])
router.add_api_route(path="/ping", endpoint=health.ping, methods=["GET"])
router.add_api_route(path="/dora", endpoint=dora.get_doras, methods=["GET"])
