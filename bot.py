import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        user_name = update.message.from_user.first_name
        
        # Groq AI API call
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a helpful AI assistant. Respond in helpful and friendly manner."
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            "model": "llama2-70b-4096",
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            await update.message.reply_text(f"🤖 {ai_response}")
        else:
            await update.message.reply_text("❌ Sorry, I'm having trouble responding right now.")
            
    except Exception as e:
        await update.message.reply_text("❌ Error occurred. Please try again.")

def main():
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("🤖 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
