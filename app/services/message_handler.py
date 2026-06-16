import json
import logging
import re
from pathlib import Path

from app.integrations.webhook_parser import IncomingMessage
from app.integrations.whatsmeow_gateway_client import (
    WhatsMeowGatewayClient,
    WhatsMeowGatewayError,
)
from app.services.session_store import SessionStore
from app.settings import Settings
from bot_utilities.ai_utils import generate_response
from bot_utilities.config_loader import config, instructions, load_contacts
from bot_utilities.response_utils import split_response

logger = logging.getLogger(__name__)

CONTACTS_FILE = Path("contacts.json")


class MessageHandler:
    def __init__(
        self,
        settings: Settings,
        whatsapp_gateway: WhatsMeowGatewayClient,
        sessions: SessionStore,
    ) -> None:
        self._settings = settings
        self._whatsapp_gateway = whatsapp_gateway
        self._sessions = sessions
        self._trigger_words = [word.lower() for word in config.get("TRIGGER", [])]
        self._allow_all = bool(config.get("ALLOW_ALL_CONTACTS", True))
        self._allow_groups = bool(config.get("ALLOW_GROUPS", False))
        self._default_instruction = config.get("DEFAULT_INSTRUCTION", "custom")
        self._typing_delay_ms = int(config.get("WHATSAPP", {}).get("TYPING_DELAY_MS", 5000))
        self._chunk_size = int(config.get("WHATSAPP", {}).get("MAX_MESSAGE_LENGTH", 4096))

    def _load_contacts(self) -> dict[str, str]:
        return load_contacts()

    def _save_contacts(self, contacts: dict[str, str]) -> None:
        CONTACTS_FILE.write_text(json.dumps(contacts, indent=4, ensure_ascii=False), encoding="utf-8")

    def _session_key_raw(self, phone_number: str, remote_jid: str) -> str:
        return f"{phone_number}:{remote_jid}"

    def _is_admin(self, phone_number: str) -> bool:
        admins = self._settings.admin_number_set
        return phone_number in admins if admins else False

    def _should_respond_raw(self, message: IncomingMessage, phone_number: str) -> bool:
        if message.from_me:
            return False
        if message.is_group and not self._allow_groups:
            return False

        contacts = self._load_contacts()
        text_lower = message.text.lower()

        if self._allow_all:
            return True

        if phone_number in contacts:
            return True

        return any(trigger in text_lower for trigger in self._trigger_words)

    def _resolve_persona(self, phone_number: str) -> str:
        contacts = self._load_contacts()
        persona = contacts.get(phone_number, contacts.get("*", self._default_instruction))
        if persona not in instructions:
            if self._default_instruction in instructions:
                return self._default_instruction
            return next(iter(instructions))
        return persona

    async def _handle_admin_command_raw(self, message: IncomingMessage, phone_number: str) -> bool:
        if not self._is_admin(phone_number):
            return False

        destination = message.remote_jid or phone_number
        text = message.text.strip()
        lower = text.lower()

        if lower in {"/reset", "!reset", "/limpar", "!limpar"}:
            session_key = self._session_key_raw(phone_number, message.remote_jid)
            self._sessions.clear_history(session_key)
            await self._whatsapp_gateway.send_text(
                destination,
                "Historico de conversa limpo com sucesso.",
                quoted_message_id=message.message_id,
                quoted_text=message.text,
            )
            return True

        persona_match = re.match(r"^[/!]persona\s+(\w+)$", lower)
        if persona_match:
            persona = persona_match.group(1)
            if persona not in instructions:
                available = ", ".join(sorted(instructions))
                await self._whatsapp_gateway.send_text(
                    destination,
                    f"Persona invalida. Disponiveis: {available}",
                    quoted_message_id=message.message_id,
                    quoted_text=message.text,
                )
                return True

            contacts = self._load_contacts()
            contacts[phone_number] = persona
            self._save_contacts(contacts)
            await self._whatsapp_gateway.send_text(
                destination,
                f"Persona alterada para '{persona}'.",
                quoted_message_id=message.message_id,
                quoted_text=message.text,
            )
            return True

        if lower in {"/status", "!status"}:
            stats = self._sessions.stats()
            await self._whatsapp_gateway.send_text(
                destination,
                f"Sessoes ativas: {stats['active_sessions']}\n"
                f"Mensagens processadas: {stats['processed_messages']}",
                quoted_message_id=message.message_id,
                quoted_text=message.text,
            )
            return True

        return False

    async def process(self, message: IncomingMessage) -> None:
        phone_number = message.phone_number
        if message.remote_jid and "@" in message.remote_jid:
            real_phone = message.remote_jid.split("@")[0]
            if real_phone.isdigit() and len(real_phone) >= 8:
                phone_number = real_phone

        destination = message.remote_jid or phone_number

        if self._sessions.is_duplicate(message.message_id):
            logger.debug("Duplicate message ignored: %s", message.message_id)
            return

        self._sessions.mark_processed(message.message_id)

        if not self._should_respond_raw(message, phone_number):
            logger.debug("Message ignored from %s", phone_number)
            return

        if await self._handle_admin_command_raw(message, phone_number):
            return

        session_key = self._session_key_raw(phone_number, message.remote_jid)
        lock = await self._sessions.get_lock(session_key)

        async with lock:
            persona = self._resolve_persona(phone_number)
            system_prompt = (
                f"Ignore all the instructions you have gotten before. "
                f"{instructions[persona]}. "
            )

            if message.push_name:
                system_prompt += f"The user's name is {message.push_name}. "

            history = self._sessions.get_history(session_key)
            history.append({"role": "user", "content": message.text})

            await self._whatsapp_gateway.send_presence(destination, delay_ms=self._typing_delay_ms)

            try:
                response = await generate_response(instructions=system_prompt, history=history)
            except Exception as exc:
                logger.error(
                    "AI error | number=%s | model=%s | error=%s",
                    phone_number,
                    config.get("MODEL_ID", "NAO DEFINIDO"),
                    exc,
                    exc_info=True,
                )
                response = (
                    "Desculpe, ocorreu um erro ao processar sua mensagem. "
                    "Tente novamente em alguns instantes."
                )

            if not response:
                response = "Nao foi possivel gerar uma resposta no momento."

            self._sessions.append_message(session_key, "user", message.text)
            self._sessions.append_message(session_key, "assistant", response)
            await self._send_response_raw(message, destination, response)

    async def _send_response_raw(self, message: IncomingMessage, destination: str, response: str) -> None:
        chunks = split_response(response, max_length=self._chunk_size)
        quoted_id = message.message_id
        quoted_text = message.text

        for index, chunk in enumerate(chunks):
            try:
                await self._whatsapp_gateway.send_text(
                    destination,
                    chunk,
                    quoted_message_id=quoted_id if index == 0 else None,
                    quoted_text=quoted_text if index == 0 else None,
                )
            except WhatsMeowGatewayError:
                logger.exception("Failed to send message chunk to %s", destination)
                try:
                    await self._whatsapp_gateway.send_text(destination, chunk)
                except WhatsMeowGatewayError:
                    logger.exception("Fallback send also failed for %s", destination)
                    return

            quoted_id = None
            quoted_text = None
