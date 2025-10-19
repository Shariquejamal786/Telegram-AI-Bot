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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
HUGGING_FACE_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")

# ========== IMAGE GENERATION ==========
def generate_image(prompt):
    try:
        # Try multiple models for better success rate
        models = [
            "black-forest-labs/FLUX.1-schnell",  # Fast model
            "stabilityai/stable-diffusion-2-1",  # Reliable model
            "runwayml/stable-diffusion-v1-5"     # Original model
        ]
        
        for model in models:
            try:
                API_URL = f"https://api-inference.huggingface.co/models/{model}"
                headers = {"Authorization": f"Bearer {HUGGING_FACE_TOKEN}"}
                
                logger.info(f"🖼️ Trying model: {model}")
                response = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=60)
                
                if response.status_code == 200:
                    logger.info(f"✅ Image generated with {model}")
                    return response.content
                elif response.status_code == 503:
                    logger.info(f"🔄 Model {model} is loading, trying next...")
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Model {model} failed: {str(e)}")
                continue
        
        logger.error("❌ All image models failed")
        return None
        
    except Exception as e:
        logger.error(f"💥 Image generation error: {str(e)}")
        return None

# ========== WEATHER COMMAND ==========
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
🌡️ **Feels Like:** {data['main']['feels_like']}°C
"""
            await update.message.reply_text(weather_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Could not fetch weather data")
            
    except Exception as e:
        await update.message.reply_text("❌ Weather service unavailable")

# ========== NEWS COMMAND ==========
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        category = " ".join(context.args) if context.args else "general"
        await update.message.reply_text(f"📡 Fetching latest {category} news...")
        
        # NewsAPI URL with proper parameters
        # Alternative endpoint
url = f"https://newsapi.org/v2/everything?q=technology&sortBy=publishedAt&language=en&pageSize=5&apiKey={NEWS_API_KEY}"
        
        logger.info(f"🌐 Calling NewsAPI for: {category}")
        response = requests.get(url, timeout=20)
        
        logger.info(f"📊 NewsAPI Status: {response.status_code}")
        logger.info(f"📄 Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            total_articles = data.get('totalResults', 0)
            articles = data.get('articles', [])
            
            logger.info(f"📰 Found {total_articles} total articles, {len(articles)} returned")
            
            if articles:
                news_text = f"📢 **Latest {category.title()} News:**\n\n"
                valid_articles = 0
                
                for i, article in enumerate(articles, 1):
                    title = article.get('title', '').strip()
                    source = article.get('source', {}).get('name', 'Unknown')
                    
                    # Filter out invalid titles
                    if (title and 
                        title != '[Removed]' and 
                        len(title) > 10 and
                        not title.startswith('[')):
                        
                        news_text += f"**{i}.** {title}\n"
                        news_text += f"   _Source: {source}_\n\n"
                        valid_articles += 1
                    
                    if valid_articles >= 5:  # Max 5 articles
                        break
                
                if valid_articles > 0:
                    news_text += f"📰 _Real-time news via NewsAPI_"
                    await update.message.reply_text(news_text, parse_mode='Markdown')
                else:
                    await update.message.reply_text("""📰 **No valid news articles**

All articles were filtered as invalid.
Try: `/news technology` or `/news sports`
""", parse_mode='Markdown')
            else:
                await update.message.reply_text("""📰 **No Articles Available**

**Possible Reasons:**
• No recent news in this category
• Try popular categories:
  `/news general`
  `/news technology` 
  `/news sports`
  `/news business`

• Or try again in some time
""", parse_mode='Markdown')
                
        elif response.status_code == 401:
            await update.message.reply_text("""🔐 **NewsAPI Key Invalid**

Your NewsAPI key may be:
• Invalid or expired
• Not activated
• Missing verification

Check your NewsAPI account.
""")
        elif response.status_code == 429:
            await update.message.reply_text("""📊 **Daily Limit Reached**

NewsAPI free tier limit reached.
Will reset at midnight UTC.

Try again tomorrow! 🌙
""")
        else:
            await update.message.reply_text(f"❌ NewsAPI Error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        await update.message.reply_text("⏰ News service timeout")
    except Exception as e:
        logger.error(f"💥 News error: {str(e)}")
        await update.message.reply_text("❌ News service error")

# ========== IMAGE COMMAND ==========
async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prompt = " ".join(context.args) if context.args else ""
        
        if not prompt:
            await update.message.reply_text("""
🖼️ **Image Generation Help**

Usage: `/image your description here`

**Examples:**
• `/image a beautiful sunset`
• `/image a cute cartoon cat`
• `/image futuristic city landscape`
• `/image peaceful mountain view`

🎨 **Be creative with your descriptions!**
""", parse_mode='Markdown')
            return
        
        await update.message.reply_text(f"🎨 Generating image: *{prompt}*", parse_mode='Markdown')
        
        # Generate image
        image_data = generate_image(prompt)
        
        if image_data:
            # Send image to Telegram
            await update.message.reply_photo(
                photo=BytesIO(image_data), 
                caption=f"🖼️ **{prompt}**\n\n✨ Generated by AI",
                parse_mode='Markdown'
            )
            logger.info("✅ Image sent successfully")
        else:
            await update.message.reply_text("""
❌ **Image Generation Failed**

**Possible Reasons:**
• AI models are currently busy
• Try a simpler description
• Wait 1 minute and try again
• Use common objects/animals

🔄 **Try these examples:**
`/image sunset`
`/image cat`
`/image flower`
""", parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"💥 Image command error: {str(e)}")
        await update.message.reply_text("❌ Error generating image. Please try again.")

# ========== AI CHAT HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        
        # Skip if it's a command
        if user_message.startswith('/'):
            return
            
        logger.info(f"💬 AI Chat: {user_message}")
        
        if not GROQ_API_KEY:
            await update.message.reply_text("❌ AI service unavailable")
            return
        
        # Groq AI API call
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
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        ))
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            await update.message.reply_text(f"🤖 {ai_response}")
        else:
            await update.message.reply_text("❌ AI service busy. Please try again.")
            
    except Exception as e:
        logger.error(f"💥 AI Chat error: {str(e)}")
        await update.message.reply_text("❌ Error processing your message.")

# ========== START & HELP COMMANDS ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 **Welcome to Your Super AI Assistant!**

✨ **Available Commands:**

🌤️ `/weather [city]` - Get weather updates
📰 `/news [category]` - Latest news headlines  
🖼️ `/image [description]` - Generate AI images
ℹ️ `/help` - Show all commands

🎯 **Examples:**
• `/weather Delhi`
• `/news technology` 
• `/image beautiful sunset`

💬 **Normal Chat:** Just type your message!

🚀 **Powered by Advanced AI Technology**
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 **Help Guide - All Commands**

🌤️ **Weather Updates:**
`/weather [city]`
Example: `/weather Mumbai`

📰 **News Updates:**
`/news [category]`  
Categories: general, business, sports, technology, entertainment

🖼️ **Image Generation:**
`/image [description]`
Example: `/image futuristic city`

💬 **AI Chat:**
Just type normal messages!

🔧 **Need Help?**
Try simpler descriptions for images
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========== MAIN FUNCTION ==========
def main():
    logger.info("🚀 Starting Super Bot with All Features...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("image", image_command))
    
    # Add message handler for AI chat
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Bot started successfully with all features!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
