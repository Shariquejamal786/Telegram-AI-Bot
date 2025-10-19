import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        logger.info(f"Received message: {user_message}")
        
        # Check if API key is available
        if not GROQ_API_KEY:
            await update.message.reply_text("❌ API Key not configured. Please check environment variables.")
            return
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [{"role": "user", "content": user_message}],
            "model": "llama2-70b-4096",
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        logger.info("Sending request to Groq API...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        logger.info(f"Groq API response status: {response.status_code}")
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            await update.message.reply_text(ai_response)
        elif response.status_code == 401:
            await update.message.reply_text("❌ Invalid API Key. Please check Groq API key.")
        elif response.status_code == 429:
            await update.message.reply_text("⚠️ Rate limit exceeded. Please try again later.")
        else:
            error_msg = f"❌ API Error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            await update.message.reply_text("Sorry, technical issue. Please try again later.")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("❌ Error occurred. Please try again.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! I'm your AI assistant. How can I help you today?")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN missing!")
        return
    if not GROQ_API_KEY:
        logger.error("❌ GROQ_API_KEY missing!")
        return
    
    logger.info("✅ Starting bot with all configurations...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", start_command))
    
    logger.info("🤖 Bot is running and polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
