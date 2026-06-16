import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.integrations.webhook_parser import parse_webhook_payload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


def _verify_webhook_secret(
    authorization: str | None,
    webhook_secret: str,
) -> None:
    if not webhook_secret:
        return

    expected = f"Bearer {webhook_secret}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook authorization",
        )


async def _handle_payload(
    payload: dict,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    messages = parse_webhook_payload(payload)
    if not messages:
        return {"status": "ignored"}

    from app.services.message_handler import MessageHandler

    handler: MessageHandler = request.app.state.message_handler
    for message in messages:
        background_tasks.add_task(handler.process, message)

    return {"status": "accepted", "count": str(len(messages))}


@router.post("/webhook/whatsmeow")
async def whatsmeow_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    settings = request.app.state.settings
    _verify_webhook_secret(authorization, settings.webhook_secret)

    try:
        payload = await request.json()
    except Exception as exc:
        logger.warning("Invalid webhook payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    logger.debug("Webhook payload received: %s", payload)
    return await _handle_payload(payload, request, background_tasks)


@router.post("/webhook/whatsmeow/{event_name}")
async def whatsmeow_webhook_by_event(
    event_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    settings = request.app.state.settings
    _verify_webhook_secret(authorization, settings.webhook_secret)

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    payload.setdefault("event", event_name.replace("-", "_").upper())
    return await _handle_payload(payload, request, background_tasks)
