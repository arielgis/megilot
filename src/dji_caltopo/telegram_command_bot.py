from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# This gets set by main.py
register_callback = None

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 4:
        await update.message.reply_text(
            "❌ Usage: /register <serial_number> <name> <token> <email>"
        )
        return

    sn, name, token, email = context.args

    if "@" not in email or "." not in email:
        await update.message.reply_text("❌ Invalid email format.")
        return

    user = update.effective_user
    logging.info(f"Register request: SN={sn}, Token={token}, Email={email}, by @{user.username} (ID={user.id})")

    if register_callback:
        register_callback(sn, name, token, email)
        await update.message.reply_text(f"✅ Registered drone {name} (SN={sn})")
    else:
        await update.message.reply_text("⚠️ Register callback not set.")

def start_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("register", register))
    print("🤖 Telegram bot is listening for commands...")
    app.run_polling()

__all__ = ["start_bot", "register_callback"]