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
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🎯 WEATHER COMMAND CALLED!")
    try:
        city = " ".join(context.args) if context.args else "Mumbai"
        await update.message.reply_text(f"🌤️ Checking weather for {city}...")
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        
        logger.info(f"Weather API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            weather_text = f"""
🌤️ *Weather in {data['name']}*
• Temperature: {data['main']['temp']}°C
• Condition: {data['weather'][0]['description'].title()}
• Humidity: {data['main']['humidity']}%
• Wind: {data['wind']['speed']} m/s
"""
            await update.message.reply_text(weather_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Weather error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Weather error: {str(e)}")
        await update.message.reply_text("❌ Weather service unavailable")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🎯 NEWS COMMAND CALLED!")
    try:
        category = " ".join(context.args) if context.args else "general"
        await update.message.reply_text(f"📰 Getting {category} news...")
        
        url = f"https://newsapi.org/v2/top-headlines?country=in&category={category}&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        
        logger.info(f"News API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            news_text = f"*📢 Top {category.title()} News:*\n\n"
            for i, article in enumerate(data['articles'][:5], 1):
                news_text += f"{i}. {article['title']}\n\n"
            
            await update.message.reply_text(news_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ News error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"News error: {str(e)}")
        await update.message.reply_text("❌ News service unavailable")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🎯 START COMMAND CALLED!")
    welcome_text = """
🤖 *Welcome to Your AI Assistant!*

*Commands:*
/weather [city] - Get weather
/news [category] - Latest news
/help - Show help

*Examples:*
/weather Mumbai
/news technology
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🎯 HELP COMMAND CALLED!")
    await update.message.reply_text("Help message here")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🎯 MESSAGE HANDLER CALLED!")
    user_message = update.message.text
    await update.message.reply_text(f"📨 You said: {user_message}")

def main():
    logger.info("🚀 Starting Simple Bot...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("news", news_command))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Bot started successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
