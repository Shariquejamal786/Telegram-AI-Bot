import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import logging
from io import BytesIO

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HUGGING_FACE_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

# Log all environment variables (keys hidden for security)
logger.info(f"🔧 Environment Check - TELEGRAM_TOKEN: {'✅' if TELEGRAM_TOKEN else '❌'}")
logger.info(f"🔧 Environment Check - GROQ_API_KEY: {'✅' if GROQ_API_KEY else '❌'}")
logger.info(f"🔧 Environment Check - HUGGING_FACE_TOKEN: {'✅' if HUGGING_FACE_TOKEN else '❌'}")
logger.info(f"🔧 Environment Check - WEATHER_API_KEY: {'✅' if WEATHER_API_KEY else '❌'}")
logger.info(f"🔧 Environment Check - NEWS_API_KEY: {'✅' if NEWS_API_KEY else '❌'}")

# ========== WEATHER FUNCTION WITH DETAILED LOGGING ==========
def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        logger.info(f"🌤️ Weather API Call - City: {city}, URL: {url.split('appid=')[0]}...")
        
        response = requests.get(url, timeout=15)
        logger.info(f"📊 Weather API Response - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            weather_info = {
                'city': data['name'],
                'temp': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'wind': data['wind']['speed']
            }
            logger.info(f"✅ Weather Data: {weather_info}")
            return weather_info
        elif response.status_code == 401:
            logger.error("❌ Weather API Error: Invalid API Key")
            return "invalid_key"
        elif response.status_code == 404:
            logger.error("❌ Weather API Error: City not found")
            return "city_not_found"
        else:
            logger.error(f"❌ Weather API Error: {response.status_code} - {response.text[:100]}")
            return None
            
    except Exception as e:
        logger.error(f"💥 Weather Exception: {str(e)}")
        return None

# ========== NEWS FUNCTION WITH DETAILED LOGGING ==========
def get_news(category="general"):
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=in&category={category}&apiKey={NEWS_API_KEY}"
        logger.info(f"📰 News API Call - Category: {category}")
        
        response = requests.get(url, timeout=15)
        logger.info(f"📊 News API Response - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            articles = data['articles'][:5]
            logger.info(f"✅ News Articles Found: {len(articles)}")
            return articles
        elif response.status_code == 401:
            logger.error("❌ News API Error: Invalid API Key")
            return "invalid_key"
        else:
            logger.error(f"❌ News API Error: {response.status_code} - {response.text[:100]}")
            return None
            
    except Exception as e:
        logger.error(f"💥 News Exception: {str(e)}")
        return None

# ========== MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        logger.info(f"📨 Received: {user_message}")
        
        # WEATHER COMMAND
        if user_message.lower().startswith('/weather'):
            city = user_message[8:].strip()
            if not city:
                await update.message.reply_text("❌ Please specify city\nExample: /weather Delhi")
                return
            
            await update.message.reply_text(f"🌤️ Fetching weather for {city}...")
            weather_data = get_weather(city)
            
            if weather_data == "invalid_key":
                await update.message.reply_text("❌ Weather service configuration error")
            elif weather_data == "city_not_found":
                await update.message.reply_text("❌ City not found. Try: /weather Mumbai")
            elif weather_data:
                weather_text = f"""
🌤️ *Weather in {weather_data['city']}*
• Temperature: {weather_data['temp']}°C
• Condition: {weather_data['description'].title()}
• Humidity: {weather_data['humidity']}%
• Wind: {weather_data['wind']} m/s
"""
                await update.message.reply_text(weather_text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Could not fetch weather data")
            return

        # NEWS COMMAND
        elif user_message.lower().startswith('/news'):
            category = user_message[5:].strip() or "general"
            
            await update.message.reply_text(f"📰 Fetching {category} news...")
            news_data = get_news(category)
            
            if news_data == "invalid_key":
                await update.message.reply_text("❌ News service configuration error")
            elif news_data:
                news_text = f"*📢 Top {category.title()} News:*\n\n"
                for i, article in enumerate(news_data, 1):
                    title = article['title'] or "No title"
                    url = article['url'] or ""
                    news_text += f"{i}. {title}\n"
                    if url:
                        news_text += f"   [Read More]({url})\n\n"
                
                await update.message.reply_text(news_text, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_text("❌ Could not fetch news")
            return

        # REST OF THE CODE SAME AS BEFORE...
        # [Include the previous image generation and AI chat code here]

    except Exception as e:
        logger.error(f"💥 Main Handler Error: {str(e)}")
        await update.message.reply_text("❌ Error occurred. Please try again.")

# [Include all other functions: start_command, help_command, main etc.]
