from google import genai
from google.genai import types

# Initialize client using the environment variable
ai_client = genai.Client(api_key=GEMINI_API_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    incoming_text = update.message.text

    # Ignore direct messages sent by you to the bot
    if user.id == MY_TELEGRAM_ID:
        return

    ai_reply = None

    if AI_ENABLED:
        try:
            # Use async API client (client.aio) to prevent blocking python-telegram-bot
            response = await ai_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=incoming_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            ai_reply = response.text
        except Exception as e:
            logging.error(f"Gemini API Exception: {e}")
            ai_reply = "Sorry, I am having trouble processing your request right now."

        # Send reply to user
        await update.message.reply_text(ai_reply)

    # Forward notification to your personal account
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

