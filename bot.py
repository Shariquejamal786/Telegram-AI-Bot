import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import logging
from io import BytesIO
from datetime import datetime, timedelta

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
HUGGING_FACE_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")

# Memory Storage - Yeh line IMPORTANT hai!
user_sessions = {}

# ========== MEMORY MANAGEMENT ==========
def get_user_session(user_id, user_name):
    current_time = datetime.now()
    
    # Clean old sessions (1 hour)
    for uid in list(user_sessions.keys()):
        if current_time - user_sessions[uid]['last_activity'] > timedelta(hours=1):
            del user_sessions[uid]
            logger.info(f"🧹 Cleared old session for user {uid}")
    
    # Create new session or update existing
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'history': [
                {
                    "role": "system", 
                    "content": f"You are {user_name}'s helpful friend. Respond in friendly Hinglish. Remember previous conversations and be contextual."
                }
            ],
            'last_activity': current_time,
            'user_name': user_name
        }
        logger.info(f"🎯 New session started for {user_name}")
    else:
        user_sessions[user_id]['last_activity'] = current_time
    
    return user_sessions[user_id]

def add_to_memory(user_id, role, content):
    if user_id in user_sessions:
        user_sessions[user_id]['history'].append({"role": role, "content": content})
        
        # Keep only last 6 messages (to avoid too long context)
        if len(user_sessions[user_id]['history']) > 6:
            user_sessions[user_id]['history'] = user_sessions[user_id]['history'][-6:]

# ========== AI CHAT WITH MEMORY ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        user_message = update.message.text
        
        # Skip commands
        if user_message.startswith('/'):
            return
        
        logger.info(f"💬 {user_name}: {user_message}")
        
        # Get user session with memory
        session = get_user_session(user_id, user_name)
        
        # Add user message to memory
        add_to_memory(user_id, "user", user_message)
        
        if not GROQ_API_KEY:
            await update.message.reply_text("❌ AI service unavailable")
            return
        
        # AI call with MEMORY
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": session['history'],
            "model": "llama-3.1-8b-instant",
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
            
            # Add AI response to memory
            add_to_memory(user_id, "assistant", ai_response)
            
            logger.info(f"🤖 Bot: {ai_response[:50]}...")
            await update.message.reply_text(ai_response)
        else:
            await update.message.reply_text("❌ AI service busy")
            
    except Exception as e:
        logger.error(f"💥 Chat error: {str(e)}")
        await update.message.reply_text("❌ Error processing message")

# ========== CLEAR MEMORY COMMAND ==========
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("🧹 Memory cleared! New conversation started.")
    else:
        await update.message.reply_text("ℹ️ No active conversation to clear.")

# ========== OTHER COMMANDS (SAME AS BEFORE) ==========
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        city = " ".join(context.args) if context.args else "Mumbai"
        await update.message.reply_text(f"🌤️ Checking weather for {city}...")
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            weather_text = f"""
🌤️ **Weather in {data['name']}**

📊 **Temperature:** {data['main']['temp']}°C
🌈 **Condition:** {data['weather'][0]['description'].title()}
💧 **Humidity:** {data['main']['humidity']}%
💨 **Wind Speed:** {data['wind']['speed']} m/s
"""
            await update.message.reply_text(weather_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Could not fetch weather data")
            
    except Exception as e:
        await update.message.reply_text("❌ Weather service unavailable")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        category = " ".join(context.args) if context.args else "general"
        await update.message.reply_text(f"📰 Getting {category} news...")
        
        url = f"https://newsapi.org/v2/top-headlines?country=in&category={category}&pageSize=5&apiKey={NEWS_API_KEY}"
        response = requests.get(url, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('articles'):
                news_text = f"📢 **Top {category.title()} News:**\n\n"
                for i, article in enumerate(data['articles'][:5], 1):
                    title = article.get('title', 'No title available')
                    title = title.split(' - ')[0]
                    news_text += f"**{i}.** {title}\n\n"
                
                await update.message.reply_text(news_text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ No news articles found")
        else:
            await update.message.reply_text("❌ News service busy")
            
    except Exception as e:
        await update.message.reply_text("❌ News service unavailable")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 **Welcome to Your Smart AI Assistant!**

✨ **Now with MEMORY!** I'll remember our conversation.

🛠 **Commands:**
/start - Welcome message  
/help - All commands guide
/weather [city] - Get weather
/news [category] - Latest news
/clear - Clear conversation memory

💬 **Normal Chat:** Just talk to me! I'll remember everything.

🚀 **Powered by AI with Memory**
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 **Help Guide**

🌤️ **Weather:** `/weather [city]`
📰 **News:** `/news [category]`
🧹 **Clear Memory:** `/clear`
💬 **Chat:** Just type normally!

🎯 **Now I remember our conversations!**
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========== MAIN FUNCTION ==========
def main():
    logger.info("🚀 Starting Bot with MEMORY...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("clear", clear_command))
    
    # Add message handler with MEMORY
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Bot with MEMORY started successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
