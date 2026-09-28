import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

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

# Global state to control whether AI is active
AI_ENABLED = True

ai_client = genai.Client(api_key=GEMINI_API_KEY)

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

# --- 3. Admin Command Handlers ---
async def pause_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AI_ENABLED
    if update.effective_user.id != MY_TELEGRAM_ID:
        return
    AI_ENABLED = False
    await update.message.reply_text("⏸ **AI auto-replies have been PAUSED.** Messages will only be forwarded to you.")

async def resume_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AI_ENABLED
    if update.effective_user.id != MY_TELEGRAM_ID:
        return
    AI_ENABLED = True
    await update.message.reply_text("▶️ **AI auto-replies have been RESUMED.**")

async def reply_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_TELEGRAM_ID:
        return
    
    # Usage: /reply <user_id> <message>
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ **Usage:** `/reply <user_id> <your message>`", parse_mode="Markdown")
        return

    target_user_id = context.args[0]
    message_to_send = " ".join(context.args[1:])

    try:
        await context.bot.send_message(chat_id=target_user_id, text=message_to_send)
        await update.message.reply_text(f"✅ Sent message to `{target_user_id}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send message: {e}")

# --- 4. Main Chat Handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    incoming_text = update.message.text

    # Ignore messages sent by you to the bot (unless they are commands handled above)
    if user.id == MY_TELEGRAM_ID:
        return

    ai_reply = None

    if AI_ENABLED:
        try:
            response = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=incoming_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            ai_reply = response.text
        except Exception as e:
            logging.error(f"Gemini API Error: {e}")
            ai_reply = "Sorry, I am having trouble processing your request right now."

        # Send AI response to the user
        await update.message.reply_text(ai_reply)

    # Always notify your personal Telegram account
    if MY_TELEGRAM_ID:
        username_str = f" (@{user.username})" if user.username else ""
        
        if AI_ENABLED:
            notification = (
                f"💬 **NEW AI CHAT INTERACTION**\n\n"
                f"**From:** {user.full_name}{username_str}\n"
                f"**User ID:** `{user.id}`\n"
                f"**User Said:** \"{incoming_text}\"\n\n"
                f"**Bot Replied:** \"{ai_reply}\""
            )
        else:
            notification = (
                f"🚨 **NEW DIRECT MESSAGE RECEIVED (AI PAUSED)**\n\n"
                f"**From:** {user.full_name}{username_str}\n"
                f"**User ID:** `{user.id}`\n"
                f"**Message:** \"{incoming_text}\"\n\n"
                f"💡 *Reply using:* `/reply {user.id} Your message here`"
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
    threading.Thread(target=run_web_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    # Admin commands (Only work when sent from your MY_TELEGRAM_ID account)
    app.add_handler(CommandHandler("pause", pause_ai))
    app.add_handler(CommandHandler("resume", resume_ai))
    app.add_handler(CommandHandler("reply", reply_user))

    # All incoming user text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("AI Answering Bot with Admin Controls is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
