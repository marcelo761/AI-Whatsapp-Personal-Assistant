import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

TEXT_MESSAGE_TYPES = {
    "conversation",
    "extendedTextMessage",
    "text",
}


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    message_id: str
    remote_jid: str
    phone_number: str
    text: str
    push_name: str
    from_me: bool
    is_group: bool
    quoted_message_id: str | None
    quoted_text: str | None
    instance: str


def _normalize_event_name(event: str | None) -> str:
    if not event:
        return ""
    return event.upper().replace(".", "_").replace("-", "_")


def _extract_phone(remote_jid: str) -> str:
    return remote_jid.split("@", 1)[0]


def _extract_text(message: dict[str, Any]) -> str | None:
    if not message:
        return None

    if conversation := message.get("conversation"):
        return str(conversation).strip()

    if extended := message.get("extendedTextMessage"):
        text = extended.get("text")
        return str(text).strip() if text else None

    if image := message.get("imageMessage"):
        caption = image.get("caption")
        return str(caption).strip() if caption else None

    if document := message.get("documentMessage"):
        caption = document.get("caption")
        return str(caption).strip() if caption else None

    return None


def _extract_quote(message: dict[str, Any]) -> tuple[str | None, str | None]:
    context = message.get("extendedTextMessage", {}).get("contextInfo") or message.get(
        "contextInfo"
    )
    if not context:
        return None, None

    quoted = context.get("quotedMessage") or {}
    quoted_id = context.get("stanzaId") or context.get("quotedMessageId")
    quoted_text = _extract_text(quoted)
    return quoted_id, quoted_text


def _parse_message_record(record: dict[str, Any], instance: str) -> IncomingMessage | None:
    key = record.get("key") or {}
    if key.get("fromMe"):
        return None

    remote_jid = key.get("remoteJid", "")
    if not remote_jid or remote_jid in {"status@broadcast"}:
        return None

    is_group = remote_jid.endswith("@g.us")
    message = record.get("message") or {}
    text = _extract_text(message)
    if not text:
        return None

    quoted_id, quoted_text = _extract_quote(message)
    message_id = key.get("id", "")

    return IncomingMessage(
        message_id=message_id,
        remote_jid=remote_jid,
        phone_number=_extract_phone(remote_jid),
        text=text,
        push_name=str(record.get("pushName") or ""),
        from_me=bool(key.get("fromMe")),
        is_group=is_group,
        quoted_message_id=quoted_id,
        quoted_text=quoted_text,
        instance=instance,
    )


def parse_webhook_payload(payload: dict[str, Any]) -> list[IncomingMessage]:
    event = _normalize_event_name(payload.get("event"))
    if event != "MESSAGES_UPSERT":
        return []

    instance = str(payload.get("instance") or "")
    data = payload.get("data")

    records: list[dict[str, Any]]
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        if "messages" in data and isinstance(data["messages"], list):
            records = data["messages"]
        else:
            records = [data]
    else:
        logger.warning("Unsupported webhook data format: %s", type(data))
        return []

    messages: list[IncomingMessage] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        parsed = _parse_message_record(record, instance)
        if parsed:
            messages.append(parsed)

    return messages
