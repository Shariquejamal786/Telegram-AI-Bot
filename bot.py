import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import logging
from io import BytesIO
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HUGGING_FACE_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

# ========== WEATHER FUNCTION ==========
def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            weather_info = {
                'city': data['name'],
                'temp': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'wind': data['wind']['speed']
            }
            return weather_info
        else:
            return None
    except Exception as e:
        logger.error(f"Weather API error: {str(e)}")
        return None

# ========== NEWS FUNCTION ==========
def get_news(category="general"):
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=in&category={category}&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            articles = data['articles'][:5]  # Top 5 news
            return articles
        else:
            return None
    except Exception as e:
        logger.error(f"News API error: {str(e)}")
        return None

# ========== IMAGE GENERATION ==========
def generate_image(prompt):
    try:
        API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {HUGGING_FACE_TOKEN}"}
        
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Image generation failed: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        return None

# ========== GROQ AI CHAT ==========
def make_groq_request(user_message):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [{"role": "user", "content": user_message}],
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
            return ai_response
        else:
            logger.error(f"Groq Error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Groq Request Error: {str(e)}")
        return None

# ========== MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        logger.info(f"📨 Received: {user_message}")
        
        # ========== IMAGE GENERATION ==========
        if user_message.lower().startswith('/image'):
            prompt = user_message[6:].strip()
            if not prompt:
                await update.message.reply_text("❌ Please provide image description\nExample: /image sunset")
                return
            
            await update.message.reply_text("🖼️ Generating image...")
            image_data = generate_image(prompt)
            
            if image_data:
                await update.message.reply_photo(photo=BytesIO(image_data), caption=f"🖼️ {prompt}")
            else:
                await update.message.reply_text("❌ Failed to generate image")
            return

        # ========== WEATHER COMMAND ==========
        elif user_message.lower().startswith('/weather'):
            city = user_message[8:].strip()
            if not city:
                await update.message.reply_text("❌ Please specify city\nExample: /weather Delhi")
                return
            
            weather_data = get_weather(city)
            if weather_data:
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

        # ========== NEWS COMMAND ==========
        elif user_message.lower().startswith('/news'):
            category = user_message[5:].strip() or "general"
            valid_categories = ['general', 'business', 'sports', 'technology', 'entertainment']
            
            if category not in valid_categories:
                category = "general"
            
            await update.message.reply_text(f"📰 Fetching {category} news...")
            news_data = get_news(category)
            
            if news_data:
                news_text = f"*📢 Top {category.title()} News:*\n\n"
                for i, article in enumerate(news_data, 1):
                    news_text += f"{i}. {article['title']}\n"
                    if article['url']:
                        news_text += f"   [Read More]({article['url']})\n\n"
                
                await update.message.reply_text(news_text, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_text("❌ Could not fetch news")
            return

        # ========== NORMAL AI CHAT ==========
        else:
            if not GROQ_API_KEY:
                await update.message.reply_text("❌ AI service unavailable")
                return
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, make_groq_request, user_message)
            
            if response:
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("❌ Technical issue. Please try again.")
            
    except Exception as e:
        logger.error(f"💥 Error: {str(e)}")
        await update.message.reply_text("❌ Error occurred. Please try again.")

# ========== COMMAND HANDLERS ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 *Welcome to Your Super AI Assistant!*

*Available Commands:*
/image [description] - Generate AI images
/weather [city] - Get weather updates  
/news [category] - Latest news headlines
/help - Show all commands

*Examples:*
• `/image beautiful sunset`
• `/weather Delhi`
• `/news technology`

Ask anything else for AI chat! 🚀
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Help Guide - All Commands*

*Image Generation:*
`/image [description]`
Example: `/image futuristic city`

*Weather Updates:*
`/weather [city]` 
Example: `/weather Mumbai`

*News Updates:*
`/news [category]`
Categories: general, business, sports, technology, entertainment

*AI Chat:*
Just type normal messages!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========== MAIN FUNCTION ==========
def main():
    logger.info("🚀 Starting Super Bot with All Features...")
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN missing!")
        return
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("image", handle_message))
        application.add_handler(CommandHandler("weather", handle_message))
        application.add_handler(CommandHandler("news", handle_message))
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"💥 Failed to start: {str(e)}")

if __name__ == "__main__":
    main()
