import logging
from typing import Any

import httpx

from app.settings import Settings

logger = logging.getLogger(__name__)


class WhatsMeowGatewayError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WhatsMeowGatewayClient:
    """Client for the local WhatsMeow gateway."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.whatsapp_gateway_url.rstrip("/")

    async def send_text(
        self,
        number: str,
        text: str,
        *,
        quoted_message_id: str | None = None,
        quoted_text: str | None = None,
        delay_ms: int = 0,
    ) -> dict[str, Any] | None:
        payload = {
            "number": number,
            "text": text,
            "quoted_id": quoted_message_id,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(f"{self._base_url}/send", json=payload)

            if response.status_code >= 400:
                logger.error("WhatsMeow HTTP %s while sending message", response.status_code)
                raise WhatsMeowGatewayError(
                    f"WhatsMeow returned {response.status_code}",
                    response.status_code,
                )

            return {"status": "success"}
        except WhatsMeowGatewayError:
            raise
        except Exception as exc:
            logger.error("Failed to send message through WhatsMeow: %s", type(exc).__name__)
            raise WhatsMeowGatewayError("Failed to send message through WhatsMeow") from exc

    async def send_presence(self, number: str, *, delay_ms: int = 5000) -> None:
        payload = {"number": number}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{self._base_url}/presence", json=payload)
        except Exception:
            logger.debug("Presence is temporarily unavailable in the Go gateway")

    async def check_connection(self) -> bool:
        """Return whether the Go gateway is responding."""

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._base_url}/send")
                return response.status_code == 405
        except Exception:
            return False
