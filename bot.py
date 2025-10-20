import os
import requests
import asyncio
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import logging
from io import BytesIO
from datetime import datetime, timedelta
import random

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
HUGGING_FACE_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI Initialized")
else:
    logger.warning("❌ Gemini API Key not found")

# Memory Storage
user_sessions = {}

# Fun responses
FUN_RESPONSES = {
    def get_gemini_response(user_message, user_name, conversation_history):
    try:
        if not GEMINI_API_KEY:
            return None
            
        # Prepare conversation context
        context = f"""You are {user_name}'s friendly AI assistant named 'MeraAI'. Respond in Hinglish (Hindi+English mix).

USER PERSONALITY:
- Name: {user_name}
- Conversation style: Friendly, casual
- Language preference: Hinglish

CONVERSATION HISTORY:
{conversation_history}

CURRENT MESSAGE:
{user_name}: {user_message}

RESPONSE GUIDELINES:
- Be conversational and friendly
- Use emojis appropriately  
- Remember context from history
- Keep responses engaging but concise
- Ask follow-up questions sometimes
- Be helpful and positive
- Use Indian cultural references when relevant"""
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(context)
        
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini error: {str(e)}")
        return None

# ========== GEMINI AI FUNCTION ==========

# ========== MEMORY MANAGEMENT ==========
def get_user_session(user_id, user_name):
    current_time = datetime.now()
    
    # Clean old sessions (2 hours)
    for uid in list(user_sessions.keys()):
        if current_time - user_sessions[uid]['last_activity'] > timedelta(hours=2):
            del user_sessions[uid]
    
    # Create new session or update existing
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'history': [],
            'last_activity': current_time,
            'user_name': user_name,
            'message_count': 0,
            'preferred_ai': 'gemini' if GEMINI_API_KEY else 'groq'
        }
        logger.info(f"🎯 New session for {user_name}")
    
    user_sessions[user_id]['last_activity'] = current_time
    user_sessions[user_id]['message_count'] += 1
    
    return user_sessions[user_id]

def add_to_memory(user_id, role, content):
    if user_id in user_sessions:
        user_sessions[user_id]['history'].append({"role": role, "content": content})
        
        # Keep optimal context length
        if len(user_sessions[user_id]['history']) > 8:
            user_sessions[user_id]['history'] = user_sessions[user_id]['history'][-8:]

def get_conversation_history(user_id):
    if user_id in user_sessions:
        history_text = ""
        for msg in user_sessions[user_id]['history'][-6:]:
            role = "You" if msg['role'] == "user" else "AI"
            history_text += f"{role}: {msg['content']}\n"
        return history_text
    return ""

