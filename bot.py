import os
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def handle_message(update: Update, context: CallbackContext):
    try:
        user_message = update.message.text
        logger.info(f"Received message: {user_message}")
        
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
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            update.message.reply_text(ai_response)
        else:
            update.message.reply_text("Sorry, technical issue. Try again.")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("Error occurred. Please try again.")

def main():
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.error("Missing environment variables!")
        return
    
    # Create updater
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    
    # Get dispatcher
    dp = updater.dispatcher
    
    # Add message handler
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Start polling
    logger.info("Bot starting...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
