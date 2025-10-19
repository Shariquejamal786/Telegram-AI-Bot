import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        logger.info(f"📨 Received: {user_message}")
        
        if not GROQ_API_KEY:
            await update.message.reply_text("❌ API Key not configured.")
            return
        
        # Groq API call with sync to async
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, make_groq_request, user_message)
        
        if response:
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("❌ Technical issue. Please try again.")
            
    except Exception as e:
        logger.error(f"💥 Error: {str(e)}")
        await update.message.reply_text("❌ Error occurred. Please try again.")

def make_groq_request(user_message):
    """Sync function for Groq API call"""
    try:
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
        
        logger.info("🔄 Calling Groq API...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        logger.info(f"📊 Groq Status: {response.status_code}")
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            logger.info("✅ AI Response successful")
            return ai_response
        else:
            logger.error(f"❌ Groq Error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"💥 Groq Request Error: {str(e)}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! I'm your AI assistant. How can I help you today?")

def main():
    logger.info("🔧 Starting bot...")
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN missing!")
        return
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CommandHandler("start", start_command))
        
        logger.info("🚀 Bot started successfully!")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"💥 Failed to start: {str(e)}")

if __name__ == "__main__":
    main()
