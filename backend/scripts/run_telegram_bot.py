"""Run the mini Telegram support bot (long polling).

Prerequisites:
  1. Backend DB migrated and reachable (same as the API).
  2. LLM available (Ollama or OPENAI_API_KEY).
  3. TELEGRAM_BOT_TOKEN set in backend/.env (from @BotFather).

Usage (from backend/):
  uv run python scripts/run_telegram_bot.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.integrations.telegram.bot import run_polling


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        asyncio.run(run_polling())
    except KeyboardInterrupt:
        print("\nTelegram bot stopped.")


if __name__ == "__main__":
    main()
