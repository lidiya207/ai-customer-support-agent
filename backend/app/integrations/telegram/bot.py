"""Long-polling Telegram bot using httpx (no extra package required)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.integrations.telegram.handler import (
    HELP,
    WELCOME,
    handle_user_message,
    start_new_conversation,
)

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LEN = 4000


def _display_name(user: dict[str, Any] | None) -> str:
    if not user:
        return "Telegram user"
    parts = [user.get("first_name") or "", user.get("last_name") or ""]
    name = " ".join(p for p in parts if p).strip()
    if name:
        return name
    username = user.get("username")
    return f"@{username}" if username else "Telegram user"


def _chunk_text(text: str, limit: int = MAX_MESSAGE_LEN) -> list[str]:
    text = text.strip() or "…"
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


class TelegramBot:
    def __init__(self, token: str) -> None:
        self.token = token.strip()
        self.base = f"{TELEGRAM_API}/bot{self.token}"
        self.offset = 0
        settings = get_settings()
        self.history_limit = settings.TELEGRAM_HISTORY_LIMIT

    async def _request(
        self,
        client: httpx.AsyncClient,
        method: str,
        **params: Any,
    ) -> dict[str, Any]:
        response = await client.post(f"{self.base}/{method}", json=params)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        return payload.get("result")

    async def send_message(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
    ) -> None:
        for chunk in _chunk_text(text):
            await self._request(
                client,
                "sendMessage",
                chat_id=chat_id,
                text=chunk,
            )

    async def send_chat_action(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        action: str = "typing",
    ) -> None:
        try:
            await self._request(
                client,
                "sendChatAction",
                chat_id=chat_id,
                action=action,
            )
        except Exception:  # noqa: BLE001
            logger.debug("sendChatAction failed", exc_info=True)

    async def get_updates(
        self,
        client: httpx.AsyncClient,
        *,
        timeout: int = 25,
    ) -> list[dict[str, Any]]:
        result = await self._request(
            client,
            "getUpdates",
            offset=self.offset,
            timeout=timeout,
            allowed_updates=["message"],
        )
        return result or []

    async def handle_update(
        self,
        client: httpx.AsyncClient,
        update: dict[str, Any],
    ) -> None:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return

        text = (message.get("text") or "").strip()
        from_user = message.get("from")
        display_name = _display_name(from_user)

        if not text:
            await self.send_message(
                client,
                chat_id,
                "I only handle text messages for now. Type /help for commands.",
            )
            return

        command = text.split()[0].split("@", 1)[0].lower()

        if command in {"/start", "/help"}:
            await self.send_message(client, chat_id, WELCOME if command == "/start" else HELP)
            return

        if command == "/new":
            db = SessionLocal()
            try:
                reply = start_new_conversation(
                    db,
                    chat_id=int(chat_id),
                    display_name=display_name,
                )
            finally:
                db.close()
            await self.send_message(client, chat_id, reply)
            return

        await self.send_chat_action(client, chat_id, "typing")
        db = SessionLocal()
        try:
            result = await handle_user_message(
                db,
                chat_id=int(chat_id),
                display_name=display_name,
                text=text,
                history_limit=self.history_limit,
            )
            reply_text = result.text
        finally:
            db.close()

        await self.send_message(client, chat_id, reply_text)

    async def run(self) -> None:
        if not self.token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is empty. Set it in backend/.env "
                "(create a bot with @BotFather)."
            )

        logger.info("Telegram bot starting (long polling)…")
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            me = await self._request(client, "getMe")
            logger.info("Connected as @%s", me.get("username") or me.get("id"))
            # Drop any webhook so getUpdates works; also drops pending conflicts.
            await self._request(client, "deleteWebhook", drop_pending_updates=False)
            logger.info("Webhook cleared; polling for messages…")

            while True:
                try:
                    updates = await self.get_updates(client)
                    for update in updates:
                        update_id = int(update["update_id"])
                        self.offset = update_id + 1
                        try:
                            await self.handle_update(client, update)
                        except Exception:  # noqa: BLE001
                            logger.exception(
                                "Failed to handle update %s", update_id
                            )
                            chat = (update.get("message") or {}).get("chat") or {}
                            chat_id = chat.get("id")
                            if chat_id is not None:
                                try:
                                    await self.send_message(
                                        client,
                                        int(chat_id),
                                        "Sorry, something went wrong. Please try again.",
                                    )
                                except Exception:  # noqa: BLE001
                                    logger.exception("Failed to send error reply")
                except httpx.HTTPError:
                    logger.exception("Telegram poll error; retrying in 3s")
                    await asyncio.sleep(3)
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001
                    logger.exception("Unexpected bot loop error; retrying in 3s")
                    await asyncio.sleep(3)


async def run_polling() -> None:
    settings = get_settings()
    bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
    await bot.run()
