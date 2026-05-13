"""
Entry point: starts FastAPI server and Telegram bot concurrently.
Usage:
    python run.py            # Full stack (API + Bot)
    python run.py --api-only # Only the FastAPI server (no Telegram)
    python run.py --bot-only # Only the Telegram bot
"""
import sys
import os
import asyncio
import threading
import uvicorn
from dotenv import load_dotenv

load_dotenv()


def run_api():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )


def run_bot():
    from backend.config import settings
    if not settings.TELEGRAM_BOT_TOKEN:
        print("  TELEGRAM_BOT_TOKEN not set -- bot will not start.")
        return
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    from bot.telegram_bot import run_bot as _run_bot
    _run_bot()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    print("=" * 55)
    print("  QuoteFlow — AI Quotation-to-Order Automation")
    print("=" * 55)

    if mode == "--api-only":
        print("  Mode: API only")
        print("  Dashboard -> http://localhost:8000")
        print("  API Docs  -> http://localhost:8000/docs")
        print("=" * 55)
        run_api()

    elif mode == "--bot-only":
        print("  Mode: Telegram Bot only")
        print("=" * 55)
        run_bot()

    else:
        print("  Mode: Full stack (API + Telegram Bot)")
        print("  Dashboard -> http://localhost:8000")
        print("  API Docs  -> http://localhost:8000/docs")
        print("=" * 55)

        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        run_api()
