from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import asyncio
import logging
import re

# --- Shared callback (set from main.py) ---
register_callback = None

# --- Email validation regex ---
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

# --- Command: /register ---
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 4:
        await update.message.reply_text(
            "❌ Usage: /register <serial_number> <name> <token> <email>"
        )
        return

    sn, name, token, email = [arg.strip() for arg in context.args]

    if not EMAIL_REGEX.match(email):
        await update.message.reply_text("❌ Invalid email format.")
        return

    user = update.effective_user
    logging.info(
        f"Register request: SN={sn}, Token={token}, Email={email}, "
        f"by @{user.username} (ID={user.id})"
    )

    if register_callback:
        success, message = register_callback(sn, name, token, email)
        if success:
            await update.message.reply_text(f"✅ Registered drone {name} (SN={sn})")
        else:
            await update.message.reply_text(f"❌ Registration failed: {message}")
    else:
        await update.message.reply_text("⚠️ Register callback not set.")

# --- Start the Telegram command bot ---
def start_bot():
    from dotenv import load_dotenv
    from telegram.request import HTTPXRequest
    import httpx
    
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_CONTROL_BOT_TOKEN")
    # Use custom AsyncClient that forces IPv4
    client = httpx.AsyncClient(local_address="0.0.0.0")
    request = HTTPXRequest(http_version="1.1", client=client)

    asyncio.set_event_loop(asyncio.new_event_loop())
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).request(request).build()
    app.add_handler(CommandHandler("register", register))
    logging.info("🤖 Telegram control bot is running...")
    app.run_polling()

__all__ = ["start_bot", "register_callback"]