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
        logger.info(f"📨 Received: {user_message}")
        
        if not GROQ_API_KEY:
            logger.error("❌ GROQ_API_KEY missing!")
            await update.message.reply_text("❌ API Key not configured.")
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
            await update.message.reply_text(ai_response)
        elif response.status_code == 401:
            logger.error("❌ Invalid Groq API Key")
            await update.message.reply_text("❌ Invalid API Key. Please check Groq settings.")
        elif response.status_code == 429:
            logger.error("⚠️ Rate limit exceeded")
            await update.message.reply_text("⚠️ Rate limit exceeded. Try later.")
        else:
            logger.error(f"❌ Groq Error: {response.status_code}")
            await update.message.reply_text("🔧 Technical issue. Please try again.")
            
    except Exception as e:
        logger.error(f"💥 Exception: {str(e)}")
        await update.message.reply_text("❌ Error occurred. Please try again.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! I'm your AI assistant. How can I help you today?")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN missing!")
        return
    
    if not GROQ_API_KEY:
        logger.error("❌ GROQ_API_KEY missing!")
    else:
        logger.info(f"✅ GROQ_API_KEY found: {GROQ_API_KEY[:10]}...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", start_command))
    
    logger.info("🚀 Bot started successfully!")
    application.run_polling()

if __name__ == "__main__":
    main()
