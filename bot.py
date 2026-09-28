import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
MY_TELEGRAM_ID = int(os.environ.get("MY_TELEGRAM_ID", 0))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

async def notify_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    incoming_text = update.message.text

    username_str = f" (@{user.username})" if user.username else ""
    notification = (
        f"🚨 **NEW DIRECT MESSAGE RECEIVED!**\n\n"
        f"**From:** {user.full_name}{username_str}\n"
        f"**User ID:** `{user.id}`\n"
        f"**Message:**\n\"{incoming_text}\""
    )

    await context.bot.send_message(
        chat_id=MY_TELEGRAM_ID, 
        text=notification, 
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, notify_me))
    print("Notification Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
