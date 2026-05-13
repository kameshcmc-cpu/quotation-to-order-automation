"""
Entry point: starts FastAPI server and Telegram bot concurrently using asyncio.
Usage:
    python run.py            # Full stack (API + Bot)
    python run.py --api-only # Only the FastAPI server
    python run.py --bot-only # Only the Telegram bot
"""
import sys
import os
import asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()


async def start_api():
    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def start_bot():
    from backend.config import settings
    if not settings.TELEGRAM_BOT_TOKEN:
        print("  TELEGRAM_BOT_TOKEN not set -- bot will not start.")
        return

    from bot.telegram_bot import build_app
    bot_app = build_app()

    async with bot_app:
        await bot_app.updater.start_polling(drop_pending_updates=True)
        await bot_app.start()
        print("  Telegram bot started (polling)")
        await asyncio.Event().wait()  # run forever
        await bot_app.updater.stop()
        await bot_app.stop()


async def start_all():
    await asyncio.gather(
        start_api(),
        start_bot(),
    )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    print("=" * 55)
    print("  QuoteFlow -- AI Quotation-to-Order Automation")
    print("=" * 55)

    if mode == "--api-only":
        print("  Mode: API only")
        print("  Dashboard -> http://localhost:8000")
        print("  API Docs  -> http://localhost:8000/docs")
        print("=" * 55)
        asyncio.run(start_api())

    elif mode == "--bot-only":
        print("  Mode: Telegram Bot only")
        print("=" * 55)
        asyncio.run(start_bot())

    else:
        print("  Mode: Full stack (API + Telegram Bot)")
        print("  Dashboard -> http://localhost:8000")
        print("  API Docs  -> http://localhost:8000/docs")
        print("=" * 55)
        asyncio.run(start_all())
