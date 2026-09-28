import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from google import genai

# --- 1. Small Web Server for Render Free Tier ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "AI Bot is alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- 2. Configurations & System Instructions ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_TELEGRAM_ID = int(os.environ.get("MY_TELEGRAM_ID", 0))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# DEFINE YOUR BOT'S INSTRUCTIONS HERE
SYSTEM_INSTRUCTION = """
You are an intelligent assistant acting on behalf of [Your Name].
Your goal is to answer questions politely, concisely, and accurately based on the following instructions:
- Be helpful and friendly.
- If someone asks how to contact [Your Name] directly, let them know their message is logged.
- Keep answers clear and brief.
"""

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    incoming_text = update.message.text

    # Generate AI Response using Gemini
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=incoming_text,
            config={"system_instruction": SYSTEM_INSTRUCTION}
        )
        ai_reply = response.text
    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        ai_reply = "Sorry, I am having trouble processing your request right now."

    # 1. Reply directly to the user who messaged the bot
    await update.message.reply_text(ai_reply)

    # 2. Notify your personal Telegram account about the interaction
    if MY_TELEGRAM_ID:
        username_str = f" (@{user.username})" if user.username else ""
        notification = (
            f"💬 **NEW AI CHAT INTERACTION**\n\n"
            f"**From:** {user.full_name}{username_str}\n"
            f"**User Said:** \"{incoming_text}\"\n\n"
            f"**Bot Replied:** \"{ai_reply}\""
        )
        try:
            await context.bot.send_message(
                chat_id=MY_TELEGRAM_ID, 
                text=notification, 
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")

def main():
    # Run Web Server in Background
    threading.Thread(target=run_web_server, daemon=True).start()

    # Run Telegram Bot
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("AI Answering Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
