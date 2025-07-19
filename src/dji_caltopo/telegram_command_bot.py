from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
from dotenv import load_dotenv

import asyncio

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = os.getenv("MQTT_BROKER_PORT")


# This gets set by main.py
register_callback = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    "🤖 Hello! I'm ready to manage your drones.\n\n"
    "Available commands:\n"
    "/register <serial_number> <name> <token> – Register your drone\n"
    "/list <token> – View your registered drones\n"
    "/unregister <serial_number> <token> – Unregister your drone"
)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /register <serial_number> <name> <token>")
        return

    sn, name, token = context.args
    if register_callback:
        register_callback(sn, name, token)
        await update.message.reply_text(f"✅ Registered drone {name} (SN={sn})")
    else:
        await update.message.reply_text("⚠️ Register callback not set")


def start_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())  # ✅ Fix: create a loop in the thread
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    print("🤖 Telegram bot is listening for commands...")
    app.run_polling()

__all__ = ["start_bot", "register_callback"]