# ========== SMART AI CHAT ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        user_message = update.message.text
        
        # Skip commands
        if user_message.startswith('/'):
            return
        
        logger.info(f"💬 {user_name}: {user_message}")
        
        # Get user session
        session = get_user_session(user_id, user_name)
        add_to_memory(user_id, "user", user_message)
        
        await update.message.chat.send_action(action="typing")
        
        # Try Gemini first if available
        ai_response = None
        ai_source = "Groq"
        
        if session.get('preferred_ai') == 'gemini' and GEMINI_API_KEY:
            conversation_history = get_conversation_history(user_id)
            ai_response = get_gemini_response(user_message, user_name, conversation_history)
            if ai_response:
                ai_source = "Google Gemini 🧠"
        
        # Fallback to Groq
        if not ai_response and GROQ_API_KEY:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = [
                {
                    "role": "system", 
                    "content": f"You are {user_name}'s friendly assistant. Respond in Hinglish. Be conversational and use emojis. Remember context: {get_conversation_history(user_id)}"
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ]
            
            data = {
                "messages": messages,
                "model": "llama-3.1-8b-instant",
                "temperature": 0.8,
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
                ai_source = "Groq AI ⚡"
        
        if ai_response:
            add_to_memory(user_id, "assistant", ai_response)
            
            # Format response
            if len(ai_response) > 400:
                parts = [ai_response[i:i+400] for i in range(0, len(ai_response), 400)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        part += f"\n\n---\n🤖 *Powered by {ai_source}*"
                    await update.message.reply_text(part, parse_mode='Markdown')
                    await asyncio.sleep(0.5)
            else:
                formatted_response = f"{ai_response}\n\n---\n🤖 *Powered by {ai_source}*"
                await update.message.reply_text(formatted_response, parse_mode='Markdown')
                
            logger.info(f"✅ Response from {ai_source}")
        else:
            await update.message.reply_text("❌ All AI services are busy. Try again!")
            
    except Exception as e:
        logger.error(f"💥 Chat error: {str(e)}")
        await update.message.reply_text("❌ Oops! Something went wrong.")

# ========== GEMINI COMMAND ==========
async def gemini_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = " ".join(context.args) if context.args else ""
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        
        if not user_message:
            await update.message.reply_text("""
🧠 **Google Gemini Pro**

Usage: `/gemini your question here`

**Examples:**
• `/gemini explain quantum computing`
• `/gemini write a python code`
• `/gemini how to learn AI`

🚀 **Powered by Google's most advanced AI**
🎯 **High quality responses**
""", parse_mode='Markdown')
            return
        
        if not GEMINI_API_KEY:
            await update.message.reply_text("❌ Gemini service not configured")
            return
        
        await update.message.reply_text("🧠 Gemini is thinking...")
        await update.message.chat.send_action(action="typing")
        
        # Set preference to Gemini
        if user_id in user_sessions:
            user_sessions[user_id]['preferred_ai'] = 'gemini'
        
        conversation_history = get_conversation_history(user_id)
        response_text = get_gemini_response(user_message, user_name, conversation_history)
        
        if response_text:
            add_to_memory(user_id, "user", user_message)
            add_to_memory(user_id, "assistant", response_text)
            
            formatted_response = f"""
🧠 **Google Gemini:**

{response_text}

---
🔷 *Powered by Google Gemini Pro*
🎯 *Advanced AI Technology*
"""
            await update.message.reply_text(formatted_response, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Gemini service busy. Try `/ai` command.")
            
    except Exception as e:
        logger.error(f"Gemini command error: {str(e)}")
        await update.message.reply_text("❌ Gemini service error")

# ========== AI COMMAND (GROQ) ==========
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = " ".join(context.args) if context.args else ""
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        
        if not user_message:
            await update.message.reply_text("""
⚡ **Groq AI Chat**

Usage: `/ai your message here`

**Examples:**
• `/ai hello how are you`
• `/ai tell me a joke`
• `/ai explain something`

🚀 **Powered by Groq - Ultra Fast**
🎯 **Free & Reliable**
""", parse_mode='Markdown')
            return
        
        if not GROQ_API_KEY:
            await update.message.reply_text("❌ AI service not available")
            return
        
        await update.message.reply_text("⚡ AI is thinking...")
        
        # Set preference to Groq
        if user_id in user_sessions:
            user_sessions[user_id]['preferred_ai'] = 'groq'
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a friendly AI assistant. Respond in Hinglish with emojis. Be helpful and engaging."
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
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
            
            add_to_memory(user_id, "user", user_message)
            add_to_memory(user_id, "assistant", ai_response)
            
            formatted_response = f"""
⚡ **Groq AI:**

{ai_response}

---
⚡ *Powered by Groq - Ultra Fast*
🎯 *Free AI Service*
"""
            await update.message.reply_text(formatted_response, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ AI service busy")
            
    except Exception as e:
        logger.error(f"AI command error: {str(e)}")
        await update.message.reply_text("❌ AI service error")

# ========== WEATHER COMMAND ==========
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        city = " ".join(context.args) if context.args else "Mumbai"
        
        await update.message.reply_text(f"🌤️ Checking weather for {city}...")
        await update.message.chat.send_action(action="typing")
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            weather_emoji = "🌤️"
            main_weather = data['weather'][0]['main'].lower()
            if 'rain' in main_weather:
                weather_emoji = "🌧️"
            elif 'cloud' in main_weather:
                weather_emoji = "☁️"
            elif 'clear' in main_weather:
                weather_emoji = "☀️"
            
            weather_text = f"""
{weather_emoji} **Weather in {data['name']}**

📊 **Temperature:** {data['main']['temp']}°C
🌡️ **Feels Like:** {data['main']['feels_like']}°C
🌈 **Condition:** {data['weather'][0]['description'].title()}
💧 **Humidity:** {data['main']['humidity']}%
💨 **Wind Speed:** {data['wind']['speed']} m/s
"""
            temp = data['main']['temp']
            if temp > 35:
                weather_text += "\n🥵 Bahut garmi hai! Thanda paani piyo! 🥤"
            elif temp < 10:
                weather_text += "\n🥶 Thand hai! Garam kapde pehno! 🧣"
            else:
                weather_text += "\n😎 Mausam mast hai! Bahar ghumne ka plan banao! 🚶‍♂️"
            
            await update.message.reply_text(weather_text, parse_mode='Markdown')
            
        else:
            await update.message.reply_text(f"❌ Could not find weather for '{city}'\n\nTry: /weather Mumbai")
            
    except Exception as e:
        await update.message.reply_text("❌ Weather service unavailable")

# ========== NEWS COMMAND ==========
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        category = " ".join(context.args) if context.args else "general"
        valid_categories = ['general', 'technology', 'sports', 'business', 'entertainment', 'science', 'health']
        
        if category.lower() not in valid_categories:
            category = "general"
        
        await update.message.reply_text(f"📡 Fetching {category} news...")
        await update.message.chat.send_action(action="typing")
        
        url = f"https://newsapi.org/v2/top-headlines?country=in&category={category}&pageSize=5&apiKey={NEWS_API_KEY}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('articles'):
                news_text = f"📢 **Top {category.title()} News:**\n\n"
                
                for i, article in enumerate(data['articles'][:5], 1):
                    title = article.get('title', 'No title available').split(' - ')[0]
                    source = article.get('source', {}).get('name', 'Unknown')
                    
                    if title and title != '[Removed]':
                        news_text += f"**{i}.** {title}\n"
                        news_text += f"   _📰 Source: {source}_\n\n"
                
                if len(news_text) > 100:
                    news_text += "🌐 _Stay updated with latest news!_"
                    await update.message.reply_text(news_text, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"📰 No recent news in {category}\n\nTry: /news technology")
            else:
                await update.message.reply_text(f"📰 No articles in {category}\n\nTry: /news sports")
        else:
            await update.message.reply_text("❌ News service busy\n\nTry again in 2 minutes! ⏰")
            
    except Exception as e:
        await update.message.reply_text("❌ News service temporarily down")

# ========== START COMMAND ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    gemini_status = "✅ Available" if GEMINI_API_KEY else "❌ Not configured"
    
    welcome_text = f"""
🎉 **Hello {user_name}!** 

🤖 **I'm MeraAI - Now with Google Gemini!**

✨ **AI Options:**
• 🧠 `/gemini` - Google Gemini (High Quality)
• ⚡ `/ai` - Groq AI (Ultra Fast)  
• 💬 Normal chat - Auto smart selection

🛠 **Other Features:**
• 🌤️ Weather updates
• 📰 Latest news  
• 🧠 Conversation memory
• 😊 Friendly personality

🔧 **Commands:**
/start - This message
/help - Full guide
/weather [city] - Weather
/news [category] - News
/gemini [question] - Gemini AI
/ai [message] - Groq AI
/clear - Clear memory

🚀 **Gemini Status:** {gemini_status}

**Let's chat! I'll remember our conversation!** 😊
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# ========== HELP COMMAND ==========
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 **MeraAI Help Guide**

🎯 **AI Chat Options:**
• **Normal Chat** - I automatically choose best AI
• **/gemini** - Google Gemini (Highest quality)
• **/ai** - Groq AI (Fastest responses)

📝 **All Commands:**
/start - Welcome message
/help - This guide
/weather [city] - Weather
/news [category] - News
/gemini [question] - Gemini AI
/ai [message] - Groq AI
/clear - Clear memory
/stats - Conversation stats

🌐 **News Categories:**
technology, sports, business, entertainment, science, health, general

💡 **Pro Tip:** Use `/gemini` for complex questions and `/ai` for quick chats!

🚀 **Now with dual AI power!**
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========== CLEAR MEMORY COMMAND ==========
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text(f"🧹 **Memory cleared!**\n\nHey {user_name}! Fresh start! 😊\n\nWhat would you like to talk about?")
    else:
        await update.message.reply_text("ℹ️ No active conversation to clear.\n\nLet's start chatting! 💬")

# ========== STATS COMMAND ==========
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    
    if user_id in user_sessions:
        session = user_sessions[user_id]
        message_count = session.get('message_count', 0)
        preferred_ai = session.get('preferred_ai', 'gemini').upper()
        
        stats_text = f"""
📊 **Your Conversation Stats**

👤 **User:** {user_name}
💬 **Messages exchanged:** {message_count}
🧠 **Preferred AI:** {preferred_ai}
🕒 **Active since:** {session['last_activity'].strftime('%I:%M %p')}

🎯 **Keep chatting! I'm learning more about you!**
"""
    else:
        stats_text = f"""
📊 **Your Conversation Stats**

👤 **User:** {user_name}
💬 **Messages exchanged:** 0
🧠 **Memory:** Not started

💡 **Start chatting to build our conversation memory!**
"""
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# ========== MAIN FUNCTION ==========
def main():
    logger.info("🚀 Starting MeraAI with Google Gemini...")
    
    # Log AI status
    if GEMINI_API_KEY:
        logger.info("✅ Gemini AI: Available")
    else:
        logger.warning("❌ Gemini AI: Not configured")
    
    if GROQ_API_KEY:
        logger.info("✅ Groq AI: Available")
    else:
        logger.warning("❌ Groq AI: Not configured")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("gemini", gemini_command))
    application.add_handler(CommandHandler("ai", ai_command))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 MeraAI with Gemini started successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
