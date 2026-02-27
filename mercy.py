from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import requests
import os
import logging
import asyncio

# Configuration - Use environment variable for security
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5"

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "Hello! I am your AI assistant powered by Qwen2.5.\n\n"
        "Send me any message and I will respond using the local Ollama model."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user messages and get AI response"""
    user_message = update.message.text
    chat_id = update.message.chat_id

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": user_message,
                "stream": False
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            bot_reply = result.get("response", "Sorry, no response received.")
            await update.message.reply_text(bot_reply)
        else:
            await update.message.reply_text(
                f"Error: Ollama server returned status {response.status_code}"
            )

    except requests.exceptions.ConnectionError:
        await update.message.reply_text(
            "Error: Cannot connect to Ollama server.\n"
            "Please ensure Ollama is running with: ollama serve"
        )
    except Exception as error:
        logger.error(f"Error: {error}")
        await update.message.reply_text(f"An error occurred: {str(error)}")


def main():
    """Initialize and run the bot"""
    logger.info("Starting bot...")
    logger.info(f"Using model: {MODEL_NAME}")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running. Send messages on Telegram.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
