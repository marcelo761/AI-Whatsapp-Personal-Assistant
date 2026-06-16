from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    gateway = request.app.state.whatsapp_gateway_client
    gateway_ok = await gateway.check_connection()
    sessions = request.app.state.session_store.stats()

    return {
        "status": "healthy" if gateway_ok else "degraded",
        "whatsapp_gateway": "connected" if gateway_ok else "unreachable",
        "sessions": sessions,
    }


@router.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "AI WhatsApp Personal Assistant",
        "webhook": "/webhook/whatsmeow",
        "health": "/health",
    }
