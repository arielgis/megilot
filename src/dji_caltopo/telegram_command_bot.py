import os
import re
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
from dotenv import load_dotenv

# Shared callback
register_callback = None

# Email validation regex
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

# --- Command: /register ---
async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 4:
        await update.message.reply_text("❌ Usage: /register <serial_number> <name> <token> <email>")
        return

    sn, name, token, email = [a.strip() for a in args]

    if not EMAIL_REGEX.match(email):
        await update.message.reply_text("❌ Invalid email format.")
        return

    user = update.effective_user
    logging.info(f"Register request: SN={sn}, Token={token}, Email={email}, by @{user.username} (ID={user.id})")

    if register_callback:
        try:
            success, msg = register_callback(sn, name, token, email)
            await update.message.reply_text("✅ " + msg if success else "❌ " + msg)
        except Exception as e:
            logging.error(f"Register callback failed: {e}")
            await update.message.reply_text("❌ Internal error while processing registration.")
    else:
        await update.message.reply_text("⚠️ Register callback not set.")


# --- Error handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.warning(f"Update {update} caused error {context.error}")
    if hasattr(update, "effective_message") and update.effective_message:
        await update.effective_message.reply_text("❌ An error occurred. Please try again later.")


# --- Start the bot (used by main.py) ---
def start_bot():
    load_dotenv()
    token = os.getenv("TELEGRAM_CONTROL_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_CONTROL_BOT_TOKEN not set in environment.")

    asyncio.set_event_loop(asyncio.new_event_loop())  # Needed in a new thread
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("register", register_command))
    app.add_error_handler(error_handler)

    logging.info("🤖 Control bot started.")
    app.run_polling()


__all__ = ["start_bot", "register_callback"]